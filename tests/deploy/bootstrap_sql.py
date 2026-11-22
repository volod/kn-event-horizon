"""The database bootstrap and role probe files as test inputs."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTGRES = ROOT / "deploy" / "postgres"
BOOTSTRAP = POSTGRES / "initdb" / "10-kn-bootstrap.sql"
VERIFY = POSTGRES / "verify-roles.sql"
# psql meta-commands such as \set start with a backslash; a server cannot run them.
PSQL_META_COMMAND = re.compile(r"^\\.*$", re.M)


def sql_text_array(path: Path, variable: str) -> list[str]:
    """The elements of a `variable CONSTANT text[] := ARRAY[...]` declaration, in file order."""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"{variable}\s+CONSTANT\s+text\[\]\s*:=\s*ARRAY\[(.*?)\]", text, re.S)
    assert match, f"{path.name}: no {variable} array"
    return re.findall(r"'([a-z_]+)'", match.group(1))


def bootstrap_schemas() -> list[str]:
    """The KN schemas that the bootstrap creates."""
    return sql_text_array(BOOTSTRAP, "kn_schemas")


def bootstrap_script() -> str:
    """The bootstrap as SQL that a client library can send, without its psql meta-commands."""
    return PSQL_META_COMMAND.sub("", BOOTSTRAP.read_text(encoding="utf-8"))
