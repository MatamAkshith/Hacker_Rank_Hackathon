from typing import List
from pydantic import BaseModel, Field

class TrustAssessment(BaseModel):
    """Assessment of sender and entity trust."""
    trust_score: float = Field(0.0, description="Evaluated trust score, between 0.0 and 1.0")
    is_verified: bool = Field(False, description="True if the sender is a verified business or contact")
    reasons: List[str] = Field(default_factory=list, description="Reasoning or evidence behind trust score")

class RiskAssessment(BaseModel):
    """Assessment of security, spam, and scam risks."""
    risk_score: float = Field(0.0, description="Evaluated risk score, between 0.0 and 1.0")
    spam_probability: float = Field(0.0, description="Evaluated probability of being spam, between 0.0 and 1.0")
    scam_probability: float = Field(0.0, description="Evaluated probability of being scam/phishing, between 0.0 and 1.0")
    threat_level: str = Field("none", description="Categorical threat level (e.g., high, medium, low, none)")
    reasons: List[str] = Field(default_factory=list, description="Reasoning or evidence behind risk score")

class UrgencyAssessment(BaseModel):
    """Assessment of message urgency."""
    urgency_score: float = Field(0.0, description="Evaluated urgency score, between 0.0 and 1.0")
    time_sensitivity: str = Field("low", description="Categorical time sensitivity (e.g., high, medium, low)")

class ImportanceAssessment(BaseModel):
    """Assessment of message importance and content value."""
    importance_score: float = Field(0.0, description="Evaluated importance score, between 0.0 and 1.0")
    value_category: str = Field("neutral", description="Categorical importance type (e.g., critical, informational, neutral, promotional)")

class PersonalizationAssessment(BaseModel):
    """Assessment of relevance and historical affinity to the specific user."""
    affinity_score: float = Field(0.0, description="Evaluated user affinity score, between 0.0 and 1.0")
    user_relevance: str = Field("general", description="Categorical relevance classification (e.g., highly_relevant, general, low_relevance)")

class AttentionAssessment(BaseModel):
    """Assessment of attention required and interruption costs."""
    attention_needed: bool = Field(False, description="True if the message demands prompt attention or action")
    interruption_cost: float = Field(0.0, description="Calculated cost of interrupting the user right now, between 0.0 and 1.0")

class MessageAssessment(BaseModel):
    """Unified container for all component message sub-assessments."""
    trust: TrustAssessment = Field(default_factory=TrustAssessment)
    risk: RiskAssessment = Field(default_factory=RiskAssessment)
    urgency: UrgencyAssessment = Field(default_factory=UrgencyAssessment)
    importance: ImportanceAssessment = Field(default_factory=ImportanceAssessment)
    personalization: PersonalizationAssessment = Field(default_factory=PersonalizationAssessment)
    attention: AttentionAssessment = Field(default_factory=AttentionAssessment)
    overall_score: float = Field(0.0, description="Aggregated overall routing scoring context value")
    status: str = Field("unassessed", description="Assessment processing status")
