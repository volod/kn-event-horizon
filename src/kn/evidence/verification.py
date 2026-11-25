"""Human verification targets for evidence rows, using the shared version-bound protocol.

The target version is the content digest of the row's declared coverage, so a changed claim
is a different target and never inherits a decision. Imported source verification labels are
ordinary content; only a trusted human decision can produce a stamp.
"""

from typing import Any

from kn.evidence.records import Record
from kn.evidence.store import evidence_contract, evidence_tables
from kn.review.model import Purpose, Target
from kn.review.targets import content_version, declared_coverage


def target(record: Record, purpose: Purpose = "factual") -> Target:
    """The record-scope target of a row as the contract resolver will find it stored."""
    contract = evidence_contract()
    coverage = next(item for item in declared_coverage(contract) if item.dataset == record.TABLE)
    table = evidence_tables()[record.TABLE]
    row = record.row()
    names = {column.info["field_id"]: column.name for column in table.columns}
    key: list[dict[str, Any]] = [
        {
            "field_id": column.info["field_id"],
            "kind": column.info["logical_type"],
            "value": row[column.name],
        }
        for column in table.primary_key.columns
    ]
    content = {field: row[names[field]] for field in coverage.record_fields}
    return Target.model_validate(
        {
            "contract_id": contract.contract_id,
            "dataset": record.TABLE,
            "key": key,
            "scope": "record",
            "version": content_version(content),
            "purpose": purpose,
        }
    )
