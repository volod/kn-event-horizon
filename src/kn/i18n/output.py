"""Operator presentation of structured operation results."""

from kn.i18n import Translator


def render_result(translator: Translator, command: str, result: dict[str, object]) -> str:
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
    if command == "source":
        if result.get("status") == "valid":
            return translator.text(
                "cli.source_config_ok",
                source_id=result["source_id"],
                state=_source_states(translator)[str(result["state"])],
            )
        sources = result["sources"]
        assert isinstance(sources, list)
        return _render_sources(translator, sources)
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
