"""Identifier, lifecycle, hierarchy and multilingual label integrity."""

import re
import unicodedata

from kn.semantic.structure import Row, Snapshot, acyclic, indexed, refuse
from kn.semantic.text import validate_text

DATASETS = {
    "entity_class": "entity_classes",
    "relation_type": "relation_types",
    "concept_scheme": "concept_schemes",
    "concept": "concepts",
    "concept_mapping": "concept_mappings",
    "entity_tag": "entity_tags",
    "attribute_definition": "attribute_definitions",
    "condition_set": "condition_sets",
    "comparison_profile": "comparison_profiles",
    "rubric": "rubrics",
}
UNLABELED_KINDS = {"concept_mapping", "entity_tag"}
NAMESPACE_CODE = re.compile(r"[a-z][a-z0-9_]*(?:[.-][a-z0-9_]+)*")
NATIVE_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*")
LOCALE = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")


def validate_terms(data: Snapshot) -> None:
    terms = indexed(data, "terms")
    namespaces = indexed(data, "namespaces")
    if terms.keys() & namespaces.keys():
        refuse(("terms",), "unique", "keep namespace IDs and term IDs distinct")
    for index, row in enumerate(data.get("namespaces", [])):
        if (
            not NAMESPACE_CODE.fullmatch(row["domain"])
            or not NAMESPACE_CODE.fullmatch(row["code"])
            or row["id"] != row["domain"] + "." + row["code"]
        ):
            refuse(("namespaces", index), "identifier", "qualify namespace codes by domain")
    datasets = {kind: indexed(data, dataset) for kind, dataset in DATASETS.items()}
    _term_kinds(data, datasets)
    _concepts(data)
    acyclic(indexed(data, "entity_classes"), "parent_id", "entity_classes")
    _labels(data)
    validate_text(data)


def _term_kinds(data: Snapshot, datasets: dict[str, dict[str, Row]]) -> None:
    terms = indexed(data, "terms")
    for index, row in enumerate(data.get("terms", [])):
        if not NATIVE_CODE.fullmatch(row["code"]) or row["id"] != (
            row["namespace_id"] + "." + row["code"]
        ):
            refuse(("terms", index), "identifier", "qualify original string codes by namespace")
        if row["id"] not in datasets[row["kind"]]:
            refuse(("terms", index), "kind", "supply exactly one row in the declared dataset")
        if row["status"] == "replaced" and row["kind"] != "concept":
            refuse(("terms", index), "status", "only concepts support replacement links")
    for kind, dataset in DATASETS.items():
        for index, row in enumerate(data.get(dataset, [])):
            if terms[row["id"]]["kind"] != kind:
                refuse((dataset, index), "kind", "match the term's declared dataset kind")


def _concepts(data: Snapshot) -> None:
    terms = indexed(data, "terms")
    concepts = indexed(data, "concepts")
    for index, row in enumerate(data.get("concepts", [])):
        scheme = terms[row["scheme_id"]]
        if terms[row["id"]]["namespace_id"] != scheme["namespace_id"]:
            refuse(("concepts", index), "scheme", "qualify concepts in their scheme namespace")
        replaced = terms[row["id"]]["status"] == "replaced"
        if replaced != bool(row.get("replacement_id")):
            refuse(("concepts", index), "replacement", "give replaced concepts a successor only")
        for column in ("parent_id", "replacement_id"):
            target = row.get(column)
            if target and concepts[target]["scheme_id"] != row["scheme_id"]:
                refuse(("concepts", index, column), "scheme", "keep primary links within a scheme")
    for column in ("parent_id", "replacement_id"):
        acyclic(concepts, column, "concepts")


def normalized_label(value: str) -> str:
    """Compare labels without changing their original spelling in storage."""
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _labels(data: Snapshot) -> None:
    terms = indexed(data, "terms")
    concepts = indexed(data, "concepts")
    seen: set[tuple[str, str, str, str]] = set()
    locales: dict[str, set[str]] = {}
    for index, row in enumerate(data.get("labels", [])):
        term = terms[row["term_id"]]
        scope = (
            concepts[term["id"]]["scheme_id"] if term["kind"] == "concept" else term["namespace_id"]
        )
        key = (term["kind"], scope, row["locale"].lower(), normalized_label(row["label"]))
        if key in seen:
            refuse(("labels", index), "label", "use distinct preferred labels within a scheme")
        seen.add(key)
        locales.setdefault(term["id"], set()).add(row["locale"])
        inverse = row.get("inverse_label")
        if (term["kind"] == "relation_type") != bool(inverse):
            refuse(("labels", index), "inverse", "give only relations localized inverse labels")
    for row in terms.values():
        if row["kind"] not in UNLABELED_KINDS:
            _required_labels(locales.get(row["id"], set()), "labels")
    _locale_rows(data)


def _required_labels(locales: set[str], dataset: str) -> None:
    if not locales:
        refuse((dataset,), "locale", "supply at least one preferred label in its source language")


def _locale_rows(data: Snapshot) -> None:
    namespaces: dict[str, set[str]] = {}
    preferred = {
        (row["term_id"], row["locale"]): normalized_label(row["label"])
        for row in data.get("labels", [])
    }
    alternatives: set[tuple[str, str, str]] = set()
    for dataset in ("labels", "namespace_labels", "alternative_labels"):
        for index, row in enumerate(data.get(dataset, [])):
            if not LOCALE.fullmatch(row["locale"]):
                refuse((dataset, index), "locale", "use a language tag such as en, uk or en-GB")
            if dataset == "namespace_labels":
                namespaces.setdefault(row["namespace_id"], set()).add(row["locale"].lower())
            if dataset == "alternative_labels":
                _alternative(row, index, preferred, alternatives)
    _unique_locales(data, "labels", "term_id")
    _unique_locales(data, "namespace_labels", "namespace_id")
    for row in data.get("namespaces", []):
        _required_labels(namespaces.get(row["id"], set()), "namespace_labels")


def _alternative(
    row: Row,
    index: int,
    preferred: dict[tuple[str, str], str],
    alternatives: set[tuple[str, str, str]],
) -> None:
    key = (row["term_id"], row["locale"], normalized_label(row["label"]))
    if key[:2] not in preferred or preferred[key[:2]] == key[2] or key in alternatives:
        refuse(
            ("alternative_labels", index),
            "label",
            "use distinct alternatives with a preferred label",
        )
    alternatives.add(key)


def _unique_locales(data: Snapshot, dataset: str, subject: str) -> None:
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(data.get(dataset, [])):
        key = (row[subject], row["locale"].lower())
        if key in seen:
            refuse((dataset, index), "locale", "use one preferred label per language tag")
        seen.add(key)
