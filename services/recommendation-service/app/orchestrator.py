"""
Recommendation Orchestrator.

Coordinates the full recommendation flow:
1. Check Redis cache
2. Call Experimentation Service for A/B group
3. Call Model Service for inference
4. Cache result
5. Return recommendations
"""

import time
import logging
from typing import Tuple, Optional

import httpx

from .cache import cache
from .config import settings
from .schemas import RecommendationItem

logger = logging.getLogger(__name__)

http_client = httpx.AsyncClient(timeout=30.0)


async def _get_experiment_group(user_id: str) -> Tuple[str, str]:
    """
    Call the Experimentation Service to get the user's A/B group.
    Returns (experiment_group, model_version).
    Falls back to ('control', 'production') if service is unavailable.
    """
    try:
        response = await http_client.get(
            f"{settings.experimentation_service_url}/assign-group",
            params={"user_id": user_id}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("group", "control"), data.get("model_version", "production")
    except httpx.RequestError as e:
        logger.warning(f"Experimentation service unavailable: {e}")

    return "control", "production"


async def _call_model_service(user_id: str, model_version: str, num: int):
    """Call the Model Service /predict endpoint."""
    try:
        response = await http_client.post(
            f"{settings.model_service_url}/predict",
            json={
                "user_id": user_id,
                "model_version": model_version,
                "num_recommendations": num
            }
        )
        if response.status_code == 200:
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Model service call failed: {e}")

    return None


async def get_recommendations(user_id: str, num: int = 10):
    """
    Orchestrate the full recommendation flow.
    Returns a dict ready for the response schema.
    """
    total_start = time.perf_counter()

    # Step 1: Get experiment group (needed for cache key)
    experiment_group, model_version = await _get_experiment_group(user_id)

    # Step 2: Check cache
    cached = await cache.get(user_id, experiment_group)
    if cached:
        total_ms = (time.perf_counter() - total_start) * 1000
        return {
            "user_id": user_id,
            "recommendations": cached["recommendations"],
            "experiment_group": experiment_group,
            "model_version": cached.get("model_version", model_version),
            "cache_hit": True,
            "total_time_ms": round(total_ms, 2)
        }

    # Step 3: Call Model Service
    prediction = await _call_model_service(user_id, model_version, num)

    if prediction:
        recommendations = prediction.get("recommendations", [])
        actual_version = prediction.get("model_version", model_version)
    else:
        # Fallback: return empty recommendations
        recommendations = []
        actual_version = "unavailable"

    # Step 4: Cache the result
    await cache.set(user_id, experiment_group, {
        "recommendations": recommendations,
        "model_version": actual_version
    })

    total_ms = (time.perf_counter() - total_start) * 1000

    return {
        "user_id": user_id,
        "recommendations": recommendations,
        "experiment_group": experiment_group,
        "model_version": actual_version,
        "cache_hit": False,
        "total_time_ms": round(total_ms, 2)
    }
