"""
Experimentation Service Main Entrypoint.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from services.shared.logging_config import setup_logging
from services.shared.metrics import PrometheusMiddleware, metrics_endpoint
from services.shared.health import HealthResponse
from .config import settings
from .routes import router
from .database import engine, Base

setup_logging(settings.service_name)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (in production, use alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="RecSys Experimentation Service",
    description="Manages A/B tests, deterministic assignment, and metric aggregation",
    version="1.0.0",
    lifespan=lifespan
)

# Middlewares
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)

# Routes
app.include_router(router, prefix="/api/v1/experiments")

# Metrics
app.add_route("/metrics", metrics_endpoint, methods=["GET"])

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check."""
    return HealthResponse(
        service=settings.service_name,
        status="healthy",
        dependencies={
            "database": "configured"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
