import json
from pathlib import Path

import pytest

from app.domain.models import Capability
from app.providers.base import ProviderContext
from app.providers.cli import ClaudeProvider, CodexProvider, CursorProvider
from app.providers.subprocess import (
    CommandResult,
    ProviderInvocationError,
    build_stage_prompt,
    parse_stage_result,
)


def stage_payload(provider: str) -> dict:
    return {
        "stage": "planner",
        "request_id": "REQ-2026-0001",
        "task_id": None,
        "output": {"tasks": []},
        "model_used": provider,
        "confidence": 0.9,
        "risk_level": "low",
        "missing_information": [],
        "human_review_required": False,
    }


class FakeRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def run(self, command, *, cwd, stdin=None, timeout_seconds=600):
        self.calls.append(
            {
                "command": tuple(command),
                "cwd": cwd,
                "stdin": stdin,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.results.pop(0)


def result(stdout="", stderr="", returncode=0):
    return CommandResult(("fake",), returncode, stdout, stderr)


def context(tmp_path: Path, stage="planner") -> ProviderContext:
    return ProviderContext(
        stage=stage,
        request_id="REQ-2026-0001",
        payload={"project_root": str(tmp_path), "original_text": "Build it."},
    )


def test_codex_provider_uses_stdin_read_only_and_parses_jsonl(tmp_path):
    payload = stage_payload("codex")
    event = {
        "type": "item.completed",
        "item": {"type": "agent_message", "text": json.dumps(payload)},
    }
    runner = FakeRunner([result(json.dumps(event))])
    provider = CodexProvider("codex", runner=runner)

    stage_result = provider.invoke(context(tmp_path))

    assert stage_result.model_used == "codex"
    command = runner.calls[0]["command"]
    assert "--sandbox" in command
    assert "read-only" in command
    assert command.count("--disable") == 4
    assert {"apps", "plugins", "browser_use", "in_app_browser"} <= set(command)
    assert "gpt-5.4" in command
    assert "model_providers.chatgpt-http.supports_websockets=false" in command
    assert command[-1] == "-"
    assert runner.calls[0]["stdin"]


def test_codex_accepts_valid_result_when_nonessential_post_sets_exit_one(tmp_path):
    payload = stage_payload("codex")
    event = {
        "type": "item.completed",
        "item": {"type": "agent_message", "text": json.dumps(payload)},
    }
    runner = FakeRunner(
        [result(json.dumps(event), stderr="analytics request failed", returncode=1)]
    )

    stage_result = CodexProvider("codex", runner=runner).invoke(context(tmp_path))

    assert stage_result.model_used == "codex"


def test_claude_provider_uses_noninteractive_structured_output(tmp_path):
    payload = stage_payload("claude-code")
    runner = FakeRunner([result(json.dumps({"structured_output": payload}))])
    provider = ClaudeProvider("claude", runner=runner)

    stage_result = provider.invoke(context(tmp_path))

    assert stage_result.stage == "planner"
    command = runner.calls[0]["command"]
    assert "-p" in command
    assert "--json-schema" in command
    assert "--permission-mode" in command
    assert "dontAsk" in command
    assert runner.calls[0]["stdin"]


def test_cursor_provider_is_light_and_planner_only(tmp_path):
    payload = stage_payload("cursor")
    runner = FakeRunner(
        [
            result("/mnt/e/project\n"),
            result(json.dumps({"type": "result", "result": json.dumps(payload)})),
        ]
    )
    provider = CursorProvider("wsl.exe", runner=runner)

    stage_result = provider.invoke(context(tmp_path))

    assert stage_result.model_used == "cursor"
    assert Capability.PLAN in provider.capabilities
    assert Capability.BUILD not in provider.capabilities
    assert "-p" in runner.calls[1]["command"]
    assert "ask" in runner.calls[1]["command"]
    assert runner.calls[1]["command"][-2] == "--"


def test_nonzero_cli_exit_is_actionable(tmp_path):
    runner = FakeRunner([result(stderr="not authenticated", returncode=1)])
    provider = ClaudeProvider("claude", runner=runner)

    with pytest.raises(ProviderInvocationError, match="not authenticated"):
        provider.invoke(context(tmp_path))


def test_parser_rejects_non_contract_output(tmp_path):
    with pytest.raises(ProviderInvocationError, match="invalid Stage Result"):
        parse_stage_result(
            '{"message":"hello"}',
            context(tmp_path),
            "provider",
        )


def test_prompt_uses_stage_specific_output_shape(tmp_path):
    prompt = build_stage_prompt(context(tmp_path, "builder"), "claude-code")

    assert '"changes"' in prompt
    assert '"stage_specific"' not in prompt


def test_parser_unwraps_accidental_stage_specific_output(tmp_path):
    payload = stage_payload("cursor")
    payload["output"] = {"stage_specific": {"tasks": []}}

    parsed = parse_stage_result(json.dumps(payload), context(tmp_path), "cursor")

    assert parsed.output == {"tasks": []}
