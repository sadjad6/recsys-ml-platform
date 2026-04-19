"""
Model Service API Routes.
"""

from fastapi import APIRouter
from .schemas import PredictRequest, PredictResponse
from .inference import run_inference
from .model_loader import model_loader

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Run multi-stage inference for a user."""
    recommendations, version, total_ms, timings = run_inference(
        user_id=request.user_id,
        model_version=request.model_version,
        num_recommendations=request.num_recommendations
    )

    return PredictResponse(
        user_id=request.user_id,
        recommendations=recommendations,
        model_version=version,
        inference_time_ms=total_ms,
        stages=timings
    )
