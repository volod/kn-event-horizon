"""Validate durable proposal row locators without reopening source workbooks."""

import re
from pathlib import Path
from typing import Any


def validate_provenance(document: dict[str, Any]) -> None:
    provenance = document["provenance"]
    identifiers = {row["id"] for row in document["snapshot"].get("terms", [])}
    if not isinstance(provenance, dict) or set(provenance) != identifiers:
        raise ValueError("every reviewed term requires provenance")
    for sources in provenance.values():
        if not isinstance(sources, list) or not sources:
            raise ValueError("reviewed provenance requires source rows")
        for source in sources:
            _validate_locator(source)


def _validate_locator(source: object) -> None:
    if not isinstance(source, dict):
        raise ValueError("reviewed provenance requires a source locator object")
    for key in ("file", "sheet", "workbook_file", "sha256", "workbook_sha256"):
        required = source.get(key)
        if not isinstance(required, str) or not required.strip():
            raise ValueError("reviewed provenance requires source file, digest, sheet, and row")
    for key in ("sha256", "workbook_sha256"):
        if re.fullmatch(r"[0-9a-f]{64}", source[key]) is None:
            raise ValueError("reviewed provenance requires SHA-256 digests")
    if type(source.get("row")) is not int or source["row"] < 1:
        raise ValueError("reviewed provenance requires a positive row locator")
    path = Path(source["file"])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("reviewed provenance file must be repository-relative")
