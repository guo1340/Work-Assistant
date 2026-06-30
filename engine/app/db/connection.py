from pathlib import Path
import sqlite3


SCHEMA_PATH = Path(__file__).with_name("schema.sql")
EXPECTED_TABLES = {
    "projects",
    "requests",
    "tasks",
    "stage_results",
    "execution_history",
    "approvals",
}


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(database_path) as connection:
        connection.executescript(schema)


def database_is_ready(database_path: Path) -> bool:
    if not database_path.is_file():
        return False
    try:
        with connect(database_path) as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
    except sqlite3.Error:
        return False
    return EXPECTED_TABLES.issubset({row[0] for row in rows})
