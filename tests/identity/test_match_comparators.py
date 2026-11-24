"""Comparator and normalizer behavior across supported profile inputs."""

from decimal import localcontext

import pytest

from kn.identity.matching.comparators import Comparator, compare
from kn.identity.matching.normalizers import normalize


@pytest.mark.parametrize(
    ("normalizer", "value", "expected"),
    [
        ("mpn-v1", "  ab-00\uff14\uff12 /TR ", "AB-0042 /TR"),
        ("identifier-v1", "  00042 ", "00042"),
        ("identifier-v1", " a:B/7 ", "a:B/7"),
        ("legal-name-v1", " Fixture-\u00dcber GmbH ", "fixture \u00fcber"),
        ("registrable-domain-v1", "https://a.B.example.co.uk./parts", "example.co.uk"),
        ("registrable-domain-v1", "x.alice.github.io", "alice.github.io"),
        ("registrable-domain-v1", "stra\u00dfe.de", "xn--strae-oqa.de"),
        ("registrable-domain-v1", "strasse.de", "strasse.de"),
        ("registrable-domain-v1", "co.uk", None),
        ("registrable-domain-v1", "issuer.example.invalid", None),
        ("registrable-domain-v1", "https://alice@example.org", None),
        ("registrable-domain-v1", "https://ex\nample.org", None),
        ("registrable-domain-v1", "127.0.0.1", None),
        ("gtin-v1", "4006381333931", "04006381333931"),
        ("gtin-v1", "4006381333932", None),
    ],
)
def test_normalizers(normalizer: str, value: str, expected: str | None) -> None:
    assert normalize(normalizer, value) == expected


@pytest.mark.parametrize(
    ("comparator", "left", "right", "tolerance", "outcome"),
    [
        ("exact", "ab", "AB", None, "disagree"),
        ("normalized_exact", "AB", "AB", None, "agree"),
        ("normalized_exact", "AB", None, None, "missing"),
        ("graded_string", "fixture components", "fixture component", None, "similar"),
        ("graded_string", "uno", "dos", None, "disagree"),
        ("graded_string", "fixture", "fixture", None, "agree"),
        ("graded_string", "a" * 513, "a" * 513, None, "invalid"),
        ("numeric_tolerance", "1.01", "1.00", 0.01, "agree"),
        ("numeric_tolerance", "1.02", "1.00", 0.01, "disagree"),
        ("numeric_tolerance", "2e1001", "1", 0.01, "invalid"),
        ("numeric_tolerance", "NaN", "1", 0.01, "invalid"),
        ("date_window", "2024-02-29", "2024-03-02", 2, "agree"),
        ("date_window", "2024-02-29", "2024-03-02", 1, "disagree"),
        ("date_window", "2025-02-29", "2025-03-02", 2, "invalid"),
        ("set_overlap", '["a","a","b"]', '["b","a"]', 1, "agree"),
        ("set_overlap", '["a","b"]', '["a","c"]', None, "disagree"),
        ("set_overlap", '["a"]', "[]", None, "missing"),
        ("set_overlap", '["a"]', '{"a":1}', None, "invalid"),
    ],
)
def test_comparisons_are_symmetric(
    comparator: Comparator,
    left: str,
    right: str | None,
    tolerance: float | None,
    outcome: str,
) -> None:
    assert compare(comparator, left, right, tolerance) == outcome
    assert compare(comparator, right, left, tolerance) == outcome


def test_numeric_tolerance_is_independent_of_decimal_context() -> None:
    with localcontext() as context:
        context.prec = 1
        assert compare("numeric_tolerance", "10.012", "10", 0.011) == "disagree"
