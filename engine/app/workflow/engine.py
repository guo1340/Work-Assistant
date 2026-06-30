from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Any

from app.core.pipeline import STAGES_BY_NAME, STAGES_BY_READY_STATE
from app.db.store import StateStore, utc_now
from app.domain.models import RequestState, RiskLevel, StageDefinition
from app.providers.base import ProviderContext
from app.providers.registry import ProviderRegistry


@dataclass(frozen=True)
class EngineConfig:
    max_retries: int = 2
    retry_base_seconds: float = 0.25


class WorkflowEngine:
    def __init__(
        self,
        store: StateStore,
        providers: ProviderRegistry,
        config: EngineConfig | None = None,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.store = store
        self.providers = providers
        self.config = config or EngineConfig()
        self.sleeper = sleeper

    def next_stage(self, request_id: str) -> StageDefinition | None:
        state = RequestState(self.store.get_request(request_id)["state"])
        return STAGES_BY_READY_STATE.get(state)

    def run_next(
        self,
        request_id: str,
        provider_id: str,
        payload: dict[str, Any] | None = None,
    ) -> RequestState:
        stage = self.next_stage(request_id)
        if stage is None:
            state = RequestState(self.store.get_request(request_id)["state"])
            if state == RequestState.REPORTED:
                self.store.transition(
                    request_id,
                    RequestState.REPORTED,
                    RequestState.DONE,
                    "REQUEST_COMPLETED",
                )
                return RequestState.DONE
            raise ValueError(f"no runnable stage for state {state}")

        provider = self.providers.get(
            provider_id,
            minimum_tier=stage.minimum_tier,
            capability=stage.capability,
        )
        initial_state = stage.ready_state
        if stage.running_state is not None:
            self.store.transition(
                request_id,
                initial_state,
                stage.running_state,
                "STAGE_STARTED",
                stage=stage.name,
            )
            active_state = stage.running_state
        else:
            self.store.record_stage_started(
                request_id,
                stage.name,
                initial_state,
            )
            active_state = initial_state

        context = ProviderContext(
            stage=stage.name,
            request_id=request_id,
            payload=payload or {},
        )
        result = self._invoke_with_retries(
            stage,
            provider_id,
            provider.invoke,
            context,
            active_state,
        )
        if result is None:
            return RequestState.FAILED

        if (
            result.risk_level == RiskLevel.HIGH
            or result.human_review_required
        ):
            reasons = []
            if result.risk_level == RiskLevel.HIGH:
                reasons.append("stage reported high risk")
            if result.human_review_required:
                reasons.append("stage requested human review")
            self.store.create_approval(
                request_id,
                stage.name,
                "; ".join(reasons),
            )
            self.store.transition(
                request_id,
                active_state,
                RequestState.AWAITING_APPROVAL,
                "APPROVAL_REQUIRED",
                stage=stage.name,
                detail={"target_state": stage.success_state},
            )
            return RequestState.AWAITING_APPROVAL

        self.store.transition(
            request_id,
            active_state,
            stage.success_state,
            "COMMITTED",
            stage=stage.name,
        )
        return stage.success_state

    def approve(self, request_id: str, decided_by: str) -> RequestState:
        approval = self.store.pending_approval(request_id)
        stage = STAGES_BY_NAME[approval["stage"]]
        self.store.decide_approval(approval["id"], "approved", decided_by)
        self.store.transition(
            request_id,
            RequestState.AWAITING_APPROVAL,
            stage.success_state,
            "APPROVED",
            stage=stage.name,
            detail={"decided_by": decided_by},
        )
        return stage.success_state

    def reject(self, request_id: str, decided_by: str) -> RequestState:
        approval = self.store.pending_approval(request_id)
        self.store.decide_approval(approval["id"], "rejected", decided_by)
        self.store.transition(
            request_id,
            RequestState.AWAITING_APPROVAL,
            RequestState.REJECTED,
            "REJECTED",
            stage=approval["stage"],
            detail={"decided_by": decided_by},
        )
        return RequestState.REJECTED

    def _invoke_with_retries(
        self,
        stage: StageDefinition,
        provider_id: str,
        invoke: Callable[[ProviderContext], Any],
        context: ProviderContext,
        active_state: RequestState,
    ) -> Any | None:
        for attempt in range(self.config.max_retries + 1):
            started_at = utc_now()
            started_clock = monotonic()
            try:
                result = invoke(context)
                if (
                    result.stage != stage.name
                    or result.request_id != context.request_id
                ):
                    raise ValueError(
                        "provider returned a result for the wrong stage or request"
                    )
            except Exception as error:
                finished_at = utc_now()
                duration_ms = round((monotonic() - started_clock) * 1000)
                self.store.record_failed_attempt(
                    context.request_id,
                    stage.name,
                    model_used=provider_id,
                    error=str(error),
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                )
                if attempt == self.config.max_retries:
                    self.store.transition(
                        context.request_id,
                        active_state,
                        RequestState.FAILED,
                        "RETRIES_EXHAUSTED",
                        stage=stage.name,
                        detail={"attempts": attempt + 1, "error": str(error)},
                    )
                    return None
                delay = self.config.retry_base_seconds * (2**attempt)
                self.store.transition(
                    context.request_id,
                    active_state,
                    RequestState.RETRYING,
                    "RETRY",
                    stage=stage.name,
                    detail={
                        "attempt": attempt + 1,
                        "delay_seconds": delay,
                        "error": str(error),
                    },
                )
                self.sleeper(delay)
                self.store.transition(
                    context.request_id,
                    RequestState.RETRYING,
                    active_state,
                    "RETRY_STARTED",
                    stage=stage.name,
                )
                continue

            finished_at = utc_now()
            duration_ms = round((monotonic() - started_clock) * 1000)
            self.store.commit_stage_result(
                result,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )
            return result
        return None
