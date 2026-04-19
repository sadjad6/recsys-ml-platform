"""
Recommendation Service API Routes.
"""

from fastapi import APIRouter, Query
from .orchestrator import get_recommendations
from .schemas import RecommendationResponse

router = APIRouter()


@router.get("/recommendations", response_model=RecommendationResponse)
async def recommendations(
    user_id: str = Query(..., description="User ID to get recommendations for"),
    num: int = Query(10, ge=1, le=100, description="Number of recommendations")
):
    """Get personalized recommendations for a user."""
    result = await get_recommendations(user_id=user_id, num=num)
    return RecommendationResponse(**result)
