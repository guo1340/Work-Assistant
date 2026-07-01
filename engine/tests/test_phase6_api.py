from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_api_project_request_and_pipeline(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", str(tmp_path / "state.db"))
    get_settings.cache_clear()
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "README.md").write_text("# Project\n", encoding="utf-8")

    with TestClient(app) as client:
        project_response = client.post(
            "/api/projects",
            json={
                "name": "Project",
                "root_path": str(project_root),
                "scan_type": "soft",
            },
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        request_response = client.post(
            "/api/requests",
            json={
                "project_id": project_id,
                "original_text": "Build the requested feature.",
            },
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["request_id"]

        state = "RECEIVED"
        for _ in range(10):
            response = client.post(
                f"/api/requests/{request_id}/advance",
                json={"provider_id": "mock"},
            )
            assert response.status_code == 200
            state = response.json()["state"]
            if state == "DONE":
                break

        assert state == "DONE"
        assert response.json()["final_report"]["verdict"] == "complete"

    get_settings.cache_clear()


def test_cors_preflight_allows_frontend_post(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", str(tmp_path / "state.db"))
    get_settings.cache_clear()

    with TestClient(app) as client:
        response = client.options(
            "/api/requests",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:5173"
    )
    assert "POST" in response.headers["access-control-allow-methods"]
    get_settings.cache_clear()
