"""Trusted adapter boundary and the initial text-only mapping."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from typing import cast

from kn.archive.model import Metadata
from kn.contracts.model import canonical
from kn.engine.outcomes import RunFailure
from kn.engine.profile import SnapshotProfile
from kn.evidence.values import TextValue
from kn.identity.model import SourceKey
from kn.identity.profiles import Profile
from kn.identity.tracking.delivery import Delivery, Statement
from kn.review.model import digest
from kn.sources.config.schema import CrawlerConfigError


@dataclass(frozen=True, slots=True)
class NativeRecord:
    locator: str
    fields: Mapping[str, str]
    language: str = "und"


@dataclass(frozen=True, slots=True)
class Snapshot:
    schema_fingerprint: str
    identity_profile: Profile
    records: tuple[NativeRecord, ...]


type Parser = Callable[[bytes], Snapshot]


@dataclass(frozen=True, slots=True)
class Adapter:
    parse: Parser
    code_digest: str

    def records_and_claims(
        self, profile: SnapshotProfile, capture: Metadata, payload: bytes
    ) -> tuple[Profile, tuple[Delivery, ...]]:
        snapshot = self.parse(payload)
        if snapshot.schema_fingerprint != profile.schema_fingerprint:
            raise RunFailure("schema_drift")
        if not profile.min_records <= len(snapshot.records) <= profile.max_records:
            raise RunFailure("integrity_lost")
        try:
            deliveries = tuple(_delivery(profile, capture, row) for row in snapshot.records)
        except ValueError:
            raise RunFailure("integrity_lost") from None
        if len({item.record for item in deliveries}) != len(deliveries):
            raise RunFailure("integrity_lost")
        return snapshot.identity_profile, deliveries


def load_adapter(entry_point: str) -> Adapter:
    """Resolve installed Python code by the namespace checked in crawler validation."""
    module_name, _, function = entry_point.partition(":")
    try:
        module = import_module(module_name)
        parser = getattr(module, function, None)
        if not callable(parser) or module.__file__ is None:
            raise ValueError("missing parser")
        files = sorted(Path(__file__).parent.glob("*.py"))
        source = Path(module.__file__)
        version = digest(
            {
                "entry_point": entry_point,
                "engine": {file.name: sha256(file.read_bytes()).hexdigest() for file in files},
                "parser": sha256(source.read_bytes()).hexdigest(),
            }
        )
    except (ImportError, OSError, ValueError):
        raise CrawlerConfigError(
            ("parse", "entry_point"), "parserUnavailable", "install the reviewed source adapter"
        ) from None
    return Adapter(cast(Parser, parser), version)


def _delivery(profile: SnapshotProfile, capture: Metadata, row: NativeRecord) -> Delivery:
    fields = row.fields
    if not profile.required_fields.issubset(fields) or not row.locator.startswith("/"):
        raise ValueError("incomplete native record")
    key = tuple(fields.get(name, "") for name in profile.record_key)
    if not all(part.strip() and "\x00" not in part for part in key):
        raise ValueError("incomplete native record key")
    return Delivery(
        record=SourceKey(source=profile.stream.source_id, key=canonical(key)),
        ordering="fetch",
        fetch_id=capture.fetch_id,
        archive_record_id=capture.record_id,
        fetched_at=capture.fetched_at,
        origin_uri=capture.origin_uri,
        locator_kind="json_pointer",
        rights=capture.retention.access,
        code_digest=capture.code_sha256,
        contract_digest=profile.schema_fingerprint,
        assertion_type="declared",
        evidence_class="primary",
        statements=tuple(
            _text_statement(field, field_id, row)
            for field, field_id in profile.fields
            if field in fields
        ),
    )


def _text_statement(field: str, field_id: str, row: NativeRecord) -> Statement:
    value = row.fields[field]
    pointer = field.replace("~", "~0").replace("/", "~1")
    return Statement(
        field_id=field_id,
        value=TextValue(text=value, language=row.language) if value.strip() else None,
        original_value=value,
        locator=f"{row.locator}/{pointer}",
    )
