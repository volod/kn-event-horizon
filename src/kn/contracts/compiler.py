"""Write contract artifacts, or verify bytes and reviewed digests without mutation."""

import hashlib
import json
import re
from pathlib import Path

from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from kn.contracts.loader import canonical
from kn.contracts.model import Contract
from kn.contracts.schemas import RESOURCES, SATCOM

DEFAULT_OUTPUT = Path("generated")


def compile_contract(contract: Contract, output: Path | None = None, check: bool = False) -> None:
    content = {name: text.encode("ascii") for name, text in artifacts(contract).items()}
    manifest = {
        "contract_digest": contract.digest,
        "artifacts": {name: hashlib.sha256(value).hexdigest() for name, value in content.items()},
    }
    if check and output is None:
        bundled_id = json.loads(SATCOM.read_text(encoding="ascii"))["id"]
        if contract.contract_id != bundled_id:
            raise ContractError((), "drift", "supply --output to check a custom contract")
        expected = RESOURCES / "satcom" / f"{contract.version}.artifacts.json"
        if not expected.is_file() or json.loads(expected.read_text(encoding="ascii")) != manifest:
            raise ContractError(
                (), "drift", "review generated output and update the artifact digest manifest"
            )
        return
    destination = output if output is not None else DEFAULT_OUTPUT
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
    if any(
        not re.fullmatch(r"(?:avro|elasticsearch|jsonschema)/[a-z][a-z0-9_]{0,47}\.json", name)
        for name in stale
    ):
        raise ContractError((), "manifest", "only managed engine artifacts can be removed")
    return stale
