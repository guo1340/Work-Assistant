import dataclasses

import pytest

from app.domain.models import RiskLevel, StageResult, Tier


def _result(**overrides):
    base = dict(
        stage="planner",
        request_id="REQ-1",
        output={},
        model_used="mock",
        confidence=0.5,
        risk_level=RiskLevel.LOW,
    )
    base.update(overrides)
    return StageResult(**base)


def test_stage_result_rejects_out_of_range_confidence():
    with pytest.raises(ValueError, match="confidence"):
        _result(confidence=1.5)
    with pytest.raises(ValueError, match="confidence"):
        _result(confidence=-0.1)


def test_stage_result_accepts_boundary_confidence():
    assert _result(confidence=0).confidence == 0
    assert _result(confidence=1).confidence == 1


def test_stage_result_requires_stage_and_request_id():
    with pytest.raises(ValueError, match="stage is required"):
        _result(stage="   ")
    with pytest.raises(ValueError, match="request_id is required"):
        _result(request_id="")


def test_stage_result_is_frozen():
    result = _result()
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.confidence = 0.9  # type: ignore[misc]


def test_risk_level_ordering_and_str():
    assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH
    assert str(RiskLevel.HIGH) == "high"
    assert RiskLevel.from_value("High") == RiskLevel.HIGH
    assert RiskLevel.from_value("medium") == RiskLevel.MEDIUM


def test_tier_ordering_and_str():
    assert Tier.LIGHT < Tier.MEDIUM < Tier.HEAVY
    assert str(Tier.MEDIUM) == "medium"
