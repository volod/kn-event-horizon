"""A loopback HTTPS server and disposable database for the fixture source."""

import shutil
import ssl
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import token_hex
from threading import Thread
from typing import Any

import pytest
import sqlalchemy as sa
import yaml
from psycopg import sql

import kn.domains.space
from kn.contracts.document import read_document
from kn.db.rebuild import rebuild
from kn.engine import runner
from kn.sources.catalogue import catalogue_table
from tests.integration.harness import ROOT, IntegrationDatabase

SOURCE = "space:fixture-snapshot"
PAYLOAD = ROOT / "tests/fixtures/fixture/snapshot.json"
DOMAIN = ROOT / "domains/fixture"
EVIDENCE = '<testsuite tests="1"><testcase name="test_fixture_profile"/></testsuite>'


@dataclass
class Site:
    body: bytes
    port: int = 0
    requests: int = 0


@pytest.fixture
def site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Site]:
    fixture = Site(PAYLOAD.read_bytes())
    key = tmp_path / "test-tls-key.pem"
    cert = tmp_path / "test-tls-cert.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-noenc",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=127.0.0.1",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
        ],
        check=True,
        capture_output=True,
    )
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    key.unlink()
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            fixture.requests += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(fixture.body)))
            self.end_headers()
            self.wfile.write(fixture.body)

        def log_message(self, format: str, *args: object) -> None:
            return

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        fixture.port = server.server_port
        thread = Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
        thread.start()
        try:
            yield fixture
        finally:
            server.shutdown()
            thread.join()


@dataclass
class ProfileFile:
    path: Path
    config: dict[str, Any]

    def save(self) -> None:
        self.path.write_text(yaml.safe_dump(self.config), encoding="ascii")


@pytest.fixture
def profile(site: Site, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProfileFile:
    monkeypatch.setattr(kn.domains.space, "__path__", [*kn.domains.space.__path__, str(DOMAIN)])
    archive = tmp_path / "archive"
    monkeypatch.setenv("KN_RAW_ARCHIVE_DIR", str(archive))
    monkeypatch.setenv("KN_RAW_INDEX_DIR", "")
    shutil.copy(PAYLOAD, tmp_path)
    (tmp_path / "suite.xml").write_text(EVIDENCE, encoding="ascii")
    config = read_document(DOMAIN / "snapshot.yaml")
    config["access"]["endpoints"] = [f"https://fixture.localhost:{site.port}/snapshot"]
    profile = ProfileFile(tmp_path / "snapshot.yaml", config)
    profile.save()
    return profile


def build_database(engine: sa.Engine, data_dir: Path, state: str = "enabled") -> None:
    with engine.begin() as connection:
        rebuild(connection, data_dir=data_dir)
        connection.execute(
            catalogue_table()
            .insert()
            .values(
                source_id=SOURCE,
                domain="space",
                original_id=None,
                label="Synthetic snapshot",
                priority="P2",
                cadence="on demand",
                access_notes_json="{}",
                access_verification="unverified",
                lifecycle_state=state,
                proposal_workbook="fixture.json",
                proposal_sheet="fixture",
                proposal_sha256="0" * 64,
                proposal_row=1000,
                proposal_values_json="{}",
            )
        )


@pytest.fixture
def engine(
    integration_database: IntegrationDatabase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[sa.Engine]:
    name = f"kn_engine_{token_hex(8)}"
    database = sa.create_engine(
        "postgresql+psycopg://",
        creator=lambda: integration_database.connect(dbname=name),
    )
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(runner, "engine_from_env", lambda: database)
    with integration_database.connect(autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            build_database(database, tmp_path)
            yield database
        finally:
            database.dispose()
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
