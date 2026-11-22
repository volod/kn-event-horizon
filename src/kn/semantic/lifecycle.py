"""Report deprecated and replaced concepts that are still in use; their rows stay valid.

The meta-model keeps retired concepts resolvable, so validation accepts them. Review needs the
opposite view: which children, mappings, tags and caller-owned records still point at them, and
where a replacement chain ends.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from kn.semantic.structure import Snapshot, indexed

RETIRED = frozenset({"deprecated", "replaced"})


def lifecycle_report(
    snapshot: Snapshot, external_uses: Mapping[str, Sequence[str]] | None = None
) -> list[dict[str, Any]]:
    """One finding per retired concept in use, in concept ID order.

    `external_uses` maps concept IDs to the records of other engines, such as claims, that cite
    them. A use is a child concept, a mapping endpoint, an entity tag, a replacement link, or an
    external record.
    """
    terms = indexed(snapshot, "terms")
    concepts = indexed(snapshot, "concepts")
    uses: dict[str, list[dict[str, str]]] = {}

    def use(concept: str | None, kind: str, identifier: str) -> None:
        if concept and terms[concept]["status"] in RETIRED:
            uses.setdefault(concept, []).append({"kind": kind, "id": identifier})

    for row in concepts.values():
        use(row.get("parent_id"), "child", row["id"])
    for row in snapshot.get("concept_mappings", []):
        use(row["source_id"], "mapping", row["id"])
        use(row["target_id"], "mapping", row["id"])
    for row in snapshot.get("entity_tags", []):
        use(row["concept_id"], "entity_tag", row["id"])
    for row in concepts.values():
        use(row.get("replacement_id"), "replacement", row["id"])
    for concept, records in sorted((external_uses or {}).items()):
        if concept in concepts:
            for record in records:
                use(concept, "external", record)
    return [
        {
            "concept_id": concept,
            "status": terms[concept]["status"],
            **_successor(concept, concepts, terms),
            "uses": found,
        }
        for concept, found in sorted(uses.items())
    ]


def _successor(
    concept: str, concepts: dict[str, dict[str, Any]], terms: dict[str, dict[str, Any]]
) -> dict[str, str | None]:
    """The end of the replacement chain, which validation keeps acyclic."""
    current = concept
    while concepts[current].get("replacement_id"):
        current = concepts[current]["replacement_id"]
    if current == concept:
        return {"successor_id": None, "successor_status": None}
    return {"successor_id": current, "successor_status": terms[current]["status"]}
