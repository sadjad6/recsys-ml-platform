"""
API Gateway Main Entrypoint.
"""

from fastapi import FastAPI
from services.shared.logging_config import setup_logging
from services.shared.metrics import PrometheusMiddleware, metrics_endpoint
from services.shared.health import HealthResponse
from .config import settings
from .routes import router
from .middleware import RateLimitMiddleware

setup_logging(settings.service_name)

app = FastAPI(
    title="RecSys API Gateway",
    description="Main entrypoint for RecSys ML Platform",
    version="1.0.0"
)

# Add Middlewares
app.add_middleware(RateLimitMiddleware)
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)

# Include routes
app.include_router(router)

# Metrics endpoint
app.add_route("/metrics", metrics_endpoint, methods=["GET"])

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Aggregate health check."""
    # In a full implementation, we might ping downstream services here.
    # For now, return gateway health.
    return HealthResponse(
        service=settings.service_name,
        status="healthy",
        dependencies={
            "redis": "healthy"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
