import json
import sqlite3

import pytest

from app.db.store import utc_now
from app.domain.models import RequestState, RiskLevel, StageResult


def test_get_unknown_request_raises(store):
    with pytest.raises(KeyError):
        store.get_request("REQ-UNKNOWN")


def test_invalid_transition_raises(store):
    # Request is in RECEIVED; pretend it is PLANNED.
    with pytest.raises(ValueError, match="invalid transition"):
        store.transition(
            "REQ-2026-0001",
            RequestState.PLANNED,
            RequestState.ANALYZED,
            "BOGUS",
        )


def test_foreign_key_enforced_on_request(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.create_request("REQ-ORPHAN", 999_999, "no such project")


def test_commit_stage_result_persists_json_and_risk(store):
    result = StageResult(
        stage="planner",
        request_id="REQ-2026-0001",
        output={"tasks": [1, 2, 3]},
        model_used="mock",
        confidence=0.8,
        risk_level=RiskLevel.MEDIUM,
        missing_information=["needs spec"],
    )
    store.commit_stage_result(
        result,
        started_at=utc_now(),
        finished_at=utc_now(),
        duration_ms=5,
    )
    rows = store.stage_results("REQ-2026-0001")
    assert len(rows) == 1
    row = rows[0]
    assert json.loads(row["output"]) == {"tasks": [1, 2, 3]}
    assert row["risk_level"] == "medium"
    assert row["status"] == "success"
    assert row["human_review_required"] == 0
    assert json.loads(row["missing_information"]) == ["needs spec"]


def test_history_is_append_only_and_ordered(store):
    store.transition(
        "REQ-2026-0001",
        RequestState.RECEIVED,
        RequestState.LOGGED,
        "COMMITTED",
    )
    store.transition(
        "REQ-2026-0001",
        RequestState.LOGGED,
        RequestState.PLANNING,
        "STAGE_STARTED",
    )
    events = [row["event"] for row in store.history("REQ-2026-0001")]
    assert events == ["REQUEST_RECEIVED", "COMMITTED", "STAGE_STARTED"]


def test_pending_approval_missing_raises(store):
    with pytest.raises(KeyError):
        store.pending_approval("REQ-2026-0001")


def test_decide_approval_twice_raises(store):
    approval_id = store.create_approval("REQ-2026-0001", "builder", "high risk")
    store.decide_approval(approval_id, "approved", "reviewer")
    with pytest.raises(ValueError, match="not pending"):
        store.decide_approval(approval_id, "approved", "reviewer")
