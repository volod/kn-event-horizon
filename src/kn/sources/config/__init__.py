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
    try:
        config = read_document(path)
    except ContractError as error:
        raise CrawlerConfigError((), error.rule, error.hint) from None
    except ValueError:
        raise CrawlerConfigError((), "syntax", "use bounded JSON-compatible numbers") from None
    except OSError:
        raise CrawlerConfigError((), "file", "use a readable crawler configuration file") from None
    validate_schema(config)
    validate_semantics(config)
    if config["approval"]["state"] == "enabled":
        verify_evidence(path, **config["verification"])
    return config


def source_validate_operation(path: Path) -> dict[str, object]:
    config = load_crawler_config(path)
    return {
        "status": "valid",
        "source_id": config["identity"]["source_id"],
        "state": config["approval"]["state"],
    }
