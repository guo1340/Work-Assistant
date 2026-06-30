from app.api.health import health
from app.core.config import get_settings


def test_health_reports_unavailable_without_db(monkeypatch, tmp_path):
    # Call the handler directly so the app lifespan does not initialize the DB.
    get_settings.cache_clear()
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", str(tmp_path / "missing.db"))
    get_settings.cache_clear()

    body = health()

    assert body["status"] == "ok"
    assert body["service"] == "devflow-engine"
    assert body["database"] == "unavailable"

    get_settings.cache_clear()
