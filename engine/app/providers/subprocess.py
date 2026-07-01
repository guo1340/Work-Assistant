from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Sequence
from urllib.request import getproxies

from app.domain.models import RiskLevel, StageResult
from app.providers.base import ProviderContext
from app.prompts.registry import PromptRegistry


class ProviderInvocationError(RuntimeError):
    pass


STAGE_OUTPUT_EXAMPLES: dict[str, dict[str, Any]] = {
    "request_logger": {"captured": True},
    "planner": {
        "interpretation": "Concise interpretation of the verbatim request.",
        "tasks": [
            {
                "task_id": "TASK-0001-01",
                "request_id": "REQ-2026-0001",
                "description": "Implement one traceable task.",
                "priority": "High",
                "acceptance_criteria": ["Observable requirement is satisfied."],
                "dependencies": [],
                "estimated_files": [],
                "status": "Pending",
            }
        ],
    },
    "repo_analyzer": {
        "context_files": [],
        "git_diff": "",
        "notes": "Minimal relevant context for the Builder.",
    },
    "builder": {
        "changes": {"relative/path.ext": "complete file contents"},
        "files_changed": ["relative/path.ext"],
        "diff_summary": "What changed and why.",
    },
    "documentation": {
        "log_entry": "Markdown implementation log entry.",
        "project_notes": "Optional durable project knowledge.",
    },
    "tester": {
        "passed": 1,
        "failed": 0,
        "coverage": None,
        "regressions": [],
        "test_log": "Markdown test evidence.",
    },
    "reviewer": {
        "verdict": "approved",
        "missing": [],
        "invented": [],
        "partial": [],
        "scope_creep": [],
    },
    "final_report": {
        "verdict": "complete",
        "report": "Traceable outcome with implementation and test evidence.",
        "traceability": [],
    },
}


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        stdin: str | None = None,
        timeout_seconds: int = 600,
    ) -> CommandResult:
        environment = os.environ.copy()
        proxies = getproxies()
        for variable, scheme in (
            ("HTTP_PROXY", "http"),
            ("HTTPS_PROXY", "https"),
        ):
            if variable not in environment and proxies.get(scheme):
                environment[variable] = proxies[scheme]
        if "ALL_PROXY" not in environment:
            proxy = proxies.get("https") or proxies.get("http")
            if proxy:
                environment["ALL_PROXY"] = proxy
        try:
            completed = subprocess.run(
                list(command),
                cwd=cwd,
                input=stdin,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ProviderInvocationError(
                f"provider timed out after {timeout_seconds} seconds"
            ) from error
        except OSError as error:
            raise ProviderInvocationError(
                f"provider executable could not start: {error}"
            ) from error
        return CommandResult(
            command=tuple(command),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def build_stage_prompt(context: ProviderContext, provider_id: str) -> str:
    output_example = STAGE_OUTPUT_EXAMPLES.get(
        context.stage,
        {"message": "Stage-specific result."},
    )
    contract = {
        "stage": context.stage,
        "request_id": context.request_id,
        "task_id": context.task_id,
        "output": output_example,
        "model_used": provider_id,
        "confidence": 0.9,
        "risk_level": "low",
        "missing_information": [],
        "human_review_required": False,
    }
    return PromptRegistry().render(
        context.stage,
        {
            "stage": context.stage,
            "context_json": json.dumps(context.payload, ensure_ascii=False),
            "contract_json": json.dumps(contract),
        },
    )


def parse_stage_result(
    text: str,
    context: ProviderContext,
    provider_id: str,
) -> StageResult:
    payload = _extract_json_object(text)
    if payload.get("type") == "result":
        payload = _unwrap_provider_result(payload)
    if "structured_output" in payload:
        payload = payload["structured_output"]
    elif isinstance(payload.get("result"), str):
        payload = _extract_json_object(payload["result"])
    elif isinstance(payload.get("result"), dict):
        payload = payload["result"]
    output = payload.get("output")
    if (
        isinstance(output, dict)
        and set(output) == {"stage_specific"}
        and isinstance(output["stage_specific"], dict)
    ):
        payload["output"] = output["stage_specific"]
    try:
        return StageResult(
            stage=str(payload["stage"]),
            request_id=str(payload["request_id"]),
            task_id=payload.get("task_id"),
            output=dict(payload.get("output", {})),
            model_used=str(payload.get("model_used") or provider_id),
            confidence=float(payload["confidence"]),
            risk_level=RiskLevel.from_value(str(payload["risk_level"])),
            missing_information=list(payload.get("missing_information", [])),
            human_review_required=bool(
                payload.get("human_review_required", False)
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderInvocationError(
            f"{provider_id} returned an invalid Stage Result: {error}"
        ) from error


def parse_codex_jsonl(
    text: str,
    context: ProviderContext,
    provider_id: str,
) -> StageResult:
    messages: list[str] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if (
            event.get("type") == "item.completed"
            and item.get("type") in {"agent_message", "assistant_message"}
        ):
            message = item.get("text") or item.get("content")
            if isinstance(message, str):
                messages.append(message)
    candidate = messages[-1] if messages else text
    return parse_stage_result(candidate, context, provider_id)


def _unwrap_provider_result(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("result", "structured_output", "message"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip().startswith(("{", "```")):
            return _extract_json_object(value)
    return payload


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for index, character in enumerate(stripped):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ProviderInvocationError("provider output did not contain a JSON object")
