"""Static checks of the Compose stack against the version manifest and the runtime rules."""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.deploy.bootstrap_sql import BOOTSTRAP, VERIFY, sql_text_array

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
FLOATING_TAGS = {"latest", "stable", "edge"}
LOOPBACK = "127.0.0.1"
LOOPBACK_NETWORK = "loopback"
DATABASE_PORT = {
    "target": 5432,
    "host_ip": LOOPBACK,
    "published": "${KN_POSTGRES_HOST_PORT:?run through make db-up}",
    "protocol": "tcp",
}
BRIDGE = "com.docker.network.bridge."
CORE_SCHEMAS = {
    "system",
    "semantic",
    "identity",
    "evidence",
    "supply",
    "interchange",
    "analytics",
}


def _load(name: str) -> dict[str, Any]:
    data = yaml.safe_load((DEPLOY / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict), name
    return data


COMPOSE = _load("compose.yaml")
MANIFEST = _load("versions.yaml")
SERVICES: dict[str, dict[str, Any]] = COMPOSE["services"]


def test_every_manifest_image_is_the_pinned_image_of_its_service() -> None:
    images = MANIFEST["images"]
    assert images
    for name, entry in images.items():
        assert DIGEST.match(entry["digest"]), name
        assert entry["tag"] not in FLOATING_TAGS, name
        expected = f"{entry['image']}:{entry['tag']}@{entry['digest']}"
        assert SERVICES[entry["service"]]["image"] == expected, name


def test_every_service_image_comes_from_the_manifest() -> None:
    pinned = {entry["service"] for entry in MANIFEST["images"].values()}
    assert set(SERVICES) == pinned
    for name, service in SERVICES.items():
        reference, _, digest = service["image"].partition("@")
        assert DIGEST.match(digest), name
        assert reference.rsplit(":", 1)[-1] not in FLOATING_TAGS, name


def test_only_the_database_publishes_a_port_and_only_on_loopback() -> None:
    for name, service in SERVICES.items():
        assert "network_mode" not in service, name
        assert service["networks"], name
    published = {name: service["ports"] for name, service in SERVICES.items() if "ports" in service}
    assert published == {"postgres": [DATABASE_PORT]}


def test_only_publishing_services_join_the_loopback_network() -> None:
    publishing = {name for name, service in SERVICES.items() if "ports" in service}
    joined = {name for name, service in SERVICES.items() if LOOPBACK_NETWORK in service["networks"]}
    assert joined == publishing


def test_loopback_network_binds_to_loopback_without_source_nat() -> None:
    network = COMPOSE["networks"][LOOPBACK_NETWORK]
    assert network.get("internal", False) is False, "Docker publishes no port on internal networks"
    assert network["enable_ipv6"] is False
    options = network["driver_opts"]
    assert options[f"{BRIDGE}host_binding_ipv4"] == LOOPBACK
    assert options[f"{BRIDGE}enable_ip_masquerade"] == "false"


def test_every_other_network_is_internal_and_unreachable_from_the_host() -> None:
    networks = COMPOSE["networks"]
    used = {network for service in SERVICES.values() for network in service["networks"]}
    assert used <= set(networks)
    for name, network in networks.items():
        if name == LOOPBACK_NETWORK:
            continue
        assert network["internal"] is True, name
        assert network["enable_ipv6"] is False, name
        assert network["driver_opts"][f"{BRIDGE}gateway_mode_ipv4"] == "isolated", name


def test_the_database_resolves_no_external_name() -> None:
    # Docker's embedded resolver forwards names it does not know to the host's resolvers, past the
    # disabled source NAT. A resolver on the container's own loopback answers nothing, while
    # service names on the stack networks still resolve.
    assert SERVICES["postgres"]["dns"] == [LOOPBACK]


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_every_service_runs_unprivileged_with_a_healthcheck(name: str) -> None:
    service = SERVICES[name]
    assert service["user"].startswith("${KN_UID"), "runs as the invoking host user"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    assert "privileged" not in service
    assert service["healthcheck"]["test"]
    assert not any("docker.sock" in str(volume) for volume in service.get("volumes", []))


def test_passwords_come_only_from_secret_files() -> None:
    for name, service in SERVICES.items():
        for key, value in service.get("environment", {}).items():
            if "PASSWORD" in key:
                assert key.endswith("_FILE"), (name, key)
                assert str(value).startswith("/run/secrets/"), (name, key)
    for name, secret in COMPOSE["secrets"].items():
        assert set(secret) == {"file"}, name
        assert secret["file"].startswith("${"), "the path comes from the environment"


def test_database_volume_lives_under_data_dir_and_is_never_created_by_docker() -> None:
    volumes = {volume["target"]: volume for volume in SERVICES["postgres"]["volumes"]}
    data = volumes["/var/lib/postgresql"]
    assert data["type"] == "bind"
    assert data["source"].startswith("${DATA_DIR")
    assert data["source"].endswith("/postgres")
    assert data["bind"]["create_host_path"] is False
    init = volumes["/docker-entrypoint-initdb.d"]
    assert (DEPLOY / init["source"]).resolve() == DEPLOY / "postgres" / "initdb"
    assert init["read_only"] is True


def test_bootstrap_and_probe_cover_core_schemas_and_every_domain_package() -> None:
    domains = {path.name for path in (ROOT / "domains").iterdir() if path.is_dir()}
    expected = CORE_SCHEMAS | domains
    assert set(sql_text_array(BOOTSTRAP, "kn_schemas")) == expected
    assert set(sql_text_array(VERIFY, "expected_schemas")) == expected


def test_only_the_kn_bootstrap_runs_at_initialization() -> None:
    scripts = sorted(path.name for path in (DEPLOY / "postgres" / "initdb").iterdir())
    assert scripts == ["10-kn-bootstrap.sql"]
