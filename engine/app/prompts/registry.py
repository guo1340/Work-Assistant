from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class PromptRegistry:
    def __init__(
        self,
        prompt_root: Path = PROJECT_ROOT / "prompts",
        active_versions: dict[str, str] | None = None,
    ) -> None:
        self.prompt_root = prompt_root
        self.active_versions = active_versions or {}

    def render(self, stage: str, variables: dict[str, str]) -> str:
        version = self.active_versions.get(stage, "v1")
        path = self.prompt_root / stage / f"{version}.md"
        if not path.is_file():
            raise KeyError(f"no active prompt for stage {stage}: {version}")
        text = path.read_text(encoding="utf-8")
        for name, value in variables.items():
            text = text.replace(f"{{{{{name}}}}}", value)
        unresolved = [
            part.split("}}", 1)[0]
            for part in text.split("{{")[1:]
            if "}}" in part
        ]
        if unresolved:
            raise ValueError(
                f"unresolved prompt variables for {stage}: {', '.join(unresolved)}"
            )
        return text
