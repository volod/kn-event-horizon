"""Mapped observations accepted from trusted source adapters."""

from typing import Self

from pydantic import model_validator

from kn.identity.model import KnId, SourceKey
from kn.review.model import Frozen, Instant, Text, digest


class Key(Frozen):
    namespace: Text
    issuer: Text
    value: Text

    @property
    def parts(self) -> tuple[str, str, str]:
        return self.namespace, self.issuer, self.value


class Reading(Frozen):
    field_id: Text
    value: Text


class Observation(Frozen):
    record: SourceKey
    version: Text
    observed_at: Instant
    attributes: tuple[Reading, ...] = ()
    authoritative: tuple[Key, ...] = ()
    aliases: tuple[KnId, ...] = ()

    @model_validator(mode="after")
    def unique_inputs(self) -> Self:
        if len({item.field_id for item in self.attributes}) != len(self.attributes):
            raise ValueError("duplicate identity observation fields")
        if len({(item.namespace, item.value) for item in self.authoritative}) != len(
            self.authoritative
        ):
            raise ValueError("duplicate authoritative identifier observations")
        return self

    def fingerprint(self, profile_digest: str) -> str:
        return digest(
            {
                "record": self.record.model_dump(mode="json"),
                "version": self.version,
                "observed_at": self.observed_at.isoformat(),
                "attributes": sorted((part.field_id, part.value) for part in self.attributes),
                "authoritative": sorted(key.parts for key in self.authoritative),
                "aliases": sorted(set(self.aliases)),
                "profile_digest": profile_digest,
            }
        )
