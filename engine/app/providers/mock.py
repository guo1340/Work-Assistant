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
            else response.get(
                "output",
                {"message": f"mock {context.stage} completed"},
            )
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
