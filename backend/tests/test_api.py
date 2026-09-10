import pytest
from fastapi.testclient import TestClient
import app.main as main
from app.providers import MockWeatherProvider
from app.store import Store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "store", Store(tmp_path / "test.db"))
    monkeypatch.setattr(main, "provider", MockWeatherProvider())
    monkeypatch.setattr(main, "locations", {"demo-user": []})
    return TestClient(main.app)


def test_health_and_feed(client):
    assert client.get("/api/health").status_code == 200
    feed = client.get("/api/users/demo-user/personalized-feed?persona=travel").json()
    assert feed["model_version"] == "mausam-rules-2.0"
    assert feed["is_demo_data"]
    assert len(feed["daily"]) == 7


def test_report_appears_in_both_endpoints_and_survives_restart(client, monkeypatch):
    response = client.post("/api/community/observations", json={
        "type":"waterlogging", "location":"Ahmedabad", "area":"SG Highway underpass", "details":"Water covers one lane"})
    assert response.status_code == 201
    report = response.json()
    assert report["verified"] is False and report["distance_km"] is None
    # Recreate the repository as happens across a process restart.
    monkeypatch.setattr(main, "store", Store(main.store.path))
    reports = client.get("/api/community/observations?location=ahmedabad").json()
    feed = client.get("/api/users/demo-user/personalized-feed?location=Ahmedabad").json()
    assert any(item["id"] == report["id"] for item in reports)
    assert any(item["id"] == report["id"] for item in feed["observations"])
    assert client.get("/api/community/observations?location=Mumbai").json() == []


def test_preferences_survive_restart_and_drive_feed(client, monkeypatch):
    saved = client.put("/api/users/demo-user/preferences", json={
        "persona":"family", "activities":["Walking"], "extra_protection":["Children"],
        "commute_time":"08:30", "routine":"school pickup", "notifications_enabled":False})
    assert saved.status_code == 200
    monkeypatch.setattr(main, "store", Store(main.store.path))
    profile = client.get("/api/users/demo-user").json()
    assert profile["commute_time"] == "08:30"
    feed = client.get("/api/users/demo-user/personalized-feed").json()
    assert feed["recommendations"][0]["type"] == "family"
    assert "school pickup" in str(feed["recommendations"])
    assert feed["notifications"] == []
    assert client.put("/api/users/demo-user/preferences", json={"commute_time":None}).status_code == 200
    assert client.get("/api/users/demo-user").json()["commute_time"] is None


def test_invalid_reports_and_preferences(client):
    assert client.post("/api/community/observations", json={"type":"made_up","location":"Ahmedabad"}).status_code == 422
    assert client.put("/api/users/demo-user/preferences", json={"activities":None}).status_code == 422
    assert client.put("/api/users/demo-user/preferences", json={"commute_time":"29:99"}).status_code == 422


def test_acknowledged_notification_stays_read(client, monkeypatch):
    class HotProvider(MockWeatherProvider):
        def bundle(self, location):
            bundle = super().bundle(location)
            bundle.weather = bundle.weather.model_copy(update={"source":"Open-Meteo live forecast","feels_like":46})
            return bundle
    monkeypatch.setattr(main, "provider", HotProvider())
    feed = client.get("/api/users/demo-user/personalized-feed").json()
    assert feed["notifications"]
    alert_id = feed["notifications"][0]["id"]
    assert client.post(f"/api/users/demo-user/notifications/{alert_id}/read").status_code == 204
    next_feed = client.get("/api/users/demo-user/personalized-feed").json()
    assert alert_id not in {alert["id"] for alert in next_feed["notifications"]}
    assert alert_id in {alert["id"] for alert in next_feed["alerts"]}


def test_live_outage_returns_error_instead_of_sample_weather(client, monkeypatch):
    class BrokenProvider:
        def bundle(self, location):
            raise RuntimeError("upstream down")
    monkeypatch.setattr(main, "provider", BrokenProvider())
    response = client.get("/api/users/demo-user/personalized-feed")
    assert response.status_code == 503


def test_demo_does_not_mutate_saved_profile(client):
    before = client.get("/api/users/demo-user").json()
    response = client.post("/api/demo/scenarios/family")
    assert response.status_code == 200 and response.json()["is_demo_data"]
    assert client.get("/api/users/demo-user").json() == before
