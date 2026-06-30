from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.domain.models import Capability, StageResult, Tier


@dataclass(frozen=True)
class ProviderContext:
    stage: str
    request_id: str
    payload: dict[str, Any]
    task_id: str | None = None


class Provider(ABC):
    id: str
    tier: Tier
    capabilities: frozenset[Capability]

    @abstractmethod
    def invoke(self, context: ProviderContext) -> StageResult:
        """Execute one stateless stage and return its result."""
