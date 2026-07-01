import pytest

from app.agents.committer import TraceabilityChecker, TraceabilityError


def test_traceability_rejects_empty_tasks():
    with pytest.raises(TraceabilityError, match="no tasks"):
        TraceabilityChecker().check("REQ-1", [])


def test_traceability_rejects_duplicate_task_ids():
    tasks = [
        {"task_id": "T1", "description": "a"},
        {"task_id": "T1", "description": "b"},
    ]
    with pytest.raises(TraceabilityError, match="unique task_id"):
        TraceabilityChecker().check("REQ-1", tasks)


def test_traceability_rejects_foreign_request_reference():
    tasks = [{"task_id": "T1", "description": "a", "request_id": "REQ-OTHER"}]
    with pytest.raises(TraceabilityError, match="different request"):
        TraceabilityChecker().check("REQ-1", tasks)


def test_traceability_accepts_well_formed_tasks():
    tasks = [
        {"task_id": "T1", "description": "a"},
        {"task_id": "T2", "description": "b", "request_id": "REQ-1"},
    ]
    TraceabilityChecker().check("REQ-1", tasks)
