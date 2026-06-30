from app.domain.models import (
    Capability,
    RequestState,
    StageDefinition,
    Tier,
)


PIPELINE: tuple[StageDefinition, ...] = (
    StageDefinition(
        "request_logger",
        Capability.LOG,
        Tier.LIGHT,
        RequestState.RECEIVED,
        None,
        RequestState.LOGGED,
    ),
    StageDefinition(
        "planner",
        Capability.PLAN,
        Tier.LIGHT,
        RequestState.LOGGED,
        RequestState.PLANNING,
        RequestState.PLANNED,
    ),
    StageDefinition(
        "repo_analyzer",
        Capability.ANALYZE,
        Tier.MEDIUM,
        RequestState.PLANNED,
        RequestState.ANALYZING,
        RequestState.ANALYZED,
    ),
    StageDefinition(
        "builder",
        Capability.BUILD,
        Tier.HEAVY,
        RequestState.ANALYZED,
        RequestState.BUILDING,
        RequestState.BUILT,
    ),
    StageDefinition(
        "documentation",
        Capability.DOCUMENT,
        Tier.LIGHT,
        RequestState.BUILT,
        RequestState.DOCUMENTING,
        RequestState.TESTING,
    ),
    StageDefinition(
        "tester",
        Capability.TEST,
        Tier.MEDIUM,
        RequestState.TESTING,
        None,
        RequestState.TESTED,
    ),
    StageDefinition(
        "reviewer",
        Capability.REVIEW,
        Tier.HEAVY,
        RequestState.TESTED,
        RequestState.REVIEWING,
        RequestState.REVIEWED,
    ),
    StageDefinition(
        "final_report",
        Capability.REPORT,
        Tier.LIGHT,
        RequestState.REVIEWED,
        None,
        RequestState.REPORTED,
    ),
)

STAGES_BY_NAME = {stage.name: stage for stage in PIPELINE}
STAGES_BY_READY_STATE = {stage.ready_state: stage for stage in PIPELINE}
