"""Registry-specific storage constraints compile through the shared toolchain."""

import json
from pathlib import Path

import pytest

from kn.contracts import load_contract
from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from kn.contracts.schemas import RESOURCES
from kn.identity.store import contract


def test_active_source_links_have_a_postgresql_unique_partial_index() -> None:
    ddl = artifacts(contract())["postgresql/schema.sql"]
    assert (
        "CREATE UNIQUE INDEX identity_active_link_idx ON identity.links USING btree (record_id) WHERE ended_event IS NULL"
        in ddl
    )


@pytest.mark.parametrize("predicate", ["unknown", "record_id"])
def test_partial_index_requires_an_existing_nullable_field(tmp_path: Path, predicate: str) -> None:
    document = json.loads(contract().document_json)
    table = next(item for item in document["schema"] if item["name"] == "links")
    table["customProperties"] = [
        item for item in table["customProperties"] if item["property"] != "kn.index"
    ]
    table["customProperties"].append(
        {
            "property": "kn.index",
            "value": [
                {
                    "name": "active_link_idx",
                    "fields": ["record_id"],
                    "method": "btree",
                    "unique": True,
                    "whereNull": predicate,
                }
            ],
        }
    )
    source = tmp_path / "identity.json"
    source.write_text(json.dumps(document))
    with pytest.raises(ContractError, match=r"nullable|existing"):
        load_contract(source, references=RESOURCES / "identity/references.json")
