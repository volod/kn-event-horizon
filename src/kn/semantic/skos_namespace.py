"""Public identifier authority and RDF namespaces for SKOS interchange."""

import re
from dataclasses import dataclass
from os import environ
from typing import Self

from rdflib import Namespace

DEFAULT_DOMAIN = "summa.dev"
DOMAIN_SETTING = "KN_VOCABULARY_DOMAIN"
MAX_DOMAIN_LENGTH = 253
DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


@dataclass(frozen=True, slots=True)
class VocabularyNamespace:
    metadata: Namespace
    terms: Namespace
    label_selections: Namespace

    @classmethod
    def for_domain(cls, domain: str) -> Self:
        authority = domain.lower().removesuffix(".")
        labels = authority.split(".")
        if (
            not domain.isascii()
            or len(authority) > MAX_DOMAIN_LENGTH
            or len(labels) < 2
            or labels[-1].isdigit()
            or any(DNS_LABEL.fullmatch(label) is None for label in labels)
        ):
            raise ValueError(f"{DOMAIN_SETTING} must be an ASCII DNS domain name")
        # RFC 3151 transcription of +//IDN <domain>//NONSGML KN Event Horizon Vocabulary//EN.
        base = f"urn:publicid:%2B:IDN+{authority}:NONSGML+KN+Event+Horizon+Vocabulary:EN"
        return cls(
            Namespace(f"{base}#semantic/"),
            Namespace(f"{base}#term/"),
            Namespace(f"{base}#label-selection/"),
        )


DEFAULT_NAMESPACE = VocabularyNamespace.for_domain(DEFAULT_DOMAIN)


def configured_namespace() -> VocabularyNamespace:
    """Read the authority for one filesystem export."""
    return VocabularyNamespace.for_domain(environ.get(DOMAIN_SETTING, DEFAULT_DOMAIN))
