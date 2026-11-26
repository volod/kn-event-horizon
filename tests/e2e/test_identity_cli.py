"""Real identity lookups and stable machine responses."""

import json
from pathlib import Path

from kn.identity.journal import Journal
from tests.e2e.support import FIXTURES, run_cli, write_json
from tests.identity.fixtures import A, C, F, history


def test_identity_lookup_goldens(tmp_path: Path, e2e_artifacts: Path) -> None:
    journal = Journal(tmp_path)
    for item in history():
        journal.append(item)

    expected = json.loads((FIXTURES / "identity-cli.json").read_text("ascii"))
    for action, kn_id in (("show", C), ("resolve", A), ("history", F)):
        arguments = ["identity", action, kn_id]
        actual = run_cli(arguments, DATA_DIR=str(tmp_path))
        write_json(e2e_artifacts / "cli" / "identity" / f"{action}.json", actual)
        assert actual == expected[action]
        machine = run_cli([*arguments, "--json"], DATA_DIR=str(tmp_path))
        assert machine["exit_code"] == 0
        assert machine == run_cli(["--json", *arguments], DATA_DIR=str(tmp_path))


def test_unknown_identity_does_not_create_a_journal(tmp_path: Path) -> None:
    actual = run_cli(["--json", "identity", "resolve", A], DATA_DIR=str(tmp_path))
    assert actual["exit_code"] == 1
    assert json.loads(str(actual["stderr"])) == {"error": {"code": "E_INPUT"}}
    assert list(tmp_path.iterdir()) == []
