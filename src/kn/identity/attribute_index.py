"""Indexes for historical blocking values, independent of the current owner."""

from dataclasses import dataclass, field

from kn.identity.matching.normalizers import normalize
from kn.identity.model import Attribute


@dataclass
class AttributeIndex:
    # Old journals or profiles can use different normalizers for the same raw value.
    by_field: dict[str, dict[str, Attribute]] = field(default_factory=dict)
    normalized: dict[str, dict[str, dict[str, set[str]]]] = field(default_factory=dict)

    def add(self, key: str, attribute: Attribute) -> None:
        self.by_field.setdefault(attribute.field_id, {})[key] = attribute
        for normalizer, values in self.normalized.get(attribute.field_id, {}).items():
            _add(values, normalizer, key, attribute)

    def lookup(self, field_id: str, normalizer: str, value: str) -> set[str]:
        field_indexes = self.normalized.setdefault(field_id, {})
        if normalizer not in field_indexes:
            values: dict[str, set[str]] = {}
            for key, attribute in self.by_field.get(field_id, {}).items():
                _add(values, normalizer, key, attribute)
            field_indexes[normalizer] = values
        return field_indexes[normalizer].get(value, set())


def _add(values: dict[str, set[str]], normalizer: str, key: str, attribute: Attribute) -> None:
    normalized = normalize(normalizer, attribute.original)
    if normalized is not None:
        values.setdefault(normalized, set()).add(key)
