import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@patch("app.routes.get_recommendations", new_callable=AsyncMock)
def test_get_recommendations_happy_path(mock_get_rec):
    mock_get_rec.return_value = {
        "user_id": "123",
        "recommendations": [{"item_id": "i1", "score": 0.99, "rank": 1}],
        "experiment_group": "A",
        "model_version": "v1",
        "cache_hit": False,
        "total_time_ms": 15.0
    }
    
    response = client.get("/recommendations?user_id=123&num=5")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "123"
    assert len(data["recommendations"]) == 1

def test_get_recommendations_unhappy_path_missing_user():
    # Unhappy path 1: missing required query parameter
    response = client.get("/recommendations?num=5")
    assert response.status_code == 422
    assert "user_id" in response.text

def test_get_recommendations_unhappy_path_invalid_num():
    # Unhappy path 2: validation bounds for num
    response = client.get("/recommendations?user_id=123&num=101")
    assert response.status_code == 422
    assert "num" in response.text

    # Unhappy path 3: lower bound validation
    response = client.get("/recommendations?user_id=123&num=0")
    assert response.status_code == 422
    assert "num" in response.text
