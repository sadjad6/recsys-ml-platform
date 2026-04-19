"""
RecSys ML Platform — Shared Health Response schema.
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional

class HealthResponse(BaseModel):
    """Standardized health check response."""
    service: str
    status: str
    version: str = "1.0.0"
    dependencies: Optional[Dict[str, str]] = None
