from collections.abc import Callable
from typing import Any

from app.domain.models import Capability, RiskLevel, StageResult, Tier
from app.providers.base import Provider, ProviderContext


class MockProvider(Provider):
    id = "mock"
    tier = Tier.HEAVY
    capabilities = frozenset(Capability)

    def __init__(
        self,
        responses: dict[str, dict[str, Any]] | None = None,
        failure_plan: dict[str, int] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.failure_plan = dict(failure_plan or {})
        self.invocations: list[ProviderContext] = []

    def invoke(self, context: ProviderContext) -> StageResult:
        self.invocations.append(context)
        failures_remaining = self.failure_plan.get(context.stage, 0)
        if failures_remaining:
            self.failure_plan[context.stage] = failures_remaining - 1
            raise RuntimeError(f"planned mock failure for {context.stage}")

        response = self.responses.get(context.stage, {})
        output_factory: Callable[[ProviderContext], dict[str, Any]] | None = (
            response.get("output_factory")
        )
        output = (
            output_factory(context)
            if output_factory
            else response.get("output", self._default_output(context))
        )
        return StageResult(
            stage=context.stage,
            request_id=context.request_id,
            task_id=context.task_id,
            output=output,
            model_used=self.id,
            confidence=response.get("confidence", 1.0),
            risk_level=RiskLevel.from_value(
                response.get("risk_level", "low")
            ),
            missing_information=response.get("missing_information", []),
            human_review_required=response.get(
                "human_review_required",
                False,
            ),
        )

    @staticmethod
    def _default_output(context: ProviderContext) -> dict[str, Any]:
        sequence = context.request_id.rsplit("-", 1)[-1]
        task_id = f"TASK-{sequence}-01"
        outputs: dict[str, dict[str, Any]] = {
            "project_scanner": {
                "summary": "Local project understood from its repository context.",
                "languages": [],
                "documents": {
                    "PROJECT_NOTES.md": (
                        "## DevFlow scan\n\nRepository inventory synthesized "
                        "by the mock provider."
                    )
                },
            },
            "request_logger": {"captured": True},
            "planner": {
                "interpretation": context.payload.get(
                    "original_text",
                    "Implement the logged request.",
                ),
                "tasks": [
                    {
                        "task_id": task_id,
                        "request_id": context.request_id,
                        "description": "Implement the logged request",
                        "priority": "High",
                        "acceptance_criteria": [
                            "The requested behavior is implemented",
                            "Relevant tests pass",
                        ],
                        "dependencies": [],
                        "estimated_files": [],
                        "status": "Pending",
                    }
                ],
            },
            "repo_analyzer": {
                "context_files": ["PROJECT_NOTES.md", "LOGS.md"],
                "git_diff": "",
                "notes": "Minimal mock context package.",
            },
            "builder": {
                "files_changed": [],
                "changes": {},
                "diff": "",
                "diff_summary": "Mock builder completed without filesystem changes.",
            },
            "documentation": {
                "log_entry": (
                    f"## {context.request_id}\n\n"
                    "Mock builder output committed by the engine."
                )
            },
            "tester": {
                "passed": 1,
                "failed": 0,
                "coverage": 1.0,
                "regressions": [],
            },
            "reviewer": {
                "missing": [],
                "invented": [],
                "scope_creep": [],
                "verdict": "approved",
            },
            "final_report": {
                "verdict": "complete",
                "report": "All mock pipeline stages completed successfully.",
            },
        }
        return outputs.get(
            context.stage,
            {"message": f"mock {context.stage} completed"},
        )
