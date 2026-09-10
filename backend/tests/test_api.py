from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_and_feed():
    assert client.get("/api/health").json()["status"] == "healthy"
    response = client.get("/api/users/demo-user/personalized-feed?persona=travel")
    assert response.status_code == 200
    assert response.json()["is_demo_data"] is True


def test_community_observation_is_clearly_labelled():
    response = client.post("/api/community/observations", json={"type": "waterlogging", "location": "Ahmedabad"})
    assert response.status_code == 201
    assert response.json()["source_type"] == "community"
    assert response.json()["verified"] is False
