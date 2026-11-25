"""PostgreSQL object names derived from contract identifiers, one rule for every artifact."""

import hashlib
import re

from kn.contracts.model import Field, Reference, Table

# Tables, fields, storage schemas, and index names. The limit leaves room for the "pk_" prefix
# within the PostgreSQL limit, so a primary key name is never shortened.
MAX_IDENTIFIER = 48
IDENTIFIER_BODY = rf"[a-z][a-z0-9_]{{0,{MAX_IDENTIFIER - 1}}}"
IDENTIFIER = re.compile(rf"^{IDENTIFIER_BODY}$")
# NAMEDATALEN - 1. PostgreSQL truncates longer names silently, so no derived name exceeds it.
POSTGRES_NAME_LIMIT = 63
NAME_HASH_LENGTH = 8


def postgres_name(*parts: str) -> str:
    """Join name parts; a name over the limit keeps its prefix and gains a stable hash suffix."""
    name = "_".join(parts)
    if len(name) <= POSTGRES_NAME_LIMIT:
        return name
    digest = hashlib.sha256(name.encode("ascii")).hexdigest()[:NAME_HASH_LENGTH]
    return f"{name[: POSTGRES_NAME_LIMIT - NAME_HASH_LENGTH - 1]}_{digest}"


def primary_key_name(table: Table) -> str:
    return postgres_name("pk", table.name)


def foreign_key_name(table: Table, reference: Reference) -> str:
    """Every referencing column is in the name, so references that share a prefix differ."""
    return postgres_name("fk", table.name, *reference.fields)


def check_name(table: Table, field: Field, kind: str) -> str:
    return postgres_name("ck", table.name, field.name, kind)


def presence_name(table: Table, rule: str) -> str:
    """The suffix never equals a field check kind, so table and field checks cannot coincide."""
    return postgres_name("ck", table.name, rule, "presence")


def table_references(table: Table) -> tuple[Reference, ...]:
    """Each composite reference once, in field order, however many of its fields declare it."""
    return tuple(dict.fromkeys(field.reference for field in table.fields if field.reference))
