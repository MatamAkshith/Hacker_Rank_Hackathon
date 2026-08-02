"""CandidateRetriever: Fetches a broad pool of historical candidate messages
that share structural or relational metadata with the incoming message.

This module performs NO ranking, scoring, or similarity computation.
Its sole responsibility is producing a wide set of structurally related
historical messages for downstream ranking in Sprint 6.3.

Four retrieval strategies are applied in priority order:
  1. same_sender      — prior messages from the identical sender_user_id
  2. same_business    — prior messages from the same business_id
  3. same_group       — prior messages posted in the same group_id
  4. conversation_type — prior messages with matching conversation_type from
                         the user's general history (broadest fallback)

Each strategy annotates every candidate dict with a `_retrieval_sources` list
so downstream rankers know which signals drove the match.
"""

from typing import Any, Dict, List, Optional, Set

from code.context.models import UnifiedContext
from code.loader.data_loader import DataLoader


# Candidate dict type alias for clarity
Candidate = Dict[str, Any]


class CandidateRetriever:
    """Retrieves a broad pool of historical candidate messages for evidence ranking.

    Accepts a shared DataLoader to reuse already-loaded, O(1) indexed data
    instead of re-reading CSV files on every call.
    """

    # Maximum raw candidates to surface per retrieval strategy (before dedup)
    _STRATEGY_LIMIT: int = 30
    # Hard cap on total candidates handed to the ranker
    _CANDIDATE_POOL_LIMIT: int = 80

    def __init__(self, loader: DataLoader):
        """Initialise with a pre-loaded DataLoader.

        Args:
            loader: A DataLoader instance with all CSVs already loaded via
                    loader.load_all().
        """
        self._loader = loader

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch_candidates(self, context: UnifiedContext) -> List[Candidate]:
        """Return a deduplicated pool of historical candidate message dicts.

        Applies four retrieval strategies in order and merges their results,
        preserving the _retrieval_sources annotation on each candidate.  No
        scoring or ranking is performed here.

        Args:
            context: The UnifiedContext for the current incoming message.

        Returns:
            A list of raw candidate dicts (subset of message_history rows)
            each annotated with ``_retrieval_sources: List[str]`` indicating
            which strategy(ies) surfaced it.
        """
        current_msg_id: str = context.conversation.message.message_id
        user_id: str = context.recipient.user_id

        # Full history for this user (source of truth for all strategies)
        history: List[Dict[str, Any]] = self._loader.get_message_history(user_id)

        # Accumulators keyed by message_id to merge _retrieval_sources
        merged: Dict[str, Candidate] = {}
        seen: Set[str] = set()

        # Run each strategy and fold results into merged pool
        strategies = [
            ("same_sender",         self._by_same_sender(context, history, current_msg_id)),
            ("same_business",       self._by_same_business(context, history, current_msg_id)),
            ("same_group",          self._by_same_group(context, history, current_msg_id)),
            ("conversation_type",   self._by_conversation_type(context, history, current_msg_id)),
        ]

        for source_label, candidates in strategies:
            for cand in candidates:
                mid = str(cand.get("message_id", ""))
                if not mid:
                    continue
                if mid not in merged:
                    merged[mid] = dict(cand)
                    merged[mid]["_retrieval_sources"] = []
                if source_label not in merged[mid]["_retrieval_sources"]:
                    merged[mid]["_retrieval_sources"].append(source_label)
                seen.add(mid)

        # Return deduplicated pool, capped at _CANDIDATE_POOL_LIMIT
        return list(merged.values())[: self._CANDIDATE_POOL_LIMIT]

    # ------------------------------------------------------------------
    # Strategy 1: Same sender (personal messages)
    # ------------------------------------------------------------------

    def _by_same_sender(
        self,
        context: UnifiedContext,
        history: List[Candidate],
        current_msg_id: str,
    ) -> List[Candidate]:
        """Return historical messages from the same individual sender_user_id."""
        sender_id: Optional[str] = context.conversation.message.sender_user_id
        if not sender_id:
            return []

        return [
            row for row in history
            if str(row.get("sender_user_id", "")) == str(sender_id)
            and str(row.get("message_id", "")) != current_msg_id
        ][: self._STRATEGY_LIMIT]

    # ------------------------------------------------------------------
    # Strategy 2: Same business account
    # ------------------------------------------------------------------

    def _by_same_business(
        self,
        context: UnifiedContext,
        history: List[Candidate],
        current_msg_id: str,
    ) -> List[Candidate]:
        """Return historical messages from the same business_id."""
        business_id: Optional[str] = context.conversation.message.business_id
        if not business_id:
            return []

        return [
            row for row in history
            if str(row.get("business_id", "")) == str(business_id)
            and str(row.get("message_id", "")) != current_msg_id
        ][: self._STRATEGY_LIMIT]

    # ------------------------------------------------------------------
    # Strategy 3: Same group
    # ------------------------------------------------------------------

    def _by_same_group(
        self,
        context: UnifiedContext,
        history: List[Candidate],
        current_msg_id: str,
    ) -> List[Candidate]:
        """Return historical messages posted in the same group_id."""
        group_id: Optional[str] = context.conversation.message.group_id
        if not group_id:
            return []

        return [
            row for row in history
            if str(row.get("group_id", "")) == str(group_id)
            and str(row.get("message_id", "")) != current_msg_id
        ][: self._STRATEGY_LIMIT]

    # ------------------------------------------------------------------
    # Strategy 4: Same conversation type (broadest fallback)
    # ------------------------------------------------------------------

    def _by_conversation_type(
        self,
        context: UnifiedContext,
        history: List[Candidate],
        current_msg_id: str,
    ) -> List[Candidate]:
        """Return historical messages with the same conversation_type (personal/group/business).

        This is the broadest fallback and intentionally capped more aggressively.
        """
        conv_type: str = context.conversation.message.conversation_type

        return [
            row for row in history
            if str(row.get("conversation_type", "")) == conv_type
            and str(row.get("message_id", "")) != current_msg_id
        ][: self._STRATEGY_LIMIT]
