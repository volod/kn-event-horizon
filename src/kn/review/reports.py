"""Private replay reports with no reviewed values, reviewers or evidence references."""

import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from kn.contracts.model import canonical

type ReplayState = Literal["applied", "pending", "orphan", "stale", "incompatible"]


@dataclass(frozen=True)
class ReplayEntry:
    target_id: str
    contract_id: str
    dataset: str
    state: ReplayState


type ReplayReport = tuple[ReplayEntry, ...]


def write_report(data_dir: Path, report: ReplayReport) -> Path:
    """Publish the report after the enclosing transaction commits."""
    root = data_dir / "human-verification"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = Path(tempfile.mkdtemp(prefix="replay-", dir=root))
    temporary = directory / ".replay.json"
    temporary.write_text(canonical([asdict(entry) for entry in report]) + "\n", encoding="ascii")
    return temporary.rename(directory / "replay.json")
