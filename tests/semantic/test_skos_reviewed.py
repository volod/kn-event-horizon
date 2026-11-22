"""Real reviewed dictionaries retain their publication boundaries in exported Turtle."""

from pathlib import Path

import pytest
from rdflib import Graph, Literal
from rdflib.namespace import RDF, SKOS

from kn.semantic.seeds import reviewed_snapshot
from kn.semantic.skos import KN, export_scheme, term_uri

SCHEMES = sorted(row["id"] for row in reviewed_snapshot()["concept_schemes"])


@pytest.mark.parametrize("scheme_id", SCHEMES)
def test_reviewed_scheme_export(scheme_id: str, tmp_path: Path) -> None:
    snapshot = reviewed_snapshot()
    result = export_scheme(scheme_id, tmp_path)
    path = Path(str(result["path"]))
    assert path.parent.parent == tmp_path / "skos"
    assert path.read_bytes().isascii()
    graph = Graph().parse(path, format="turtle")
    selected = {row["id"] for row in snapshot["concepts"] if row["scheme_id"] == scheme_id}
    assert result["concepts"] == len(selected)
    assert set(graph.subjects(SKOS.inScheme, term_uri(scheme_id))) == {
        term_uri(key) for key in selected
    }
    for row in snapshot["labels"]:
        if row["term_id"] in selected | {scheme_id}:
            assert (
                term_uri(row["term_id"]),
                SKOS.prefLabel,
                Literal(row["label"], lang=row["locale"]),
            ) in graph
    for subject in graph.subjects(RDF.type, SKOS.ConceptScheme):
        assert graph.value(subject, KN.origin) is not None
        assert graph.value(subject, KN.verificationState) is not None
        assert len(list(graph.objects(subject, SKOS.scopeNote))) == 2
        assert graph.value(subject, KN.contentSha256) is not None
    second = export_scheme(scheme_id, tmp_path)
    assert path != Path(str(second["path"]))
    assert path.read_bytes() == Path(str(second["path"])).read_bytes()


@pytest.mark.parametrize(
    "scheme_id", ["microelectronics.product_v1.scheme", "microelectronics.oecd_2024.scheme"]
)
def test_cross_scheme_mappings_include_incoming_without_promoting_extensions(
    scheme_id: str, tmp_path: Path
) -> None:
    result = export_scheme(scheme_id, tmp_path)
    graph = Graph().parse(str(result["path"]), format="turtle")
    snapshot = reviewed_snapshot()
    for mapping in snapshot["concept_mappings"]:
        predicate = (
            KN.analystCrosswalk
            if mapping["mapping_type"] == "analyst_crosswalk"
            else SKOS[mapping["mapping_type"]]
        )
        assert (term_uri(mapping["source_id"]), predicate, term_uri(mapping["target_id"])) in graph
    product = term_uri("microelectronics.product_v1.scheme")
    oecd = term_uri("microelectronics.oecd_2024.scheme")
    assert (product, KN.origin, Literal("kb_normalized")) in graph
    assert (product, KN.verificationState, Literal("unverified")) in graph
    assert (oecd, KN.origin, Literal("official")) in graph
    assert (oecd, KN.verificationState, Literal("verified")) in graph
    extension = term_uri("microelectronics.product_v1.L.MCU.AI")
    assert (extension, SKOS.inScheme, product) in graph
    assert (extension, SKOS.inScheme, oecd) not in graph


def test_ascii_escaping_round_trips_unicode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Reviewed uk labels currently use source fallback; exercise actual Unicode serialization too.
    from kn.semantic import skos

    original = skos.reviewed_snapshot
    snapshot = original()
    label = next(
        row
        for row in snapshot["labels"]
        if row["term_id"] == "gdelt.services.S01" and row["locale"] == "uk"
    )
    label["label"] = 'caf\u00e9 \u041a\u0438\u0457\u0432 "quoted" \\ \n\U0001f680'
    monkeypatch.setattr(skos, "reviewed_snapshot", lambda: snapshot)
    result = export_scheme("gdelt.services.scheme", tmp_path)
    path = Path(str(result["path"]))
    assert path.read_bytes().isascii()
    graph = Graph().parse(path, format="turtle")
    assert (term_uri(label["term_id"]), SKOS.prefLabel, Literal(label["label"], lang="uk")) in graph
