from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.db.store import StateStore
from app.domain.models import StageResult
from app.git.safety import GitSafety
from app.kb.markdown import MarkdownKnowledgeBase


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


class TraceabilityError(ValueError):
    pass


class TraceabilityChecker:
    def check(self, request_id: str, tasks: list[dict[str, Any]]) -> None:
        if not tasks:
            raise TraceabilityError("planner produced no tasks")
        task_ids: set[str] = set()
        for task in tasks:
            if task.get("request_id", request_id) != request_id:
                raise TraceabilityError("task references a different request")
            task_id = str(task.get("task_id", ""))
            if not task_id or task_id in task_ids:
                raise TraceabilityError("tasks need unique task_id values")
            task_ids.add(task_id)


class AgentResultCommitter:
    def __init__(
        self,
        store: StateStore,
        git_safety_by_project: dict[int, GitSafety] | None = None,
    ) -> None:
        self.store = store
        self.traceability = TraceabilityChecker()
        self.git_safety_by_project = (
            git_safety_by_project
            if git_safety_by_project is not None
            else {}
        )

    def commit(self, result: StageResult) -> None:
        request = self.store.get_request(result.request_id)
        project = self.store.get_project(request["project_id"])
        kb = MarkdownKnowledgeBase(Path(project["root_path"]))
        handler = getattr(self, f"_commit_{result.stage}", None)
        if handler:
            handler(kb, request, result)

    def reject(self, request_id: str) -> None:
        request = self.store.get_request(request_id)
        git_safety = self.git_safety_by_project.get(request["project_id"])
        if git_safety:
            git_safety.reject(request_id)

    def _commit_request_logger(self, kb, request, result) -> None:
        kb.append(
            "REQUESTS.md",
            "\n".join(
                (
                    f"## {request['request_id']} — {timestamp()}",
                    "",
                    "### Original request",
                    "",
                    request["original_text"],
                )
            ),
        )

    def _commit_planner(self, kb, request, result) -> None:
        tasks = list(result.output.get("tasks", []))
        self.traceability.check(request["request_id"], tasks)
        interpretation = str(result.output.get("interpretation", ""))
        self.store.replace_tasks(request["request_id"], tasks)
        self.store.update_planner_interpretation(
            request["request_id"],
            interpretation,
        )
        kb.append(
            "REQUESTS.md",
            f"### Planner interpretation\n\n{interpretation}",
        )
        blocks = []
        for task in tasks:
            criteria = "\n".join(
                f"  - {item}"
                for item in task.get("acceptance_criteria", [])
            )
            blocks.append(
                "\n".join(
                    (
                        f"## {task['task_id']}",
                        f"- Request: `{request['request_id']}`",
                        f"- Priority: {task.get('priority', 'Medium')}",
                        f"- Status: {task.get('status', 'Pending')}",
                        f"- Description: {task['description']}",
                        "- Acceptance criteria:",
                        criteria or "  - Not specified",
                    )
                )
            )
        kb.append("TASKS.md", "\n\n".join(blocks))

    def _commit_repo_analyzer(self, kb, request, result) -> None:
        # Context packages are persisted in stage_results; no KB mutation.
        return None

    def _commit_builder(self, kb, request, result) -> None:
        git_safety = self.git_safety_by_project.get(request["project_id"])
        changes = dict(result.output.get("changes", {}))
        if git_safety and changes:
            sha = git_safety.apply_and_commit(request["request_id"], changes)
            result.output["git_sha"] = sha
            self.store.append_history(
                request["request_id"],
                "GIT_COMMITTED",
                stage="builder",
                git_sha=sha,
                detail={"files": list(changes)},
            )

    def _commit_documentation(self, kb, request, result) -> None:
        kb.append(
            "LOGS.md",
            str(
                result.output.get(
                    "log_entry",
                    f"## {request['request_id']}\n\nMock implementation recorded.",
                )
            ),
        )
        notes = result.output.get("project_notes")
        if notes:
            kb.append("PROJECT_NOTES.md", str(notes))

    def _commit_tester(self, kb, request, result) -> None:
        kb.append(
            "TEST_LOGS.md",
            str(
                result.output.get(
                    "test_log",
                    (
                        f"## {request['request_id']}\n\n"
                        f"- Passed: {result.output.get('passed', 0)}\n"
                        f"- Failed: {result.output.get('failed', 0)}"
                    ),
                )
            ),
        )

    def _commit_reviewer(self, kb, request, result) -> None:
        return None

    def _commit_final_report(self, kb, request, result) -> None:
        task_ids = [task["task_id"] for task in self.store.tasks(request["request_id"])]
        kb.append(
            "TRACEABILITY.md",
            "\n".join(
                (
                    f"## {request['request_id']}",
                    f"- Tasks: {', '.join(f'`{task_id}`' for task_id in task_ids)}",
                    f"- Verdict: {result.output.get('verdict', 'complete')}",
                    f"- Report: {result.output.get('report', 'Pipeline completed.')}",
                )
            ),
        )
