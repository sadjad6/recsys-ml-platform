"""
API Gateway Routes — Proxy to downstream services.
"""

import httpx
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from .config import settings

router = APIRouter()
client = httpx.AsyncClient(timeout=30.0)

async def proxy_request(request: Request, target_url: str):
    """Proxy the incoming request to the target downstream service."""
    try:
        url = httpx.URL(target_url, path=request.url.path, query=request.url.query.encode("utf-8"))
        headers = dict(request.headers)
        headers.pop("host", None) # Remove original host to let httpx set it
        
        req = client.build_request(
            method=request.method,
            url=url,
            headers=headers,
            content=request.stream()
        )
        
        response = await client.send(req, stream=True)
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

@router.api_route("/api/v1/events", methods=["POST", "OPTIONS"])
async def proxy_events(request: Request):
    return await proxy_request(request, settings.event_service_url)

@router.api_route("/api/v1/recommendations", methods=["GET", "OPTIONS"])
async def proxy_recommendations(request: Request):
    return await proxy_request(request, settings.recommendation_service_url)

@router.api_route("/api/v1/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_users(request: Request, path: str):
    return await proxy_request(request, settings.user_service_url)

@router.api_route("/api/v1/experiments/assign", methods=["GET", "OPTIONS"])
async def proxy_experiments(request: Request):
    return await proxy_request(request, settings.experimentation_service_url)
