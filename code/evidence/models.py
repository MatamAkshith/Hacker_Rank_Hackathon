from typing import List, Optional
from pydantic import BaseModel, Field

class EvidenceItem(BaseModel):
    """Represents a single retrieved historical message as supporting evidence."""
    message_id: str = Field(..., description="The unique ID of the retrieved historical message")
    similarity_score: float = Field(0.0, description="Similarity relevance score to the current message, between 0.0 and 1.0")
    reason: str = Field("", description="Human-readable explanation of why this message was retrieved as evidence")
    matched_features: List[str] = Field(default_factory=list, description="List of feature names that drove the retrieval match")
    user_action: Optional[str] = Field(None, description="Historical user response action: e.g., 'ignored', 'opened', 'muted'")

class EvidenceResult(BaseModel):
    """Root container returned by the RetrievalEngine representing the full set of retrieved evidence."""
    top_evidence: List[EvidenceItem] = Field(default_factory=list, description="Ranked list of retrieved historical evidence items")
    retrieval_summary: str = Field("No evidence retrieved.", description="Short human-readable summary of what was retrieved and why")
    retrieval_status: str = Field("scaffold_complete", description="Processing status of the evidence retrieval step")
