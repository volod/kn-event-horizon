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
