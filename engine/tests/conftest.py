from pathlib import Path

import pytest

from app.db.connection import initialize_database
from app.db.store import StateStore


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    database_path = tmp_path / "devflow.db"
    initialize_database(database_path)
    state_store = StateStore(database_path)
    project_id = state_store.create_project("Fixture", str(tmp_path))
    state_store.create_request(
        "REQ-2026-0001",
        project_id,
        "Keep this request exactly as written.",
    )
    return state_store
