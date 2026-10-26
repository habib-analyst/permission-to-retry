"""The four recovery strategies.

Each strategy sees only what it is entitled to see:
- naive strategies never see the ledger and never check current authority
  (except revalidation, which checks dispatch authority only);
- retained-ledger reconciliation sees the ledger (when the provider exposes a
  query) plus current authority and reconcile permission, and never
  re-dispatches an action the ledger shows as effected.
"""

from .model import (
    Authority,
    Checkpoint,
    Contract,
    EffectTruth,
    History,
    Outcome,
    ResumeState,
)


def _dispatch_attempt(state: ResumeState, key: str) -> Outcome:
    """Outcome of a (re)dispatch against the hidden provider truth."""
    h = state.history
    if h.provider_enforces and h.authority == Authority.REVOKED:
        return Outcome.DENIED  # provider itself refuses
    if state.checkpoint == Checkpoint.DISPATCHED_UNKNOWN:
        if h.effect == EffectTruth.EFFECTED:
            # Re-dispatching an already-effected action double-fires unless
            # the provider is idempotent AND the original key is presented.
            if h.contract == Contract.IDEMPOTENT and key == "original":
                return Outcome.COMPLETED
            return Outcome.DOUBLE_FIRE
        # Nothing was effected: a fresh dispatch is legitimate.
        return Outcome.COMPLETED
    # Not dispatched before: a fresh dispatch is legitimate.
    return Outcome.COMPLETED


def cached_retry(state: ResumeState) -> Outcome:
    """Naive cached retry: replays the cached request, no authority check,
    no ledger query. The cache loses the original key unless retained."""
    h = state.history
    if h.provider_enforces and h.authority == Authority.REVOKED:
        return Outcome.DENIED
    if not h.ledger_queryable and state.checkpoint == Checkpoint.DISPATCHED_UNKNOWN:
        # Effect unknowable: completing anyway is a silent completion.
        return Outcome.SILENT_COMPLETION
    if state.checkpoint == Checkpoint.DISPATCHED_ACKED:
        return Outcome.COMPLETED
    key = "original" if state.key_available else "fresh"
    return _dispatch_attempt(state, key)


def revalidation_before_retry(state: ResumeState) -> Outcome:
    """Revalidates current dispatch authority; holds (rather than retries)
    when the effect is unknowable; otherwise replays like cached retry."""
    h = state.history
    if h.authority == Authority.REVOKED:
        return Outcome.DENIED
    if not h.ledger_queryable and state.checkpoint == Checkpoint.DISPATCHED_UNKNOWN:
        return Outcome.UNKNOWN_RESERVED  # conservative hold, reservation kept
    if state.checkpoint == Checkpoint.DISPATCHED_ACKED:
        return Outcome.COMPLETED
    key = "original" if state.key_available else "fresh"
    return _dispatch_attempt(state, key)


def stable_key_retry(state: ResumeState) -> Outcome:
    """Retries with the same idempotency key re-derived from the action id.
    No authority check, no ledger query. Safe on idempotent providers only."""
    h = state.history
    if h.provider_enforces and h.authority == Authority.REVOKED:
        return Outcome.DENIED
    if not h.ledger_queryable and state.checkpoint == Checkpoint.DISPATCHED_UNKNOWN:
        return Outcome.SILENT_COMPLETION
    if state.checkpoint == Checkpoint.DISPATCHED_ACKED:
        return Outcome.COMPLETED
    return _dispatch_attempt(state, "original")


def retained_ledger_reconciliation(state: ResumeState) -> Outcome:
    """The four-obligation protocol: checkpoint state + current dispatch
    authority + ledger evidence of effect + permission to reconcile."""
    h = state.history
    # Obligation 2: permission to dispatch (current authority).
    if h.authority == Authority.REVOKED:
        return Outcome.DENIED
    # Obligation 3: evidence of an external effect (ledger, when queryable).
    if not h.ledger_queryable:
        # Obligation 4 cannot be satisfied on unknown evidence: retain.
        return Outcome.UNKNOWN_RESERVED
    if h.effect == EffectTruth.EFFECTED:
        # Obligation 4: permission to reconcile/settle.
        if h.reconcile == Authority.GRANTED:
            return Outcome.COMPLETED  # checked completion, no re-dispatch
        return Outcome.DENIED
    # Nothing effected and dispatch is permitted: dispatch fresh, checked.
    return Outcome.COMPLETED


STRATEGIES = {
    "cached-retry": cached_retry,
    "revalidation-before-retry": revalidation_before_retry,
    "stable-key-retry": stable_key_retry,
    "retained-ledger-reconciliation": retained_ledger_reconciliation,
}
