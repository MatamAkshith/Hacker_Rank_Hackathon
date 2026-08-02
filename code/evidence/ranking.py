"""SimilarityRanker: Scores each candidate historical message against the
current incoming message using a weighted multi-signal algorithm.

Scoring Dimensions (weights sum to 1.0):
  1. identity_match    (0.30) — same sender / business / group as the incoming message
  2. semantic_overlap  (0.30) — boolean semantic flag overlap (urgency, payment, promo, event)
  3. structural_match  (0.15) — conversation type, media type, forwarding pattern
  4. text_similarity   (0.15) — lightweight Jaccard overlap on word token sets
  5. engagement_signal (0.10) — historical user response pattern (opened, replied, dismissed)

Each dimension returns a partial score in [0.0, 1.0].
The final similarity_score = weighted sum, clamped to [0.0, 1.0].
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from code.context.models import UnifiedContext
from code.loader.data_loader import DataLoader
from code.understanding.models import UnderstandingResult

# Candidate dict type alias (raw rows from message_history + _retrieval_sources)
Candidate = Dict[str, Any]

# ── Dimension weights ────────────────────────────────────────────────────────
_W_IDENTITY   = 0.30
_W_SEMANTIC   = 0.30
_W_STRUCTURAL = 0.15
_W_TEXT       = 0.15
_W_ENGAGEMENT = 0.10

assert abs(_W_IDENTITY + _W_SEMANTIC + _W_STRUCTURAL + _W_TEXT + _W_ENGAGEMENT - 1.0) < 1e-9


def _tokenize(text: Optional[str]) -> Set[str]:
    """Lowercase word-tokenize a string, stripping punctuation."""
    if not text:
        return set()
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def _jaccard(a: Set[str], b: Set[str]) -> float:
    """Standard Jaccard similarity between two token sets."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


