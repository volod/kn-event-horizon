"""Publication decisions stay scoped, reproducible, and fail closed on seed drift."""

import json
from pathlib import Path

from kn.semantic.seeds import RESOURCES, reviewed_snapshot


def test_publication_decisions_reach_reviewed_schemes() -> None:
    snapshot = reviewed_snapshot()
    schemes = {row["id"]: row for row in snapshot["concept_schemes"]}
    assert schemes["space.euspa_2026.scheme"]["verification_state"] == "verified"
    assert schemes["microelectronics.ecs_sria_2026.scheme"]["edition"] == "2026"
    assert schemes["gdelt.cameo_v2.scheme"]["verification_state"] == "unverified"
    assert "20" in schemes["gdelt.cameo_v2.scheme"]["verification_reason"]
    assert "TX17" in schemes["space.nasa_tx_2024.scheme"]["verification_reason"]
    assert all("pending" not in row["verification_reason"].lower() for row in schemes.values())


def test_every_scheme_has_a_publication_or_local_review() -> None:
    for domain in ("space", "gdelt", "microelectronics"):
        report = json.loads((RESOURCES / f"{domain}-verification.json").read_bytes())
        assert (Path("domains") / domain / "seeds/verification.json").read_bytes() == (
            RESOURCES / f"{domain}-verification.json"
        ).read_bytes()
        schemes = json.loads((RESOURCES / f"{domain}.json").read_bytes())["snapshot"][
            "concept_schemes"
        ]
        assert {row["id"] for row in schemes} == {row["scheme_id"] for row in report["schemes"]}
        assert all(
            row["scope"] and row["comparison"] and row["verification_reason"]
            for row in report["schemes"]
        )


def test_selected_publication_rows_reproduce_review_findings() -> None:
    snapshot = reviewed_snapshot()
    terms = {row["id"]: row for row in snapshot["terms"]}
    labels = {row["term_id"]: row["label"] for row in snapshot["labels"] if row["locale"] == "en"}
    fixtures = json.loads(
        (Path(__file__).parent / "fixtures/official_comparisons.json").read_bytes()
    )
    schemes = {row["id"]: row for row in snapshot["concept_schemes"]}
    for sid, reference in fixtures.items():
        scheme = schemes[sid]
        concepts = [row for row in snapshot["concepts"] if row["scheme_id"] == sid]
        assert scheme["source_uri"] == reference["source_uri"]
        assert scheme["source_sha256"] == reference["source_sha256"]
        assert {terms[row["id"]]["code"] for row in concepts} == reference["rows"].keys()
        mismatches = {
            terms[row["id"]]["code"]
            for row in concepts
            if labels[row["id"]].casefold()
            != reference["rows"][terms[row["id"]]["code"]].casefold()
        }
        assert mismatches == set(reference["mismatches"])
        assert scheme["verification_state"] == ("unverified" if mismatches else "verified")
    # These remain the supplied labels, including the disagreements.
    assert labels["gdelt.cameo_v2.20"] == "Engage in unconventional mass violence"
    assert labels["space.nasa_tx_2024.TX17"] == "Guidance, Navigation, and Control (GN&C)"
    assert labels["microelectronics.ecs_sria_2026.ECS:2.3"].endswith("Method and Tools")


def test_oecd_download_has_checksum_without_promoting_local_extensions() -> None:
    scheme = next(
        row
        for row in reviewed_snapshot()["concept_schemes"]
        if row["id"] == "microelectronics.product_v1.scheme"
    )
    assert (
        scheme["source_sha256"]
        == "25f7ec43f76d5fc1ddac65d1a16b179262aa8b68371545eef87ccac384d40083"
    )
    assert scheme["verification_state"] == "unverified"
    assert scheme["origin"] == "kb_normalized"
    assert "unavailable" not in scheme["verification_reason"]
    report = json.loads((RESOURCES / "microelectronics-verification.json").read_bytes())
    review = next(row for row in report["schemes"] if row["scheme_id"] == scheme["id"])
    assert {finding["kind"] for finding in review["findings"]} == {"local_extension"}
