"""Read-only SKOS interchange from validated semantic snapshots and reviewed seeds."""

from pathlib import Path
from uuid import uuid4

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

from kn.semantic import ExternalReferences, validate_model
from kn.semantic.oecd_reference import publication_references
from kn.semantic.proposals import DOMAINS
from kn.semantic.seeds import RESOURCES, reviewed_snapshot
from kn.semantic.skos_namespace import DEFAULT_NAMESPACE, VocabularyNamespace, configured_namespace
from kn.semantic.structure import Row, Snapshot, indexed
from kn.semantic.text import select_label
from kn.semantic.verification import VerificationReport

KN = DEFAULT_NAMESPACE.metadata
TERM = DEFAULT_NAMESPACE.terms
LABEL_SELECTION = DEFAULT_NAMESPACE.label_selections
DISPLAY_LOCALES = ("en", "uk")
MAX_BMP_CODEPOINT = 0xFFFF
MAPPING_PROPERTIES = {
    name: SKOS[name]
    for name in ("exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch")
}
SCHEME_PROPERTIES = {
    "origin": "origin",
    "verification_state": "verificationState",
    "verification_reason": "verificationReason",
    "edition": "edition",
    "source_sha256": "sourceSha256",
}


def term_uri(identifier: str, namespace: VocabularyNamespace = DEFAULT_NAMESPACE) -> URIRef:
    """Stable KN identity; publication URLs never become identifiers for local terms."""
    return namespace.terms[identifier]


def skos_graph(
    snapshot: Snapshot,
    scheme_id: str,
    *,
    references: ExternalReferences | None = None,
    namespace: VocabularyNamespace = DEFAULT_NAMESPACE,
) -> Graph:
    """Export one scheme and touching mappings, preserving their stored direction.

    Counterpart concepts and schemes receive descriptions but no expanded hierarchy. This keeps
    incoming mappings useful without recursively exporting unrelated vocabularies.
    """
    validate_model(snapshot, references)
    schemes = indexed(snapshot, "concept_schemes")
    if scheme_id not in schemes:
        raise ValueError("unknown concept scheme")
    concepts = indexed(snapshot, "concepts")
    selected = {key for key, row in concepts.items() if row["scheme_id"] == scheme_id}
    mappings = [
        row
        for row in snapshot.get("concept_mappings", [])
        if row["source_id"] in selected or row["target_id"] in selected
    ]
    included = selected | {row[key] for row in mappings for key in ("source_id", "target_id")}
    scheme_ids = {scheme_id} | {concepts[key]["scheme_id"] for key in included}
    graph = Graph(bind_namespaces="none")
    for prefix, rdf_namespace in (
        ("skos", SKOS),
        ("kn", namespace.metadata),
        ("term", namespace.terms),
        ("dcterms", DCTERMS),
        ("rdf", RDF),
        ("owl", OWL),
        ("rdfs", RDFS),
        ("selection", namespace.label_selections),
    ):
        graph.bind(prefix, rdf_namespace)
    for key in sorted(scheme_ids):
        _scheme(graph, schemes[key], namespace)
    for key in sorted(included):
        _concept(graph, concepts[key], namespace, hierarchy=key in selected)
    for row in mappings:
        _mapping(graph, row, namespace)
    _terms(graph, snapshot, included | scheme_ids | {row["id"] for row in mappings}, namespace)
    return graph


def _scheme(graph: Graph, row: Row, namespace: VocabularyNamespace) -> None:
    subject = term_uri(row["id"], namespace)
    graph.add((subject, RDF.type, SKOS.ConceptScheme))
    for key, predicate in SCHEME_PROPERTIES.items():
        if row.get(key) is not None:
            graph.add((subject, namespace.metadata[predicate], Literal(row[key])))
    graph.add((subject, SKOS.scopeNote, Literal(row["verification_reason"])))
    if row.get("publisher") is not None:
        graph.add((subject, DCTERMS.publisher, Literal(row["publisher"])))
    if row.get("source_uri"):
        graph.add((subject, DCTERMS.source, URIRef(row["source_uri"])))


def _concept(graph: Graph, row: Row, namespace: VocabularyNamespace, *, hierarchy: bool) -> None:
    subject = term_uri(row["id"], namespace)
    scheme = term_uri(row["scheme_id"], namespace)
    graph.add((subject, RDF.type, SKOS.Concept))
    graph.add((subject, SKOS.inScheme, scheme))
    if row.get("replacement_id"):
        graph.add((subject, DCTERMS.isReplacedBy, term_uri(row["replacement_id"], namespace)))
    if not hierarchy:
        return
    if row.get("parent_id"):
        parent = term_uri(row["parent_id"], namespace)
        graph.add((subject, SKOS.broader, parent))
        graph.add((parent, SKOS.narrower, subject))
    else:
        graph.add((subject, SKOS.topConceptOf, scheme))
        graph.add((scheme, SKOS.hasTopConcept, subject))


def _mapping(graph: Graph, row: Row, namespace: VocabularyNamespace) -> None:
    metadata = namespace.metadata
    subject = term_uri(row["id"], namespace)
    source = term_uri(row["source_id"], namespace)
    target = term_uri(row["target_id"], namespace)
    mapping_type = row["mapping_type"]
    predicate = (
        metadata.analystCrosswalk
        if mapping_type == "analyst_crosswalk"
        else MAPPING_PROPERTIES[mapping_type]
    )
    graph.add((source, predicate, target))
    # Named RDF statements retain each reviewed mapping's identity, method and evidence.
    graph.add((subject, RDF.type, RDF.Statement))
    graph.add((subject, RDF.subject, source))
    graph.add((subject, RDF.predicate, predicate))
    graph.add((subject, RDF.object, target))
    graph.add((subject, metadata.method, Literal(row["method"])))
    graph.add((subject, metadata.evidenceId, Literal(row["evidence_id"])))


