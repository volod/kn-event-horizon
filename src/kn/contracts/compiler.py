"""Write portable artifacts, or check their reviewed digest manifest without mutation."""

import json
from pathlib import Path

from kn.contracts.exports import artifact_digests, artifacts
from kn.contracts.loader import canonical
from kn.contracts.model import Contract
from kn.contracts.schemas import RESOURCES


def compile_contract(contract: Contract, output: Path | None = None, check: bool = False) -> None:
    expected = RESOURCES / "satcom" / f"{contract.version}.artifacts.json"
    manifest = {"contract_digest": contract.digest, "artifacts": artifact_digests(contract)}
    if check:
        if json.loads(expected.read_text()) != manifest:
            raise ValueError(
                "generated contract artifact drift; review and update the digest manifest"
            )
        return
    if output is None:
        raise ValueError("an output directory is required")
    output.mkdir(parents=True, exist_ok=True)
    for name, text in artifacts(contract).items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (output / "manifest.json").write_text(canonical(manifest) + "\n")
