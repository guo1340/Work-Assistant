import sqlite3

from app.db.connection import EXPECTED_TABLES, database_is_ready, initialize_database


def test_initialize_database_creates_full_schema(tmp_path):
    database_path = tmp_path / "devflow.db"

    initialize_database(database_path)

    assert database_is_ready(database_path)
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        }

    assert EXPECTED_TABLES <= tables
    assert {
        "idx_requests_project_state",
        "idx_tasks_request",
        "idx_stage_results_request",
        "idx_history_request_time",
        "idx_approvals_request",
    } <= indexes
