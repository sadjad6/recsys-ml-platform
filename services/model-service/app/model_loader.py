"""
Model Loader — loads models from MLflow Model Registry.

Caches models in memory and periodically checks for newer versions.
"""

import logging
import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import mlflow
from mlflow.tracking import MlflowClient

from .config import settings

logger = logging.getLogger(__name__)

CANDIDATE_MODEL_NAME = "als-candidate-generation"
RANKING_MODEL_NAME = "ranking-model"


@dataclass
class LoadedModel:
    """Container for a loaded model with metadata."""
    model: Any
    version: str
    stage: str
    loaded_at: datetime = field(default_factory=datetime.utcnow)


class ModelLoader:
    """
    Manages model loading from MLflow registry.
    Caches models in memory and supports periodic refresh.
    """

    def __init__(self):
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        self.client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
        self._models: Dict[str, LoadedModel] = {}
        self._refresh_task: Optional[asyncio.Task] = None

    def _load_model_by_stage(self, model_name: str, stage: str) -> Optional[LoadedModel]:
        """Load the latest model version for a given stage."""
        try:
            versions = self.client.get_latest_versions(model_name, stages=[stage])
            if not versions:
                logger.warning(f"No model found for {model_name} at stage '{stage}'")
                return None

            mv = versions[0]
            model_uri = f"models:/{model_name}/{mv.version}"
            model = mlflow.pyfunc.load_model(model_uri)

            loaded = LoadedModel(model=model, version=str(mv.version), stage=stage)
            logger.info(f"Loaded {model_name} v{mv.version} (stage={stage})")
            return loaded
        except Exception as e:
            logger.error(f"Failed to load {model_name} from stage {stage}: {e}")
            return None

    def _load_model_by_version(self, model_name: str, version: str) -> Optional[LoadedModel]:
        """Load a specific model version number."""
        try:
            model_uri = f"models:/{model_name}/{version}"
            model = mlflow.pyfunc.load_model(model_uri)
            loaded = LoadedModel(model=model, version=version, stage="specific")
            logger.info(f"Loaded {model_name} v{version}")
            return loaded
        except Exception as e:
            logger.error(f"Failed to load {model_name} v{version}: {e}")
            return None

    def load_production_models(self):
        """Load 'Production' stage models on startup."""
        for name in [CANDIDATE_MODEL_NAME, RANKING_MODEL_NAME]:
            loaded = self._load_model_by_stage(name, "Production")
            if loaded:
                cache_key = f"{name}:production"
                self._models[cache_key] = loaded

    def get_model(self, model_name: str, version: str = "production") -> Optional[LoadedModel]:
        """
        Retrieve a model from cache.
        If version is 'production', return the production-stage cached model.
        Otherwise, load the specific version on demand and cache it.
        """
        cache_key = f"{model_name}:{version}"

        if cache_key in self._models:
            return self._models[cache_key]

        # On-demand load for specific versions (A/B testing)
        if version != "production":
            loaded = self._load_model_by_version(model_name, version)
            if loaded:
                self._models[cache_key] = loaded
            return loaded

        return None

    def get_loaded_versions(self) -> Dict[str, str]:
        """Return a summary of currently loaded models."""
        return {key: m.version for key, m in self._models.items()}

    async def _periodic_refresh(self):
        """Background task to check for newer production models."""
        while True:
            await asyncio.sleep(settings.model_refresh_interval_seconds)
            try:
                logger.info("Checking MLflow registry for updated production models...")
                self.load_production_models()
            except Exception as e:
                logger.error(f"Error during model refresh: {e}")

    async def start_refresh_loop(self):
        """Start the background refresh loop."""
        self._refresh_task = asyncio.create_task(self._periodic_refresh())

    async def stop_refresh_loop(self):
        """Cancel the background refresh loop."""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass


model_loader = ModelLoader()
