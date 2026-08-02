"""Single-process entry point for the message notification routing pipeline.

Runs DataLoader → Context → Features → Understanding → Assessment → Evidence →
Decision → OutputGenerator and writes the validated submission CSV.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Union

# Ensure repo root is importable when invoked as ``python main.py`` from code/.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(_REPO_ROOT / ".env", override=False)

from code.assessment.assessment_engine import AssessmentEngine as MessageAssessmentEngine
from code.context.context_builder import ContextBuilder
from code.decision.decision_engine import DecisionEngine
from code.decision.models import DecisionResult
from code.evidence.models import EvidenceResult
from code.evidence.retrieval_engine import RetrievalEngine as EvidenceRetrievalEngine
from code.features.extractor import FeatureExtractor
from code.loader.data_loader import DataLoader
from code.output.generator import OutputGenerator, OutputRow
from code.understanding.models import UnderstandingResult
from code.understanding.understanding_engine import UnderstandingEngine


logger = logging.getLogger(__name__)
_DEFAULT_DATA_DIR = _REPO_ROOT / "dataset"


def run_pipeline(data_dir: Union[str, Path, None] = None) -> List[DecisionResult]:
    """Run the complete routing pipeline for every message in ``messages.csv``.

    Individual message failures are logged and replaced with a safe fallback row
    so the submission still covers every input message_id. Dataset-loading
    failures are re-raised because no meaningful pipeline run can proceed
    without the source data.
    """
    dataset_path = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR
    if not dataset_path.is_absolute() and not dataset_path.exists():
        candidate = _REPO_ROOT / dataset_path
        if candidate.exists():
            dataset_path = candidate

    loader = DataLoader()

    try:
        loader.load_all(str(dataset_path))
    except Exception:
        logger.exception("Unable to load dataset from %s", dataset_path)
        raise

    if loader._messages is None or loader._messages.empty:
        logger.warning("No messages found in %s", dataset_path / "messages.csv")
        return []

    context_builder = ContextBuilder(loader)
    feature_extractor = FeatureExtractor()
    understanding_engine = UnderstandingEngine()
    assessment_engine = MessageAssessmentEngine()
    evidence_engine = EvidenceRetrievalEngine(loader)
    decision_engine = DecisionEngine()

    decisions: List[DecisionResult] = []
    output_rows: List[OutputRow] = []
    output_generator = OutputGenerator()
    message_ids = loader._messages["message_id"].tolist()
    logger.info("Processing %d messages from %s", len(message_ids), dataset_path)

    for idx, message_id in enumerate(message_ids, start=1):
        try:
            logger.info("Processing message %d/%d id=%s", idx, len(message_ids), message_id)
            context = context_builder.build_context(message_id)
            features = feature_extractor.extract(context)
            understanding = understanding_engine.analyze(context)
            assessment = assessment_engine.evaluate(context, understanding, features)
            evidence = evidence_engine.retrieve(context, assessment, understanding)
            decision = decision_engine.decide(
                features, understanding, assessment, evidence
            )
            decisions.append(decision)
            output_rows.append(
                output_generator.build_row(
                    message_id, decision, understanding, evidence
                )
            )
        except Exception:
            logger.exception("Pipeline failed for message_id=%s", message_id)
            fallback_decision, fallback_understanding, fallback_evidence = (
                _fallback_outputs(str(message_id))
            )
            decisions.append(fallback_decision)
            output_rows.append(
                output_generator.build_row(
                    message_id,
                    fallback_decision,
                    fallback_understanding,
                    fallback_evidence,
                )
            )

    output_path = dataset_path / "output.csv"
    try:
        output_generator.write(output_rows, output_path, expected_message_ids=message_ids)
    except Exception:
        logger.exception("Unable to validate and write output to %s", output_path)
        raise

    logger.info(
        "Pipeline completed: %d/%d messages produced decisions",
        len(decisions),
        len(message_ids),
    )
    logger.info("Wrote validated output to %s", output_path)
    return decisions


def _fallback_outputs(message_id: str) -> tuple[DecisionResult, UnderstandingResult, EvidenceResult]:
    """Build a schema-valid fallback decision when a single message crashes."""
    decision = DecisionResult(
        action="digest",
        reason=f"Pipeline error for {message_id}; defaulting to digest.",
        confidence=0.0,
        decision_trace=["pipeline_fallback"],
    )
    understanding = UnderstandingResult(
        summary="Pipeline fallback",
        intent="general",
        message_type="unknown",
        urgency="low",
        entities=[],
        requires_attention=False,
        promotion_detected=False,
        payment_detected=False,
        event_detected=False,
        contains_media=False,
        processing_status="pipeline_fallback",
    )
    evidence = EvidenceResult(
        top_evidence=[],
        retrieval_summary="No evidence available due to pipeline failure.",
        retrieval_status="pipeline_fallback",
    )
    return decision, understanding, evidence


def main() -> None:
    """Run the pipeline and write the validated submission CSV."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    decisions = run_pipeline()
    logger.info("Returned %d DecisionResult objects", len(decisions))


if __name__ == "__main__":
    main()