def _terms(
    graph: Graph, snapshot: Snapshot, included: set[str], namespace: VocabularyNamespace
) -> None:
    for row in snapshot.get("terms", []):
        if row["id"] in included:
            _term(graph, row, namespace)
    _labels(graph, snapshot, included, namespace)
    _label_selections(graph, snapshot, included, namespace)


def _term(graph: Graph, row: Row, namespace: VocabularyNamespace) -> None:
    subject = term_uri(row["id"], namespace)
    graph.add((subject, DCTERMS.identifier, Literal(row["id"])))
    if row.get("definition") is not None:
        graph.add((subject, SKOS.definition, Literal(row["definition"])))
    graph.add((subject, namespace.metadata.status, Literal(row["status"])))
    if row["kind"] == "concept":
        graph.add((subject, SKOS.notation, Literal(row["code"])))
    if row["status"] in {"deprecated", "replaced"}:
        graph.add((subject, OWL.deprecated, Literal(True)))


def _labels(
    graph: Graph, snapshot: Snapshot, included: set[str], namespace: VocabularyNamespace
) -> None:
    for dataset, predicate in (("labels", SKOS.prefLabel), ("alternative_labels", SKOS.altLabel)):
        for row in snapshot.get(dataset, []):
            if row["term_id"] in included:
                subject = term_uri(row["term_id"], namespace)
                graph.add((subject, predicate, Literal(row["label"], lang=row["locale"])))
                if row.get("definition"):
                    graph.add(
                        (subject, SKOS.definition, Literal(row["definition"], lang=row["locale"]))
                    )


def _review_notes(graph: Graph, namespace: VocabularyNamespace) -> None:
    metadata = namespace.metadata
    for domain in DOMAINS:
        report = VerificationReport.model_validate_json(
            (RESOURCES / f"{domain}-verification.json").read_bytes()
        )
        for review in report.schemes:
            subject = term_uri(review.scheme_id, namespace)
            if (subject, RDF.type, SKOS.ConceptScheme) in graph:
                graph.add((subject, SKOS.scopeNote, Literal(review.scope)))
                graph.add((subject, metadata.comparison, Literal(review.comparison)))
                graph.add((subject, metadata.contentSha256, Literal(review.content_sha256)))


def _label_selections(
    graph: Graph, snapshot: Snapshot, included: set[str], namespace: VocabularyNamespace
) -> None:
    metadata = namespace.metadata
    labelled = {row["term_id"] for row in snapshot.get("labels", [])} & included
    for identifier in sorted(labelled):
        for locale in DISPLAY_LOCALES:
            chosen = select_label(snapshot, identifier, locale)
            selection = namespace.label_selections[identifier + ":" + locale]
            graph.add((term_uri(identifier, namespace), metadata.labelSelection, selection))
            graph.add((selection, RDF.type, metadata.LabelSelection))
            graph.add((selection, metadata.requestedLanguage, Literal(locale)))
            graph.add((selection, metadata.selectedLanguage, Literal(chosen.variant.language)))
            graph.add(
                (selection, RDFS.label, Literal(chosen.variant.text, lang=chosen.variant.language))
            )
            graph.add((selection, metadata.provenance, Literal(chosen.variant.provenance)))
            graph.add((selection, metadata.fallback, Literal(chosen.fallback)))
            graph.add((selection, metadata.isOriginal, Literal(chosen.is_original)))


def _fallbacks(graph: Graph, locale: str, namespace: VocabularyNamespace) -> int:
    metadata = namespace.metadata
    return sum(
        graph.value(selection, metadata.fallback) == Literal(True)
        for selection in graph.subjects(metadata.requestedLanguage, Literal(locale))
    )


def export_scheme(scheme_id: str, data_dir: Path) -> dict[str, object]:
    """Write an ASCII Turtle artifact only after reviewed content passes all checks."""
    namespace = configured_namespace()
    snapshot = reviewed_snapshot()
    graph = skos_graph(
        snapshot, scheme_id, references=publication_references(RESOURCES), namespace=namespace
    )
    _review_notes(graph, namespace)
    # Turtle Unicode escapes preserve exact text while keeping runtime evidence ASCII.
    turtle = graph.serialize(format="turtle")
    escapes = {
        ord(character): (
            f"\\u{ord(character):04X}"
            if ord(character) <= MAX_BMP_CODEPOINT
            else f"\\U{ord(character):08X}"
        )
        for character in set(turtle)
        if not character.isascii()
    }
    content = turtle.translate(escapes).encode("ascii")
    destination = data_dir / "skos" / uuid4().hex
    destination.mkdir(parents=True)
    path = destination / "vocabulary.ttl"
    path.write_bytes(content)
    scheme = indexed(snapshot, "concept_schemes")[scheme_id]
    return {
        "status": "exported",
        "format": "skos",
        "scheme_id": scheme_id,
        "path": str(path),
        "concepts": sum(row["scheme_id"] == scheme_id for row in snapshot["concepts"]),
        "origin": scheme["origin"],
        "verification_state": scheme["verification_state"],
        "fallbacks_en": _fallbacks(graph, "en", namespace),
        "fallbacks_uk": _fallbacks(graph, "uk", namespace),
    }
