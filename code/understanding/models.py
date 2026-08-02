from typing import List, Optional
from pydantic import BaseModel, Field

class UnderstandingResult(BaseModel):
    """Represents the standardized semantic output of the Understanding Framework."""
    summary: str = Field(..., description="A short summary of the message contents")
    intent: str = Field(..., description="The main intent/purpose of the message")
    message_type: str = Field(..., description="Category of the message (e.g., transactional, personal, promotional)")
    urgency: str = Field(..., description="The level of urgency (e.g., high, medium, low)")
    entities: List[str] = Field(default_factory=list, description="Extracted entities like people, places, organizations")
    requires_attention: bool = Field(..., description="True if the message content demands user action/reply")
    promotion_detected: bool = Field(..., description="True if promotional or marketing content is identified")
    payment_detected: bool = Field(..., description="True if transactional or payment details are found")
    event_detected: bool = Field(..., description="True if an event, appointment, or schedule is mentioned")
    contains_media: bool = Field(..., description="True if the message contains images, audio, or other media")
    processing_status: str = Field("pending", description="Status of the semantic understanding extraction")
