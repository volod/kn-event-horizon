"""Project reviewed source proposal cells without interpreting their access claims."""

import re
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from pydantic import Field, StringConstraints

from kn.contracts.diagnostics import ContractError, Location
from kn.contracts.model import canonical
from kn.sources.ranks import validate_rank_overrides
from kn.sources.validation import ReviewDocument, read_model

RESOURCES = Path(__file__).parent / "resources"
ACCESS_FIELDS = {
    "space": ("access_format", "api_machine_access", "authentication_cost", "key_limitation"),
    "microelectronics": ("machine_format", "access_conditions", "limit_rule"),
    "gdelt": ("access", "review_status", "limitation"),
}
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

type Cell = str | int | float | bool | None
type ShortText = Annotated[str, StringConstraints(min_length=1)]
type Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Proposal(ReviewDocument):
    file_name: ShortText
    sheet_name: ShortText
    sha256: Digest


class SeedRow(ReviewDocument):
    source_id: str
    source_row: Annotated[int, Field(gt=0)]
    values: dict[str, Cell]


class Seed(ReviewDocument):
    format: Literal["kn.source-catalogue.candidates.v1"]
    domain: Literal["space", "microelectronics", "gdelt"]
    proposal: Proposal
    records: Annotated[list[SeedRow], Field(min_length=1)]


class CatalogueRow(TypedDict):
    source_id: str
    domain: str
    original_id: str | None
    label: str
    priority: str
    cadence: str
    access_notes_json: str
    access_verification: Literal["unverified"]
    lifecycle_state: Literal["candidate"]
    proposal_workbook: str
    proposal_sheet: str
    proposal_sha256: str
    proposal_row: int
    proposal_values_json: str


def _row_text(values: dict[str, Cell], key: str, location: Location) -> str:
    text = values.get(key)
    if not isinstance(text, str) or not text.strip() or CONTROL.search(text):
        raise ContractError(
            (*location, "values", key), "sourceValue", "preserve nonempty single-line source text"
        )
    return text


def _source_row(seed: Seed, row: SeedRow, location: Location) -> CatalogueRow:
    original_id = (
        _row_text(row.values, "id", location) if seed.domain == "microelectronics" else None
    )
    expected_id = f"{seed.domain}:{original_id or f'row-{row.source_row}'}"
    if row.source_id != expected_id:
        raise ContractError(
            (*location, "source_id"), "sourceId", "use the qualified original ID or row locator"
        )
    priority = _row_text(row.values, "priority", location)
    if priority not in {"P0", "P1", "P2"}:
        raise ContractError(
            (*location, "values", "priority"), "sourceValue", "preserve priority P0, P1 or P2"
        )
    notes = {key: _row_text(row.values, key, location) for key in ACCESS_FIELDS[seed.domain]}
    return CatalogueRow(
        source_id=row.source_id,
        domain=seed.domain,
        original_id=original_id,
        label=_row_text(row.values, "resource", location),
        priority=priority,
        cadence=_row_text(row.values, "cadence", location),
        access_notes_json=canonical(notes),
        access_verification="unverified",
        lifecycle_state="candidate",
        proposal_workbook=seed.proposal.file_name,
        proposal_sheet=seed.proposal.sheet_name,
        proposal_sha256=seed.proposal.sha256,
        proposal_row=row.source_row,
        proposal_values_json=canonical(row.values),
    )


def read_seed(domain: str, path: Path) -> list[CatalogueRow]:
    """Validate all rows before returning candidates, with a safe location for every error."""
    seed = read_model(path, Seed, (domain,))
    if seed.domain != domain:
        raise ContractError((domain, "domain"), "domain", "use the reviewed seed's owning domain")
    rows: list[CatalogueRow] = []
    seen_ids: set[str] = set()
    seen_rows: set[int] = set()
    for index, record in enumerate(seed.records):
        location = (domain, "records", index)
        row = _source_row(seed, record, location)
        if row["source_id"] in seen_ids or row["proposal_row"] in seen_rows:
            raise ContractError(location, "duplicate", "use unique source IDs and proposal rows")
        rows.append(row)
        seen_ids.add(row["source_id"])
        seen_rows.add(row["proposal_row"])
    return sorted(rows, key=lambda row: row["proposal_row"])


def reviewed_catalogue() -> list[CatalogueRow]:
    """Read only the packaged candidates and validate rank references before loading them."""
    rows = [
        row
        for domain in sorted(ACCESS_FIELDS)
        for row in read_seed(domain, RESOURCES / f"{domain}.json")
    ]
    validate_rank_overrides(RESOURCES / "source-ranks.yaml", {row["source_id"] for row in rows})
    return rows
