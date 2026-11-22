"""Build deterministic semantic snapshots while retaining every contributing proposal row."""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from kn.semantic.proposals import Proposal
from kn.semantic.structure import Snapshot
from kn.semantic.terms import DATASETS, UNLABELED_KINDS


def native_code(label: str) -> str:
    """Stable textual identifiers for proposal labels without native codes; never row numbers."""
    code = re.sub(r"[^A-Za-z0-9_.:-]+", "_", label).strip("_")
    if not code:
        raise ValueError("label cannot supply a native identifier")
    return code


def required_text(values: dict[str, Any], *keys: str) -> str:
    """Select a nonempty textual proposal field without coercing missing data."""
    for key in keys:
        value = values.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError("required proposal text is missing")


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("ascii")


@dataclass
class SeedBuilder:
    domain: str
    snapshot: Snapshot = field(default_factory=dict)
    lineage: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def add(self, dataset: str, row: dict[str, Any]) -> None:
        rows = self.snapshot.setdefault(dataset, [])
        if row not in rows:
            rows.append(row)

    def namespace(self, code: str) -> str:
        identifier = self.domain + "." + code
        self.add(
            "namespaces",
            {
                "id": identifier,
                "domain": self.domain,
                "code": code,
                "definition": "Proposal-derived seed namespace; terminology review pending.",
            },
        )
        for locale in ("en", "uk"):
            self.add(
                "namespace_labels",
                {"namespace_id": identifier, "locale": locale, "label": identifier},
            )
        return identifier

    def term(
        self,
        namespace: str,
        code: str,
        kind: str,
        label: str,
        definition: str,
        proposal: Proposal,
        *,
        origin: str,
        inverse: str | None = None,
        **fields: Any,
    ) -> str:
        identifier = self.namespace(namespace) + "." + code
        self.add(
            "terms",
            {
                "id": identifier,
                "namespace_id": self.domain + "." + namespace,
                "code": code,
                "kind": kind,
                "status": "draft",
                "definition": definition,
            },
        )
        if kind not in UNLABELED_KINDS:
            for locale in ("en", "uk"):
                row = {"term_id": identifier, "locale": locale, "label": label}
                if inverse:
                    row["inverse_label"] = inverse
                self.add("labels", row)
        if kind == "concept_scheme":
            fields["origin"] = origin
        self.add(DATASETS[kind], {"id": identifier, **fields})
        self.lineage.setdefault(identifier, []).append(
            {
                **proposal.provenance,
                "origin": origin,
                "label_policy": "source spelling; uk review pending",
            }
        )
        return identifier

    def scheme(self, namespace: str, proposal: Proposal, origin: str) -> str:
        identifier = self.domain + "." + namespace + ".scheme"
        if identifier in self.lineage:
            return identifier
        return self.term(
            namespace,
            "scheme",
            "concept_scheme",
            namespace,
            "Proposal-derived vocabulary subset; see scheme verification state and review scope.",
            proposal,
            origin=origin,
            verification_state="unverified",
            verification_reason="Official publication comparison is pending.",
        )

    def concept(
        self,
        namespace: str,
        code: str,
        label: str,
        proposal: Proposal,
        *,
        origin: str,
        parent: str | None = None,
        scheme_origin: str | None = None,
    ) -> str:
        scheme = self.scheme(namespace, proposal, scheme_origin or origin)
        # Original row values (including edition, URLs, and mappings) remain in reconciliation.
        return self.term(
            namespace,
            code,
            "concept",
            label,
            encoded(proposal.values).decode().strip(),
            proposal,
            origin=origin,
            scheme_id=scheme,
            parent_id=self.domain + "." + namespace + "." + parent if parent else None,
        )

    def document(self) -> dict[str, Any]:
        snapshot = {
            name: sorted(rows, key=lambda row: encoded(row))
            for name, rows in sorted(self.snapshot.items())
        }
        return {
            "format": "kn.semantic.reviewed-seeds.v1",
            "domain": self.domain,
            "snapshot": snapshot,
            "provenance": self.lineage,
        }
