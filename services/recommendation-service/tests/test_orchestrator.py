import pytest
from unittest.mock import AsyncMock, patch

from app.orchestrator import get_recommendations

@pytest.fixture
def mock_cache():
    with patch("app.orchestrator.cache.get", new_callable=AsyncMock) as mock_get, \
         patch("app.orchestrator.cache.set", new_callable=AsyncMock) as mock_set:
        yield mock_get, mock_set

@pytest.fixture
def mock_http_client():
    with patch("app.orchestrator.http_client.get", new_callable=AsyncMock) as mock_get, \
         patch("app.orchestrator.http_client.post", new_callable=AsyncMock) as mock_post:
        yield mock_get, mock_post

@pytest.mark.asyncio
async def test_get_recommendations_cache_hit(mock_cache, mock_http_client):
    mock_get_cache, _ = mock_cache
    mock_get_cache.return_value = {
        "recommendations": [{"item_id": "1", "score": 0.9, "rank": 1}],
        "model_version": "v1"
    }
    mock_http_client[0].return_value.status_code = 200
    mock_http_client[0].return_value.json.return_value = {"group": "test", "model_version": "v1"}
    
    result = await get_recommendations("user1", 10)
    
    assert result["cache_hit"] is True
    assert result["experiment_group"] == "test"
    assert len(result["recommendations"]) == 1

@pytest.mark.asyncio
async def test_get_recommendations_unhappy_path_experimentation_fails(mock_cache, mock_http_client):
    import httpx
    mock_get_cache, _ = mock_cache
    mock_get_cache.return_value = None
    
    # Unhappy path 1: Experimentation service raises RequestError
    mock_http_client[0].side_effect = httpx.RequestError("Timeout")
    
    # Model service succeeds
    mock_http_client[1].return_value.status_code = 200
    mock_http_client[1].return_value.json.return_value = {
        "recommendations": [{"item_id": "2", "score": 0.8, "rank": 1}],
        "model_version": "production"
    }
    
    result = await get_recommendations("user2", 10)
    
    assert result["cache_hit"] is False
    assert result["experiment_group"] == "control"
    assert result["model_version"] == "production"

@pytest.mark.asyncio
async def test_get_recommendations_unhappy_path_model_service_fails(mock_cache, mock_http_client):
    mock_get_cache, _ = mock_cache
    mock_get_cache.return_value = None
    
    # Experimentation service succeeds
    mock_http_client[0].return_value.status_code = 200
    mock_http_client[0].return_value.json.return_value = {"group": "A", "model_version": "v2"}
    
    # Unhappy path 2: Model service returns 500
    mock_http_client[1].return_value.status_code = 500
    
    result = await get_recommendations("user3", 10)
    
    assert result["cache_hit"] is False
    assert result["recommendations"] == []
    assert result["model_version"] == "unavailable"
