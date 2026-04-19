"""
Event Service Pydantic Schemas.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

class EventPayload(BaseModel):
    user_id: str = Field(..., description="ID of the user performing the action")
    item_id: str = Field(..., description="ID of the item interacted with")
    event_type: str = Field(..., description="Type of interaction (click, view, purchase, etc)")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    
class EventEnriched(EventPayload):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    received_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

class EventResponse(BaseModel):
    status: str
    event_id: str
