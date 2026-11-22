"""Password-file connections without secrets in URLs, logs, or exceptions."""

import os
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Engine, make_url


def engine_from_env() -> Engine:
    value = os.environ.get("KN_DATABASE_URL")
    if not value:
        raise ValueError("KN_DATABASE_URL is required; use the Make database targets")
    url = make_url(value)
    if url.get_backend_name() != "postgresql":
        raise ValueError("deployment requires PostgreSQL")
    password_file = os.environ.get("KN_DATABASE_PASSWORD_FILE")
    password = Path(password_file).read_text().rstrip("\r\n") if password_file else url.password
    if not password:
        raise ValueError("a non-empty database password or password file is required")
    return sa.create_engine(
        url.set(drivername="postgresql+psycopg", password=password),
        hide_parameters=True,
        connect_args={"connect_timeout": 10},
    )
