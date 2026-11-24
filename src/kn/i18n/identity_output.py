"""Localized identity headings with the canonical records available for inspection."""

from kn.contracts.model import canonical
from kn.i18n import Translator


def identity_result(tr: Translator, result: dict[str, object]) -> str:
    action = result["action"]
    if action == "applied":
        return tr.text(
            "cli.identity_applied",
            decision_id=result["decision_id"],
            event=canonical(result["event"]),
        )
    if action == "resolve":
        successors = result["successors"]
        assert isinstance(successors, list)
        return tr.text(
            "cli.identity_resolved", kn_id=result["kn_id"], successors=", ".join(successors)
        )
    if action == "history":
        return _records(
            tr.text("cli.identity_event_history", kn_id=result["kn_id"]), result["events"]
        )
    states = {
        "active": tr.text("cli.identity_active"),
        "merged": tr.text("cli.identity_merged"),
        "split": tr.text("cli.identity_split"),
        "retired": tr.text("cli.identity_retired"),
    }
    successors = result["successors"]
    assert isinstance(successors, list)
    heading = tr.text(
        "cli.identity_shown",
        kn_id=result["kn_id"],
        entity_class=canonical(result["entity_class"]),
        state=states[str(result["state"])],
        anchor=canonical(result["anchor"]),
        mint_event=result["mint_event"],
    )
    if successors:
        heading += "\n" + tr.text("cli.identity_shown_successors", successors=", ".join(successors))
    return _records(heading, result["holdings"])


def _records(heading: str, records: object) -> str:
    assert isinstance(records, list)
    return "\n".join([heading, *(canonical(row) for row in records)])
