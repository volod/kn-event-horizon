"""Combined fixture rebuild for the registered subset of the development model.

This prepares the checkpoint; missing model owners remain open plan prerequisites.
"""

import csv
import json
import shutil
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.archive import Archive
from kn.contracts.compiler import compile_registry
from kn.contracts.model import Contract, canonical
from kn.contracts.registry import registered_contracts
from kn.contracts.sqlalchemy import metadata
from kn.db.governance import verify
from kn.db.platform import role_name
from kn.db.rebuild import rebuild
from kn.db.statements import ResetRole, SetConstraints, SetRole
from kn.domains.space.satcom.archive import archive
from kn.domains.space.satcom.importer import import_package
from kn.domains.space.satcom.package import CSV_DIRECTORY, Package, read_package
from kn.engine.state import CONTRACT_ID, ingestion_contract
from kn.review import store as reviews
from kn.review.journal import Journal
from kn.review.model import Decision, Stamp
from kn.review.projection import read
from kn.review.reports import ReplayReport, write_report
from kn.review.targets import ContractResolver
from kn.semantic import Snapshot, validate_model
from kn.semantic.seeds import reviewed_snapshot
from kn.sources.catalogue import TABLE_NAME
from kn.sources.seeds import reviewed_catalogue
from tests.integration.evidence_fixtures import seed_evidence_fixture
from tests.integration.identity_fixtures import seed_identity_fixture
from tests.integration.ingestion_fixtures import (
    assert_ingestion_snapshot,
    fixture_archive,
    seed_ingestion_fixture,
)
from tests.integration.review_fixtures import (
    OPEN,
    SATCOM,
    TERMINAL,
    assert_audit_rights,
    assert_label_isolation,
    assert_stamps,
    first,
    seed_reviews,
)
from tests.integration.semantic_fixtures import native_rows, text_fixture
from tests.semantic.conftest import REFERENCES

# Every new owner must supply fixture replay before this suite can cover its registration.
FIXTURE_OWNERS = {
    "kn.system.governance",
    "kn.system.source_catalogue",
    CONTRACT_ID,
    "kn.space.satcom",
    "kn.core.semantic",
    "kn.core.human_verification",
    "kn.core.identity",
    "kn.core.evidence",
}


def _snapshot(connection: Connection, contracts: Sequence[Contract]) -> dict[str, list[dict]]:
    result = {}
    for contract in contracts:
        for table in metadata(contract).tables.values():
            result[table.fullname] = [
                dict(row)
                for row in connection.execute(
                    sa.select(table).order_by(*table.primary_key.columns)
                ).mappings()
            ]
    return result


def _encoded(value: object) -> dict[str, str]:
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {"type": "timestamp", "value": value.isoformat()}
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    raise TypeError(f"unsupported baseline value: {type(value).__name__}")


def _assert_satcom(snapshot: dict[str, list[dict]], package: Package, contract: Contract) -> None:
    for name, rows in package.rows.items():
        keys = contract.table(name).primary_key
        expected = sorted(rows, key=lambda row: tuple(row[key] for key in keys))
        assert snapshot[f"space.{name}"] == expected, name
    raw = {
        (row["table_name"], row["row_number"]): row["cells_json"]
        for row in snapshot["space.satcom_rows"]
    }
    assert raw == {
        (name, number): canonical(row)
        for name, rows in package.raw_rows.items()
        for number, row in enumerate(rows, start=2)
    }


def _assert_semantic(
    snapshot: dict[str, list[dict]], contract: Contract, fixture: Snapshot
) -> None:
    expected_rows = native_rows(contract, reviewed_snapshot())
    for name, rows in fixture.items():
        expected_rows.setdefault(name, []).extend(rows)
    for name, rows in expected_rows.items():
        table = contract.table(name)
        expected = list(rows)
        expected.sort(key=lambda row: tuple(row[key] for key in table.primary_key))
        assert snapshot[f"semantic.{name}"] == expected, name


def _drain_references(connection: Connection, contract: Contract) -> None:
    names = tuple(
        sorted(
            str(reference.name)
            for table in metadata(contract).tables.values()
            for reference in table.foreign_key_constraints
        )
    )
    connection.execute(SetConstraints(contract.schema, names, deferred=False))
    connection.execute(SetConstraints(contract.schema, names, deferred=True))


def _assert_unreviewed(
    connection: Connection, contracts: Sequence[Contract], resolver: ContractResolver
) -> None:
    for contract in contracts:
        for table in contract.tables:
            dataset = resolver.dataset(contract.contract_id, table.name)
            row = first(connection, dataset)
            result = read(connection, dataset, dataset.key(row), "terminology", rights=OPEN)
            assert result is not None and result.values == row
            assert result.record == Stamp()
            assert result.fields == dict.fromkeys(dataset.fields, Stamp())


def _assert_rebuild_report(report: ReplayReport, decisions: tuple[Decision, ...]) -> None:
    label, _, terminal, audit, bilingual = decisions
    states = {entry.target_id: entry.state for entry in report}
    assert states[label.target.target_id] == "applied"
    for pending in (terminal, audit, bilingual):
        assert states[pending.target.target_id] == "pending"


