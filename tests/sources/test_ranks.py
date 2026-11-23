"""Reviewed rank overrides must refer to exact, domain-qualified catalogue IDs."""

from pathlib import Path

import pytest

from kn.contracts.diagnostics import ContractError
from kn.sources.ranks import validate_rank_overrides

KNOWN_IDS = {"microelectronics:D01", "space:row-4"}


def test_known_sources_can_have_rank_overrides_scoped_to_field_groups(tmp_path: Path) -> None:
    path = tmp_path / "source-ranks.yaml"
    path.write_text(
        "overrides:\n"
        "  - {source_id: 'space:row-4', rank: third_party}\n"
        "  - {source_id: 'space:row-4', rank: first_party, field_group: launch}\n",
        encoding="ascii",
    )
    validate_rank_overrides(path, KNOWN_IDS)


@pytest.mark.parametrize(
    ("entries", "rule", "location"),
    [
        ("  - {source_id: D01, rank: first_party}\n", "sourceId", "/0/source_id"),
        ("  - {source_id: 'space:D01', rank: first_party}\n", "sourceId", "/0/source_id"),
        ("  - {source_id: 'space:row-4', rank: P0}\n", "literal_error", "/0/rank"),
        (
            "  - {source_id: 'space:row-4', rank: third_party}\n"
            "  - {source_id: 'space:row-4', rank: first_party}\n",
            "duplicate",
            "/1",
        ),
    ],
)
def test_invalid_rank_overrides_are_rejected(
    tmp_path: Path, entries: str, rule: str, location: str
) -> None:
    path = tmp_path / "source-ranks.yaml"
    path.write_text(f"overrides:\n{entries}", encoding="ascii")
    with pytest.raises(ContractError) as error:
        validate_rank_overrides(path, KNOWN_IDS)
    assert error.value.path == f"$/overrides{location}"
    assert error.value.rule == rule
