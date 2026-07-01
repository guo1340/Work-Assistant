from pathlib import Path
import subprocess

import pytest

from app.agents.committer import AgentResultCommitter
from app.domain.models import RiskLevel, StageResult
from app.git.safety import GitSafety
from app.risk.rules import RiskRuleEngine


def _result(risk, output):
    return StageResult(
        stage="builder",
        request_id="REQ-1",
        output=output,
        model_used="mock",
        confidence=1.0,
        risk_level=risk,
    )


def test_high_diff_pattern_is_high_risk():
    assert (
        RiskRuleEngine().assess({"diff": "SELECT 1;\nDROP TABLE users;"}).level
        == RiskLevel.HIGH
    )


def test_config_file_change_is_medium():
    assert (
        RiskRuleEngine().assess({"files_changed": ["app/settings.yaml"]}).level
        == RiskLevel.MEDIUM
    )


def test_large_diff_boundary_is_low_at_threshold():
    diff = "\n".join(f"+line {i}" for i in range(400))
    assert RiskRuleEngine().assess({"diff": diff}).level == RiskLevel.LOW


def test_resolve_takes_max_of_agent_and_rule_risk():
    rules = RiskRuleEngine()
    # Agent says low, rule says high (auth path) -> high.
    level, reasons = rules.resolve(
        _result(RiskLevel.LOW, {"files_changed": ["auth/x.py"]})
    )
    assert level == RiskLevel.HIGH
    assert reasons
    # Agent says high, rule says low -> still high.
    level2, _ = rules.resolve(
        _result(RiskLevel.HIGH, {"files_changed": ["src/x.py"]})
    )
    assert level2 == RiskLevel.HIGH


def test_low_confidence_threshold_value():
    assert RiskRuleEngine().low_confidence_threshold == 0.7


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_git_safety_blocks_changes_escaping_root(tmp_path):
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "README.md").write_text("# T\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "init")
    safety = GitSafety(tmp_path)
    with pytest.raises(ValueError, match="escapes project root"):
        safety.apply_and_commit("REQ-1", {"../escape.txt": "nope"})
    # Cleanup branch to leave repo tidy (best effort).
    safety.reject("REQ-1")


def test_committer_keeps_live_reference_to_empty_git_registry(store):
    registry = {}

    committer = AgentResultCommitter(store, registry)

    assert committer.git_safety_by_project is registry
