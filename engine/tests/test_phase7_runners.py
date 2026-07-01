from pathlib import Path

from app.providers.subprocess import CommandResult
from app.testing.runners import (
    JavaTestRunner,
    PythonTestRunner,
    TestRunnerRegistry,
    TypeScriptTestRunner,
)


class FakeRunner:
    def __init__(self, output="", returncode=0):
        self.output = output
        self.returncode = returncode
        self.calls = []

    def run(self, command, *, cwd, stdin=None, timeout_seconds=600):
        self.calls.append(tuple(command))
        return CommandResult(
            tuple(command),
            self.returncode,
            self.output,
            "",
        )


def test_runner_priority_prefers_typescript_then_java_then_python(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"vitest"},"devDependencies":{"vitest":"1"}}',
        encoding="utf-8",
    )
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")

    assert TestRunnerRegistry().detect(tmp_path).id == "typescript"


def test_typescript_adapter_parses_vitest(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"vitest"},"devDependencies":{"vitest":"1"}}',
        encoding="utf-8",
    )
    fake = FakeRunner("Tests  12 passed (12)\nAll files | 87.5")
    result = TypeScriptTestRunner(fake).run(tmp_path)

    assert result.passed == 12
    assert result.failed == 0
    assert result.coverage == 0.875
    assert "--run" in result.command


def test_java_adapter_parses_maven_summary(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
    fake = FakeRunner("Tests run: 9, Failures: 1, Errors: 1, Skipped: 0", 1)
    result = JavaTestRunner(fake).run(tmp_path)

    assert result.passed == 7
    assert result.failed == 2
    assert not result.successful


def test_python_adapter_parses_pytest(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    fake = FakeRunner("46 passed, 2 failed in 3.2s", 1)
    result = PythonTestRunner(fake).run(tmp_path)

    assert result.passed == 46
    assert result.failed == 2


def test_registry_reports_unsupported_project(tmp_path):
    registry = TestRunnerRegistry()

    try:
        registry.run_detected(tmp_path)
    except LookupError as error:
        assert "no supported test runner" in str(error)
    else:
        raise AssertionError("unsupported project should fail")
