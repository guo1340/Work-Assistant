from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.db.connection import connect
from app.domain.models import RequestState, StageResult


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class StateStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            yield connection

    def create_project(self, name: str, root_path: str) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO projects (name, root_path) VALUES (?, ?)",
                (name, root_path),
            )
            return int(cursor.lastrowid)

    def create_request(
        self,
        request_id: str,
        project_id: int,
        original_text: str,
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO requests (
                    request_id, project_id, original_text, state
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    request_id,
                    project_id,
                    original_text,
                    RequestState.RECEIVED,
                ),
            )
            self._append_history(
                connection,
                request_id=request_id,
                event="REQUEST_RECEIVED",
                to_state=RequestState.RECEIVED,
            )

    def get_request(self, request_id: str) -> dict[str, Any]:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown request: {request_id}")
        return dict(row)

    def transition(
        self,
        request_id: str,
        expected: RequestState,
        target: RequestState,
        event: str,
        *,
        stage: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE requests
                SET state = ?
                WHERE request_id = ? AND state = ?
                """,
                (target, request_id, expected),
            )
            if cursor.rowcount != 1:
                actual = connection.execute(
                    "SELECT state FROM requests WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                actual_state = actual["state"] if actual else "missing"
                raise ValueError(
                    f"invalid transition for {request_id}: "
                    f"expected {expected}, found {actual_state}"
                )
            self._append_history(
                connection,
                request_id=request_id,
                stage=stage,
                from_state=expected,
                to_state=target,
                event=event,
                detail=detail,
            )

    def record_stage_started(
        self,
        request_id: str,
        stage: str,
        state: RequestState,
    ) -> None:
        with self.transaction() as connection:
            self._append_history(
                connection,
                request_id=request_id,
                stage=stage,
                from_state=state,
                to_state=state,
                event="STAGE_STARTED",
            )

    def commit_stage_result(
        self,
        result: StageResult,
        *,
        started_at: str,
        finished_at: str,
        duration_ms: int,
        status: str = "success",
        error: str | None = None,
    ) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO stage_results (
                    request_id, task_id, stage, output, model_used,
                    confidence, risk_level, missing_information,
                    human_review_required, status, error, started_at,
                    finished_at, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.request_id,
                    result.task_id,
                    result.stage,
                    json.dumps(result.output),
                    result.model_used,
                    result.confidence,
                    str(result.risk_level),
                    json.dumps(result.missing_information),
                    int(result.human_review_required),
                    status,
                    error,
                    started_at,
                    finished_at,
                    duration_ms,
                ),
            )
            return int(cursor.lastrowid)

    def record_failed_attempt(
        self,
        request_id: str,
        stage: str,
        *,
        model_used: str,
        error: str,
        started_at: str,
        finished_at: str,
        duration_ms: int,
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO stage_results (
                    request_id, stage, model_used, human_review_required,
                    status, error, started_at, finished_at, duration_ms
                ) VALUES (?, ?, ?, 0, 'failed', ?, ?, ?, ?)
                """,
                (
                    request_id,
                    stage,
                    model_used,
                    error,
                    started_at,
                    finished_at,
                    duration_ms,
                ),
            )

    def create_approval(
        self,
        request_id: str,
        stage: str,
        reason: str,
    ) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO approvals (request_id, stage, reason)
                VALUES (?, ?, ?)
                """,
                (request_id, stage, reason),
            )
            return int(cursor.lastrowid)

    def pending_approval(self, request_id: str) -> dict[str, Any]:
        with self.transaction() as connection:
            row = connection.execute(
                """
                SELECT * FROM approvals
                WHERE request_id = ? AND status = 'pending'
                ORDER BY id DESC LIMIT 1
                """,
                (request_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"no pending approval for {request_id}")
        return dict(row)

    def decide_approval(
        self,
        approval_id: int,
        status: str,
        decided_by: str,
    ) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE approvals
                SET status = ?, decided_by = ?, decided_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (status, decided_by, utc_now(), approval_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"approval {approval_id} is not pending")

    def history(self, request_id: str) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT * FROM execution_history
                WHERE request_id = ? ORDER BY id
                """,
                (request_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def stage_results(self, request_id: str) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT * FROM stage_results
                WHERE request_id = ? ORDER BY id
                """,
                (request_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _append_history(
        connection: sqlite3.Connection,
        *,
        request_id: str,
        event: str,
        stage: str | None = None,
        from_state: RequestState | None = None,
        to_state: RequestState | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO execution_history (
                request_id, stage, from_state, to_state, event, detail
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                stage,
                from_state,
                to_state,
                event,
                json.dumps(detail) if detail is not None else None,
            ),
        )
