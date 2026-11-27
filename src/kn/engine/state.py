"""Registered ingestion tables used by loaders and health readers."""

from functools import cache

import sqlalchemy as sa

from kn.contracts.loader import load_contract
from kn.contracts.model import Contract
from kn.contracts.schemas import RESOURCES
from kn.contracts.sqlalchemy import metadata

CONTRACT_ID = "kn.system.ingestion_state"
ATTEMPTS = "source_run_attempts"
ERRORS = "source_run_errors"
BATCHES = "source_loaded_batches"
CHECKPOINTS = "source_checkpoints"


@cache
def ingestion_contract() -> Contract:
    return load_contract(RESOURCES / "system" / "ingestion-state" / "1.0.0.json")


@cache
def _state_metadata() -> sa.MetaData:
    return metadata(ingestion_contract())


def state_table(name: str) -> sa.Table:
    schema = ingestion_contract().schema
    return _state_metadata().tables[f"{schema}.{name}"]