class SimilarityRanker:
    """Scores and ranks a pool of candidate dicts by multi-signal similarity.

    Accepts a shared DataLoader to resolve message event data (open/reply/dismiss)
    for the engagement dimension.
    """

    def __init__(self, loader: DataLoader):
        """Initialise with a pre-loaded DataLoader.

        Args:
            loader: DataLoader instance with all CSVs loaded via load_all().
        """
        self._loader = loader

    # ── Public interface ─────────────────────────────────────────────────────

    def rank_candidates(
        self,
        current_context: UnifiedContext,
        current_understanding: UnderstandingResult,
        candidates: List[Candidate],
    ) -> List[Candidate]:
        """Score each candidate and return them sorted descending by similarity_score.

        Each candidate dict is mutated in-place to add:
          - ``similarity_score``   float [0.0, 1.0]
          - ``matched_features``   List[str]  — dimension labels that contributed

        Args:
            current_context:      UnifiedContext for the incoming message.
            current_understanding: UnderstandingResult for the incoming message.
            candidates:            Raw candidate dicts from CandidateRetriever.

        Returns:
            The same list, sorted descending by similarity_score.
        """
        msg  = current_context.conversation.message
        # Pre-compute tokens from the incoming message text once
        current_tokens = _tokenize(msg.message_text)

        for cand in candidates:
            score, features = self._score(
                msg_business_id=msg.business_id,
                msg_sender_id=msg.sender_user_id,
                msg_group_id=msg.group_id,
                msg_conv_type=msg.conversation_type,
                msg_media_type=msg.media_type,
                msg_forwarded=msg.forwarded_count,
                current_tokens=current_tokens,
                current_understanding=current_understanding,
                cand=cand,
            )
            cand["similarity_score"] = round(score, 4)
            cand["matched_features"] = features

        # Sort descending
        candidates.sort(key=lambda c: c["similarity_score"], reverse=True)
        return candidates

    # ── Private scoring orchestrator ─────────────────────────────────────────

    def _score(
        self,
        msg_business_id: Optional[str],
        msg_sender_id: Optional[str],
        msg_group_id: Optional[str],
        msg_conv_type: str,
        msg_media_type: Optional[str],
        msg_forwarded: Optional[int],
        current_tokens: Set[str],
        current_understanding: UnderstandingResult,
        cand: Candidate,
    ) -> Tuple[float, List[str]]:
        """Compute the weighted multi-dimensional similarity score."""
        features: List[str] = []
        total = 0.0

        # 1. Identity match ─────────────────────────────────────────────────
        id_score = self._identity_match(
            msg_business_id, msg_sender_id, msg_group_id,
            cand, features
        )
        total += _W_IDENTITY * id_score

        # 2. Semantic overlap ────────────────────────────────────────────────
        sem_score = self._semantic_overlap(current_understanding, cand, features)
        total += _W_SEMANTIC * sem_score

        # 3. Structural match ────────────────────────────────────────────────
        struct_score = self._structural_match(
            msg_conv_type, msg_media_type, msg_forwarded, cand, features
        )
        total += _W_STRUCTURAL * struct_score

        # 4. Text similarity ─────────────────────────────────────────────────
        text_score = self._text_similarity(current_tokens, cand, features)
        total += _W_TEXT * text_score

        # 5. Engagement signal ───────────────────────────────────────────────
        eng_score = self._engagement_signal(cand, features)
        total += _W_ENGAGEMENT * eng_score

        # Clamp to [0, 1]
        return min(1.0, max(0.0, total)), features

    # ── Dimension 1: Identity match (weight 0.30) ────────────────────────────

    def _identity_match(
        self,
        msg_business_id: Optional[str],
        msg_sender_id: Optional[str],
        msg_group_id: Optional[str],
        cand: Candidate,
        features: List[str],
    ) -> float:
        """Score identity overlap between incoming message and candidate.

        Scoring rules (multiple can apply, capped at 1.0):
          - Same business_id         → +1.00  (strongest identity signal)
          - Same sender_user_id      → +0.90
          - Same group_id            → +0.60
          - No identity overlap      → 0.00
        """
        score = 0.0

        if msg_business_id and str(cand.get("business_id", "")) == str(msg_business_id):
            score = max(score, 1.00)
            features.append("identity:same_business")

        if msg_sender_id and str(cand.get("sender_user_id", "")) == str(msg_sender_id):
            score = max(score, 0.90)
            features.append("identity:same_sender")

        if msg_group_id and str(cand.get("group_id", "")) == str(msg_group_id):
            score = max(score, 0.60)
            features.append("identity:same_group")

        return score

    # ── Dimension 2: Semantic boolean overlap (weight 0.30) ──────────────────

    def _semantic_overlap(
        self,
        understanding: UnderstandingResult,
        cand: Candidate,
        features: List[str],
    ) -> float:
        """Score overlap of boolean semantic flags between current and candidate.

        We infer candidate flags from lightweight keyword heuristics because
        candidates are raw message_history dicts without an UnderstandingResult.

        Four boolean signals checked (equal weight = 0.25 each):
          - urgency      — urgent keywords in candidate text
          - payment      — payment keywords
          - promotion    — promotional keywords
          - event        — event/calendar keywords
        """
        text = (cand.get("message_text") or "").lower()

        # Heuristic flag inference for the candidate
        cand_urgent = any(kw in text for kw in (
            "urgent", "asap", "immediately", "emergency", "critical", "deadline", "expire",
            "last chance", "final", "limited time"
        ))
        cand_payment = any(kw in text for kw in (
            "pay", "payment", "invoice", "bill", "amount", "fee", "otp", "bank",
            "transfer", "debit", "credit", "wallet", "recharge"
        ))
        cand_promo = any(kw in text for kw in (
            "offer", "discount", "sale", "deal", "promo", "coupon", "cashback",
            "free", "reward", "win", "prize", "shop", "buy now"
        ))
        cand_event = any(kw in text for kw in (
            "meeting", "appointment", "call", "schedule", "event", "reminder",
            "rsvp", "join", "confirm", "interview", "webinar", "today", "tomorrow"
        ))

        matches = 0
        total_flags = 0

        # urgency
        if understanding.urgency in ("high", "medium"):
            total_flags += 1
            if cand_urgent:
                matches += 1
                features.append("semantic:urgency_match")

        # payment
        if understanding.payment_detected:
            total_flags += 1
            if cand_payment:
                matches += 1
                features.append("semantic:payment_match")

        # promotion
        if understanding.promotion_detected:
            total_flags += 1
            if cand_promo:
                matches += 1
                features.append("semantic:promotion_match")

        # event
        if understanding.event_detected:
            total_flags += 1
            if cand_event:
                matches += 1
                features.append("semantic:event_match")

        # When the current message has no detectable semantic flags, fall back
        # to checking any overlap (gives a baseline rather than zero)
        if total_flags == 0:
            any_flag = cand_urgent or cand_payment or cand_promo or cand_event
            return 0.10 if any_flag else 0.0

        return matches / total_flags

    # ── Dimension 3: Structural match (weight 0.15) ──────────────────────────

    def _structural_match(
        self,
        msg_conv_type: str,
        msg_media_type: Optional[str],
        msg_forwarded: Optional[int],
        cand: Candidate,
        features: List[str],
    ) -> float:
        """Score structural similarity (conversation type, media, forwarding pattern).

        Three sub-signals (equal weight 0.333 each):
          - conversation_type matches
          - media_type matches (both None = match; text-only vs media)
          - forwarded pattern matches (both forwarded or both original)
        """
        sub_scores: List[float] = []

        # Conversation type
        if str(cand.get("conversation_type", "")) == str(msg_conv_type):
            sub_scores.append(1.0)
            features.append("structural:conv_type_match")
        else:
            sub_scores.append(0.0)

        # Media type (None and None = both text-only = match)
        cand_media = cand.get("media_type") or None
        incoming_media = msg_media_type or None
        if cand_media == incoming_media:
            sub_scores.append(1.0)
            features.append("structural:media_type_match")
        else:
            sub_scores.append(0.0)

        # Forwarding pattern
        cand_fwd = int(cand.get("forwarded_count") or 0)
        incoming_fwd = int(msg_forwarded or 0)
        both_forwarded = (cand_fwd > 0) and (incoming_fwd > 0)
        both_original  = (cand_fwd == 0) and (incoming_fwd == 0)
        if both_forwarded or both_original:
            sub_scores.append(1.0)
            features.append("structural:forward_pattern_match")
        else:
            sub_scores.append(0.0)

        return sum(sub_scores) / len(sub_scores)

    # ── Dimension 4: Text similarity (weight 0.15) ───────────────────────────

    def _text_similarity(
        self,
        current_tokens: Set[str],
        cand: Candidate,
        features: List[str],
    ) -> float:
        """Jaccard token overlap between incoming and candidate message text.

        A Jaccard score > 0.05 is considered meaningful and earns the
        'text:keyword_overlap' feature label.
        """
        cand_tokens = _tokenize(cand.get("message_text"))
        score = _jaccard(current_tokens, cand_tokens)
        if score > 0.05:
            features.append("text:keyword_overlap")
        return score

    # ── Dimension 5: Engagement signal (weight 0.10) ─────────────────────────

    def _engagement_signal(
        self,
        cand: Candidate,
        features: List[str],
    ) -> float:
        """Score based on how the user historically responded to this candidate.

        Scoring rules (capped at 1.0):
          - Replied     → 1.00 (strongest positive engagement)
          - Opened      → 0.60 (passive positive signal)
          - Dismissed   → 0.10 (weak — barely relevant)
          - Reported    → 0.00 (strongly negative — treat as noise)
          - No data     → 0.30 (neutral prior)

        Data source: _message_events_idx field already merged onto candidate
        by DataLoader, OR read from the loader by message_id if available.
        """
        # Candidates carry event fields if they were merged by the context builder;
        # otherwise hydrate from the loader and attach them for downstream selectors.
        reported  = bool(cand.get("message_reported"))
        replied   = bool(cand.get("message_replied"))
        opened    = bool(cand.get("message_opened"))
        dismissed = bool(cand.get("notification_dismissed"))

        if not replied and not opened and not dismissed and not reported:
            cand_mid = str(cand.get("message_id", ""))
            event = self._loader._message_events_idx.get(cand_mid, {})
            if event:
                for key in (
                    "message_opened",
                    "message_replied",
                    "notification_dismissed",
                    "muted_after_message",
                    "message_reported",
                ):
                    if key in event:
                        cand[key] = event[key]
                reported  = bool(event.get("message_reported", False))
                replied   = bool(event.get("message_replied", False))
                opened    = bool(event.get("message_opened", False))
                dismissed = bool(event.get("notification_dismissed", False))

        if reported:
            features.append("engagement:message_reported")
            return 0.00

        if replied:
            features.append("engagement:user_replied")
            return 1.00
        if opened:
            features.append("engagement:user_opened")
            return 0.60
        if dismissed:
            features.append("engagement:notification_dismissed")
            return 0.10

        # No event data at all — neutral prior
        return 0.30
