from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    database_path: Path
    cors_origins: tuple[str, ...]


@lru_cache
def get_settings() -> Settings:
    origins = os.getenv(
        "DEVFLOW_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return Settings(
        host=os.getenv("DEVFLOW_HOST", "127.0.0.1"),
        port=int(os.getenv("DEVFLOW_PORT", "8000")),
        database_path=_resolve_project_path(
            os.getenv("DEVFLOW_DATABASE_PATH", "data/devflow.db")
        ),
        cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
    )
