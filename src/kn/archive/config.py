"""Explicit archive storage configuration."""

import os
from pathlib import Path

from dotenv import dotenv_values

from kn.archive.model import ArchiveError
from kn.quality.project_root import discover_project_root

ROOT_VARIABLE = "KN_RAW_ARCHIVE_DIR"


def archive_root(project_root: Path | None = None) -> Path:
    """Resolve the archive root from the environment or the project's .env."""
    root = project_root.resolve() if project_root is not None else _checkout_root()
    configured = os.environ.get(ROOT_VARIABLE)
    if configured is None and root is not None:
        configured = dotenv_values(root / ".env", interpolate=False).get(ROOT_VARIABLE)
    if not configured or not configured.strip():
        raise ArchiveError("archive_root_required")
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
