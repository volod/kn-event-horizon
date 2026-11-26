"""Real CLI exports carry reviewed vocabulary and language metadata."""

import json
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import SKOS

from kn.i18n import Translator
from kn.semantic.skos import KN, term_uri
from tests.e2e.support import run_cli, write_json


def test_skos_export_entrypoint(tmp_path: Path, e2e_artifacts: Path) -> None:
    scheme_id = "microelectronics.oecd_2024.scheme"
    arguments = [
        "vocabulary",
        "export",
        "--format",
        "skos",
        "--scheme",
        scheme_id,
        "--data-dir",
        str(tmp_path),
    ]
    machine = run_cli([*arguments, "--json"])
    assert machine["exit_code"] == 0 and machine["stdout"] == ""
    result = json.loads(machine["stderr"])
    path = Path(result["path"])
    content = path.read_bytes()
    assert content.isascii()
    graph = Graph().parse(path, format="turtle")
    assert (term_uri(scheme_id), KN.verificationState, Literal("verified")) in graph
    assert len(list(graph.subjects(SKOS.inScheme, term_uri(scheme_id)))) == 29
    human = run_cli(arguments)
    assert human["exit_code"] == 0
    paths = list((tmp_path / "skos").glob("*/vocabulary.ttl"))
    assert len(paths) == 2
    human_path = next(candidate for candidate in paths if candidate != path)
    assert (
        human["stderr"]
        == Translator().text("cli.skos_ok", **{**result, "path": str(human_path)}) + "\n"
    )
    assert human_path.read_bytes() == content
    write_json(e2e_artifacts / "cli" / "skos-export.json", result)
