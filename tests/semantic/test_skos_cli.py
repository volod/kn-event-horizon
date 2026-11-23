"""The export command follows bilingual CLI and stable machine error conventions."""

import json
import logging
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import SKOS

from kn import cli
from kn.i18n import Translator
from kn.semantic.skos import term_uri

SCHEME = "gdelt.services.scheme"


@pytest.mark.parametrize("locale", ["en", "uk"])
@pytest.mark.parametrize("machine", [False, True])
def test_skos_cli(
    locale: str,
    machine: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "runtime data"))
    caplog.set_level(logging.INFO, logger="kn.operator")
    arguments = ["--locale", locale, "vocabulary", "export", "--format", "skos", "--scheme", SCHEME]
    assert cli.main([*arguments, *(["--json"] if machine else [])]) == 0
    paths = list((tmp_path / "runtime data/skos").glob("*/vocabulary.ttl"))
    assert len(paths) == 1
    graph = Graph().parse(paths[0], format="turtle")
    assert len(list(graph.subjects(SKOS.inScheme, term_uri(SCHEME)))) == 13
    expected = {
        "status": "exported",
        "format": "skos",
        "scheme_id": SCHEME,
        "path": str(paths[0]),
        "concepts": 13,
        "origin": "service_extension",
        "verification_state": "unverified",
        "fallbacks_en": 0,
        "fallbacks_uk": 14,
    }
    if machine:
        assert json.loads(caplog.records[-1].message) == expected
    else:
        assert caplog.records[-1].message == Translator(locale).text("cli.skos_ok", **expected)


@pytest.mark.parametrize("locale", ["en", "uk"])
def test_skos_cli_unknown_scheme_and_unwritable_output(
    locale: str,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    arguments = [
        "--locale",
        locale,
        "--json",
        "vocabulary",
        "export",
        "--format",
        "skos",
        "--data-dir",
        str(tmp_path),
    ]
    assert cli.main([*arguments, "--scheme", "unknown.scheme"]) == 1
    assert json.loads(caplog.records[-1].message) == {"error": {"code": "E_INPUT"}}
    assert not list(tmp_path.iterdir())
    (tmp_path / "skos").write_text("blocked", encoding="ascii")
    assert cli.main([*arguments, "--scheme", SCHEME]) == 1
    assert json.loads(caplog.records[-1].message) == {"error": {"code": "E_INPUT"}}


@pytest.mark.parametrize(
    "options",
    [
        [],
        ["--format", "skos"],
        ["--scheme", SCHEME],
        ["--scheme", SCHEME, "--format", "rdfxml"],
        ["--scheme", SCHEME, "--format", "skos", "--check"],
    ],
)
def test_skos_cli_invalid_arguments(options: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["--json", "vocabulary", "export", *options])
    assert error.value.code == 2
    assert json.loads(capsys.readouterr().err) == {"error": {"code": "E_ARGUMENTS"}}
