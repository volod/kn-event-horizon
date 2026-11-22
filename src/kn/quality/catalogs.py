"""Validate interface catalogs, key usage, and the CLI translation boundary."""

import argparse
import logging
from pathlib import Path

from babel.core import UnknownLocaleError

from kn.i18n.catalog import CatalogValue, compare_catalogs, read_catalog
from kn.quality.catalog_usage import inspect_source
from kn.quality.project_root import discover_project_root

_LOG = logging.getLogger(__name__)
REQUIRED_LOCALES = {"en", "uk"}


def check_catalogs(root: Path) -> list[str]:
    findings: list[str] = []
    catalogs: dict[str, dict[str, CatalogValue]] = {}
    for path in sorted((root / "locales").glob("*/messages.json")):
        try:
            catalogs[path.parent.name] = read_catalog(
                path.read_text(encoding="ascii"), path.parent.name
            )
        except (ValueError, OSError, UnknownLocaleError) as error:
            findings.append(f"{path.relative_to(root)}: {error}")
    for locale in sorted(REQUIRED_LOCALES - catalogs.keys()):
        findings.append(f"missing or invalid required catalog: {locale}")
    reference = catalogs.get("en", {})
    for locale, catalog in catalogs.items():
        findings.extend(f"{locale}: {item}" for item in compare_catalogs(reference, catalog))
    used, source_findings = _inspect_sources(root)
    findings.extend(source_findings)
    for key in sorted(reference.keys() - used.keys()):
        findings.append(f"unused key: {key}")
    for key, kind in used.items():
        if key not in reference:
            findings.append(f"referenced key missing: {key}")
        elif isinstance(reference[key], str) != (kind == "text"):
            findings.append(f"message kind mismatch in source: {key}")
    return findings


def _inspect_sources(root: Path) -> tuple[dict[str, str], list[str]]:
    used: dict[str, str] = {}
    findings = []
    for path in sorted((root / "src" / "kn").rglob("*.py")):
        if "quality" in path.relative_to(root / "src" / "kn").parts:
            continue
        operator = path.stem.startswith("cli") or path.name in {
            "operations.py",
            "parser.py",
            "output.py",
        }
        try:
            keys, errors = inspect_source(path, operator=operator)
        except SyntaxError as error:
            findings.append(f"{path.relative_to(root)}: {error}")
            continue
        for key, kind in keys.items():
            if key in used and used[key] != kind:
                findings.append(f"mixed message kind across modules: {key}")
            used[key] = kind
        findings.extend(f"{path.relative_to(root)}: {error}" for error in errors)
    return used, findings


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=discover_project_root())
    args = parser.parse_args(argv)
    findings = check_catalogs(args.root)
    for finding in findings:
        _LOG.error("ERROR: %s", finding)
    _LOG.info("[catalogs] %d finding(s)", len(findings))
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
