"""English review output; canonical JSON safely escapes untrusted source strings."""

from kn.contracts.model import canonical


def review_result(result: dict[str, object]) -> str:
    action = result["action"]
    if action == "target":
        return "Verification target: " + canonical(result)
    if action == "decided":
        return "Review decision recorded: " + canonical(result["decision"])
    if action == "replayed":
        return "Review replay: " + canonical(result["report"])
    rows = result["items"]
    assert isinstance(rows, list)
    flagged = (
        ["Owner overrides: " + canonical(result["overrides"])] if "overrides" in result else []
    )
    return "\n".join(
        [
            "Review queue:",
            *(canonical(row) for row in rows),
            *flagged,
            "Source dispute rates: " + canonical(result["dispute_rates"]),
            "Unattached decisions: " + canonical(result["orphans"]),
        ]
    )
