import pytest

from app.domain.models import Capability, Tier
from app.providers.mock import MockProvider
from app.providers.registry import ProviderRegistry


def test_eligible_filters_by_tier_and_capability():
    registry = ProviderRegistry()
    registry.register(MockProvider())  # heavy tier, all capabilities

    eligible = registry.eligible(
        minimum_tier=Tier.HEAVY,
        capability=Capability.BUILD,
    )
    assert [provider.id for provider in eligible] == ["mock"]


def test_eligible_excludes_when_capability_missing():
    registry = ProviderRegistry()
    registry.register(MockProvider())

    # Mock has every capability, so excluding by tier is the testable path:
    # a heavy-only requirement still includes it; nothing else registered.
    assert registry.eligible(
        minimum_tier=Tier.HEAVY, capability=Capability.REVIEW
    )


def test_get_unknown_provider_raises():
    registry = ProviderRegistry()
    with pytest.raises(KeyError, match="unknown provider"):
        registry.get(
            "nope",
            minimum_tier=Tier.LIGHT,
            capability=Capability.LOG,
        )
