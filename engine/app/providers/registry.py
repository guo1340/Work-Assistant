from app.domain.models import Capability, Tier
from app.providers.base import Provider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        if provider.id in self._providers:
            raise ValueError(f"provider already registered: {provider.id}")
        self._providers[provider.id] = provider

    def get(
        self,
        provider_id: str,
        *,
        minimum_tier: Tier,
        capability: Capability,
    ) -> Provider:
        try:
            provider = self._providers[provider_id]
        except KeyError as error:
            raise KeyError(f"unknown provider: {provider_id}") from error
        if provider.tier < minimum_tier:
            raise ValueError(
                f"provider {provider_id} is {provider.tier}; "
                f"{minimum_tier} is required"
            )
        if capability not in provider.capabilities:
            raise ValueError(
                f"provider {provider_id} lacks capability: {capability}"
            )
        return provider

    def eligible(
        self,
        *,
        minimum_tier: Tier,
        capability: Capability,
    ) -> list[Provider]:
        return [
            provider
            for provider in self._providers.values()
            if provider.tier >= minimum_tier
            and capability in provider.capabilities
        ]
