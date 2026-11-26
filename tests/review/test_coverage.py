"""Every deployed datum has explicit, versioned verification coverage."""

from kn.contracts.registry import registered_contracts
from kn.review.targets import ContractResolver


def test_all_registered_fields_are_addressable() -> None:
    contracts = registered_contracts()
    resolver = ContractResolver.registered(contracts)
    baseline = {
        "kn.system.governance": 1,
        "kn.space.satcom": 31,
        "kn.core.semantic": 18,
    }
    for contract in contracts:
        if contract.contract_id in baseline:
            assert len(contract.tables) >= baseline[contract.contract_id]
        for table in contract.tables:
            dataset = resolver.dataset(contract.contract_id, table.name)
            assert set(dataset.coverage.field_context) == {field.field_id for field in table.fields}
