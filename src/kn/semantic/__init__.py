"""The semantic meta-model: validate complete snapshots before any reviewed content load."""

from kn.semantic.policies import ExternalReferences, validate_policies
from kn.semantic.structure import Snapshot, validate_rows
from kn.semantic.terms import validate_terms

__all__ = ["ExternalReferences", "Snapshot", "validate_model"]


def validate_model(data: Snapshot, references: ExternalReferences | None = None) -> None:
    """Reject invalid structure without mutation, database access, or content import.

    Omitted datasets are empty. Values use the contract's JSON wire encoding (including exact
    decimal and aware timestamp strings). External entity and evidence IDs are explicitly supplied
    by their owning engines; an empty registry permits no external references.
    """
    validate_rows(data)
    validate_terms(data)
    validate_policies(data, references or ExternalReferences())
