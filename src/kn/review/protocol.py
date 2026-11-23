"""Trusted actor boundary and order-independent event graph projection."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from kn.review.model import Decision, Projection, Request, Stamp, Target, digest, utc


@dataclass(frozen=True)
class Reviewer:
    """Provided by a trusted authenticator, never deserialized from a decision request.

    This is a process trust boundary, not an authentication implementation. Entry points must
    establish identity and purpose authorization independently of payload/source attributes.
    """

    principal: str
    kind: str
    authenticated: bool
    purposes: frozenset[str]

    def authorize(self, target: Target) -> None:
        if (
            self.kind != "human"
            or not self.authenticated
            or not self.principal.strip()
            or target.purpose not in self.purposes
        ):
            raise ValueError("an authenticated authorized human reviewer is required")


def decide(request: Request, reviewer: Reviewer, recorded_at: datetime) -> Decision:
    reviewer.authorize(request.target)
    data = {
        **request.model_dump(mode="json"),
        "schema_version": 1,
        "reviewer": reviewer.principal,
        "recorded_at": utc(recorded_at).isoformat(),
    }
    # Normalize all instants to the same JSON representation used on replay.
    data["recorded_at"] = utc(recorded_at).isoformat().replace("+00:00", "Z")
    return Decision.model_validate({**data, "decision_id": digest(data)})


def validate_history(events: Iterable[Decision]) -> dict[str, Decision]:
    """Validate causal references, retries and cycles without relying on input order."""
    by_id: dict[str, Decision] = {}
    requests: dict[tuple[str, str], str] = {}
    for event in events:
        key = (event.reviewer, event.request_id)
        if key in requests and requests[key] != event.decision_id:
            raise ValueError("request ID reused with different decision content")
        requests[key] = event.decision_id
        by_id[event.decision_id] = event
    for event in by_id.values():
        for prior_id in event.predecessors:
            prior = by_id.get(prior_id)
            if prior is None or prior.target != event.target:
                raise ValueError("predecessor must exist for the exact target and purpose")
            if prior.recorded_at > event.recorded_at:
                raise ValueError("decision cannot precede its recorded predecessor")
    _acyclic(by_id)
    return by_id


def _acyclic(events: dict[str, Decision]) -> None:
    remaining = {key: set(event.predecessors) for key, event in events.items()}
    while remaining:
        ready = {key for key, parents in remaining.items() if not parents}
        if not ready:
            raise ValueError("decision history contains a cycle")
        remaining = {key: parents - ready for key, parents in remaining.items() if key not in ready}


def project(events: Iterable[Decision], target: Target) -> Projection:
    history = validate_history(events)
    relevant = {key: event for key, event in history.items() if event.target == target}
    consumed = {prior for event in relevant.values() for prior in event.predecessors}
    heads = tuple(sorted(relevant.keys() - consumed))
    if not heads:
        return Projection(state="unreviewed")
    if len(heads) > 1:
        return Projection(state="conflict", heads=heads)
    event = relevant[heads[0]]
    if event.outcome in {"accept", "supersede"}:
        return Projection(
            state="accepted",
            heads=heads,
            stamp=Stamp(
                human_verified_at=event.performed_at,
                human_verified_by=event.reviewer,
                human_verification_decision_id=event.decision_id,
            ),
        )
    if event.outcome == "reject":
        return Projection(state="rejected", heads=heads)
    return Projection(state="revoked", heads=heads)
