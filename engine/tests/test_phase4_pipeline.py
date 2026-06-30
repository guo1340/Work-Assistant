from pathlib import Path

from app.agents.committer import AgentResultCommitter
from app.db.connection import initialize_database
from app.db.store import StateStore
from app.domain.models import RequestState
from app.providers.mock import MockProvider
from app.providers.registry import ProviderRegistry
from app.risk.rules import RiskRuleEngine
from app.workflow.engine import EngineConfig, WorkflowEngine


def test_mock_agents_update_every_pipeline_kb_file(tmp_path: Path):
    database = tmp_path / "state.db"
    initialize_database(database)
    store = StateStore(database)
    project_id = store.create_project("Example", str(tmp_path))
    request_id = "REQ-2026-0042"
    original = "Preserve this exact request — punctuation and all."
    store.create_request(request_id, project_id, original)
    registry = ProviderRegistry()
    registry.register(MockProvider())
    engine = WorkflowEngine(
        store,
        registry,
        EngineConfig(retry_base_seconds=0),
        sleeper=lambda _: None,
        committer=AgentResultCommitter(store),
        risk_rules=RiskRuleEngine(),
    )

    while engine.run_next(
        request_id,
        "mock",
        {"original_text": original},
    ) != RequestState.DONE:
        pass

    assert original in (tmp_path / "REQUESTS.md").read_text(encoding="utf-8")
    assert request_id in (tmp_path / "TASKS.md").read_text(encoding="utf-8")
    assert request_id in (tmp_path / "LOGS.md").read_text(encoding="utf-8")
    assert request_id in (tmp_path / "TEST_LOGS.md").read_text(encoding="utf-8")
    assert request_id in (tmp_path / "TRACEABILITY.md").read_text(
        encoding="utf-8"
    )
    assert store.tasks(request_id)
