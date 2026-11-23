"""Exercise the real catalogue rebuild and failure paths in PostgreSQL."""

import shutil
from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Connection

from kn.contracts.diagnostics import ContractError
from kn.db.platform import role_name
from kn.db.rebuild import rebuild
from kn.db.seeds import load_reviewed_seeds
from kn.db.statements import ResetRole, SetRole
from kn.sources import seeds
from kn.sources.catalogue import catalogue_table, list_sources, load_reviewed_catalogue


def test_rebuild_loads_and_lists_every_source_as_candidates(rebuild_connection: Connection) -> None:
    connection = rebuild_connection
    rebuild(connection)
    connection.execute(SetRole(role_name("system", "reader")))
    listed = list_sources(connection)
    assert Counter(row["domain"] for row in listed) == {
        "space": 37,
        "microelectronics": 65,
        "gdelt": 17,
    }
    assert {row["lifecycle_state"] for row in listed} == {"candidate"}
    assert {row["access_verification"] for row in listed} == {"unverified"}
    assert len({row["source_id"] for row in listed}) == 119
    assert all(row["access_notes"] for row in listed)
    connection.execute(ResetRole())
    load_reviewed_seeds(connection)
    assert list_sources(connection) == listed
    rebuild(connection)
    assert list_sources(connection) == listed


def test_reapplying_changed_seeds_refuses_and_rolls_back_partial_inserts(
    rebuild_connection: Connection,
) -> None:
    connection = rebuild_connection
    rebuild(connection)
    table = catalogue_table()
    connection.execute(table.delete().where(table.c.source_id == "gdelt:row-5"))
    changed = table.c.source_id == "space:row-4"
    connection.execute(table.update().where(changed).values(label="sentinel"))
    with pytest.raises(ValueError, match=r"conflicts.*system\.source_catalogue"):
        load_reviewed_catalogue(connection)
    assert connection.scalar(select(table.c.label).where(changed)) == "sentinel"
    assert len(list_sources(connection)) == 118


def test_unknown_rank_override_rolls_back_the_catalogue_rebuild(
    rebuild_connection: Connection, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    connection = rebuild_connection
    rebuild(connection)
    table = catalogue_table()
    source_id = "space:row-4"
    connection.execute(
        table.update().where(table.c.source_id == source_id).values(label="sentinel")
    )
    resources = tmp_path / "resources"
    shutil.copytree(seeds.RESOURCES, resources)
    (resources / "source-ranks.yaml").write_text(
        "overrides:\n  - {source_id: 'space:D01', rank: first_party}\n", encoding="ascii"
    )
    monkeypatch.setattr(seeds, "RESOURCES", resources)
    with pytest.raises(ContractError, match="sourceId"):
        rebuild(connection)
    assert (
        connection.scalar(select(table.c.label).where(table.c.source_id == source_id)) == "sentinel"
    )
    assert len(list_sources(connection)) == 119
