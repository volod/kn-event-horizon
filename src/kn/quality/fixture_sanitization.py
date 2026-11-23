"""Reject sensitive or unscannable repository test fixture files."""

import argparse
import csv
import logging
import re
import stat
from collections.abc import Iterator, Sequence
from pathlib import Path

from kn.quality.fixture_patterns import sensitive_columns, sensitive_patterns
from kn.quality.project_root import discover_project_root

_LOG = logging.getLogger(__name__)
_MAX_BYTES = 8 * 1024 * 1024
_TEXT_FORMATS = frozenset(
    {
        ".csv",
        ".html",
        ".http",
        ".json",
        ".jsonl",
        ".md",
        ".ndjson",
        ".tsv",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)
_NON_TEXT = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _fixture_paths(root: Path, errors: list[Path]) -> Iterator[Path]:
    tests = root / "tests"
    if tests.is_symlink():
        errors.append(tests)
        return

    def on_error(error: OSError) -> None:
        errors.append(Path(error.filename) if error.filename else tests)

    for directory, _, names in tests.walk(on_error=on_error):
        in_fixtures = "fixtures" in directory.relative_to(tests).parts
        for name in names:
            if in_fixtures or name == "fixtures":
                yield directory / name


def _file_findings(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    try:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            return ["symbolic link"]
        if not stat.S_ISREG(mode):
            return ["not a regular file"]
        if suffix not in _TEXT_FORMATS:
            return ["unsupported file type"]
        with path.open("rb") as stream:
            data = stream.read(_MAX_BYTES + 1)
        if len(data) > _MAX_BYTES:
            return ["exceeds 8 MiB"]
        content = data.decode("utf-8-sig")
    except OSError:
        return ["cannot read fixture"]
    except UnicodeError:
        return ["not UTF-8 text"]
    if _NON_TEXT.search(content):
        return ["not UTF-8 text"]
    findings = sensitive_patterns(content)
    try:
        findings.update(sensitive_columns(content, suffix))
    except csv.Error:
        return [*(f"{rule} pattern" for rule in sorted(findings)), "cannot scan delimited text"]
    return [f"{rule} pattern" for rule in sorted(findings)]


def _path_report(path: Path, root: Path) -> tuple[str, set[str]]:
    relative = path.relative_to(root).as_posix()
    findings = sensitive_patterns(relative)
    return ("<redacted fixture path>" if findings else ascii(relative), findings)


def main(argv: Sequence[str] | None = None) -> int:
    """Check fixture directories throughout tests and report locations and rules only."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="check repository test fixture sanitization")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else discover_project_root()
    traversal_errors: list[Path] = []
    paths = sorted(_fixture_paths(root, traversal_errors))
    errors = [(path, "cannot traverse fixture tree") for path in sorted(traversal_errors)]
    errors.extend((path, finding) for path in paths for finding in _file_findings(path))
    for path in paths:
        _, rules = _path_report(path, root)
        errors.extend((path, f"{rule} pattern in path") for rule in sorted(rules))
    for path, finding in errors:
        location, _ = _path_report(path, root)
        _LOG.error("ERROR: %s: %s", location, finding)
    _LOG.info("[fixture-check] %d file(s) checked", len(paths))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
