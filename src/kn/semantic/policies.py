"""Mapping consistency, verification evidence and condition-bound policy references."""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlsplit

from kn.semantic.structure import Snapshot, indexed, refuse

SHA256 = re.compile(r"[0-9a-f]{64}")
# RFC 3987 excludes these from an IRI; RDF serializations cannot write them in an IRI reference.
IRI_EXCLUDED = re.compile(r'[\x00-\x20<>"{}|\\^`\x7f]')


@dataclass(frozen=True)
class ExternalReferences:
    """Explicit caller-owned IDs; no identity or evidence records are invented here."""

    entity_ids: frozenset[str] = frozenset()
    evidence_ids: frozenset[str] = frozenset()


def validate_policies(data: Snapshot, references: ExternalReferences) -> None:
    _schemes(data)
    _mappings(data)
    _external(data, references)
    _profiles(data)


def _schemes(data: Snapshot) -> None:
    for index, row in enumerate(data.get("concept_schemes", [])):
        checksum = row.get("source_sha256")
        if checksum is not None and not SHA256.fullmatch(checksum):
            refuse(("concept_schemes", index), "checksum", "use a lowercase SHA-256 checksum")
        if row.get("source_uri") and not _publication_uri(row["source_uri"]):
            refuse(("concept_schemes", index), "uri", "use a credential-free publication URL")
        if row["verification_state"] == "verified" and not all(
            row.get(key) for key in ("publisher", "edition", "source_uri", "source_sha256")
        ):
            refuse(
                ("concept_schemes", index),
                "verification",
                "record publisher, edition, URI and checksum",
            )


def _publication_uri(uri: str) -> bool:
    try:
        parsed = urlsplit(uri)
        return (
            not IRI_EXCLUDED.search(uri)
            and parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def _mappings(data: Snapshot) -> None:
    seen: dict[tuple[str, str, bool], tuple[str, str, str]] = {}
    exact_edges: dict[str, set[str]] = {}
    for index, row in enumerate(data.get("concept_mappings", [])):
        source, target, kind = row["source_id"], row["target_id"], row["mapping_type"]
        if source == target:
            refuse(("concept_mappings", index), "mapping", "map distinct concepts")
        if kind == "narrowMatch":
            source, target, kind = target, source, "broadMatch"
        if kind != "broadMatch":
            source, target = sorted((source, target))
        pair = (*sorted((source, target)), kind == "analyst_crosswalk")
        signature = (source, target, kind)
        if pair in seen:
            refuse(
                ("concept_mappings", index), "mapping", "avoid duplicate or conflicting mappings"
            )
        seen[pair] = signature
        if kind == "exactMatch":
            exact_edges.setdefault(source, set()).add(target)
            exact_edges.setdefault(target, set()).add(source)
    # exactMatch is transitive: indirect exact matches must not conceal a conflicting edge.
    components = _components(exact_edges)
    for (source, target, analyst), signature in seen.items():
        if (
            not analyst
            and signature[2] != "exactMatch"
            and source in components
            and components.get(source) == components.get(target)
        ):
            refuse(
                ("concept_mappings",),
                "mapping",
                "keep exact equivalence consistent transitively",
            )


def _components(edges: dict[str, set[str]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for start in edges:
        if start in result:
            continue
        component = len(result)
        pending = [start]
        while pending:
            node = pending.pop()
            if node not in result:
                result[node] = component
                pending.extend(edges[node] - result.keys())
    return result


def _external(data: Snapshot, references: ExternalReferences) -> None:
    for dataset in ("concept_mappings", "entity_tags"):
        for index, row in enumerate(data.get(dataset, [])):
            if row["evidence_id"] not in references.evidence_ids:
                refuse(
                    (dataset, index, "evidence_id"),
                    "endpoint",
                    "resolve evidence in the caller's registry",
                )
    for index, row in enumerate(data.get("entity_tags", [])):
        if row["entity_id"] not in references.entity_ids:
            refuse(
                ("entity_tags", index, "entity_id"),
                "endpoint",
                "resolve the entity in the identity registry",
            )
        start, end = row.get("valid_from"), row.get("valid_to")
        if (
            start
            and end
            and datetime.fromisoformat(start.upper()) >= datetime.fromisoformat(end.upper())
        ):
            refuse(
                ("entity_tags", index), "validity", "keep half-open validity intervals increasing"
            )


def _profiles(data: Snapshot) -> None:
    attributes = indexed(data, "attribute_definitions")
    profiles = indexed(data, "comparison_profiles")
    rubrics = indexed(data, "rubrics")
    fields: dict[str, set[str]] = {}
    for index, row in enumerate(data.get("profile_attributes", [])):
        profile = profiles[row["profile_id"]]
        if attributes[row["attribute_id"]]["entity_class_id"] != profile["entity_class_id"]:
            refuse(
                ("profile_attributes", index),
                "profile",
                "use attributes of the profile's entity class",
            )
        fields.setdefault(row["profile_id"], set()).add(row["attribute_id"])
    for index, row in enumerate(data.get("rubric_criteria", [])):
        profile_id = rubrics[row["rubric_id"]]["profile_id"]
        if row["attribute_id"] not in fields.get(profile_id, set()) or Decimal(row["weight"]) <= 0:
            refuse(
                ("rubric_criteria", index),
                "rubric",
                "weight a profile attribute with a positive decimal",
            )
    conditions: dict[str, set[str]] = {}
    for row in data.get("condition_values", []):
        conditions.setdefault(row["condition_set_id"], set()).add(row["attribute_id"])
    for index, row in enumerate(data.get("comparison_profiles", [])):
        if any(
            attributes[key]["entity_class_id"] != row["entity_class_id"]
            for key in conditions.get(row["condition_set_id"], set())
        ):
            refuse(
                ("comparison_profiles", index),
                "profile",
                "use conditions for the profile's entity class",
            )
