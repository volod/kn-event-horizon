"""The official Figure 9 tree is separate from local products and evidence-backed crosswalks."""

import json
from pathlib import Path

from kn.semantic.seeds import RESOURCES, reviewed_snapshot

PREFIX = "microelectronics.oecd_2024."
PRODUCT = "microelectronics.product_v1."


def test_official_oecd_scheme_has_only_the_29_publication_nodes() -> None:
    snapshot = reviewed_snapshot()
    scheme = next(row for row in snapshot["concept_schemes"] if row["id"] == PREFIX + "scheme")
    assert scheme["origin"] == "official"
    assert scheme["verification_state"] == "verified"
    assert (
        scheme["source_sha256"]
        == "25f7ec43f76d5fc1ddac65d1a16b179262aa8b68371545eef87ccac384d40083"
    )
    nodes = [row for row in snapshot["concepts"] if row["scheme_id"] == scheme["id"]]
    assert len(nodes) == 29
    assert {row["id"] for row in nodes} == {
        PREFIX + row["code"]
        for row in json.loads((RESOURCES / "oecd_2024.json").read_bytes())["nodes"]
    }
    assert not any(row["id"].startswith(PREFIX + "X") for row in nodes)


def test_original_product_concepts_are_unchanged() -> None:
    snapshot = reviewed_snapshot()
    baseline = json.loads(
        (Path(__file__).parent / "fixtures/product_v1_baseline.json").read_bytes()
    )
    for name, rows in baseline.items():
        key = "term_id" if name == "labels" else "id"
        assert rows == [
            row
            for row in snapshot[name]
            if row[key].startswith(PRODUCT) and row[key] != PRODUCT + "scheme"
        ]
    scheme = next(row for row in snapshot["concept_schemes"] if row["id"] == PRODUCT + "scheme")
    assert scheme["origin"] == "kb_normalized" and scheme["verification_state"] == "unverified"


def test_product_crosswalks_distinguish_equivalence_from_local_classification() -> None:
    snapshot = reviewed_snapshot()
    rows = {row["source_id"]: row for row in snapshot.get("concept_mappings", [])}
    assert len(rows) == 69
    assert rows[PRODUCT + "L.MCU"]["mapping_type"] == "exactMatch"
    assert rows[PRODUCT + "L.MCU"]["target_id"] == PREFIX + "L.MCU"
    assert rows[PRODUCT + "L.MCU.ULP"]["mapping_type"] == "broadMatch"
    assert rows[PRODUCT + "O.SENS.RANGE"]["mapping_type"] == "analyst_crosswalk"
    assert not any(key.startswith(PRODUCT + "X") for key in rows)
    assert all(row["evidence_id"].startswith("urn:sha256:") for row in rows.values())


def test_figure9_source_labels_and_parent_edges_match_independent_transcription() -> None:
    snapshot = reviewed_snapshot()
    reference = json.loads((Path(__file__).parent / "fixtures/oecd_figure9.json").read_bytes())
    concepts = {row["id"]: row for row in snapshot["concepts"]}
    labels = {(row["term_id"], row["locale"]): row["label"] for row in snapshot["labels"]}
    alternatives = {
        (row["term_id"], row["locale"], row["label"]) for row in snapshot["alternative_labels"]
    }
    assert len(reference) == 29
    assert sum(row["parent_code"] is not None for row in reference) == 25
    for row in reference:
        identifier = PREFIX + row["code"]
        assert concepts[identifier]["parent_id"] == (
            PREFIX + row["parent_code"] if row["parent_code"] else None
        )
        for locale in ("en", "uk"):
            if row["source_label"] == "Others":
                assert labels[identifier, locale] == "Others (" + row["code"] + ")"
                assert (identifier, locale, "Others") in alternatives
            else:
                assert labels[identifier, locale] == row["source_label"]


def test_all_crosswalk_decisions_and_original_row_provenance_are_preserved() -> None:
    from collections import Counter

    from kn.semantic.oecd_reference import read_reference
    from kn.semantic.seeds import reconcile

    review, evidence_id = read_reference(RESOURCES)
    assert Counter(row.mapping_type for row in review.crosswalks) == {
        "exactMatch": 29,
        "broadMatch": 23,
        "analyst_crosswalk": 17,
        None: 7,
    }
    assert {row.code for row in review.crosswalks if row.target_code is None} == {
        "X",
        "X.MOD",
        "X.DEV",
        "X.IP",
        "X.SW",
        "X.FAB",
        "X.MAT",
    }
    assert all(row.reason for row in review.crosswalks)
    documents, report, *_ = reconcile(Path(__file__).resolve().parents[2])
    doc = documents["microelectronics"]
    mentioned = {identifier for row in report for identifier in row["term_ids"]}
    generated = [
        row["id"]
        for row in doc["snapshot"]["terms"]
        if row["id"].startswith((PREFIX, "microelectronics.oecd_2024_crosswalk."))
    ]
    assert set(generated) - {PREFIX + "scheme"} <= mentioned
    for identifier in generated:
        source = doc["provenance"][identifier][0]
        assert source["publication_sha256"] == review.publication.source_sha256
        assert source["review_evidence_id"] == evidence_id
        assert source["publication_locator"] == review.locator
