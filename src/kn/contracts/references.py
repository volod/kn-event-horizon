"""Resolve compile-time symbols from a bounded, local reference catalog."""

from typing import Any

from kn.contracts.diagnostics import ContractError, Location
from kn.i18n.catalog import load_catalog

# Reference kinds are deliberately separate, so a policy cannot satisfy a class reference.
SYMBOLS = {
    "entityClass",
    "relation",
    "matchProfile",
    "normalizer",
    "comparator",
    "mapping",
    "unit",
    "quantityType",
    "conversionRule",
    "comparisonProfile",
    "licensePolicy",
    "vocabulary",
    "dataset",
}
SINGLE = {
    "entityClass": "entityClass",
    "comparisonProfile": "comparisonProfile",
    "enumRef": "vocabulary",
}
MEMBERS = {
    "relation": {"type": "relation", "sourceClass": "entityClass", "targetClass": "entityClass"},
    "units": {
        "originalUnit": "unit",
        "normalizedUnit": "unit",
        "quantityType": "quantityType",
        "conversionRule": "conversionRule",
    },
    "licensePolicy": {"policyRef": "licensePolicy"},
    "lineageRefs": {"dataset": "dataset", "mapping": "mapping"},
}


def validate_catalog(catalog: dict[str, Any]) -> None:
    """Definitions are objects keyed by ID; payloads remain owned by their domain."""
    if set(catalog) - SYMBOLS:
        raise ContractError((), "references", "use registered reference kinds")
    for kind, entries in catalog.items():
        if not isinstance(entries, dict) or any(
            not key.strip() or not isinstance(value, dict) for key, value in entries.items()
        ):
            raise ContractError((kind,), "references", "map nonempty symbol IDs to objects")


def resolve_extensions(data: dict[str, Any], catalog: dict[str, Any]) -> None:
    """Validate external symbols and field references before interpreting extensions."""
    validate_catalog(catalog)
    global_fields = {
        item["value"]
        for table in data["schema"]
        for field in table["properties"]
        for item in field.get("customProperties", [])
        if item["property"] == "kn.fieldId"
    }
    _node(data, (), global_fields, catalog)
    for index, table in enumerate(data["schema"]):
        fields = {field["name"] for field in table["properties"]} | {
            item["value"]
            for field in table["properties"]
            for item in field.get("customProperties", [])
            if item["property"] == "kn.fieldId"
        }
        path: Location = ("schema", index)
        _node(table, path, fields, catalog)
        for number, field in enumerate(table["properties"]):
            _node(field, (*path, "properties", number), fields, catalog)


def _symbol(kind: str, value: str, catalog: dict[str, Any], path: Location) -> None:
    if value not in catalog.get(kind, {}):
        raise ContractError(path, "reference", f"define the referenced {kind} in --references")


def _members(
    value: dict[str, Any], kinds: dict[str, str], catalog: dict[str, Any], path: Location
) -> None:
    for member, kind in kinds.items():
        _symbol(kind, value[member], catalog, (*path, member))


def _field(value: str, fields: set[str], path: Location) -> None:
    if value not in fields:
        raise ContractError(
            path, "reference", "reference an existing field name or stable field ID"
        )


def _node(node: dict[str, Any], path: Location, fields: set[str], catalog: dict[str, Any]) -> None:
    for index, item in enumerate(node.get("customProperties", [])):
        name = item["property"].removeprefix("kn.")
        value = item["value"]
        location = (*path, "customProperties", index, "value")
        if name in SINGLE:
            _symbol(SINGLE[name], value, catalog, location)
        elif name in MEMBERS:
            for entry in value if isinstance(value, list) else [value]:
                _members(entry, MEMBERS[name], catalog, location)
        elif name == "vocabularyRefs":
            for entry in value:
                _symbol("vocabulary", entry, catalog, location)
        _special(name, value, fields, catalog, location)


def _special(
    name: str, value: Any, fields: set[str], catalog: dict[str, Any], path: Location
) -> None:
    if name == "temporalProfile":
        for key, ref in value.items():
            if key not in {"asOf", "nullSemantics"}:
                _field(ref, fields, (*path, key))
    elif name == "evidence":
        for ref in value["referenceFields"]:
            _field(ref, fields, path)
    elif name == "identity":
        _identity(value, fields, catalog, path)
    elif name == "interchange":
        for ref in value.get("counterpartMappingRefs", []):
            _symbol("mapping", ref, catalog, path)
    else:
        _labels_and_relation(name, value, catalog, path)


def _labels_and_relation(name: str, value: Any, catalog: dict[str, Any], path: Location) -> None:
    if name == "i18nKey":
        if any(value not in load_catalog(locale) for locale in ("en", "uk")):
            raise ContractError(path, "reference", "use a key in both interface catalogs")
    elif name == "relation":
        definition = catalog["relation"][value["type"]]
        if any(definition.get(key) != value[key] for key in ("sourceClass", "targetClass")):
            raise ContractError(
                path, "reference", "match the relation definition's endpoint classes"
            )


def _identity(
    value: dict[str, Any], fields: set[str], catalog: dict[str, Any], path: Location
) -> None:
    _symbol("matchProfile", value["matchProfile"], catalog, path)
    refs = [*value["sourceRecordKey"]]
    refs.extend(key for entry in value["externalKeys"] for key in entry["fields"])
    if "sourceVersionField" in value:
        refs.append(value["sourceVersionField"])
    for entry in value["attributes"]:
        refs.append(entry["fieldId"])
        _members(entry, {"normalizer": "normalizer", "comparator": "comparator"}, catalog, path)
    for ref in refs:
        _field(ref, fields, path)
