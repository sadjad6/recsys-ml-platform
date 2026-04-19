"""
Recommendation Service Main Entrypoint.
"""

from fastapi import FastAPI
from services.shared.logging_config import setup_logging
from services.shared.metrics import PrometheusMiddleware, metrics_endpoint
from services.shared.health import HealthResponse
from .config import settings
from .routes import router

setup_logging(settings.service_name)

app = FastAPI(
    title="RecSys Recommendation Service",
    description="Orchestrates recommendation pipeline with caching",
    version="1.0.0"
)

# Middlewares
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)

# Routes
app.include_router(router)

# Metrics
app.add_route("/metrics", metrics_endpoint, methods=["GET"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check."""
    return HealthResponse(
        service=settings.service_name,
        status="healthy",
        dependencies={
            "redis": "configured",
            "model-service": "configured",
            "experimentation-service": "configured"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
