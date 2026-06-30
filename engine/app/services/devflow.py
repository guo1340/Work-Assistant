import json
from pathlib import Path
from threading import Lock
from typing import Any

from app.agents.committer import AgentResultCommitter
from app.db.store import StateStore
from app.domain.models import RequestState
from app.git.safety import GitSafety
from app.providers.mock import MockProvider
from app.providers.registry import ProviderRegistry
from app.risk.rules import RiskRuleEngine
from app.scanner.project import ProjectScanner
from app.workflow.engine import WorkflowEngine


class DevFlowService:
    def __init__(self, store: StateStore):
        self.store = store
        self.providers = ProviderRegistry()
        self.mock_provider = MockProvider()
        self.providers.register(self.mock_provider)
        self.git_safety: dict[int, GitSafety] = {}
        for project in self.store.list_projects():
            root = Path(project["root_path"])
            if (root / ".git").is_dir():
                self.git_safety[project["id"]] = GitSafety(root)
        self.committer = AgentResultCommitter(store, self.git_safety)
        self.engine = WorkflowEngine(
            store,
            self.providers,
            committer=self.committer,
            risk_rules=RiskRuleEngine(),
        )
        self.scanner = ProjectScanner(store, self.mock_provider)
        self._lock = Lock()

    def add_project(
        self,
        name: str,
        root_path: str,
        scan_type: str = "soft",
    ) -> dict[str, Any]:
        root = Path(root_path).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"project directory does not exist: {root}")
        with self._lock:
            project_id = self.scanner.register_and_scan(name, root, scan_type)
            if (root / ".git").is_dir():
                self.git_safety[project_id] = GitSafety(root)
            return self.project(project_id)

    def scan_project(self, project_id: int, scan_type: str) -> dict[str, Any]:
        with self._lock:
            return self.scanner.scan(project_id, scan_type)

    def project(self, project_id: int) -> dict[str, Any]:
        project = self.store.get_project(project_id)
        project["languages"] = json.loads(project["languages"] or "[]")
        return project

    def projects(self) -> list[dict[str, Any]]:
        return [self.project(project["id"]) for project in self.store.list_projects()]

    def create_request(self, project_id: int, original_text: str) -> dict[str, Any]:
        if not original_text.strip():
            raise ValueError("request text is required")
        self.store.get_project(project_id)
        with self._lock:
            request_id = self.store.next_request_id()
            self.store.create_request(request_id, project_id, original_text)
        return self.request_detail(request_id)

    def advance_request(
        self,
        request_id: str,
        provider_id: str = "mock",
    ) -> dict[str, Any]:
        request = self.store.get_request(request_id)
        payload = self._stage_payload(request_id, request)
        with self._lock:
            self.engine.run_next(request_id, provider_id, payload)
        return self.request_detail(request_id)

    def approve(self, request_id: str, decided_by: str) -> dict[str, Any]:
        with self._lock:
            self.engine.approve(request_id, decided_by)
        return self.request_detail(request_id)

    def reject(self, request_id: str, decided_by: str) -> dict[str, Any]:
        with self._lock:
            self.engine.reject(request_id, decided_by)
        return self.request_detail(request_id)

    def request_detail(self, request_id: str) -> dict[str, Any]:
        request = self.store.get_request(request_id)
        results = self.store.stage_results(request_id)
        for result in results:
            result["output"] = json.loads(result["output"] or "{}")
            result["missing_information"] = json.loads(
                result["missing_information"] or "[]"
            )
            result["human_review_required"] = bool(
                result["human_review_required"]
            )
        tasks = self.store.tasks(request_id)
        for task in tasks:
            for key in (
                "acceptance_criteria",
                "dependencies",
                "estimated_files",
            ):
                task[key] = json.loads(task[key] or "[]")
        approval = None
        if request["state"] == RequestState.AWAITING_APPROVAL:
            approval = self.store.pending_approval(request_id)
        final_report = next(
            (
                result["output"]
                for result in reversed(results)
                if result["stage"] == "final_report"
                and result["status"] == "success"
            ),
            None,
        )
        return {
            **request,
            "tasks": tasks,
            "stage_results": results,
            "history": self.store.history(request_id),
            "approval": approval,
            "final_report": final_report,
            "next_stage": (
                self.engine.next_stage(request_id).name
                if self.engine.next_stage(request_id)
                else None
            ),
        }

    def requests(self, project_id: int) -> list[dict[str, Any]]:
        return self.store.list_requests(project_id)

    def provider_options(self) -> list[dict[str, Any]]:
        return [
            {
                "id": self.mock_provider.id,
                "tier": str(self.mock_provider.tier),
                "capabilities": sorted(
                    capability.value
                    for capability in self.mock_provider.capabilities
                ),
            }
        ]

    def _stage_payload(
        self,
        request_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        project = self.store.get_project(request["project_id"])
        return {
            "original_text": request["original_text"],
            "planner_interpretation": request["planner_interpretation"],
            "tasks": self.store.tasks(request_id),
            "project_root": project["root_path"],
            "history": self.store.history(request_id)[-10:],
        }
