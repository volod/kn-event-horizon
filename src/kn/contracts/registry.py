"""The reviewed deployment set: every storage contract that KN deploys, in deployment order.

`resources/registry.json` lists contract files relative to itself. The governance contract,
which defines the installed-contract marker, comes first. Contracts reference each other only
through stable field IDs; SQL foreign keys stay within one contract.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from functools import cache
from pathlib import Path

import sqlalchemy as sa

from kn.contracts.diagnostics import ContractError
from kn.contracts.document import read_document
from kn.contracts.loader import load_contract
from kn.contracts.model import Contract
from kn.contracts.physical import extensions, relation_names
from kn.contracts.schemas import RESOURCES
from kn.contracts.sqlalchemy import metadata
from kn.contracts.verification import field_contexts

REGISTRY = RESOURCES / "registry.json"
MARKER_CONTRACT = "kn.system.governance"
MARKER_PATH = RESOURCES / "system" / "1.0.0.json"
MARKER_TABLE = "installed_contracts"


def registered_contracts(path: Path | None = None) -> tuple[Contract, ...]:
    """Load and validate every registered contract; nothing here touches a database."""
    registry = path or REGISTRY
    document = read_document(registry)
    entries = document.get("contracts")
    if set(document) != {"contracts"} or not isinstance(entries, list) or not entries:
        raise ContractError((), "registry", "list registered contracts under contracts")
    contracts = tuple(_load(registry.parent, entry, number) for number, entry in enumerate(entries))
    validate_registry(contracts)
    return contracts


def _load(root: Path, entry: object, number: int) -> Contract:
    if not isinstance(entry, dict) or set(entry) - {"path", "references"} or "path" not in entry:
        raise ContractError(("contracts", number), "registry", "use path and optional references")
    paths = [
        _inside(root, entry[key], number, key) for key in ("path", "references") if key in entry
    ]
    return load_contract(paths[0], references=paths[1] if len(paths) > 1 else None)


def _inside(root: Path, value: object, number: int, key: str) -> Path:
    """Registered files stay beside the registry, so a reviewed list cannot point elsewhere."""
    if not isinstance(value, str) or Path(value).is_absolute():
        raise ContractError(("contracts", number, key), "registry", "use a relative file path")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ContractError(
            ("contracts", number, key), "registry", "name a file inside the registry directory"
        )
    return path


def validate_registry(contracts: Sequence[Contract]) -> None:
    """One deployment: unique contracts and field IDs, and one namespace per schema."""
    if not contracts or contracts[0].contract_id != MARKER_CONTRACT:
        raise ContractError((), "registry", f"register {MARKER_CONTRACT} first")
    _unique((contract.contract_id for contract in contracts), "contract IDs")
    _unique(
        (
            field.field_id
            for contract in contracts
            for table in contract.tables
            for field in table.fields
        ),
        "field IDs",
    )
    for schema in {contract.schema for contract in contracts}:
        _unique(
            (
                name
                for contract in contracts
                if contract.schema == schema
                for name in relation_names(contract.tables)
            ),
            f"table and index names in schema {schema}",
        )
    _validate_coverage(contracts)


def _validate_coverage(contracts: Sequence[Contract]) -> None:
    for contract in contracts:
        for table in contract.tables:
            declaration = extensions(table).get("humanVerification")
            if (
                declaration is None
                or declaration.get("strategy") not in {"external", "decision-log"}
                or set(field_contexts(table, declaration))
                != {field.field_id for field in table.fields}
            ):
                raise ContractError(
                    (),
                    "registry",
                    f"declare record and field verification coverage for "
                    f"{contract.contract_id}/{table.name}",
                )


def _unique(values: Iterable[str], what: str) -> None:
    if any(count > 1 for count in Counter(values).values()):
        raise ContractError((), "registry", f"use {what} that are unique across the registry")


@cache
def marker_contract() -> Contract:
    return load_contract(MARKER_PATH)


def marker_table(schema: str | None = None) -> sa.Table:
    """The installed-contract marker, in its own schema unless a test supplies another."""
    model = metadata(marker_contract(), schema)
    prefix = f"{model.schema}." if model.schema else ""
    return model.tables[f"{prefix}{MARKER_TABLE}"]
