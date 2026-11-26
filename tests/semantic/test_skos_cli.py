"""The export command follows English CLI and stable machine error conventions."""

import json
import logging
from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS

from kn import cli
from kn.i18n import Translator
from kn.semantic.skos import term_uri

SCHEME = "gdelt.services.scheme"


@pytest.mark.parametrize("machine", [False, True])
def test_skos_cli(
    machine: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "runtime data"))
    caplog.set_level(logging.INFO, logger="kn.operator")
    arguments = ["vocabulary", "export", "--format", "skos", "--scheme", SCHEME]
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
        assert caplog.records[-1].message == Translator().text("cli.skos_ok", **expected)


def test_skos_cli_unknown_scheme_and_unwritable_output(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    arguments = [
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


def test_skos_cli_uses_configured_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scheme = "microelectronics.oecd_2024.scheme"
    monkeypatch.setenv("KN_VOCABULARY_DOMAIN", "Vocabulary.Example.Test.")
    assert (
        cli.main(
            [
                "vocabulary",
                "export",
                "--scheme",
                scheme,
                "--format",
                "skos",
                "--data-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    path = next(tmp_path.glob("skos/*/vocabulary.ttl"))
    graph = Graph().parse(path, format="turtle")
    base = "urn:publicid:%2B:IDN+vocabulary.example.test:NONSGML+KN+Event+Horizon+Vocabulary:EN"
    assert len(list(graph.subjects(SKOS.inScheme, URIRef(f"{base}#term/{scheme}")))) == 29
    project_iris = {
        node
        for triple in graph
        for node in triple
        if isinstance(node, URIRef) and node.startswith("urn:publicid:")
    }
    assert all(node.startswith(f"{base}#") for node in project_iris)
    assert URIRef(f"{base}#semantic/analystCrosswalk") in project_iris
    assert URIRef(f"{base}#label-selection/{scheme}:uk") in project_iris


@pytest.mark.parametrize("domain", ["", "https://example.test", "127.0.0.1", "x..example.test"])
def test_skos_cli_rejects_invalid_namespace_domain(
    domain: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("KN_VOCABULARY_DOMAIN", domain)
    assert (
        cli.main(
            [
                "--json",
                "vocabulary",
                "export",
                "--scheme",
                SCHEME,
                "--format",
                "skos",
                "--data-dir",
                str(tmp_path),
            ]
        )
        == 1
    )
    assert json.loads(caplog.records[-1].message) == {"error": {"code": "E_INPUT"}}
    assert not list(tmp_path.iterdir())


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
