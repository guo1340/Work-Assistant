import pytest

from app.domain.models import (
    Capability,
    RequestState,
    RiskLevel,
    StageResult,
    Tier,
)
from app.providers.base import Provider, ProviderContext
from app.providers.mock import MockProvider
from app.providers.registry import ProviderRegistry
from app.workflow.engine import EngineConfig, WorkflowEngine


def make_engine(store, provider=None, max_retries=2):
    registry = ProviderRegistry()
    registry.register(provider or MockProvider())
    return WorkflowEngine(
        store,
        registry,
        EngineConfig(max_retries=max_retries, retry_base_seconds=0),
        sleeper=lambda _: None,
    )


def test_next_stage_maps_initial_state(store):
    engine = make_engine(store)
    stage = engine.next_stage("REQ-2026-0001")
    assert stage is not None
    assert stage.name == "request_logger"


def test_run_next_on_terminal_state_raises(store):
    engine = make_engine(store)
    while engine.run_next("REQ-2026-0001", "mock") != RequestState.DONE:
        pass
    assert engine.next_stage("REQ-2026-0001") is None
    with pytest.raises(ValueError, match="no runnable stage"):
        engine.run_next("REQ-2026-0001", "mock")


def test_approve_without_pending_raises(store):
    engine = make_engine(store)
    with pytest.raises(KeyError):
        engine.approve("REQ-2026-0001", "user")


class WrongStageProvider(Provider):
    id = "wrong"
    tier = Tier.HEAVY
    capabilities = frozenset(Capability)

    def invoke(self, context: ProviderContext) -> StageResult:
        return StageResult(
            stage="not_" + context.stage,
            request_id=context.request_id,
            output={},
            model_used=self.id,
            confidence=1.0,
            risk_level=RiskLevel.LOW,
        )


def test_wrong_stage_result_eventually_fails(store):
    engine = make_engine(store, WrongStageProvider(), max_retries=1)
    assert engine.run_next("REQ-2026-0001", "wrong") == RequestState.FAILED
    assert store.get_request("REQ-2026-0001")["state"] == "FAILED"


def test_retry_emits_retry_history_events(store):
    engine = make_engine(
        store,
        MockProvider(failure_plan={"request_logger": 1}),
        max_retries=2,
    )
    assert engine.run_next("REQ-2026-0001", "mock") == RequestState.LOGGED
    events = [row["event"] for row in store.history("REQ-2026-0001")]
    assert "RETRY" in events
    assert "RETRY_STARTED" in events


def test_reject_is_terminal_and_blocks_further_runs(store):
    provider = MockProvider(
        responses={"request_logger": {"human_review_required": True}}
    )
    engine = make_engine(store, provider)
    assert (
        engine.run_next("REQ-2026-0001", "mock")
        == RequestState.AWAITING_APPROVAL
    )
    assert engine.reject("REQ-2026-0001", "user") == RequestState.REJECTED
    with pytest.raises(ValueError, match="no runnable stage"):
        engine.run_next("REQ-2026-0001", "mock")
