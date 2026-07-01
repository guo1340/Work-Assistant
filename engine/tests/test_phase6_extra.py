from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.connection import initialize_database
from app.db.store import StateStore
from app.domain.models import RequestState
from app.providers.mock import MockProvider
from app.providers.registry import ProviderRegistry
from app.risk.rules import RiskRuleEngine
from app.workflow.engine import EngineConfig, WorkflowEngine
from app.main import app


# --- Engine <-> risk-rule integration -------------------------------------

def _engine(store, provider):
    registry = ProviderRegistry()
    registry.register(provider)
    return WorkflowEngine(
        store,
        registry,
        EngineConfig(retry_base_seconds=0),
        sleeper=lambda _: None,
        risk_rules=RiskRuleEngine(),
    )


def _seed(tmp_path):
    database = tmp_path / "state.db"
    initialize_database(database)
    store = StateStore(database)
    project_id = store.create_project("Example", str(tmp_path))
    store.create_request("REQ-2026-0001", project_id, "text")
    return store


def test_rule_detected_high_risk_forces_approval(tmp_path):
    store = _seed(tmp_path)
    provider = MockProvider(
        responses={
            "request_logger": {"output": {"files_changed": ["auth/login.py"]}}
        }
    )
    engine = _engine(store, provider)
    assert (
        engine.run_next("REQ-2026-0001", "mock")
        == RequestState.AWAITING_APPROVAL
    )
    reason = store.pending_approval("REQ-2026-0001")["reason"]
    assert "high-risk path" in reason


def test_low_confidence_forces_approval(tmp_path):
    store = _seed(tmp_path)
    provider = MockProvider(responses={"request_logger": {"confidence": 0.5}})
    engine = _engine(store, provider)
    assert (
        engine.run_next("REQ-2026-0001", "mock")
        == RequestState.AWAITING_APPROVAL
    )
    assert "below threshold" in store.pending_approval("REQ-2026-0001")["reason"]


# --- API error handling ----------------------------------------------------

def test_api_rejects_nonexistent_project_root(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", str(tmp_path / "state.db"))
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.post(
            "/api/projects",
            json={
                "name": "X",
                "root_path": str(tmp_path / "missing"),
                "scan_type": "soft",
            },
        )
    assert response.status_code == 400
    get_settings.cache_clear()


def test_api_rejects_blank_request_text(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", str(tmp_path / "state.db"))
    get_settings.cache_clear()
    root = tmp_path / "project"
    root.mkdir()
    with TestClient(app) as client:
        created = client.post(
            "/api/projects",
            json={"name": "X", "root_path": str(root), "scan_type": "soft"},
        )
        project_id = created.json()["id"]
        response = client.post(
            "/api/requests",
            json={"project_id": project_id, "original_text": "   "},
        )
    assert response.status_code == 400
    get_settings.cache_clear()


def test_api_unknown_request_returns_404(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVFLOW_DATABASE_PATH", str(tmp_path / "state.db"))
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/api/requests/REQ-DOES-NOT-EXIST")
    assert response.status_code == 404
    get_settings.cache_clear()
