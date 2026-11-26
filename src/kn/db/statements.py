"""Typed PostgreSQL statements that SQLAlchemy and Alembic have no construct for.

Roles, grants, default privileges, extensions, schema owners, role switches, and constraint timing
are DDL elements.
Each renders through the dialect's identifier preparer, so names are quoted when needed and no
statement is assembled from free text. Keywords come from fixed sets and are checked on creation.
"""

from typing import Any, Literal

from sqlalchemy import Table
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import ExecutableDDLElement
from sqlalchemy.sql.compiler import DDLCompiler

PUBLIC = "PUBLIC"
PRIVILEGES = frozenset(
    {"ALL", "CONNECT", "TEMPORARY", "CREATE", "USAGE", "SELECT", "INSERT", "UPDATE", "DELETE"}
)
ROLE_ATTRIBUTES = frozenset(
    {"NOLOGIN", "NOSUPERUSER", "NOCREATEDB", "NOCREATEROLE", "NOREPLICATION", "NOBYPASSRLS"}
    | {"INHERIT"}
)
type ObjectKind = Literal[
    "DATABASE", "SCHEMA", "ALL TABLES IN SCHEMA", "ALL SEQUENCES IN SCHEMA", "TABLES", "SEQUENCES"
]
DEFAULT_KINDS = frozenset({"TABLES", "SEQUENCES"})


class _Statement(ExecutableDDLElement):
    inherit_cache = False


class CreateExtension(_Statement):
    def __init__(self, name: str, schema: str) -> None:
        self.name, self.schema = name, schema


class UpdateExtension(_Statement):
    def __init__(self, name: str) -> None:
        self.name = name


class CreateRole(_Statement):
    def __init__(self, name: str) -> None:
        self.name = name


class AlterRole(_Statement):
    def __init__(self, name: str, attributes: tuple[str, ...]) -> None:
        if not attributes or not set(attributes) <= ROLE_ATTRIBUTES:
            raise ValueError("use known role attributes")
        self.name, self.attributes = name, attributes


class AlterSchemaOwner(_Statement):
    def __init__(self, schema: str, owner: str) -> None:
        self.schema, self.owner = schema, owner


class Privileges(_Statement):
    """GRANT or REVOKE fixed privileges on one object, or as an owner's default privileges."""

    def __init__(
        self,
        action: Literal["GRANT", "REVOKE"],
        privileges: tuple[str, ...],
        kind: ObjectKind,
        target: str | None,
        grantees: tuple[str, ...],
        *,
        defaults: tuple[str, str] | None = None,
    ) -> None:
        if not privileges or not set(privileges) <= PRIVILEGES or not grantees:
            raise ValueError("use known privileges and at least one grantee")
        if (kind in DEFAULT_KINDS) != (defaults is not None) or (target is None) != bool(defaults):
            raise ValueError("default privileges name an owner and schema, not a target")
        self.action, self.privileges, self.kind = action, privileges, kind
        self.object_name, self.grantees, self.defaults = target, grantees, defaults


class SetRole(_Statement):
    """SET LOCAL ROLE: the role ends with the transaction, even when a caller forgets RESET."""

    def __init__(self, role: str) -> None:
        self.role = role


class ResetRole(_Statement):
    pass


class SetConstraints(_Statement):
    """Change only explicitly named, schema-qualified constraints; never affect unrelated callers."""

    def __init__(self, schema: str, names: tuple[str, ...], *, deferred: bool) -> None:
        if not schema or not names or any(not name for name in names):
            raise ValueError("name at least one constraint in a schema")
        self.schema, self.names, self.deferred = schema, names, deferred


class LockTableForWrite(_Statement):
    """Exclude other writers and allow reads until the transaction ends."""

    def __init__(self, table: Table) -> None:
        self.table = table


@compiles(LockTableForWrite)
def _lock_table(element: LockTableForWrite, compiler: DDLCompiler, **kw: Any) -> str:
    table = compiler.preparer.format_table(element.table)
    return f"LOCK TABLE {table} IN SHARE ROW EXCLUSIVE MODE"


@compiles(CreateExtension)
def _create_extension(element: CreateExtension, compiler: DDLCompiler, **kw: Any) -> str:
    quote = compiler.preparer.quote
    return (
        f"CREATE EXTENSION IF NOT EXISTS {quote(element.name)} WITH SCHEMA {quote(element.schema)}"
    )


@compiles(UpdateExtension)
def _update_extension(element: UpdateExtension, compiler: DDLCompiler, **kw: Any) -> str:
    return f"ALTER EXTENSION {compiler.preparer.quote(element.name)} UPDATE"


@compiles(CreateRole)
def _create_role(element: CreateRole, compiler: DDLCompiler, **kw: Any) -> str:
    return f"CREATE ROLE {compiler.preparer.quote(element.name)}"


@compiles(AlterRole)
def _alter_role(element: AlterRole, compiler: DDLCompiler, **kw: Any) -> str:
    return f"ALTER ROLE {compiler.preparer.quote(element.name)} {' '.join(element.attributes)}"


@compiles(AlterSchemaOwner)
def _alter_schema_owner(element: AlterSchemaOwner, compiler: DDLCompiler, **kw: Any) -> str:
    quote = compiler.preparer.quote
    return f"ALTER SCHEMA {quote(element.schema)} OWNER TO {quote(element.owner)}"


@compiles(Privileges)
def _privileges(element: Privileges, compiler: DDLCompiler, **kw: Any) -> str:
    quote = compiler.preparer.quote
    prefix = ""
    if element.defaults:
        owner, schema = element.defaults
        prefix = f"ALTER DEFAULT PRIVILEGES FOR ROLE {quote(owner)} IN SCHEMA {quote(schema)} "
    target = (
        element.kind
        if element.object_name is None
        else f"{element.kind} {quote(element.object_name)}"
    )
    direction = "TO" if element.action == "GRANT" else "FROM"
    grantees = ", ".join(name if name == PUBLIC else quote(name) for name in element.grantees)
    privileges = ", ".join(element.privileges)
    return f"{prefix}{element.action} {privileges} ON {target} {direction} {grantees}"


@compiles(SetRole)
def _set_role(element: SetRole, compiler: DDLCompiler, **kw: Any) -> str:
    return f"SET LOCAL ROLE {compiler.preparer.quote(element.role)}"


@compiles(ResetRole)
def _reset_role(element: ResetRole, compiler: DDLCompiler, **kw: Any) -> str:
    return "RESET ROLE"


@compiles(SetConstraints)
def _set_constraints(element: SetConstraints, compiler: DDLCompiler, **kw: Any) -> str:
    quote = compiler.preparer.quote
    names = ", ".join(quote(element.schema) + "." + quote(name) for name in element.names)
    timing = "DEFERRED" if element.deferred else "IMMEDIATE"
    return f"SET CONSTRAINTS {names} {timing}"
