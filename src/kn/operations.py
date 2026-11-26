"""CLI operations return stable data; presentation belongs at the interface boundary."""

import hashlib
from pathlib import Path

from kn.contracts import load_contract
from kn.contracts.compiler import compile_contract, compile_registry
from kn.contracts.diagnostics import ContractError
from kn.contracts.lint import lint_contract
from kn.contracts.loader import canonical
from kn.contracts.model import Contract
from kn.contracts.registry import registered_contracts
from kn.contracts.schemas import SATCOM
from kn.db.connection import engine_from_env
from kn.db.governance import upgrade, verify, verify_contracts
from kn.db.rebuild import rebuild, rebuild_data_dir, require_development
from kn.domains.space.satcom.archive import archive
from kn.domains.space.satcom.importer import import_package
from kn.domains.space.satcom.package import read_package
from kn.evidence.lineage import SqlEvidenceRows
from kn.evidence.ranking import Audience
from kn.identity.journal import Journal
from kn.identity.lineage import lineage, target
from kn.review import store as review_store
from kn.review.journal import Journal as ReviewJournal
from kn.review.reports import ReplayReport, write_report
from kn.review.targets import ContractResolver
from kn.sources.catalogue import list_sources


def contract_operation(
    action: str,
    output: Path | None,
    check: bool,
    source: Path | None = None,
    references: Path | None = None,
) -> dict[str, object]:
    """One supplied contract, or without a source every registered contract."""
    if source is None:
        if references is not None:
            raise ContractError((), "references", "supply a contract source with --references")
        contracts = registered_contracts()
        if action == "compile":
            compile_registry(contracts, output, check)
        return {"contracts": [_summary(contract) for contract in contracts]}
    if action == "lint":
        data = lint_contract(source)
        return {
            "contract_id": data["id"],
            "version": data["version"],
            "digest": hashlib.sha256(canonical(data).encode()).hexdigest(),
        }
    contract = load_contract(source, references=references)
    if action == "compile":
        compile_contract(contract, output, check)
    return _summary(contract)


def _summary(contract: Contract) -> dict[str, object]:
    return {
        "contract_id": contract.contract_id,
        "version": contract.version,
        "digest": contract.digest,
    }


def database_operation(action: str) -> dict[str, object]:
    if action == "rebuild":
        require_development()
    # An invalid registry, such as a contract outside the KN schemas, fails before any connection.
    contracts = registered_contracts()
    directory = rebuild_data_dir() if action == "rebuild" else None
    engine = engine_from_env()
    report: ReplayReport = ()
    try:
        with engine.begin() as connection:
            if action == "upgrade":
                upgrade(connection, contracts)
            elif directory is not None:
                report = rebuild(connection, contracts, data_dir=directory)
            verify(connection, contracts)
        result: dict[str, object] = {"status": "verified"}
        if directory is not None and report:
            result["verification_replay"] = str(write_report(directory, report))
        return result
    finally:
        engine.dispose()


def satcom_operation(action: str, source: Path, data_dir: Path) -> dict[str, object]:
    contract = load_contract(SATCOM)
    package = read_package(source, contract)
    if action == "validate":
        return package.manifest()
    data_dir = rebuild_data_dir(data_dir)
    destination = archive(package, data_dir)
    contracts = registered_contracts()
    engine = engine_from_env()
    try:
        with engine.begin() as connection:
            review_store.lock(connection)
            verify_contracts(connection, contracts)
            changed = import_package(connection, package, contract)
            report = review_store.replay(
                connection,
                ReviewJournal(data_dir),
                ContractResolver.registered(contracts),
                contract_id=contract.contract_id,
            )
        result: dict[str, object] = {
            "import_id": package.import_id,
            "status": "imported" if changed else "already_imported",
            "archive": str(destination),
        }
        if report:
            result["verification_replay"] = str(write_report(data_dir, report))
        return result
    finally:
        engine.dispose()


def source_list_operation() -> dict[str, object]:
    engine = engine_from_env()
    try:
        with engine.connect() as connection:
            return {"sources": list_sources(connection)}
    finally:
        engine.dispose()


def lineage_operation(
    journal: Journal, reference: str, field_id: str | None, audience: Audience
) -> dict[str, object]:
    """Read the identity journal, then the evidence schema in a read-only transaction.

    The reference resolves first, so an unknown object never opens the database.
    """
    state = journal.state()
    target(state, reference)
    engine = engine_from_env()
    try:
        with engine.connect() as base:
            connection = base.execution_options(postgresql_readonly=True)
            with connection.begin():
                rows = SqlEvidenceRows(connection)
                return lineage(state, rows, reference, field_id=field_id, audience=audience)
    finally:
        engine.dispose()
