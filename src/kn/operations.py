"""CLI operations compose domain modules; command parsing lives in cli.py."""

import logging
from pathlib import Path

from kn.contracts import load_contract
from kn.contracts.compiler import compile_contract
from kn.contracts.loader import canonical
from kn.db.connection import engine_from_env
from kn.db.governance import upgrade, verify, verify_contract
from kn.db.rebuild import rebuild
from kn.domains.space.satcom.archive import archive
from kn.domains.space.satcom.importer import import_package
from kn.domains.space.satcom.package import read_package

_LOG = logging.getLogger(__name__)


def contract_operation(action: str, output: Path | None, check: bool) -> None:
    contract = load_contract()
    if action == "compile":
        compile_contract(contract, output, check)
    _LOG.info("contract %s %s %s", contract.contract_id, contract.version, contract.digest)


def database_operation(action: str) -> None:
    engine = engine_from_env()
    try:
        with engine.begin() as connection:
            if action == "upgrade":
                upgrade(connection)
            elif action == "rebuild":
                rebuild(connection)
            _LOG.info("%s", verify(connection))
    finally:
        engine.dispose()


def satcom_operation(action: str, source: Path, data_dir: Path) -> None:
    contract = load_contract()
    package = read_package(source, contract)
    if action == "validate":
        _LOG.info("%s", canonical(package.manifest()))
        return
    destination = archive(package, data_dir)
    engine = engine_from_env()
    try:
        with engine.begin() as connection:
            verify_contract(connection)
            changed = import_package(connection, package, contract)
        _LOG.info(
            "SATCOM %s: %s; archive %s",
            package.import_id,
            "imported" if changed else "already imported",
            destination,
        )
    finally:
        engine.dispose()
