"""Text claims keep their original; translations are derived text, not more facts."""

from typing import Any

import pytest

from kn.evidence.records import CLAIM_REFERENCE
from kn.evidence.text import Translation, display, source_text
from tests.evidence.fixtures import T0, fact, name_claim


def translation(language: str, text: str, **changes: Any) -> dict[str, Any]:
    return Translation.model_validate(
        {
            "claim_key": name_claim().key,
            "language": language,
            "text": text,
            "method": "human",
            "provenance": f"review:{language}",
            "recorded_at": T0,
            **changes,
        }
    ).row()


@pytest.mark.parametrize(
    ("locale", "languages", "selected", "fallback"),
    [
        ("uk", ["uk", "en"], "uk", False),
        ("uk", ["en"], "en", True),
        ("uk", [], "zh", True),
        ("en", ["uk"], "zh", True),
        ("zh", ["uk", "en"], "zh", False),
    ],
)
def test_display_prefers_requested_then_english_then_the_original(
    locale: str, languages: list[str], selected: str, fallback: bool
) -> None:
    claim = name_claim().row()
    rows = [translation(language, f"text-{language}") for language in languages]
    result = display(claim, rows, locale)
    assert (result.variant.language, result.fallback) == (selected, fallback)
    assert result.is_original == (selected == "zh")


def test_the_original_keeps_text_tag_and_claim_provenance() -> None:
    claim = name_claim().row()
    text = source_text(claim, [translation("en", "Satellite One")])
    assert text.original.text == "\u536b\u661f\u4e00\u53f7"
    assert text.original.language == "zh"
    assert text.original.provenance == CLAIM_REFERENCE + claim["claim_key"]
    assert text.translations[0].provenance == "review:en"


def test_translations_never_multiply_facts() -> None:
    claim = name_claim()
    before = fact(claim)
    rows = [translation(language, f"text-{language}") for language in ("en", "uk", "de")]
    for locale in ("en", "uk"):
        assert display(claim.row(), rows, locale).variant.text == f"text-{locale}"
    assert fact(claim).row() == before.row()
    assert {row["claim_key"] for row in rows} == {claim.key}


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([translation("zh", "dup")], "duplicate language"),
        ([translation("en", "a"), translation("EN", "b")], "duplicate language"),
        ([translation("en", "x", claim_key="c" * 64)], "exactly one text claim"),
    ],
)
def test_ambiguous_translations_are_refused(rows: list[dict], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        source_text(name_claim().row(), rows)


def test_only_text_claims_have_translations_and_translations_need_provenance() -> None:
    from tests.evidence.fixtures import claim

    with pytest.raises(ValueError, match="text claim"):
        source_text(claim().row(), [])
    with pytest.raises(ValueError, match="provenance"):
        translation("en", "x", provenance=" ")
