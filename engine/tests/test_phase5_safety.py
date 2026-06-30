from pathlib import Path
import subprocess

from app.git.safety import GitSafety
from app.risk.rules import RiskRuleEngine
from app.domain.models import RiskLevel


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_risk_rules_classify_high_medium_and_low():
    rules = RiskRuleEngine()

    assert rules.assess({"files_changed": ["auth/session.py"]}).level == RiskLevel.HIGH
    assert rules.assess({"files_deleted": ["notes.txt"]}).level == RiskLevel.HIGH
    assert rules.assess({"files_changed": ["package.json"]}).level == RiskLevel.MEDIUM
    assert rules.assess({"files_changed": ["src/view.tsx"]}).level == RiskLevel.LOW


def test_large_diff_threshold_is_medium():
    diff = "\n".join(f"+line {index}" for index in range(401))
    assert RiskRuleEngine().assess({"diff": diff}).level == RiskLevel.MEDIUM


def test_git_safety_commits_on_request_branch_and_rejects_cleanly(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-m", "Initial")
    safety = GitSafety(tmp_path)

    sha = safety.apply_and_commit(
        "REQ-2026-0001",
        {"src/output.txt": "implemented\n"},
    )

    assert git(tmp_path, "branch", "--show-current") == "devflow/REQ-2026-0001"
    assert sha == git(tmp_path, "rev-parse", "HEAD")
    safety.reject("REQ-2026-0001")
    assert git(tmp_path, "branch", "--show-current") == "main"
    assert not (tmp_path / "src" / "output.txt").exists()
