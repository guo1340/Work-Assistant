import pytest

from app.domain.models import Capability, RiskLevel, StageResult, Tier
from app.providers.base import Provider, ProviderContext
from app.providers.mock import MockProvider
from app.providers.registry import ProviderRegistry


class LightPlanner(Provider):
    id = "light-planner"
    tier = Tier.LIGHT
    capabilities = frozenset({Capability.PLAN})

    def invoke(self, context: ProviderContext) -> StageResult:
        return StageResult(
            stage=context.stage,
            request_id=context.request_id,
            output={},
            model_used=self.id,
            confidence=1,
            risk_level=RiskLevel.LOW,
        )


def test_registry_enforces_tier_and_capability():
    provider = MockProvider()
    registry = ProviderRegistry()
    registry.register(provider)

    assert (
        registry.get(
            "mock",
            minimum_tier=Tier.HEAVY,
            capability=Capability.BUILD,
        )
        is provider
    )


def test_registry_rejects_duplicate_provider():
    registry = ProviderRegistry()
    registry.register(MockProvider())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(MockProvider())


def test_registry_rejects_provider_below_minimum_tier():
    registry = ProviderRegistry()
    registry.register(LightPlanner())

    with pytest.raises(ValueError, match="heavy is required"):
        registry.get(
            "light-planner",
            minimum_tier=Tier.HEAVY,
            capability=Capability.PLAN,
        )


def test_registry_rejects_missing_capability():
    registry = ProviderRegistry()
    registry.register(LightPlanner())

    with pytest.raises(ValueError, match="lacks capability"):
        registry.get(
            "light-planner",
            minimum_tier=Tier.LIGHT,
            capability=Capability.BUILD,
        )
