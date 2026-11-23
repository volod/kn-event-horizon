"""An independent strict parser, Oxigraph, reads every exported scheme as RDFLib does."""

from pathlib import Path

import pytest
from pyoxigraph import Literal as OxigraphLiteral
from pyoxigraph import NamedNode, RdfFormat, parse
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.term import Node

from kn.semantic.seeds import reviewed_snapshot
from kn.semantic.skos import export_scheme

SCHEMES = sorted(row["id"] for row in reviewed_snapshot()["concept_schemes"])


def rdflib_term(term: object) -> Node:
    """The export has no blank nodes, so every term is an IRI or a literal."""
    if isinstance(term, NamedNode):
        return URIRef(term.value)
    assert isinstance(term, OxigraphLiteral), term
    if term.language:
        return Literal(term.value, lang=term.language)
    if term.datatype.value == str(XSD.string):
        return Literal(term.value)
    return Literal(term.value, datatype=URIRef(term.datatype.value))


@pytest.mark.parametrize("scheme_id", SCHEMES)
def test_an_independent_parser_reads_the_same_triples(scheme_id: str, tmp_path: Path) -> None:
    data = Path(str(export_scheme(scheme_id, tmp_path)["path"])).read_bytes()
    # Oxigraph parses strictly by default: an invalid IRI, escape or term fails here.
    independent = {
        (rdflib_term(quad.subject), rdflib_term(quad.predicate), rdflib_term(quad.object))
        for quad in parse(data, RdfFormat.TURTLE)
    }
    reference = set(Graph().parse(data=data, format="turtle"))
    assert independent and independent == reference


def test_the_independent_parser_refuses_what_the_exporter_must_never_write() -> None:
    with pytest.raises(SyntaxError):
        list(parse(b"<https://example.org/a b> <urn:p> <urn:o> .", RdfFormat.TURTLE))
