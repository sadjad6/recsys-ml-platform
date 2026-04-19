"""
Recommendation Service Pydantic Schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class RecommendationItem(BaseModel):
    item_id: str
    score: float
    rank: int


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[RecommendationItem]
    experiment_group: Optional[str] = None
    model_version: str
    cache_hit: bool
    total_time_ms: float
