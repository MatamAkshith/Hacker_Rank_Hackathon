"""Data models for the Decision Engine.

DecisionScores holds the raw calculated weights for each possible routing action.
DecisionResult is the root container returned by the DecisionEngine.
"""

from typing import List
from pydantic import BaseModel, Field


class DecisionScores(BaseModel):
    """Raw calculated weights for each possible routing action.

    All scores are unbounded floats — normalisation and argmax selection
    happen downstream in ActionSelector.
    """
    notify_score: float = Field(0.0, description="Accumulated score favouring a notify action")
    digest_score: float = Field(0.0, description="Accumulated score favouring a digest action")
    mute_score:   float = Field(0.0, description="Accumulated score favouring a mute action")


class DecisionResult(BaseModel):
    """Root container returned by DecisionEngine.decide().

    Represents the final routing decision for a single incoming message.
    """
    action: str = Field(
        "unassigned",
        description="Final routing action: 'notify', 'digest', or 'mute'. "
                    "'unassigned' is the scaffold-phase default."
    )
    reason: str = Field(
        "Scaffold complete.",
        description="Human-readable explanation of why this action was chosen."
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Engine's confidence in the chosen action, normalised to [0.0, 1.0]."
    )
    decision_trace: List[str] = Field(
        default_factory=list,
        description="Ordered audit log of every rule, scorer, or adjuster that fired "
                    "during the decision process for full explainability."
    )
