from pathlib import Path

from app.core.config import get_settings


def test_settings_env_overrides(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("DEVFLOW_HOST", "0.0.0.0")
    monkeypatch.setenv("DEVFLOW_PORT", "9999")
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", "/tmp/devflow-test/devflow.db")
    monkeypatch.setenv("DEVFLOW_CORS_ORIGINS", "http://a , http://b")

    settings = get_settings()

    assert settings.host == "0.0.0.0"
    assert settings.port == 9999
    assert settings.database_path == Path("/tmp/devflow-test/devflow.db")
    assert settings.cors_origins == ("http://a", "http://b")

    get_settings.cache_clear()


def test_relative_database_path_resolves_under_project_root(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", "data/devflow.db")

    settings = get_settings()

    assert settings.database_path.is_absolute()
    assert settings.database_path.name == "devflow.db"

    get_settings.cache_clear()
