"""
Event Service Main Entrypoint.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from services.shared.logging_config import setup_logging
from services.shared.metrics import PrometheusMiddleware, metrics_endpoint
from services.shared.health import HealthResponse
from .config import settings
from .routes import router
from .producer import producer

setup_logging(settings.service_name)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Kafka Producer
    await producer.start()
    yield
    # Stop Kafka Producer
    await producer.stop()

app = FastAPI(
    title="RecSys Event Service",
    description="Ingests user interactions to Kafka",
    version="1.0.0",
    lifespan=lifespan
)

# Add Middlewares
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)

# Include routes
app.include_router(router, prefix="/api/v1/events")

# Metrics endpoint
app.add_route("/metrics", metrics_endpoint, methods=["GET"])

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check."""
    return HealthResponse(
        service=settings.service_name,
        status="healthy",
        dependencies={
            "kafka": "healthy" if producer.producer is not None else "unhealthy"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
