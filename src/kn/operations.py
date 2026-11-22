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
from kn.db.rebuild import rebuild, require_development
from kn.domains.space.satcom.archive import archive
from kn.domains.space.satcom.importer import import_package
from kn.domains.space.satcom.package import read_package


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
    engine = engine_from_env()
    try:
        with engine.begin() as connection:
            if action == "upgrade":
                upgrade(connection, contracts)
            elif action == "rebuild":
                rebuild(connection, contracts)
            verify(connection, contracts)
        return {"status": "verified"}
    finally:
        engine.dispose()


def satcom_operation(action: str, source: Path, data_dir: Path) -> dict[str, object]:
    contract = load_contract(SATCOM)
    package = read_package(source, contract)
    if action == "validate":
        return package.manifest()
    destination = archive(package, data_dir)
    engine = engine_from_env()
    try:
        with engine.begin() as connection:
            verify_contracts(connection)
            changed = import_package(connection, package, contract)
        return {
            "import_id": package.import_id,
            "status": "imported" if changed else "already_imported",
            "archive": str(destination),
        }
    finally:
        engine.dispose()
