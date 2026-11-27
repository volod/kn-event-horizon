"""Offline entry point for validating reviewed crawler configuration."""

from pathlib import Path
from typing import Any

from kn.contracts.diagnostics import ContractError
from kn.contracts.document import read_document
from kn.sources.config.evidence import verify_evidence
from kn.sources.config.schema import CrawlerConfigError, validate_schema
from kn.sources.config.semantics import validate_semantics


def load_crawler_config(path: Path) -> dict[str, Any]:
    """Read a config and verify schema, references, and enabled-state evidence."""
    return _load(path, offline_catalogue=True)


def load_runtime_config(path: Path) -> dict[str, Any]:
    """Validate enablement evidence before the runner checks the deployed catalogue."""
    config = _load(path, offline_catalogue=False)
    if config["approval"]["state"] != "enabled":
        raise CrawlerConfigError(
            ("approval", "state"), "enabledState", "use a reviewed enabled profile"
        )
    return config


def load_status_config(path: Path) -> dict[str, Any]:
    """Validate a monitoring profile independently of acquisition evidence files."""
    return _load(path, offline_catalogue=False, verify_enablement=False)


def _load(path: Path, *, offline_catalogue: bool, verify_enablement: bool = True) -> dict[str, Any]:
    try:
        config = read_document(path)
    except ContractError as error:
        raise CrawlerConfigError((), error.rule, error.hint) from None
    except ValueError:
        raise CrawlerConfigError((), "syntax", "use bounded JSON-compatible numbers") from None
    except OSError:
        raise CrawlerConfigError((), "file", "use a readable crawler configuration file") from None
    validate_schema(config)
    validate_semantics(config, offline_catalogue=offline_catalogue)
    if verify_enablement and config["approval"]["state"] == "enabled":
        verify_evidence(path, **config["verification"])
    return config


def source_validate_operation(path: Path) -> dict[str, object]:
    config = load_crawler_config(path)
    return {
        "status": "valid",
        "source_id": config["identity"]["source_id"],
        "state": config["approval"]["state"],
    }
