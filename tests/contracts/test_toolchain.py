"""The external tool pin must agree across dependency, lock, and deployment metadata."""

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_external_tool_is_exactly_pinned_and_separate_from_runtime() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    versions = yaml.safe_load((ROOT / "deploy/versions.yaml").read_text())
    tool = versions["schema_governance"]["external_tool"]
    package, version = tool["package"], tool["version"]
    assert project["dependency-groups"][tool["dependency_group"]] == [f"{package}=={version}"]
    assert next(p for p in lock["package"] if p["name"] == package)["version"] == version
    requirements = (
        project["project"]["dependencies"] + project["project"]["optional-dependencies"]["dev"]
    )
    assert all(not dependency.startswith(package) for dependency in requirements)
