"""Interpret linted field and node extensions within the compiler profile."""

from typing import Any, cast

from kn.contracts.diagnostics import ContractError, Location
from kn.contracts.model import LOGICAL_TYPES, Field, LogicalType, Reference, canonical

SEMANTIC_EXTENSIONS = {
    "humanVerification",
    "entityClass",
    "relation",
    "identity",
    "updatePolicy",
    "interchange",
    "units",
    "comparisonProfile",
    "temporalProfile",
    "spatialProfile",
    "evidence",
    "licensePolicy",
    "enumRef",
    "vocabularyRefs",
    "index",
    "partition",
    "presence",
    "i18nKey",
    "lineageRefs",
}
FIELD_EXTENSIONS = {"fieldId", "foreignKey", "enum", "partialDate", "precision", "scale"}
DEFAULT_PRECISION = 38
DEFAULT_SCALE = 18


def extensions_of(node: dict[str, Any], allowed: set[str], path: Location) -> dict[str, Any]:
    """Map KN extensions by short name; lint already checked registered names and scopes."""
    result: dict[str, Any] = {}
    for index, item in enumerate(node.get("customProperties", [])):
        name = item["property"]
        short = name.removeprefix("kn.")
        if name != f"kn.{short}" or short not in allowed | SEMANTIC_EXTENSIONS or short in result:
            raise ContractError(
                (*path, "customProperties", index, "property"),
                "profile",
                "use extensions that the compiler supports at this location, once each",
            )
        result[short] = item["value"]
    return result


def model_field(node: dict[str, Any], catalog: dict[str, Any], path: Location) -> Field:
    meta = extensions_of(node, FIELD_EXTENSIONS, path)
    if "fieldId" not in meta:
        raise ContractError(path, "fieldId", "add a kn.fieldId extension")
    logical = node["logicalType"]
    if logical not in LOGICAL_TYPES:
        raise ContractError(
            (*path, "logicalType"), "profile", "use one of: " + ", ".join(LOGICAL_TYPES)
        )
    _check_scalar_extensions(meta, logical, path)
    ref = meta.get("foreignKey")
    return Field(
        node["name"],
        meta["fieldId"],
        cast(LogicalType, logical),
        node.get("required", False),
        node.get("primaryKey", False),
        node.get("description", ""),
        Reference(ref["table"], tuple(ref["fields"]), tuple(ref["targetFields"])) if ref else None,
        _enum(meta, catalog, logical, path),
        meta.get("partialDate", False),
        meta.get("precision", DEFAULT_PRECISION),
        meta.get("scale", DEFAULT_SCALE),
        canonical(meta),
    )


def _check_scalar_extensions(meta: dict[str, Any], logical: str, path: Location) -> None:
    if ("enum" in meta or "partialDate" in meta) and logical != "string":
        raise ContractError(path, "profile", "use kn.enum and kn.partialDate on string fields")
    if {"precision", "scale"} & set(meta) and logical != "number":
        raise ContractError(path, "profile", "use kn.precision and kn.scale on number fields")
    if meta.get("scale", DEFAULT_SCALE) > meta.get("precision", DEFAULT_PRECISION):
        raise ContractError(
            path,
            "decimal",
            f"set kn.scale at most kn.precision; the defaults are "
            f"{DEFAULT_PRECISION} and {DEFAULT_SCALE}",
        )


def _enum(
    meta: dict[str, Any], catalog: dict[str, Any], logical: str, path: Location
) -> tuple[str, ...]:
    if "enumRef" not in meta:
        return tuple(meta.get("enum", []))
    vocabulary = catalog["vocabulary"][meta["enumRef"]].get("values")
    if (
        not isinstance(vocabulary, list)
        or not vocabulary
        or any(not isinstance(value, str) for value in vocabulary)
    ):
        raise ContractError(
            path, "enumRef", "define a nonempty string values array for the vocabulary"
        )
    if len(vocabulary) != len(set(vocabulary)) or ("enum" in meta and meta["enum"] != vocabulary):
        raise ContractError(path, "enumRef", "use unique vocabulary values consistent with kn.enum")
    if logical != "string":
        raise ContractError(path, "enumRef", "enumerated vocabularies require string fields")
    return tuple(vocabulary)
