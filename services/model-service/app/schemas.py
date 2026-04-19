"""
Model Service Pydantic Schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class PredictRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user to generate recommendations for")
    model_version: str = Field(default="production", description="Model stage or version number")
    num_recommendations: int = Field(default=10, ge=1, le=100)


class RecommendationItem(BaseModel):
    item_id: str
    score: float
    rank: int


class StageTimings(BaseModel):
    candidate_generation_ms: float
    ranking_ms: float
    reranking_ms: float


class PredictResponse(BaseModel):
    user_id: str
    recommendations: List[RecommendationItem]
    model_version: str
    inference_time_ms: float
    stages: StageTimings
