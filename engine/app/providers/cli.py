import json
import os
from pathlib import Path
import shutil
from typing import Sequence

from app.domain.models import Capability, StageResult, Tier
from app.providers.base import Provider, ProviderContext
from app.providers.subprocess import (
    CommandRunner,
    ProviderInvocationError,
    build_stage_prompt,
    parse_codex_jsonl,
    parse_stage_result,
)


SCHEMA_PATH = Path(__file__).with_name("stage_result.schema.json")


def _npm_command(name: str) -> str | None:
    appdata = os.getenv("APPDATA")
    if appdata:
        candidate = Path(appdata) / "npm" / f"{name}.cmd"
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


def _claude_command() -> str | None:
    appdata = os.getenv("APPDATA")
    if appdata:
        native = (
            Path(appdata)
            / "npm"
            / "node_modules"
            / "@anthropic-ai"
            / "claude-code"
            / "bin"
            / "claude.exe"
        )
        if native.is_file():
            return str(native)
    return _npm_command("claude")


class CliProvider(Provider):
    executable: str

    def __init__(
        self,
        executable: str,
        *,
        runner: CommandRunner | None = None,
        timeout_seconds: int = 600,
    ) -> None:
        self.executable = executable
        self.runner = runner or CommandRunner()
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self.executable)

    def _cwd(self, context: ProviderContext) -> Path:
        root = context.payload.get("project_root")
        return Path(str(root)).resolve() if root else Path.cwd()

    def _invoke_command(
        self,
        context: ProviderContext,
        command: Sequence[str],
        *,
        stdin: str | None = None,
    ) -> str:
        result = self.runner.run(
            command,
            cwd=self._cwd(context),
            stdin=stdin,
            timeout_seconds=self.timeout_seconds,
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ProviderInvocationError(
                f"{self.id} exited {result.returncode}: {detail[-1000:]}"
            )
        return result.stdout

    def authentication_status(self) -> str:
        return "unknown"


class CodexProvider(CliProvider):
    id = "codex"
    tier = Tier.HEAVY
    capabilities = frozenset(
        {
            Capability.ANALYZE,
            Capability.BUILD,
            Capability.TEST,
            Capability.REVIEW,
            Capability.DOCUMENT,
            Capability.REPORT,
        }
    )

    @classmethod
    def discover(cls, runner: CommandRunner | None = None) -> "CodexProvider | None":
        executable = _npm_command("codex")
        return cls(executable, runner=runner) if executable else None

    def invoke(self, context: ProviderContext) -> StageResult:
        prompt = build_stage_prompt(context, self.id)
        command = (
            self.executable,
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--sandbox",
            "read-only",
            "--disable",
            "apps",
            "--disable",
            "plugins",
            "--disable",
            "browser_use",
            "--disable",
            "in_app_browser",
            "--model",
            "gpt-5.4",
            "--config",
            'model_provider="chatgpt-http"',
            "--config",
            'model_providers.chatgpt-http.name="ChatGPT HTTP"',
            "--config",
            (
                'model_providers.chatgpt-http.base_url='
                '"https://chatgpt.com/backend-api/codex"'
            ),
            "--config",
            'model_providers.chatgpt-http.wire_api="responses"',
            "--config",
            "model_providers.chatgpt-http.requires_openai_auth=true",
            "--config",
            "model_providers.chatgpt-http.supports_websockets=false",
            "--cd",
            str(self._cwd(context)),
            "-",
        )
        result = self.runner.run(
            command,
            cwd=self._cwd(context),
            stdin=prompt,
            timeout_seconds=self.timeout_seconds,
        )
        try:
            return parse_codex_jsonl(result.stdout, context, self.id)
        except ProviderInvocationError:
            if result.returncode:
                detail = result.stderr.strip() or result.stdout.strip()
                raise ProviderInvocationError(
                    f"{self.id} exited {result.returncode}: {detail[-1000:]}"
                )
            raise

    def authentication_status(self) -> str:
        result = self.runner.run(
            (self.executable, "login", "status"),
            cwd=Path.cwd(),
            timeout_seconds=20,
        )
        text = f"{result.stdout}\n{result.stderr}".lower()
        return "authenticated" if result.returncode == 0 and "logged in" in text else "login_required"


class ClaudeProvider(CliProvider):
    id = "claude-code"
    tier = Tier.HEAVY
    capabilities = frozenset(Capability)

    @classmethod
    def discover(cls, runner: CommandRunner | None = None) -> "ClaudeProvider | None":
        executable = _claude_command()
        return cls(executable, runner=runner) if executable else None

    def invoke(self, context: ProviderContext) -> StageResult:
        prompt = build_stage_prompt(context, self.id)
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        stdout = self._invoke_command(
            context,
            (
                self.executable,
                "-p",
                "--output-format",
                "json",
                "--json-schema",
                schema,
                "--permission-mode",
                "dontAsk",
                "--tools",
                "Read,Glob,Grep",
                "--no-session-persistence",
            ),
            stdin=prompt,
        )
        return parse_stage_result(stdout, context, self.id)

    def authentication_status(self) -> str:
        result = self.runner.run(
            (self.executable, "auth", "status", "--json"),
            cwd=Path.cwd(),
            timeout_seconds=20,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return "unknown"
        return "authenticated" if payload.get("loggedIn") else "login_required"


class CursorProvider(CliProvider):
    id = "cursor"
    tier = Tier.LIGHT
    capabilities = frozenset({Capability.LOG, Capability.PLAN})

    def __init__(
        self,
        executable: str = "wsl.exe",
        *,
        agent_path: str = "~/.local/bin/cursor-agent",
        runner: CommandRunner | None = None,
        timeout_seconds: int = 600,
    ) -> None:
        super().__init__(
            executable,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        self.agent_path = agent_path

    @classmethod
    def discover(cls, runner: CommandRunner | None = None) -> "CursorProvider | None":
        wsl = shutil.which("wsl.exe")
        if not wsl:
            return None
        probe_runner = runner or CommandRunner()
        result = probe_runner.run(
            (
                wsl,
                "bash",
                "-lc",
                'test -x ~/.local/bin/cursor-agent && '
                'readlink -f ~/.local/bin/cursor-agent',
            ),
            cwd=Path.cwd(),
            timeout_seconds=15,
        )
        agent_path = result.stdout.strip()
        return (
            cls(wsl, agent_path=agent_path, runner=runner)
            if result.returncode == 0 and agent_path
            else None
        )

    def invoke(self, context: ProviderContext) -> StageResult:
        prompt = build_stage_prompt(context, self.id)
        linux_root = self._wsl_path(self._cwd(context))
        stdout = self._invoke_command(
            context,
            (
                self.executable,
                "--cd",
                linux_root,
                self.agent_path,
                "-p",
                "--output-format",
                "json",
                "--mode",
                "ask",
                "--trust",
                "--",
                prompt,
            ),
        )
        return parse_stage_result(stdout, context, self.id)

    def _wsl_path(self, path: Path) -> str:
        result = self.runner.run(
            (self.executable, "wslpath", "-a", str(path)),
            cwd=Path.cwd(),
            timeout_seconds=15,
        )
        if result.returncode:
            raise ProviderInvocationError("could not translate project path for WSL")
        return result.stdout.strip()

    def authentication_status(self) -> str:
        result = self.runner.run(
            (
                self.executable,
                self.agent_path,
                "status",
            ),
            cwd=Path.cwd(),
            timeout_seconds=30,
        )
        text = f"{result.stdout}\n{result.stderr}".lower()
        return "authenticated" if result.returncode == 0 and "not logged in" not in text else "login_required"


def discover_cli_providers(
    runner: CommandRunner | None = None,
) -> list[CliProvider]:
    providers: list[CliProvider] = []
    for factory in (
        CodexProvider.discover,
        ClaudeProvider.discover,
        CursorProvider.discover,
    ):
        provider = factory(runner)
        if provider is not None:
            providers.append(provider)
    return providers
