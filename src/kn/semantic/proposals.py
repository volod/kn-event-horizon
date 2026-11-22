"""Read lossless workbook proposals with checked manifests and durable row locators."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DOMAINS = ("space", "gdelt", "microelectronics")


@dataclass(frozen=True)
class Proposal:
    domain: str
    workbook: str
    sheet: str
    row: int
    provenance: dict[str, Any]
    values: dict[str, Any]
    formulas: dict[str, str] = field(default_factory=dict)


def read_proposals(root: Path) -> list[Proposal]:
    """Refuse changed conversions rather than reconciling bytes the manifest never covered."""
    result: list[Proposal] = []
    for domain in DOMAINS:
        manifests = sorted((root / "domains" / domain / "seeds/proposals").glob("*/workbook.json"))
        expected = {"ontology_and_tags_v1"}
        if domain != "gdelt":
            expected.add("data_sources_v1")
        if not expected <= {path.parent.name for path in manifests}:
            raise ValueError("missing proposal workbook")
        for manifest in manifests:
            result.extend(_workbook(root, domain, manifest))
    return result


def _workbook(root: Path, domain: str, manifest: Path) -> list[Proposal]:
    document = json.loads(manifest.read_bytes())
    sheets = document["sheets"]
    expected = {sheet["file"] for sheet in sheets}
    actual = {path.name for path in manifest.parent.glob("*.json") if path != manifest}
    if len(expected) != len(sheets) or expected != actual or document["domain"] != domain:
        raise ValueError("proposal manifest file set or domain mismatch")
    result: list[Proposal] = []
    for sheet in sheets:
        result.extend(_sheet(root, domain, manifest, document, sheet))
    return result


def _sheet(
    root: Path, domain: str, manifest: Path, document: dict[str, Any], sheet: dict[str, Any]
) -> list[Proposal]:
    path = manifest.parent / sheet["file"]
    if path.parent != manifest.parent or path.is_symlink():
        raise ValueError("proposal sheets must be local files")
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    data = json.loads(payload)
    if digest != sheet["sha256"] or data["status"] != "unreviewed_proposal":
        raise ValueError("proposal checksum or status mismatch")
    source = data["source"]
    if any(source[key] != document["workbook"][key] for key in ("file_name", "sha256")):
        raise ValueError("proposal workbook provenance mismatch")
    if (source["sheet_name"], source["sheet_position"]) != (
        sheet["sheet_name"],
        sheet["sheet_position"],
    ):
        raise ValueError("proposal sheet provenance mismatch")
    rows = data.get("records", data.get("rows", []))
    if len(rows) != sheet.get("record_count", sheet.get("row_count")):
        raise ValueError("proposal row count mismatch")
    result: list[Proposal] = []
    seen: set[int] = set()
    for row in rows:
        number = row["source_row"]
        if not isinstance(number, int) or number < 1 or number in seen:
            raise ValueError("proposal row locator must be a unique positive integer")
        seen.add(number)
        provenance = {
            "file": path.relative_to(root).as_posix(),
            "sha256": digest,
            "workbook_file": document["workbook"]["file_name"],
            "workbook_sha256": document["workbook"]["sha256"],
            "sheet": sheet["sheet_name"],
            "row": number,
        }
        result.append(
            Proposal(
                domain,
                manifest.parent.name,
                path.stem,
                number,
                provenance,
                row.get("values", row.get("cells", {})),
                row.get("formulas_not_evaluated", {}),
            )
        )
    return result
