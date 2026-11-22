"""Term-level differences between staged and reviewed seeds, for the reconciliation report."""

from kn.semantic.seed_model import encoded
from kn.semantic.structure import Snapshot


def term_changes(staged: Snapshot, reviewed: Snapshot) -> dict[str, list[str]]:
    """Term IDs added, changed or removed relative to the reviewed seeds that rebuilds load."""
    before, after = _term_rows(reviewed), _term_rows(staged)
    return {
        "added": sorted(after.keys() - before.keys()),
        "changed": sorted(key for key in after.keys() & before.keys() if after[key] != before[key]),
        "removed": sorted(before.keys() - after.keys()),
    }


# Rows without their own term ID belong to the term they describe.
TERM_KEYS = ("term_id", "condition_set_id", "profile_id", "rubric_id", "id")
NAMESPACE_TABLES = {"namespaces", "namespace_labels"}


def _term_rows(snapshot: Snapshot) -> dict[str, list[bytes]]:
    rows: dict[str, list[bytes]] = {}
    for name, table in snapshot.items():
        if name in NAMESPACE_TABLES:
            continue
        for row in table:
            key = next(row[column] for column in TERM_KEYS if column in row)
            rows.setdefault(key, []).append(encoded({"table": name, **row}))
    return {key: sorted(value) for key, value in rows.items()}
