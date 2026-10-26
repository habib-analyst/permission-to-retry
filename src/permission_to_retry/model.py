"""Core types for the permission-to-retry conformance harness."""

from dataclasses import dataclass, field
from enum import Enum


class Contract(str, Enum):
    IDEMPOTENT = "idempotent"        # same key -> same effect, no double-fire
    NON_IDEMPOTENT = "non-idempotent"  # key ignored, re-dispatch fires again
    AMBIGUOUS = "ambiguous"          # dispatch may have effected despite lost ack


class Authority(str, Enum):
    GRANTED = "granted"
    REVOKED = "revoked"


class Checkpoint(str, Enum):
    NOT_DISPATCHED = "not-dispatched"
    DISPATCHED_UNKNOWN = "dispatched-unknown"  # dispatched, outcome unconfirmed
    DISPATCHED_ACKED = "dispatched-acked"      # dispatched, ack recorded


class EffectTruth(str, Enum):
    EFFECTED = "effected"
    NOT_EFFECTED = "not-effected"
    INCONCLUSIVE = "inconclusive"  # provider exposes no effect query


class Outcome(str, Enum):
    COMPLETED = "completed"                  # checked completion
    DENIED = "denied"                        # permission refused, denial retained
    UNKNOWN_RESERVED = "unknown-reserved"   # unknown, reservation retained
    # Violations (never a correct outcome):
    UNAUTHORIZED_DISPATCH = "unauthorized-dispatch"
    DOUBLE_FIRE = "double-fire"
    SILENT_COMPLETION = "silent-completion"  # completed without evidence/permission
    DROPPED_OBLIGATION = "dropped-obligation"


VIOLATIONS = {
    Outcome.UNAUTHORIZED_DISPATCH,
    Outcome.DOUBLE_FIRE,
    Outcome.SILENT_COMPLETION,
    Outcome.DROPPED_OBLIGATION,
}


@dataclass(frozen=True)
class History:
    """One frozen campaign history: a resume situation for one action."""

    hid: str                      # e.g. "S08-IDEMPOTENT"
    schedule: str                 # schedule id, e.g. "S08"
    schedule_desc: str
    contract: Contract
    authority: Authority          # current authority at resume
    reconcile: Authority          # current permission to reconcile/settle
    checkpoint: Checkpoint
    effect: EffectTruth            # hidden ledger truth (never shown to naive strategies)
    ledger_queryable: bool        # whether the provider exposes an effect query
    provider_enforces: bool       # provider itself rejects dispatch when revoked
    key_retained: bool            # whether the cached request kept its original key
    expected: Outcome             # conformance oracle outcome
    family: str                   # design family (denial/unknown/evidence/keylost/pass)


@dataclass
class ResumeState:
    """What a host reconstructs at resume; identical across host mechanics."""

    history: History
    checkpoint: Checkpoint
    key_available: bool = field(init=False)

    def __post_init__(self) -> None:
        self.key_available = self.history.key_retained


@dataclass(frozen=True)
class StrategyResult:
    history_id: str
    strategy: str
    host: str
    outcome: Outcome
    passed: bool
