"""Multilingual text projection: one text claim, its original and derived translations.

A translation is derived text attached to a claim, not another claim or fact, so the number of
facts never depends on the locales. Display uses the shared localization selector.
"""

from collections.abc import Iterable, Mapping
from typing import Any, ClassVar, Self

from pydantic import model_validator

from kn.evidence.records import CLAIM_REFERENCE, Record
from kn.evidence.vocabulary import TranslationMethod
from kn.i18n.data import SelectedText, SourceText, TextVariant, select_text
from kn.review.model import Digest, Instant, Text


class Translation(Record):
    TABLE: ClassVar[str] = "text_translations"
    KEY: ClassVar[str] = "translation_id"

    claim_key: Digest
    language: Text
    text: Text
    method: TranslationMethod
    provenance: Text
    recorded_at: Instant

    @model_validator(mode="after")
    def _variant(self) -> Self:
        TextVariant(self.text, self.language, self.provenance)
        return self

    def columns(self) -> dict[str, Any]:
        return self.model_dump()


def source_text(claim: Mapping[str, Any], translations: Iterable[Mapping[str, Any]]) -> SourceText:
    """Rebuild the text of a stored claim row; the original keeps its text, tag and claim key.

    Rows are mappings as SQL returns them or as `Record.row()` gives them. A translation of
    another claim, a duplicate language, or a translation in the original's language fails.
    """
    if claim["value_text"] is None:
        raise ValueError("only a text claim has translations")
    variants = []
    for row in sorted(translations, key=lambda item: (item["language"].lower(), item["text"])):
        if row["claim_key"] != claim["claim_key"]:
            raise ValueError("a translation belongs to exactly one text claim")
        variants.append(TextVariant(row["text"], row["language"], row["provenance"]))
    original = TextVariant(
        claim["value_text"], claim["value_language"], CLAIM_REFERENCE + claim["claim_key"]
    )
    return SourceText(original, tuple(variants))


def display(
    claim: Mapping[str, Any], translations: Iterable[Mapping[str, Any]], locale: str
) -> SelectedText:
    """Requested language, then English, then the unchanged original."""
    return select_text(source_text(claim, translations), locale)
