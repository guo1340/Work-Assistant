from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
from typing import Sequence

from app.providers.subprocess import CommandRunner


@dataclass(frozen=True)
class TestRunResult:
    runner: str
    command: tuple[str, ...]
    passed: int
    failed: int
    coverage: float | None
    exit_code: int
    output: str

    @property
    def successful(self) -> bool:
        return self.exit_code == 0 and self.failed == 0


class TestRunner(ABC):
    id: str
    priority: int

    def __init__(self, command_runner: CommandRunner | None = None):
        self.command_runner = command_runner or CommandRunner()

    @abstractmethod
    def detect(self, root: Path) -> bool:
        """Return whether this adapter owns the project."""

    def install_dependencies(self, root: Path) -> None:
        """Install dependencies when the adapter requires an explicit step."""

    @abstractmethod
    def command(self, root: Path) -> Sequence[str]:
        """Return the native test command."""

    def run(self, root: Path, timeout_seconds: int = 900) -> TestRunResult:
        command = tuple(self.command(root))
        result = self.command_runner.run(
            command,
            cwd=root,
            timeout_seconds=timeout_seconds,
        )
        passed, failed, coverage = self.parse(result.stdout + "\n" + result.stderr)
        return TestRunResult(
            runner=self.id,
            command=command,
            passed=passed,
            failed=failed,
            coverage=coverage,
            exit_code=result.returncode,
            output=(result.stdout + "\n" + result.stderr).strip(),
        )

    def parse(self, output: str) -> tuple[int, int, float | None]:
        passed = _last_int(output, r"(\d+)\s+passed") or 0
        failed = _last_int(output, r"(\d+)\s+failed") or 0
        coverage_percent = _last_float(
            output,
            r"(?:All files|TOTAL).*?(\d+(?:\.\d+)?)%",
        )
        return (
            passed,
            failed,
            coverage_percent / 100 if coverage_percent is not None else None,
        )


class TypeScriptTestRunner(TestRunner):
    id = "typescript"
    priority = 1

    def detect(self, root: Path) -> bool:
        package_path = root / "package.json"
        if not package_path.is_file():
            return False
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        dependencies = {
            **package.get("dependencies", {}),
            **package.get("devDependencies", {}),
        }
        scripts = package.get("scripts", {})
        return bool(
            "test" in scripts
            or "vitest" in dependencies
            or "jest" in dependencies
        )

    def install_dependencies(self, root: Path) -> None:
        if (root / "node_modules").is_dir():
            return
        npm = _windows_command("npm")
        command = (npm, "ci") if (root / "package-lock.json").is_file() else (npm, "install")
        result = self.command_runner.run(command, cwd=root, timeout_seconds=900)
        if result.returncode:
            raise RuntimeError(result.stderr or "npm dependency installation failed")

    def command(self, root: Path) -> Sequence[str]:
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        dependencies = {
            **package.get("dependencies", {}),
            **package.get("devDependencies", {}),
        }
        argument = "--runInBand" if "jest" in dependencies else "--run"
        return (_windows_command("npm"), "test", "--", argument)

    def parse(self, output: str) -> tuple[int, int, float | None]:
        passed = _last_int(output, r"Tests\s+(\d+)\s+passed")
        failed = _last_int(output, r"Tests\s+(\d+)\s+failed")
        if passed is None:
            passed = _last_int(output, r"(\d+)\s+passed") or 0
        if failed is None:
            failed = _last_int(output, r"(\d+)\s+failed") or 0
        coverage = _last_float(
            output,
            r"(?:All files|Statements).*?(\d+(?:\.\d+)?)",
        )
        return passed, failed, coverage / 100 if coverage is not None else None


class JavaTestRunner(TestRunner):
    id = "java"
    priority = 2

    def detect(self, root: Path) -> bool:
        return any(
            (root / filename).exists()
            for filename in ("pom.xml", "build.gradle", "build.gradle.kts")
        )

    def command(self, root: Path) -> Sequence[str]:
        if (root / "mvnw.cmd").is_file():
            return (str(root / "mvnw.cmd"), "test")
        if (root / "mvnw").is_file():
            return (str(root / "mvnw"), "test")
        if (root / "pom.xml").is_file():
            return (_windows_command("mvn"), "test")
        if (root / "gradlew.bat").is_file():
            return (str(root / "gradlew.bat"), "test")
        if (root / "gradlew").is_file():
            return (str(root / "gradlew"), "test")
        return (_windows_command("gradle"), "test")

    def parse(self, output: str) -> tuple[int, int, float | None]:
        matches = re.findall(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)",
            output,
        )
        if not matches:
            return 0, 0, None
        total = sum(int(match[0]) for match in matches)
        failed = sum(int(match[1]) + int(match[2]) for match in matches)
        return total - failed, failed, None


class PythonTestRunner(TestRunner):
    id = "python"
    priority = 3

    def detect(self, root: Path) -> bool:
        return bool(
            (root / "pytest.ini").is_file()
            or (root / "pyproject.toml").is_file()
            or (root / "tests").is_dir()
        )

    def command(self, root: Path) -> Sequence[str]:
        return (os.getenv("DEVFLOW_PYTHON", shutil.which("python") or "python"), "-m", "pytest")


class TestRunnerRegistry:
    __test__ = False

    def __init__(self, runners: Sequence[TestRunner] | None = None):
        self.runners = sorted(
            runners
            or (
                TypeScriptTestRunner(),
                JavaTestRunner(),
                PythonTestRunner(),
            ),
            key=lambda runner: runner.priority,
        )

    def detect(self, root: Path) -> TestRunner | None:
        return next((runner for runner in self.runners if runner.detect(root)), None)

    def run_detected(
        self,
        root: Path,
        *,
        install_dependencies: bool = False,
        timeout_seconds: int = 900,
    ) -> TestRunResult:
        runner = self.detect(root)
        if runner is None:
            raise LookupError("no supported test runner detected")
        if install_dependencies:
            runner.install_dependencies(root)
        return runner.run(root, timeout_seconds)


def _windows_command(name: str) -> str:
    if os.name == "nt":
        command = shutil.which(f"{name}.cmd")
        if command:
            return command
    return shutil.which(name) or name


def _last_int(text: str, pattern: str) -> int | None:
    matches = re.findall(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return int(matches[-1]) if matches else None


def _last_float(text: str, pattern: str) -> float | None:
    matches = re.findall(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return float(matches[-1]) if matches else None
