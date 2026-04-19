"""
API Gateway Middleware — Rate Limiting.
"""

import time
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from .config import settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    Limits requests based on client IP address.
    """
    def __init__(self, app):
        super().__init__(app)
        self.redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        
    async def dispatch(self, request: Request, call_next):
        # Exclude health and metrics from rate limiting
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        current_minute = int(time.time() // settings.rate_limit_window_seconds)
        redis_key = f"rate_limit:{client_ip}:{current_minute}"
        
        try:
            # Atomic increment and expire
            async with self.redis.pipeline(transaction=True) as pipe:
                await pipe.incr(redis_key)
                await pipe.expire(redis_key, settings.rate_limit_window_seconds * 2)
                results = await pipe.execute()
                
            request_count = results[0]
            
            if request_count > settings.rate_limit_requests:
                logger.warning(f"Rate limit exceeded for IP {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests"}
                )
                
            response = await call_next(request)
            # Inject Request ID header
            response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "gateway-generated")
            return response
            
        except redis.RedisError as e:
            # Fail open if Redis is down
            logger.error(f"Redis error during rate limiting: {e}")
            return await call_next(request)
