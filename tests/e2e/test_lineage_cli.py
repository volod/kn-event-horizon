"""Lineage goldens shared by the in-memory and PostgreSQL paths."""

import json
from pathlib import Path

from kn.i18n import Translator
from kn.i18n.output import render_result
from kn.identity.lineage import lineage
from tests.e2e.support import FIXTURES, write_json
from tests.identity.lineage_fixtures import CASES, build

GOLDENS = FIXTURES / "lineage-cli.json"


def rendered(data_dir: Path) -> dict[str, dict[str, object]]:
    """Each case as the JSON result and its text output."""
    fixture = build(data_dir)
    state, rows = fixture.journal.state(), fixture.rows
    result: dict[str, dict[str, object]] = {}
    for name, case in CASES.items():
        view = lineage(state, rows, case.reference, field_id=case.field_id, audience=case.audience)
        result[name] = {
            "json": view,
            "text": render_result(Translator(), "lineage", view),
        }
    return result


def test_lineage_goldens(tmp_path: Path, e2e_artifacts: Path) -> None:
    expected = json.loads(GOLDENS.read_text("ascii"))
    for name, output in rendered(tmp_path).items():
        write_json(e2e_artifacts / "cli" / "lineage" / f"{name}.json", output["text"])
        assert output["text"] == expected[name], name
