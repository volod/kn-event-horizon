"""Write contract artifacts, or verify their exact bytes without mutation."""

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path

from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from kn.contracts.model import Contract, canonical
from kn.contracts.names import IDENTIFIER_BODY

# Committed review output: one directory per contract, beside other generators' directories.
GENERATED_CONTRACTS = Path("generated") / "contracts"
PLAIN_DIRECTORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ENGINE_ARTIFACT = re.compile(rf"(?:avro|elasticsearch|jsonschema)/{IDENTIFIER_BODY}\.json")


def default_output(contract: Contract) -> Path:
    """The compile and check default, relative to the working directory."""
    if not PLAIN_DIRECTORY.fullmatch(contract.contract_id):
        raise ContractError(
            ("id",), "output", "supply --output for a contract ID that is not a plain file name"
        )
    return GENERATED_CONTRACTS / contract.contract_id


def compile_registry(
    contracts: Sequence[Contract], root: Path | None = None, check: bool = False
) -> None:
    """Each contract in `<root>/<contract-id>/`; a check also refuses directories of others."""
    base = root if root is not None else GENERATED_CONTRACTS
    destinations = [base / default_output(contract).name for contract in contracts]
    if check:
        actual = {path.name for path in base.iterdir()} if base.is_dir() else set()
        if actual != {path.name for path in destinations}:
            raise ContractError(
                (), "drift", "regenerate output for exactly the registered contracts"
            )
    for contract, destination in zip(contracts, destinations, strict=True):
        compile_contract(contract, destination, check)


def compile_contract(contract: Contract, output: Path | None = None, check: bool = False) -> None:
    content = {name: text.encode("ascii") for name, text in artifacts(contract).items()}
    manifest = {
        "contract_digest": contract.digest,
        "artifacts": {name: hashlib.sha256(value).hexdigest() for name, value in content.items()},
    }
    destination = output if output is not None else default_output(contract)
    content["manifest.json"] = (canonical(manifest) + "\n").encode("ascii")
    _safe_paths(destination, content)
    if check:
        _check(destination, content)
        return
    stale = _stale_artifacts(destination, content)
    _safe_paths(destination, dict.fromkeys(stale, b""))
    destination.mkdir(parents=True, exist_ok=True)
    for name in stale:
        (destination / name).unlink(missing_ok=True)
    for name, value in content.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)


def _safe_paths(output: Path, content: dict[str, bytes]) -> None:
    for path in [output, *output.parents, *(output / name for name in content)]:
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ContractError((), "symlink", "use an artifact directory without symlinks")


def _check(output: Path, content: dict[str, bytes]) -> None:
    actual = {
        str(path.relative_to(output)): path for path in output.rglob("*") if not path.is_dir()
    }
    if set(actual) != set(content) or any(path.is_symlink() for path in output.rglob("*")):
        raise ContractError((), "drift", "regenerate missing, extra, or symlinked artifacts")
    if any(actual[name].read_bytes() != value for name, value in content.items()):
        raise ContractError((), "drift", "regenerate changed artifacts")


def _stale_artifacts(output: Path, content: dict[str, bytes]) -> set[str]:
    manifest = output / "manifest.json"
    if not manifest.is_file():
        return set()
    old = json.loads(manifest.read_text(encoding="ascii"))
    entries = old.get("artifacts") if isinstance(old, dict) else None
    if not isinstance(entries, dict):
        raise ContractError((), "manifest", "restore the previous generated artifact manifest")
    stale = set(entries) - content.keys()
    if any(not ENGINE_ARTIFACT.fullmatch(name) for name in stale):
        raise ContractError((), "manifest", "only managed engine artifacts can be removed")
    return stale
