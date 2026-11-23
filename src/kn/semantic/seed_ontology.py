"""Explicit class aliases and endpoint-pair normalization for the three proposal ontologies."""

from itertools import product

from kn.semantic.proposals import Proposal
from kn.semantic.seed_model import SeedBuilder, native_code, proposal_source, required_text

CLASS_SHEETS = {
    "space": "01_entity_ontology",
    "microelectronics": "01_entity_ontology",
    "gdelt": "01_ontology",
}

# Local classes needed by the SATCOM pilot and the space proposal's generic endpoints.
SPACE_EXTENSIONS = {
    "Asset": "A physical or operational asset; no ownership or operation is implied.",
    "System": "A system comprising related assets or products.",
    "Network": "A communications network, separate from its spacecraft and stations.",
    "Material": "An industrial material, distinct from a finished component.",
    "Software": "A versioned software product.",
    "SpacecraftModel": "A spacecraft design/model, distinct from an individual spacecraft.",
    "LaunchConfiguration": "A launch vehicle configuration, distinct from a launch event.",
    "EvidenceClaim": "A source-grounded assertion; not automatically a verified fact.",
    "FinancialObservation": "A dated financial observation with currency and source context.",
    "DeploymentObservation": "A dated deployment observation, distinct from a spacecraft model.",
    "Opportunity": "A prospective opportunity; not an award or contract.",
    "Compatibility": "A scoped compatibility assertion requiring evidence.",
}
SPACE_ALIASES = {
    "Component": "Component_Subsystem",
    "Subsystem": "Component_Subsystem",
    "Payload": "Payload_Instrument",
    "Constellation": "Constellation_Fleet",
    "Fleet": "Constellation_Fleet",
    "Contract": "Contract_Award",
    "Dataset": "Dataset_Data_Product",
    "Filing": "Licence_Regulatory_Filing",
    "Project": "R_D_Project",
    "Agency": "Organization",
    "Investor": "Organization",
    "Regulator": "Organization",
    "Administration": "Organization",
    "Registry": "Organization",
    "State": "Organization",
}
INVERSES = {
    "operates": "operated_by",
    "manufactures": "manufactured_by",
    "owns": "owned_by",
    "provides_service": "provided_by",
    "contains_spacecraft": "member_of_constellation",
    "carries_payload": "carried_by",
    "funds": "funded_by",
    "licenses": "licensed_by",
    "has_mpn": "variant_of",
    "contains_model": "member_of_family",
    "partners_with": "partners_with",
    "co_occurs_with": "co_occurs_with",
}
# Canonical direction and the row's inverse spelling are both retained.
REVERSED = {
    "member_of_constellation": "contains_spacecraft",
    "operated_by": "operates",
    "variant_of": "has_mpn",
}
CARDINALITIES = {
    "1 : 0..1": "one_to_one",
    "1 : N": "one_to_many",
    "N : 1": "many_to_one",
    "N : 0..1": "many_to_one",
    "N : N": "many_to_many",
}


def import_classes(builder: SeedBuilder, rows: list[Proposal]) -> None:
    classes = [
        row
        for row in rows
        if row.sheet == CLASS_SHEETS[row.domain] and row.workbook == "ontology_and_tags_v1"
    ]
    for row in classes:
        values = row.values
        label = required_text(values, "class", "entity_class")
        code = values.get("id", native_code(label))
        definition = required_text(values, "definition_purpose", "definition", "interpretation")
        builder.term(
            "ontology",
            code,
            "entity_class",
            label,
            definition,
            row,
            origin="native" if values.get("origin") == "NATIVE" else "kb_extension",
        )
    if builder.domain == "space":
        for code, definition in SPACE_EXTENSIONS.items():
            builder.term(
                "kb_extension",
                code,
                "entity_class",
                code,
                "kb_extension: " + definition,
                classes[0],
                origin="kb_extension",
            )


def class_ids(builder: SeedBuilder) -> dict[str, str]:
    result = {
        row["code"]: row["id"] for row in builder.snapshot["terms"] if row["kind"] == "entity_class"
    }
    if builder.domain == "space":
        result.update({alias: result[code] for alias, code in SPACE_ALIASES.items()})
    return result


def endpoints(value: str, classes: dict[str, str]) -> list[str] | None:
    """Resolve a named combined class before treating a slash as a union."""
    code = native_code(value)
    if code in classes:
        return [classes[code]]
    parts = [native_code(part.strip()) for part in value.split("/")]
    if any(part not in classes for part in parts):
        return None
    return sorted({classes[part] for part in parts})


def import_relation(builder: SeedBuilder, row: Proposal) -> tuple[list[str], str]:
    values = row.values
    classes = class_ids(builder)
    sources = endpoints(required_text(values, "allowed_from", "from"), classes)
    targets = endpoints(required_text(values, "allowed_to", "to"), classes)
    if not sources or not targets:
        return (
            [],
            "Relation endpoint is not an entity class; map the class or concept-tag semantics first.",
        )
    name = values["relation"]
    cardinality = values.get("cardinality", "N : N")
    cardinality = next(
        (mapped for text, mapped in CARDINALITIES.items() if cardinality.startswith(text)), None
    )
    if not cardinality:
        return [], "Cardinality needs explicit mapping."
    canonical = REVERSED.get(name, name)
    if canonical != name:
        sources, targets = targets, sources
        cardinality = {"one_to_many": "many_to_one", "many_to_one": "one_to_many"}.get(
            cardinality, cardinality
        )
    inverse = INVERSES.get(canonical, "inverse of " + canonical)
    result: list[str] = []
    existing = {term["id"] for term in builder.snapshot["terms"]}
    for source, target in product(sources, targets):
        code = canonical + "." + source.rsplit(".", 1)[1] + "." + target.rsplit(".", 1)[1]
        identifier = builder.domain + ".relations." + code
        if identifier in existing:
            builder.lineage[identifier].append(proposal_source(row, "kb_normalized"))
            result.append(identifier)
            continue
        result.append(
            builder.term(
                "relations",
                code,
                "relation_type",
                f"{canonical} ({source} -> {target})",
                values.get("meaning", values.get("derivation", canonical)),
                row,
                origin="kb_normalized",
                inverse=f"{inverse} ({target} -> {source})",
                source_class_id=source,
                target_class_id=target,
                cardinality=cardinality,
                minimum_evidence="extracted"
                if values.get("origin") == "NATIVE_MAPPING"
                else "primary",
                guarded_errors=values.get(
                    "common_error_to_avoid",
                    values.get("constraint", values.get("minimum_evidence")),
                ),
            )
        )
    reason = "Normalized direction, explicit endpoint pairs, and inverse labels; unspecified cardinality is unconstrained many-to-many."
    return result, reason
