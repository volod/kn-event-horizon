"""Real bilingual exports carry identical reviewed vocabulary bytes."""

import hashlib
import json
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import SKOS

from kn.i18n import Translator
from kn.semantic.skos import KN, term_uri
from tests.e2e.support import LOCALES, run_cli, write_json


def test_skos_export_bilingual_entrypoint(tmp_path: Path, e2e_artifacts: Path) -> None:
    hashes: set[str] = set()
    scheme_id = "microelectronics.oecd_2024.scheme"
    for locale in LOCALES:
        arguments = [
            "vocabulary",
            "export",
            "--format",
            "skos",
            "--scheme",
            scheme_id,
            "--data-dir",
            str(tmp_path / locale),
        ]
        machine = run_cli([*arguments, "--json"], KN_LOCALE=locale)
        assert machine["exit_code"] == 0 and machine["stdout"] == ""
        result = json.loads(machine["stderr"])
        path = Path(result["path"])
        content = path.read_bytes()
        assert content.isascii()
        hashes.add(hashlib.sha256(content).hexdigest())
        graph = Graph().parse(path, format="turtle")
        assert (term_uri(scheme_id), KN.verificationState, Literal("verified")) in graph
        assert len(list(graph.subjects(SKOS.inScheme, term_uri(scheme_id)))) == 29
        human = run_cli(arguments, KN_LOCALE=locale)
        assert human["exit_code"] == 0
        paths = list((tmp_path / locale / "skos").glob("*/vocabulary.ttl"))
        assert len(paths) == 2
        human_path = next(candidate for candidate in paths if candidate != path)
        assert (
            human["stderr"]
            == Translator(locale).text("cli.skos_ok", **{**result, "path": str(human_path)}) + "\n"
        )
        assert human_path.read_bytes() == content
        write_json(e2e_artifacts / locale / "cli/skos-export.json", result)
    assert len(hashes) == 1
