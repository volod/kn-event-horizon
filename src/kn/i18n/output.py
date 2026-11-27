"""Operator presentation of structured operation results."""

from kn.i18n import Translator
from kn.i18n.identity_output import identity_result
from kn.i18n.lineage_output import lineage_result


def render_result(translator: Translator, command: str, result: dict[str, object]) -> str:
    if command == "review":
        from kn.i18n.review_output import review_result

        return review_result(result)
    if command == "identity":
        return identity_result(translator, result)
    if command == "lineage":
        return lineage_result(translator, result)
    if command == "info":
        return translator.text("cli.info", **result)
    if command == "contract":
        contracts = result.get("contracts", [result])
        assert isinstance(contracts, list)
        return "\n".join(translator.text("cli.contract_ok", **item) for item in contracts)
    if command == "vocabulary":
        if result["status"] == "exported":
            return translator.text("cli.skos_ok", **result)
        return translator.text("cli.seed_ok", **result)
    if command == "db":
        return translator.text("cli.db_ok")
    if command == "raw":
        return _raw_result(translator, result)
    if command == "source":
        return _source_result(translator, result)
    return _artifact_result(translator, result)


def _source_result(translator: Translator, result: dict[str, object]) -> str:
    if result.get("status") == "valid":
        return translator.text(
            "cli.source_config_ok",
            source_id=result["source_id"],
            state=_source_states(translator)[str(result["state"])],
        )
    if "run_id" in result:
        summary = translator.text("cli.source_outcome", **result)
        if result["error_code"] is not None:
            return translator.text("cli.source_outcome_error", summary=summary, **result)
        return summary
    if "source_status" in result:
        status = result["source_status"]
        assert isinstance(status, dict)
        return _source_status(translator, status)
    sources = result["sources"]
    assert isinstance(sources, list)
    return _render_sources(translator, sources)


def _source_status(translator: Translator, status: dict[str, object]) -> str:
    missing = translator.text("cli.source_status_missing")
    values = {
        key: missing if value is None else _status_text(value) for key, value in status.items()
    }
    yes = translator.text("cli.source_status_yes")
    no = translator.text("cli.source_status_no")
    for key in ("stale", "failing"):
        values[key] = yes if status[key] else no
    return "\n".join(
        (
            translator.text("cli.source_status_summary", **values),
            translator.text("cli.source_status_times", **values),
            translator.text("cli.source_status_freshness", **values),
            translator.text("cli.source_status_counts", **values),
            translator.text("cli.source_status_checkpoint", **values),
        )
    )


def _status_text(value: object) -> str:
    text = str(value)
    return text if text.isascii() and text.isprintable() else ascii(text)


def _raw_result(translator: Translator, result: dict[str, object]) -> str:
    if result["status"] == "reindexed":
        return translator.text("cli.raw_reindexed", **result)
    return translator.text("cli.raw_verified", **result)


def _artifact_result(translator: Translator, result: dict[str, object]) -> str:
    if "tables" in result:
        tables = result["tables"]
        assert isinstance(tables, dict)
        return translator.text(
            "cli.validated",
            import_id=result["import_id"],
            tables=translator.plural("cli.tables", len(tables)),
        )
    if result["status"] == "imported":
        return translator.text("cli.imported", **result)
    return translator.text("cli.already_imported", **result)


def _source_states(translator: Translator) -> dict[str, str]:
    return {
        "candidate": translator.text("cli.source_candidate"),
        "investigating": translator.text("cli.source_investigating"),
        "sampling_authorized": translator.text("cli.source_sampling_authorized"),
        "approved": translator.text("cli.source_approved"),
        "enabled": translator.text("cli.source_enabled"),
        "paused": translator.text("cli.source_paused"),
        "retired": translator.text("cli.source_retired"),
        "rejected": translator.text("cli.source_rejected"),
    }


def _render_sources(translator: Translator, sources: list[dict[str, object]]) -> str:
    if not sources:
        return translator.text("cli.source_empty")
    states = _source_states(translator)
    access = translator.text("cli.source_unverified")
    return "\n".join(
        [
            translator.text("cli.source_heading"),
            *(
                translator.text(
                    "cli.source_row",
                    **source,
                    state=states[str(source["lifecycle_state"])],
                    access=access,
                )
                for source in sources
            ),
        ]
    )
