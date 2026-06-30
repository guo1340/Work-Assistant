from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_health_reports_engine_and_database(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", str(tmp_path / "devflow.db"))
    get_settings.cache_clear()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ready",
        "service": "devflow-engine",
    }
    get_settings.cache_clear()
