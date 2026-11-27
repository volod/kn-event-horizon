"""Explicit archive storage configuration."""

import os
from pathlib import Path

from dotenv import dotenv_values

from kn.archive.model import ArchiveError
from kn.quality.project_root import discover_project_root

ROOT_VARIABLE = "KN_RAW_ARCHIVE_DIR"
INDEX_VARIABLE = "KN_RAW_INDEX_DIR"


def archive_root(project_root: Path | None = None) -> Path:
    """Resolve the archive root from the environment or the project's .env."""
    configured = _configured_root(ROOT_VARIABLE, project_root)
    if configured is None:
        raise ArchiveError("archive_root_required")
    return configured


def index_root(project_root: Path | None = None, *, required: bool = True) -> Path | None:
    configured = _configured_root(INDEX_VARIABLE, project_root)
    if required and configured is None:
        raise ArchiveError("index_root_required")
    return configured


def check_roots(archive: Path, index: Path) -> None:
    if archive.is_relative_to(index) or index.is_relative_to(archive):
        raise ArchiveError("index_root_overlap")


def _configured_root(variable: str, project_root: Path | None) -> Path | None:
    root = project_root.resolve() if project_root is not None else _checkout_root()
    configured = os.environ.get(variable)
    if configured is None and root is not None:
        configured = dotenv_values(root / ".env", interpolate=False).get(variable)
    if not configured or not configured.strip():
        return None
    return resolve_archive_path(Path(configured), root)


def resolve_archive_path(path: Path, project_root: Path | None = None) -> Path:
    if path.is_absolute():
        return path.resolve()
    root = project_root or _checkout_root()
    if root is None:
        raise ArchiveError("project_root_required")
    return (root / path).resolve()


def _checkout_root() -> Path | None:
    for start in (Path.cwd(), Path(__file__).parent):
        try:
            return discover_project_root(start)
        except FileNotFoundError:
            continue
    return None
