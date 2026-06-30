from pathlib import Path

from app.db.connection import initialize_database
from app.db.store import StateStore
from app.kb.markdown import MarkdownKnowledgeBase
from app.providers.mock import MockProvider
from app.scanner.project import ProjectScanner


def make_store(tmp_path: Path) -> StateStore:
    database = tmp_path / "state.db"
    initialize_database(database)
    return StateStore(database)


def test_markdown_kb_never_overwrites_existing_content(tmp_path):
    kb = MarkdownKnowledgeBase(tmp_path)
    (tmp_path / "README.md").write_text("# Human content\n", encoding="utf-8")

    kb.merge_generated("README.md", "## Generated understanding")

    text = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# Human content")
    assert "Generated understanding" in text


def test_soft_scan_registers_project_from_markdown(tmp_path):
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    scanner = ProjectScanner(make_store(tmp_path), MockProvider())

    project_id = scanner.register_and_scan("Example", tmp_path, "soft")
    project = scanner.store.get_project(project_id)

    assert project["scan_type"] == "soft"
    assert project["summary"]


def test_hard_scan_walks_repo_detects_languages_and_creates_kb(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.tsx").write_text(
        "export const App = () => null",
        encoding="utf-8",
    )
    scanner = ProjectScanner(make_store(tmp_path), MockProvider())

    project_id = scanner.register_and_scan("Example", tmp_path, "hard")
    project = scanner.store.get_project(project_id)

    assert "TypeScript" in project["languages"]
    assert (tmp_path / "PROJECT_NOTES.md").is_file()
    assert (tmp_path / "TRACEABILITY.md").is_file()