def _restore_sources(
    connection: Connection,
    package: Package,
    satcom: Contract,
    semantic: Contract,
    fixture: Snapshot,
) -> None:
    connection.execute(SetRole(role_name(satcom.schema, "loader")))
    assert import_package(connection, package, satcom)
    assert not import_package(connection, package, satcom)
    connection.execute(ResetRole())
    _drain_references(connection, satcom)
    connection.execute(SetRole(role_name(semantic.schema, "loader")))
    for table in metadata(semantic).tables.values():
        connection.execute(table.insert(), fixture[table.name])
    connection.execute(ResetRole())
    _drain_references(connection, semantic)


def _assert_package_bytes(source: Path, archived: Path, package: Package) -> None:
    for name, content in package.files.items():
        assert (source / name).read_bytes() == content
        assert (archived / "package" / name).read_bytes() == content


def _assert_edited_delivery(
    connection: Connection,
    resolver: ContractResolver,
    source: Path,
    satcom: Contract,
    decision: Decision,
) -> None:
    edited = source.with_name("edited")
    shutil.copytree(source, edited)
    file = edited / CSV_DIRECTORY / "terminal_models.csv"
    # Change one source cell while letting the normal package reader derive a new snapshot ID.
    with file.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        headers = reader.fieldnames
    terminal = next(row for row in rows if row["terminal_id"] == TERMINAL)
    assert terminal["mass_antenna_kg"] != "35.0"
    terminal["mass_antenna_kg"] = "35.0"
    with file.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    package = read_package(edited, satcom)
    dataset = resolver.dataset(SATCOM, "terminal_models")
    assert import_package(connection, package, satcom)
    row = first(connection, dataset, import_id=package.import_id, terminal_id=TERMINAL)
    result = read(connection, dataset, dataset.key(row), "factual", rights=OPEN)
    assert result is not None and set(result.fields.values()) == {Stamp()}
    assert result.values["mass_antenna_kg"] == Decimal("35.0")
    assert_stamps(connection, resolver, (decision,))


def test_registered_model_fixture_rebuild_is_lossless_and_repeatable(
    rebuild_connection: Connection, source_package: Path, tmp_path: Path
) -> None:
    contracts = registered_contracts()
    assert {contract.contract_id for contract in contracts} == FIXTURE_OWNERS, (
        "extend combined-baseline fixtures for every newly registered model owner"
    )
    compile_registry(contracts, tmp_path / "compiled")
    compile_registry(contracts, tmp_path / "compiled", check=True)
    satcom = next(contract for contract in contracts if contract.contract_id == "kn.space.satcom")
    semantic = next(
        contract for contract in contracts if contract.contract_id == "kn.core.semantic"
    )
    package = read_package(source_package, satcom)
    archived = archive(package, tmp_path)
    raw_archive = Archive(tmp_path / "raw-archive")
    manifest = fixture_archive(raw_archive.root)
    semantic_fixture = text_fixture()
    validate_model(semantic_fixture, REFERENCES)
    semantic_fixture = native_rows(semantic, semantic_fixture)
    connection = rebuild_connection
    seed_identity_fixture(tmp_path)
    resolver = ContractResolver.registered(contracts)
    journal = Journal(tmp_path)
    rebuild(connection, contracts, data_dir=tmp_path)
    _restore_sources(connection, package, satcom, semantic, semantic_fixture)
    decisions = seed_reviews(connection, resolver, tmp_path)
    snapshots = []
    for iteration in range(2):
        report = rebuild(connection, contracts, data_dir=tmp_path)
        _assert_rebuild_report(report, decisions)
        write_report(tmp_path, report)
        _restore_sources(connection, package, satcom, semantic, semantic_fixture)
        report = reviews.replay(connection, journal, resolver, complete=True)
        assert len(report) == len(decisions) and {entry.state for entry in report} == {"applied"}
        write_report(tmp_path, report)
        assert_stamps(connection, resolver, decisions)
        evidence = next(item for item in contracts if item.contract_id == "kn.core.evidence")
        assert seed_evidence_fixture(connection) > 0
        _drain_references(connection, evidence)
        capture = raw_archive.metadata(manifest.captures[0].record_id)
        seed_ingestion_fixture(connection, capture)
        _drain_references(connection, ingestion_contract())
        verify(connection, contracts)
        snapshot = _snapshot(connection, contracts)
        _assert_satcom(snapshot, package, satcom)
        assert_ingestion_snapshot(snapshot, capture)
        _assert_semantic(snapshot, semantic, semantic_fixture)
        assert snapshot[TABLE_NAME] == sorted(
            reviewed_catalogue(), key=lambda row: row["source_id"]
        )
        assert all(snapshot.values()), "provide at least one representative row per table"
        _assert_unreviewed(connection, contracts, resolver)
        (tmp_path / f"rebuild-{iteration + 1}.json").write_text(
            json.dumps(snapshot, default=_encoded, ensure_ascii=True, sort_keys=True, indent=2)
            + "\n",
            encoding="ascii",
        )
        snapshots.append(snapshot)
    assert snapshots[0] == snapshots[1]
    assert tuple(journal.read()) == decisions
    _assert_package_bytes(source_package, archived, package)
    assert_audit_rights(connection, resolver, decisions[2])
    assert_label_isolation(connection, resolver, decisions[-1])
    _assert_edited_delivery(connection, resolver, source_package, satcom, decisions[2])
