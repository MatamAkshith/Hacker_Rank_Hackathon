"""EvidenceSelector: Slices the top-K ranked candidates, generates a human-readable
reason for each selection, and maps them to the strict EvidenceItem schema.

Reason generation is purely descriptive — it explains WHY the candidate was
retrieved/matched, never whether the incoming message should be notified or muted.

Reason templates are assembled from three axes:
  1. Identity signal   — who sent / which channel
  2. Semantic signal   — what kind of content matched
  3. Engagement signal — how the user previously responded
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from code.evidence.models import EvidenceItem

Candidate = Dict[str, Any]


class EvidenceSelector:
    """Selects the top-K evidence items and maps them to the EvidenceItem schema."""

    # Minimum similarity_score for a candidate to be included in top_evidence.
    # Candidates below this threshold are noise and should be excluded even if
    # they rank within top-K by position.
    _MIN_SCORE_THRESHOLD: float = 0.05

    def select_top(self, ranked_candidates: List[Candidate], k: int = 3) -> List[EvidenceItem]:
        """Select the top-K candidates and convert them to EvidenceItems.

        Args:
            ranked_candidates: Ranked list of candidate dicts from SimilarityRanker,
                               sorted descending by similarity_score.
            k:                 Maximum number of evidence items to return. Default 3.

        Returns:
            A list of at most k EvidenceItem objects with populated reason and
            matched_features fields.  Returns an empty list if ranked_candidates
            is empty or all candidates fall below _MIN_SCORE_THRESHOLD.
        """
        if not ranked_candidates:
            return []

        # Filter below noise threshold, then slice top-k
        eligible = [
            c for c in ranked_candidates
            if c.get("similarity_score", 0.0) >= self._MIN_SCORE_THRESHOLD
        ]
        top_k = eligible[:k]

        return [self._to_evidence_item(cand) for cand in top_k]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _to_evidence_item(self, cand: Candidate) -> EvidenceItem:
        """Convert a scored/ranked candidate dict into an EvidenceItem."""
        msg_id          = str(cand.get("message_id", "unknown"))
        similarity      = float(cand.get("similarity_score", 0.0))
        matched_feats   = list(cand.get("matched_features", []))
        retrieval_srcs  = list(cand.get("_retrieval_sources", []))

        reason = self._build_reason(cand, matched_feats, retrieval_srcs)

        # Determine user_action: ignored, opened, muted (None when unknown)
        user_action = None
        if cand.get("message_reported") or "engagement:message_reported" in matched_feats:
            user_action = "muted"
        elif cand.get("muted_after_message"):
            user_action = "muted"
        elif cand.get("message_replied") or "engagement:user_replied" in matched_feats:
            user_action = "opened"
        elif cand.get("message_opened") or "engagement:user_opened" in matched_feats:
            user_action = "opened"
        elif cand.get("notification_dismissed") or "engagement:notification_dismissed" in matched_feats:
            user_action = "ignored"

        return EvidenceItem(
            message_id=msg_id,
            similarity_score=similarity,
            reason=reason,
            matched_features=matched_feats,
            user_action=user_action,
        )

    def _build_reason(
        self,
        cand: Candidate,
        features: List[str],
        sources: List[str],
    ) -> str:
        """Dynamically build a human-readable reason string from matched signals.

        The reason is structured as:
          "<identity phrase> that <content phrase>[, <engagement phrase>]."

        Examples:
          "Prior message from the same verified bank that also contained payment details,
           previously opened by the user."
          "Earlier group message from the same sender that matched promotional content."
          "Historical personal message with similar keyword content."
        """
        identity_phrase  = self._identity_phrase(cand, features, sources)
        content_phrase   = self._content_phrase(features)
        engagement_phrase = self._engagement_phrase(features)

        parts = [identity_phrase]
        if content_phrase:
            parts.append(f"that {content_phrase}")
        if engagement_phrase:
            parts.append(engagement_phrase)

        return " ".join(parts).strip().rstrip(",") + "."

    # ── Phrase builders ───────────────────────────────────────────────────────

    def _identity_phrase(
        self,
        cand: Candidate,
        features: List[str],
        sources: List[str],
    ) -> str:
        """Describe the identity relationship between the candidate and the current message."""
        conv_type   = str(cand.get("conversation_type", "")).lower()
        business_id = cand.get("business_id") or ""
        sender_id   = cand.get("sender_user_id") or ""
        group_id    = cand.get("group_id") or ""

        has_biz    = "identity:same_business" in features or "same_business" in sources
        has_sender = "identity:same_sender"   in features or "same_sender"   in sources
        has_group  = "identity:same_group"    in features or "same_group"    in sources

        if has_biz and conv_type == "business":
            return "Prior message from the same business account"
        if has_biz:
            return "Earlier message from the same business sender"
        if has_sender and conv_type == "personal":
            return "Previous personal message from the same contact"
        if has_sender and has_group:
            return "Earlier group message from the same member"
        if has_sender:
            return "Previous message from the same sender"
        if has_group:
            return "Earlier message in the same group chat"
        if conv_type == "business":
            return "Historical business message with matching conversation type"
        if conv_type == "group":
            return "Historical group message with matching conversation type"
        return "Historical personal message with similar metadata"

    def _content_phrase(self, features: List[str]) -> str:
        """Describe the semantic content overlap."""
        parts: List[str] = []

        if "semantic:payment_match" in features:
            parts.append("contained payment or transaction details")
        if "semantic:urgency_match" in features:
            parts.append("carried a similar urgency level")
        if "semantic:promotion_match" in features:
            parts.append("matched promotional content")
        if "semantic:event_match" in features:
            parts.append("referenced a similar event or schedule")
        if "text:keyword_overlap" in features and not parts:
            parts.append("shared similar keyword content")
        if "structural:conv_type_match" in features and not parts:
            parts.append("shared the same conversation channel type")

        if len(parts) == 0:
            return ""
        if len(parts) == 1:
            return parts[0]
        return ", ".join(parts[:-1]) + " and " + parts[-1]

    def _engagement_phrase(self, features: List[str]) -> str:
        """Describe how the user previously responded to this candidate."""
        if "engagement:user_replied" in features:
            return "previously replied to by the user"
        if "engagement:user_opened" in features:
            return "previously opened by the user"
        if "engagement:notification_dismissed" in features:
            return "notification previously dismissed by the user"
        return ""
