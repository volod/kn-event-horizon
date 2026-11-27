"""Normal CLI parsing, terminal authorization, SQL application, and stable list output."""

import json
import logging
from contextlib import contextmanager, nullcontext

import sqlalchemy as sa

from kn import cli
from kn.evidence.store import record
from kn.review import operator
from kn.review.journal import Journal
from tests.evidence.fixtures import claim, fact
from tests.identity.test_identity_operator import Session
from tests.integration.test_review_queue import prepare


class Engine:
    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return nullcontext(self.connection)

    @contextmanager
    def begin(self):
        with self.connection.begin_nested():
            yield self.connection

    def dispose(self):
        pass


def test_cli_prepares_reviews_accepts_and_revokes_a_field(
    rebuild_connection, tmp_path, monkeypatch, caplog
):
    connection = rebuild_connection
    resolver, _ = prepare(connection, tmp_path)
    monkeypatch.setattr(operator, "engine_from_env", lambda: Engine(connection))
    dataset = resolver.dataset("kn.core.semantic", "namespace_labels")
    row = dict(
        connection.execute(
            sa.select(dataset.table).order_by(*dataset.table.primary_key.columns).limit(1)
        )
        .mappings()
        .one()
    )
    query = tmp_path / "query.json"
    query.write_text(
        json.dumps(
            {
                "contract_id": "kn.core.semantic",
                "dataset": "namespace_labels",
                "key": [part.model_dump(mode="json") for part in dataset.key(row)],
                "purpose": "terminology",
                "field_id": "semantic.namespace_labels.label",
            }
        )
    )
    with caplog.at_level(logging.INFO):
        assert cli.main(["review", "list", "--target", str(query), "--json"]) == 0
        result = json.loads(caplog.records[-1].message)
        assert result["state"] == "unreviewed"
        target = tmp_path / "target.json"
        target.write_text(json.dumps(result["target"]))
        common = [
            "review",
            "decide",
            "--target",
            str(target),
            "--performed-at",
            "2026-03-01T12:00:00Z",
            "--reason",
            "Compared label",
            "--evidence",
            "review:fixture",
            "--domain",
            "fixture",
            "--json",
        ]
        session = Session("yes")
        monkeypatch.setattr(operator, "TTY", session)
        assert cli.main([*common, "--request-id", "accept-label", "--outcome", "accept"]) == 0
        accepted = json.loads(caplog.records[-1].message)["decision"]
        assert accepted["target"]["scope"] == "field"
        assert accepted["reviewer"].startswith("local:")
        assert result["target"]["version"] in session.output.message
        monkeypatch.setattr(operator, "TTY", Session("yes"))
        assert (
            cli.main(
                [
                    *common,
                    "--request-id",
                    "revoke-label",
                    "--outcome",
                    "revoke",
                    "--predecessor",
                    accepted["decision_id"],
                ]
            )
            == 0
        )
        assert cli.main(["review", "list", "--target", str(query), "--json"]) == 0
        assert json.loads(caplog.records[-1].message)["human_verified_at"] is None
        assert len(Journal(tmp_path, "fixture").read()) == 2


def test_overrides_lists_flags_even_after_the_review_item_is_settled(rebuild_connection, tmp_path):
    connection = rebuild_connection
    resolver, _ = prepare(connection, tmp_path)
    value = claim()
    record(connection, [value, fact(value, owner_override=True)])
    result = operator.listing(connection, tmp_path, resolver, overrides=True)
    assert len(result["overrides"]) == 1
    assert result["overrides"][0]["owner_override"] is True
