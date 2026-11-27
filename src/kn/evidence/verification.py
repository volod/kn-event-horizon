"""Human verification targets for evidence rows through the contract resolver."""

from functools import cache

from kn.evidence.records import Record
from kn.evidence.store import evidence_contract
from kn.review.model import Purpose, Target
from kn.review.targets import ContractResolver


@cache
def _resolver() -> ContractResolver:
    return ContractResolver.registered((evidence_contract(),))


def target(record: Record, purpose: Purpose = "factual") -> Target:
    """The record-scope target of a row as the contract resolver will find it stored."""
    dataset = _resolver().dataset(evidence_contract().contract_id, record.TABLE)
    return dataset.target(record.row(), purpose)
