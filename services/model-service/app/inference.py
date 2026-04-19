"""
Model Service — Multi-stage inference pipeline.

Wraps the candidate generation → ranking → re-ranking stages
and returns scored recommendations with per-stage timing.
"""

import time
import logging
from typing import List, Dict, Any

from .model_loader import model_loader, CANDIDATE_MODEL_NAME, RANKING_MODEL_NAME
from .schemas import RecommendationItem, StageTimings

logger = logging.getLogger(__name__)

# Fallback items when models are not yet loaded (demo / cold-start)
FALLBACK_ITEMS = [f"item_{i}" for i in range(1, 51)]


def _run_candidate_generation(user_id: str, model_version: str, num_candidates: int) -> List[str]:
    """Stage 1: Generate candidate item IDs using ALS."""
    loaded = model_loader.get_model(CANDIDATE_MODEL_NAME, model_version)
    if loaded and loaded.model:
        try:
            # MLflow pyfunc models expose a .predict() interface
            candidates = loaded.model.predict({"user_id": user_id, "n": num_candidates})
            return list(candidates) if candidates is not None else FALLBACK_ITEMS[:num_candidates]
        except Exception as e:
            logger.warning(f"Candidate generation failed, using fallback: {e}")
    return FALLBACK_ITEMS[:num_candidates]


def _run_ranking(candidates: List[str], user_id: str, model_version: str) -> List[Dict[str, Any]]:
    """Stage 2: Score and rank candidates using the ranking model."""
    loaded = model_loader.get_model(RANKING_MODEL_NAME, model_version)
    if loaded and loaded.model:
        try:
            scored = loaded.model.predict({"user_id": user_id, "item_ids": candidates})
            return [{"item_id": item, "score": float(score)} for item, score in zip(candidates, scored)]
        except Exception as e:
            logger.warning(f"Ranking model failed, using fallback scores: {e}")

    # Fallback: assign decreasing scores
    return [{"item_id": item, "score": round(1.0 - i * 0.01, 4)} for i, item in enumerate(candidates)]


def _run_reranking(scored_items: List[Dict[str, Any]], num_results: int) -> List[Dict[str, Any]]:
    """Stage 3: Apply diversity re-ranking (MMR-style)."""
    # Sort by score descending, then apply simple diversity dampening
    sorted_items = sorted(scored_items, key=lambda x: x["score"], reverse=True)

    reranked: List[Dict[str, Any]] = []
    seen_prefix: set = set()

    for item in sorted_items:
        if len(reranked) >= num_results:
            break

        # Simple diversity: dampen score if item prefix already seen
        prefix = item["item_id"].rsplit("_", 1)[0]
        score = item["score"]
        if prefix in seen_prefix:
            score *= 0.8  # diversity penalty

        reranked.append({"item_id": item["item_id"], "score": round(score, 4)})
        seen_prefix.add(prefix)

    # Re-sort after diversity adjustment
    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked


def run_inference(user_id: str, model_version: str, num_recommendations: int):
    """
    Execute the full multi-stage inference pipeline.
    Returns recommendations and per-stage timing.
    """
    total_start = time.perf_counter()

    # Stage 1: Candidate Generation
    t0 = time.perf_counter()
    candidates = _run_candidate_generation(user_id, model_version, num_candidates=100)
    candidate_ms = (time.perf_counter() - t0) * 1000

    # Stage 2: Ranking
    t1 = time.perf_counter()
    scored = _run_ranking(candidates, user_id, model_version)
    ranking_ms = (time.perf_counter() - t1) * 1000

    # Stage 3: Re-ranking
    t2 = time.perf_counter()
    reranked = _run_reranking(scored, num_recommendations)
    reranking_ms = (time.perf_counter() - t2) * 1000

    total_ms = (time.perf_counter() - total_start) * 1000

    # Build response items
    recommendations = [
        RecommendationItem(item_id=item["item_id"], score=item["score"], rank=i + 1)
        for i, item in enumerate(reranked)
    ]

    # Resolve actual version string
    loaded_candidate = model_loader.get_model(CANDIDATE_MODEL_NAME, model_version)
    actual_version = loaded_candidate.version if loaded_candidate else "fallback"

    timings = StageTimings(
        candidate_generation_ms=round(candidate_ms, 2),
        ranking_ms=round(ranking_ms, 2),
        reranking_ms=round(reranking_ms, 2)
    )

    return recommendations, actual_version, round(total_ms, 2), timings
