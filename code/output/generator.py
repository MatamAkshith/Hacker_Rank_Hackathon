"""Create and validate submission rows from pipeline results."""

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

from code.decision.models import DecisionResult
from code.evidence.models import EvidenceResult
from code.understanding.models import UnderstandingResult


OUTPUT_COLUMNS = (
    "message_id",
    "action",
    "message_type",
    "reason",
    "confidence",
    "evidence_message_ids",
)
VALID_ACTIONS = {"notify", "digest", "mute"}
VALID_MESSAGE_TYPES = {
    "personal",
    "urgent",
    "event",
    "payment",
    "business_update",
    "promotion",
    "greeting",
    "forward",
    "spam",
    "scam",
    "unknown",
}
MESSAGE_TYPE_ALIASES = {
    "promotional": "promotion",
    "transactional": "business_update",
}


@dataclass(frozen=True)
class OutputRow:
    """One fully validated row in the submission schema."""

    message_id: str
    action: str
    message_type: str
    reason: str
    confidence: float
    evidence_message_ids: str


class OutputGenerator:
    """Transforms decision, understanding, and evidence results into CSV rows."""

    def build_row(
        self,
        message_id: str,
        decision: DecisionResult,
        understanding: UnderstandingResult,
        evidence: EvidenceResult,
    ) -> OutputRow:
        """Build a submission row for one processed message."""
        is_scam = False
        is_spam = False

        if decision.decision_trace:
            for t in decision.decision_trace:
                if "scam_prevention" in t:
                    is_scam = True
                elif "spam_prevention" in t:
                    is_spam = True

        if "High probability of scam" in decision.reason:
            is_scam = True

        if is_scam:
            msg_type = "scam"
        elif is_spam:
            msg_type = "spam"
        else:
            msg_type = self._normalize_message_type(understanding)

        return OutputRow(
            message_id=str(message_id),
            action=decision.action,
            message_type=msg_type,
            reason=decision.reason,
            confidence=float(decision.confidence),
            evidence_message_ids=self._serialize_evidence(evidence),
        )

    def write(
        self,
        rows: Sequence[OutputRow],
        output_path: Union[str, Path],
        expected_message_ids: Optional[Iterable[str]] = None,
    ) -> None:
        """Validate rows and write the exact submission schema to ``output_path``."""
        self.validate(rows, expected_message_ids)

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=OUTPUT_COLUMNS,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(asdict(row) for row in rows)

    def validate(
        self,
        rows: Sequence[OutputRow],
        expected_message_ids: Optional[Iterable[str]] = None,
    ) -> None:
        """Raise ``ValueError`` when any submission contract check fails."""
        message_ids = []
        for row in rows:
            values = asdict(row)
            missing = [key for key, value in values.items() if self._is_missing(value)]
            if missing:
                raise ValueError(f"Output row has missing values for {row.message_id}: {missing}")
            if row.action not in VALID_ACTIONS:
                raise ValueError(f"Invalid action for {row.message_id}: {row.action}")
            if row.message_type not in VALID_MESSAGE_TYPES:
                raise ValueError(f"Invalid message_type for {row.message_id}: {row.message_type}")
            if not math.isfinite(row.confidence) or not 0.0 <= row.confidence <= 1.0:
                raise ValueError(f"Confidence must be in [0, 1] for {row.message_id}")
            if row.evidence_message_ids != "none":
                evidence_ids = row.evidence_message_ids.split(";")
                if any(not evidence_id.strip() for evidence_id in evidence_ids):
                    raise ValueError(f"Invalid evidence IDs for {row.message_id}")
            message_ids.append(row.message_id)

        if len(message_ids) != len(set(message_ids)):
            raise ValueError("Output contains duplicate message_id values")

        if expected_message_ids is not None:
            expected = [str(message_id) for message_id in expected_message_ids]
            if set(message_ids) != set(expected) or len(message_ids) != len(expected):
                raise ValueError("Output rows do not exactly match input message IDs")

    @staticmethod
    def _normalize_message_type(understanding: UnderstandingResult) -> str:
        """Map understanding output to the fixed submission vocabulary."""
        raw_type = (understanding.message_type or "").strip().lower()
        if raw_type in VALID_MESSAGE_TYPES:
            return raw_type
        if raw_type in MESSAGE_TYPE_ALIASES:
            if raw_type == "transactional" and understanding.payment_detected:
                return "payment"
            return MESSAGE_TYPE_ALIASES[raw_type]
        if understanding.promotion_detected:
            return "promotion"
        if understanding.payment_detected:
            return "payment"
        if understanding.event_detected:
            return "event"
        return "unknown"

    @staticmethod
    def _serialize_evidence(evidence: EvidenceResult) -> str:
        """Return de-duplicated evidence IDs separated by semicolons, or ``none``."""
        evidence_ids = []
        for item in evidence.top_evidence:
            if item.message_id and item.message_id not in evidence_ids:
                evidence_ids.append(item.message_id)
        return ";".join(evidence_ids) if evidence_ids else "none"

    @staticmethod
    def _is_missing(value: object) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())
