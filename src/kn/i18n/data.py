"""Lossless source text and optional translations, independent of interface catalogs."""

import re
from dataclasses import dataclass

_LANGUAGE_TAG = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*")


def _language_key(language: str) -> str:
    """Compare tags case-insensitively without guessing a language from source text."""
    if not _LANGUAGE_TAG.fullmatch(language):
        raise ValueError("language tag must be BCP-47 shaped; use und when unknown")
    return language.lower()


@dataclass(frozen=True, slots=True)
class TextVariant:
    """Original text or a translation, with a durable source/review/model reference."""

    text: str
    language: str
    provenance: str

    def __post_init__(self) -> None:
        _language_key(self.language)
        if not self.provenance.strip():
            raise ValueError("text provenance is required")


@dataclass(frozen=True, slots=True)
class SourceText:
    """One fact's original text, retained even when every translation is absent."""

    original: TextVariant
    translations: tuple[TextVariant, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "translations", tuple(self.translations))
        seen = {_language_key(self.original.language)}
        for variant in self.translations:
            key = _language_key(variant.language)
            if key in seen:
                raise ValueError(f"duplicate language: {variant.language}")
            if not variant.text.strip():
                raise ValueError("translation must not be blank")
            seen.add(key)


@dataclass(frozen=True, slots=True)
class SelectedText:
    """A display choice with its language and provenance, never a rewritten fact."""

    variant: TextVariant
    is_original: bool
    fallback: bool


def select_text(data: SourceText, requested: str) -> SelectedText:
    """Prefer requested language, then English, then the unchanged original."""
    requested_key = _language_key(requested)
    variants = (data.original, *data.translations)
    available = {_language_key(variant.language): variant for variant in variants}
    selected = available.get(requested_key, available.get("en", data.original))
    return SelectedText(
        selected,
        is_original=selected is data.original,
        fallback=_language_key(selected.language) != requested_key,
    )
