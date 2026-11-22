"""Immutable package archives support retries without replacing previous evidence."""

import json
import shutil
import tempfile
from pathlib import Path

from kn.contracts.loader import canonical
from kn.domains.space.satcom.package import Package, file_manifest


def archive(package: Package, data_dir: Path) -> Path:
    root = data_dir / "satcom-import"
    root.mkdir(parents=True, exist_ok=True)
    target = root / package.import_id
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=root))
    try:
        for name, data in package.files.items():
            path = staging / "package" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (staging / "manifest.json").write_text(canonical(package.manifest()) + "\n")
        try:
            staging.rename(target)
        except OSError:
            if not target.is_dir():
                raise
        _verify(target, package)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return target


def _verify(target: Path, package: Package) -> None:
    stored = json.loads((target / "manifest.json").read_text())
    if stored != package.manifest():
        raise ValueError("existing archive manifest differs from package")
    files = {
        path.relative_to(target / "package").as_posix(): path.read_bytes()
        for path in (target / "package").rglob("*")
        if path.is_file()
    }
    if file_manifest(files) != file_manifest(package.files):
        raise ValueError("existing archive bytes differ from package")
