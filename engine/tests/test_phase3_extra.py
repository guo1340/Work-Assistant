from pathlib import Path

import pytest

from app.db.connection import initialize_database
from app.db.store import StateStore
from app.providers.mock import MockProvider
from app.scanner.project import (
    DeterministicRepositoryScanner,
    ProjectScanner,
)


def make_store(tmp_path: Path) -> StateStore:
    database = tmp_path / "state.db"
    initialize_database(database)
    return StateStore(database)


def test_scan_rejects_unknown_scan_type(tmp_path):
    store = make_store(tmp_path)
    project_id = store.create_project("Example", str(tmp_path))
    scanner = ProjectScanner(store, MockProvider())
    with pytest.raises(ValueError, match="soft or hard"):
        scanner.scan(project_id, "sideways")


def test_soft_scan_does_not_create_markdown(tmp_path):
    store = make_store(tmp_path)
    scanner = ProjectScanner(store, MockProvider())
    scanner.register_and_scan("Example", tmp_path, "soft")
    # Soft scan only reads existing docs; it must not fabricate the KB.
    assert not (tmp_path / "PROJECT_NOTES.md").exists()
    assert not (tmp_path / "TRACEABILITY.md").exists()


def test_hard_scan_detects_frameworks_from_package_json(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"react": "18.0.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "app.tsx").write_text("export default 1", encoding="utf-8")
    store = make_store(tmp_path)
    scanner = ProjectScanner(store, MockProvider())
    project_id = scanner.register_and_scan("Example", tmp_path, "hard")
    languages = store.get_project(project_id)["languages"]
    assert "React" in languages
    assert "TypeScript" in languages


def test_repository_scanner_ignores_vendored_dirs(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("x", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1", encoding="utf-8")
    inventory = DeterministicRepositoryScanner().inspect(tmp_path)
    assert "src/main.py" in inventory.files
    assert all("node_modules" not in path for path in inventory.files)
    assert "Python" in inventory.languages
    assert "JavaScript" not in inventory.languages


def test_update_project_scan_unknown_project_raises(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(KeyError):
        store.update_project_scan(
            424242,
            summary="x",
            languages=[],
            scan_type="soft",
        )
