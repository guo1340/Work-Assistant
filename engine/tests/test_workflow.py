from app.db.store import StateStore
from app.domain.models import RequestState
from app.providers.mock import MockProvider
from app.providers.registry import ProviderRegistry
from app.workflow.engine import EngineConfig, WorkflowEngine


def make_engine(
    store: StateStore,
    provider: MockProvider | None = None,
) -> WorkflowEngine:
    registry = ProviderRegistry()
    registry.register(provider or MockProvider())
    return WorkflowEngine(
        store,
        registry,
        EngineConfig(max_retries=2, retry_base_seconds=0),
        sleeper=lambda _: None,
    )


def test_mock_pipeline_runs_end_to_end(store):
    engine = make_engine(store)

    states = []
    while True:
        state = engine.run_next("REQ-2026-0001", "mock")
        states.append(state)
        if state == RequestState.DONE:
            break

    assert states == [
        RequestState.LOGGED,
        RequestState.PLANNED,
        RequestState.ANALYZED,
        RequestState.BUILT,
        RequestState.TESTING,
        RequestState.TESTED,
        RequestState.REVIEWED,
        RequestState.REPORTED,
        RequestState.DONE,
    ]
    assert len(store.stage_results("REQ-2026-0001")) == 8
    events = [row["event"] for row in store.history("REQ-2026-0001")]
    assert events[0] == "REQUEST_RECEIVED"
    assert events[-1] == "REQUEST_COMPLETED"


def test_high_risk_stage_waits_for_approval(store):
    provider = MockProvider(
        responses={"builder": {"risk_level": "high"}}
    )
    engine = make_engine(store, provider)

    engine.run_next("REQ-2026-0001", "mock")
    engine.run_next("REQ-2026-0001", "mock")
    engine.run_next("REQ-2026-0001", "mock")
    state = engine.run_next("REQ-2026-0001", "mock")

    assert state == RequestState.AWAITING_APPROVAL
    assert engine.approve("REQ-2026-0001", "test-user") == RequestState.BUILT


def test_rejected_gate_is_terminal(store):
    provider = MockProvider(
        responses={"request_logger": {"human_review_required": True}}
    )
    engine = make_engine(store, provider)

    assert (
        engine.run_next("REQ-2026-0001", "mock")
        == RequestState.AWAITING_APPROVAL
    )
    assert (
        engine.reject("REQ-2026-0001", "test-user")
        == RequestState.REJECTED
    )


def test_transient_failure_retries_then_succeeds(store):
    provider = MockProvider(failure_plan={"planner": 1})
    engine = make_engine(store, provider)
    engine.run_next("REQ-2026-0001", "mock")

    assert engine.run_next("REQ-2026-0001", "mock") == RequestState.PLANNED
    planner_results = [
        result
        for result in store.stage_results("REQ-2026-0001")
        if result["stage"] == "planner"
    ]
    assert [result["status"] for result in planner_results] == [
        "failed",
        "success",
    ]


def test_exhausted_retries_fail_request(store):
    provider = MockProvider(failure_plan={"request_logger": 3})
    engine = make_engine(store, provider)

    assert engine.run_next("REQ-2026-0001", "mock") == RequestState.FAILED
    assert store.get_request("REQ-2026-0001")["state"] == "FAILED"


def test_original_request_remains_verbatim(store):
    request = store.get_request("REQ-2026-0001")

    assert request["original_text"] == "Keep this request exactly as written."
