from pathlib import Path


KB_FILENAMES = (
    "README.md",
    "ARCHITECTURE.md",
    "SCHEMA.md",
    "AGENTS.md",
    "TASKS.md",
    "LOGS.md",
    "PROJECT_NOTES.md",
    "TEST_LOGS.md",
    "REQUESTS.md",
    "TRACEABILITY.md",
    "DECISIONS.md",
    "BUILD_PLAN.md",
)


class MarkdownKnowledgeBase:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def path(self, filename: str) -> Path:
        if filename not in KB_FILENAMES:
            raise ValueError(f"unsupported knowledge-base file: {filename}")
        return self.root / filename

    def read(self, filename: str) -> str:
        path = self.path(filename)
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def existing_documents(self) -> dict[str, str]:
        return {
            filename: self.read(filename)
            for filename in KB_FILENAMES
            if self.path(filename).is_file()
        }

    def ensure(self, filename: str, heading: str) -> None:
        path = self.path(filename)
        if path.exists():
            return
        path.write_text(f"# {heading}\n", encoding="utf-8")

    def append(self, filename: str, content: str) -> None:
        path = self.path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = ""
        if path.exists() and path.stat().st_size:
            prefix = "\n\n"
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{prefix}{content.rstrip()}\n")

    def merge_generated(self, filename: str, content: str) -> None:
        path = self.path(filename)
        if not path.exists():
            path.write_text(content.rstrip() + "\n", encoding="utf-8")
            return
        marker = "<!-- devflow:generated-scan -->"
        existing = path.read_text(encoding="utf-8")
        if content.strip() and content.strip() not in existing:
            self.append(filename, f"{marker}\n{content}")
