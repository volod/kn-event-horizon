"""Localized lineage headings; each section lists its canonical records."""

from kn.contracts.model import canonical
from kn.i18n import Translator


def lineage_result(tr: Translator, result: dict[str, object]) -> str:
    terminals = result["terminals"]
    assert isinstance(terminals, list)
    field = result["field_id"]
    lines = [
        tr.text(
            "cli.lineage_heading",
            reference=result["reference"],
            kn_id=result["kn_id"],
            terminals=", ".join(terminals),
        ),
        tr.text(
            "cli.lineage_scope",
            field=tr.text("cli.lineage_all_fields") if field is None else field,
            audience=result["audience"],
            permitted=tr.text("cli.lineage_all_rights")
            if result["permitted"] is None
            else canonical(result["permitted"]),
        ),
    ]
    for name, heading in _headings(tr, result).items():
        rows = result[name]
        assert isinstance(rows, list)
        lines.extend([heading, *(canonical(row) for row in rows)])
    withheld = result["withheld"]
    if withheld:
        lines.append(tr.text("cli.lineage_withheld", counts=canonical(withheld)))
    return "\n".join(lines)


def _headings(tr: Translator, result: dict[str, object]) -> dict[str, str]:
    def count(name: str) -> str:
        rows = result[name]
        assert isinstance(rows, list)
        return tr.number(len(rows))

    return {
        "objects": tr.text("cli.lineage_objects", count=count("objects")),
        "history": tr.text("cli.lineage_history", count=count("history")),
        "identifiers": tr.text("cli.lineage_identifiers", count=count("identifiers")),
        "attributes": tr.text("cli.lineage_attributes", count=count("attributes")),
        "links": tr.text("cli.lineage_links", count=count("links")),
        "matches": tr.text("cli.lineage_matches", count=count("matches")),
        "records": tr.text("cli.lineage_records", count=count("records")),
        "claims": tr.text("cli.lineage_claims", count=count("claims")),
        "confirmations": tr.text("cli.lineage_confirmations", count=count("confirmations")),
        "evidence": tr.text("cli.lineage_evidence", count=count("evidence")),
        "facts": tr.text("cli.lineage_facts", count=count("facts")),
        "outcomes": tr.text("cli.lineage_outcomes", count=count("outcomes")),
        "review_items": tr.text("cli.lineage_review_items", count=count("review_items")),
        "review_decisions": tr.text(
            "cli.lineage_review_decisions", count=count("review_decisions")
        ),
        "gaps": tr.text("cli.lineage_gaps", count=count("gaps")),
    }
