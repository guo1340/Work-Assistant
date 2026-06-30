from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from app.domain.models import RiskLevel, StageResult


DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "risk_rules.json"


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    reasons: tuple[str, ...]


class RiskRuleEngine:
    def __init__(self, rules_path: Path = DEFAULT_RULES_PATH):
        self.rules = json.loads(rules_path.read_text(encoding="utf-8"))

    def assess(self, output: dict[str, Any]) -> RiskAssessment:
        files = [
            str(path).replace("\\", "/").lower()
            for path in (
                output.get("files_changed", output.get("planned_files", []))
                or output.get("changes", {}).keys()
            )
        ]
        diff = str(output.get("diff", output.get("git_diff", "")))
        deleted = [
            str(path).replace("\\", "/").lower()
            for path in output.get("files_deleted", [])
        ]
        reasons: list[str] = []

        for path in files:
            if any(pattern in path for pattern in self.rules["high_path_patterns"]):
                reasons.append(f"high-risk path: {path}")
        if deleted:
            reasons.append("file deletion")
        for pattern in self.rules["high_diff_patterns"]:
            if pattern.lower() in diff.lower():
                reasons.append(f"high-risk diff pattern: {pattern}")
        if reasons:
            return RiskAssessment(RiskLevel.HIGH, tuple(dict.fromkeys(reasons)))

        for path in files:
            filename = Path(path).name
            if filename in self.rules["dependency_files"]:
                reasons.append(f"dependency file: {path}")
            elif Path(path).suffix in self.rules["config_suffixes"]:
                reasons.append(f"configuration file: {path}")
        changed_lines = sum(
            1
            for line in diff.splitlines()
            if (line.startswith("+") and not line.startswith("+++"))
            or (line.startswith("-") and not line.startswith("---"))
        )
        if changed_lines > self.rules["large_diff_lines"]:
            reasons.append(f"large diff: {changed_lines} changed lines")
        if reasons:
            return RiskAssessment(RiskLevel.MEDIUM, tuple(dict.fromkeys(reasons)))
        return RiskAssessment(RiskLevel.LOW, ())

    def resolve(self, result: StageResult) -> tuple[RiskLevel, tuple[str, ...]]:
        assessment = self.assess(result.output)
        return max(result.risk_level, assessment.level), assessment.reasons

    @property
    def low_confidence_threshold(self) -> float:
        return float(self.rules["low_confidence_threshold"])
