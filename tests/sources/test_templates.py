"""Keep the onboarding crawler template valid and complete against the version 1 schema."""

import json
import re
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from typing import Any

from kn.sources.config import load_crawler_config

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/guide/templates/source-crawler-config.yaml"
# Counterpart instance profiles declare these blocks in their own InvenTree instance template.
COUNTERPART_ONLY = frozenset({"adapter", "exchange"})
# Block and flow mapping keys, including those in commented alternatives.
KEY = re.compile(r"(?:^|[\s{,#-])([a-z_]+):(?=\s|$)", re.MULTILINE)


def _required(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        yield from node.get("required", ())
        for key, value in node.items():
            if key not in COUNTERPART_ONLY:
                yield from _required(value)
    elif isinstance(node, list):
        for item in node:
            yield from _required(item)


def test_template_is_a_valid_candidate_profile() -> None:
    config = load_crawler_config(TEMPLATE)
    assert config["approval"] == {"state": "candidate"}
    assert config["rights"] == {"permission": "pending"}


def test_template_names_every_property_the_schema_can_require() -> None:
    schema = json.loads(
        files("kn.sources.config").joinpath("crawler.schema.json").read_text(encoding="ascii")
    )
    required = set(_required(schema)) - COUNTERPART_ONLY
    assert required
    assert required - set(KEY.findall(TEMPLATE.read_text(encoding="ascii"))) == set()
