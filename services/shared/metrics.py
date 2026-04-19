"""
RecSys ML Platform — Shared Prometheus Metrics Middleware.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Define global metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status_code", "service"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency",
    ["method", "endpoint", "service"]
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track request counts and latency."""
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Don't track the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
            
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            latency = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=status_code,
                service=self.service_name
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path,
                service=self.service_name
            ).observe(latency)
            
        return response

def metrics_endpoint():
    """Return the current Prometheus metrics payload."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
