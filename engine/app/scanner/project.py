from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any

from app.db.store import StateStore
from app.kb.markdown import KB_FILENAMES, MarkdownKnowledgeBase
from app.providers.base import Provider, ProviderContext


IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".vue": "Vue",
}


@dataclass(frozen=True)
class RepositoryInventory:
    files: tuple[str, ...]
    languages: tuple[str, ...]
    frameworks: tuple[str, ...]
    git_branch: str | None
    recent_commits: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "files": list(self.files),
            "languages": list(self.languages),
            "frameworks": list(self.frameworks),
            "git_branch": self.git_branch,
            "recent_commits": list(self.recent_commits),
        }


class DeterministicRepositoryScanner:
    def inspect(self, root: Path) -> RepositoryInventory:
        root = root.resolve()
        files: list[str] = []
        languages: set[str] = set()
        frameworks: set[str] = set()
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in IGNORED_DIRS for part in relative.parts):
                continue
            relative_text = relative.as_posix()
            files.append(relative_text)
            language = LANGUAGE_EXTENSIONS.get(path.suffix.lower())
            if language:
                languages.add(language)
            if path.name == "vite.config.ts":
                frameworks.add("Vite")
            if path.name in {"package.json", "package-lock.json"}:
                try:
                    package = json.loads(path.read_text(encoding="utf-8"))
                    dependencies = {
                        **package.get("dependencies", {}),
                        **package.get("devDependencies", {}),
                    }
                    for dependency, framework in (
                        ("react", "React"),
                        ("vue", "Vue"),
                        ("fastapi", "FastAPI"),
                    ):
                        if dependency in dependencies:
                            frameworks.add(framework)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            if path.name == "pyproject.toml":
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "fastapi" in text.lower():
                    frameworks.add("FastAPI")
        branch = self._git(root, "branch", "--show-current")
        commits_text = self._git(root, "log", "-5", "--pretty=%h %s")
        commits = tuple(line for line in commits_text.splitlines() if line)
        return RepositoryInventory(
            files=tuple(sorted(files)),
            languages=tuple(sorted(languages)),
            frameworks=tuple(sorted(frameworks)),
            git_branch=branch or None,
            recent_commits=commits,
        )

    @staticmethod
    def _git(root: Path, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""


class ProjectScanner:
    def __init__(
        self,
        store: StateStore,
        provider: Provider,
        repository_scanner: DeterministicRepositoryScanner | None = None,
    ) -> None:
        self.store = store
        self.provider = provider
        self.repository_scanner = (
            repository_scanner or DeterministicRepositoryScanner()
        )

    def register_and_scan(
        self,
        name: str,
        root: Path,
        scan_type: str = "soft",
    ) -> int:
        project_id = self.store.create_project(name, str(root.resolve()))
        self.scan(project_id, scan_type)
        return project_id

    def scan(self, project_id: int, scan_type: str) -> dict[str, Any]:
        if scan_type not in {"soft", "hard"}:
            raise ValueError("scan_type must be soft or hard")
        project = self.store.get_project(project_id)
        root = Path(project["root_path"])
        kb = MarkdownKnowledgeBase(root)
        inventory = (
            self.repository_scanner.inspect(root)
            if scan_type == "hard"
            else None
        )
        context = ProviderContext(
            stage="project_scanner",
            request_id=f"PROJECT-{project_id}",
            payload={
                "scan_type": scan_type,
                "documents": kb.existing_documents(),
                "inventory": inventory.as_dict() if inventory else None,
            },
        )
        result = self.provider.invoke(context)
        summary = str(
            result.output.get(
                "summary",
                f"{name_or_fallback(project)} project scanned from Markdown.",
            )
        )
        languages = list(result.output.get("languages") or ())
        if not languages and inventory:
            languages = list((*inventory.languages, *inventory.frameworks))
        if scan_type == "hard":
            documents = result.output.get("documents", {})
            for filename in KB_FILENAMES:
                heading = filename.removesuffix(".md").replace("_", " ").title()
                kb.ensure(filename, heading)
            for filename, content in documents.items():
                if filename in KB_FILENAMES:
                    kb.merge_generated(filename, str(content))
        self.store.update_project_scan(
            project_id,
            summary=summary,
            languages=languages,
            scan_type=scan_type,
        )
        return {
            "project_id": project_id,
            "summary": summary,
            "languages": languages,
            "scan_type": scan_type,
            "inventory": inventory.as_dict() if inventory else None,
        }


def name_or_fallback(project: dict[str, Any]) -> str:
    return str(project.get("name") or "Local")
