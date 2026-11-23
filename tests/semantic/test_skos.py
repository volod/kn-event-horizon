"""SKOS interchange preserves identifiers, language text and mapping semantics."""

from copy import deepcopy
from pathlib import Path

import pytest
from rdflib import Graph, Literal
from rdflib.namespace import DCTERMS, OWL, RDF, SKOS

from kn.contracts.diagnostics import ContractError
from kn.semantic import Snapshot
from kn.semantic.skos import KN, export_scheme, skos_graph, term_uri
from tests.semantic.conftest import REFERENCES

SCHEME = "space.demo.scheme"


def test_labels_definitions_hierarchy_and_lifecycle_round_trip(model: Snapshot) -> None:
    text = 'Quoted "label" \\ newline\n\u041a\u0438\u0457\u0432 \U0001f680'
    model["labels"][8]["label"] = text
    model["alternative_labels"] = [
        {"term_id": "space.demo.001", "locale": "en", "label": "Alternative"}
    ]
    model["terms"][6]["status"] = "replaced"
    model["concepts"][2]["replacement_id"] = "space.demo.001"
    original = deepcopy(model)
    graph = skos_graph(model, SCHEME, references=REFERENCES)
    parsed = Graph().parse(data=graph.serialize(format="turtle"), format="turtle")
    root, child, replaced = (term_uri("space.demo." + code) for code in ("001", "002", "003"))
    assert (root, SKOS.prefLabel, Literal(text, lang="en")) in parsed
    assert (root, SKOS.altLabel, Literal("Alternative", lang="en")) in parsed
    assert (root, SKOS.notation, Literal("001")) in parsed
    assert (root, SKOS.definition, Literal("001 definition")) in parsed
    assert (root, SKOS.definition, Literal("001 definition uk", lang="uk")) in parsed
    assert (child, SKOS.broader, root) in parsed
    assert (root, SKOS.narrower, child) in parsed
    assert (term_uri(SCHEME), SKOS.hasTopConcept, root) in parsed
    assert (root, SKOS.topConceptOf, term_uri(SCHEME)) in parsed
    assert (replaced, DCTERMS.isReplacedBy, root) in parsed
    assert (replaced, OWL.deprecated, Literal(True)) in parsed
    assert (replaced, KN.status, Literal("replaced")) in parsed
    assert not list(parsed.subjects(RDF.type, KN.OfficialScheme))
    assert (term_uri(SCHEME), KN.origin, Literal("kb_extension")) in parsed
    assert (term_uri(SCHEME), KN.verificationState, Literal("unverified")) in parsed
    assert not list(parsed.triples((term_uri("space.demo.Organization"), None, None)))
    assert model == original


@pytest.mark.parametrize(
    "mapping_type",
    ["exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch", "analyst_crosswalk"],
)
def test_mapping_direction_and_evidence(model: Snapshot, mapping_type: str) -> None:
    row = model["concept_mappings"][0]
    row["mapping_type"] = mapping_type
    graph = skos_graph(model, SCHEME, references=REFERENCES)
    predicate = KN.analystCrosswalk if mapping_type == "analyst_crosswalk" else SKOS[mapping_type]
    source, target = term_uri(row["source_id"]), term_uri(row["target_id"])
    statement = term_uri(row["id"])
    assert (source, predicate, target) in graph
    assert (target, predicate, source) not in graph
    assert (statement, RDF.type, RDF.Statement) in graph
    assert (statement, RDF.subject, source) in graph
    assert (statement, RDF.predicate, predicate) in graph
    assert (statement, RDF.object, target) in graph
    assert (statement, KN.method, Literal("fixture")) in graph
    assert (statement, KN.evidenceId, Literal("fixture.evidence")) in graph
    if mapping_type == "analyst_crosswalk":
        assert not any(graph.triples((source, SKOS.mappingRelation, None)))
        assert not any(graph.triples((source, SKOS.exactMatch, None)))


def test_invalid_model_and_unknown_scheme_fail(model: Snapshot, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="scheme"):
        skos_graph(model, "space.demo.001", references=REFERENCES)
    model["concepts"][0]["parent_id"] = "space.demo.002"
    with pytest.raises(ContractError, match=r"semantic\.cycle"):
        skos_graph(model, SCHEME, references=REFERENCES)
    with pytest.raises(ValueError, match="scheme"):
        export_scheme("../../outside", tmp_path)
    assert not list(tmp_path.iterdir())


def test_empty_scheme_and_reordered_input_are_stable(model: Snapshot) -> None:
    graph = skos_graph(model, SCHEME, references=REFERENCES)
    reordered = {key: list(reversed(rows)) for key, rows in reversed(list(model.items()))}
    assert graph.serialize(format="turtle") == skos_graph(
        reordered, SCHEME, references=REFERENCES
    ).serialize(format="turtle")
    model["concepts"] = []
    model["concept_mappings"] = []
    model["entity_tags"] = []
    model["alternative_labels"] = []
    model["terms"] = [
        row
        for row in model["terms"]
        if row["kind"] not in {"concept", "concept_mapping", "entity_tag"}
    ]
    model["labels"] = [
        row
        for row in model["labels"]
        if row["term_id"] not in {"space.demo.001", "space.demo.002", "space.demo.003"}
    ]
    graph = skos_graph(model, SCHEME, references=REFERENCES)
    assert (term_uri(SCHEME), RDF.type, SKOS.ConceptScheme) in graph
    assert not list(graph.subjects(RDF.type, SKOS.Concept))
