"""
Model Service Main Entrypoint.
"""

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from services.shared.logging_config import setup_logging
from services.shared.metrics import PrometheusMiddleware, metrics_endpoint
from services.shared.health import HealthResponse
from .config import settings
from .routes import router
from .model_loader import model_loader

setup_logging(settings.service_name)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load production models on startup
    try:
        model_loader.load_production_models()
    except Exception as e:
        logger.warning(f"Could not load production models on startup: {e}")

    # Start background refresh loop
    await model_loader.start_refresh_loop()
    yield
    # Cleanup
    await model_loader.stop_refresh_loop()


app = FastAPI(
    title="RecSys Model Service",
    description="Loads models from MLflow and runs multi-stage inference",
    version="1.0.0",
    lifespan=lifespan
)

# Middlewares
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)

# Routes
app.include_router(router)

# Metrics
app.add_route("/metrics", metrics_endpoint, methods=["GET"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check — returns loaded model versions."""
    versions = model_loader.get_loaded_versions()
    return HealthResponse(
        service=settings.service_name,
        status="healthy",
        dependencies=versions if versions else {"models": "none_loaded"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
