from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any


class RequestState(StrEnum):
    RECEIVED = "RECEIVED"
    LOGGED = "LOGGED"
    PLANNING = "PLANNING"
    PLANNED = "PLANNED"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    BUILDING = "BUILDING"
    BUILT = "BUILT"
    DOCUMENTING = "DOCUMENTING"
    TESTING = "TESTING"
    TESTED = "TESTED"
    REVIEWING = "REVIEWING"
    REVIEWED = "REVIEWED"
    REPORTED = "REPORTED"
    DONE = "DONE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class RiskLevel(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def from_value(cls, value: str) -> "RiskLevel":
        return cls[value.upper()]

    def __str__(self) -> str:
        return self.name.lower()


class Tier(IntEnum):
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3

    def __str__(self) -> str:
        return self.name.lower()


class Capability(StrEnum):
    SCAN = "scan"
    LOG = "log"
    PLAN = "plan"
    ANALYZE = "analyze"
    BUILD = "build"
    DOCUMENT = "document"
    TEST = "test"
    REVIEW = "review"
    REPORT = "report"


@dataclass(frozen=True)
class StageResult:
    stage: str
    request_id: str
    output: dict[str, Any]
    model_used: str
    confidence: float
    risk_level: RiskLevel
    missing_information: list[str] = field(default_factory=list)
    human_review_required: bool = False
    task_id: str | None = None
    rule_risk_level: RiskLevel = RiskLevel.LOW

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.stage.strip():
            raise ValueError("stage is required")
        if not self.request_id.strip():
            raise ValueError("request_id is required")

    @property
    def effective_risk_level(self) -> RiskLevel:
        return max(self.risk_level, self.rule_risk_level)


@dataclass(frozen=True)
class StageDefinition:
    name: str
    capability: Capability
    minimum_tier: Tier
    ready_state: RequestState
    running_state: RequestState | None
    success_state: RequestState
