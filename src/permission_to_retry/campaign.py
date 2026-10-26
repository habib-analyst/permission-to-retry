"""The frozen 42-history campaign: 14 schedules x 3 provider contracts.

Families (cell counts sum to 42 per host):
- denial (provider-enforced): 5 schedules x 3 contracts = 15 -> DENIED
- unknown (provider exposes no effect query): 2 schedules x 3 = 6 -> UNKNOWN_RESERVED
- evidence, key retained: 2 schedules -> IDEMPOTENT pass, NON_IDEMPOTENT and
  AMBIGUOUS double-fire (T2=3, T3=2 after the key-lost schedule below)
- evidence, key lost: 1 schedule -> IDEMPOTENT key-lost (T12=1),
  NON_IDEMPOTENT double-fire (T2 total 3), AMBIGUOUS not-effected (all pass)
- all-pass completions: 4 fresh/acked schedules x 3 = 12, plus the 3
  idempotent/ambiguous pass cells above = 15 pass cells

Oracle mix per host: 21 COMPLETED, 15 DENIED, 6 UNKNOWN_RESERVED.
"""

from .model import (
    Authority,
    Checkpoint,
    Contract,
    EffectTruth,
    History,
    Outcome,
)

G = Authority.GRANTED
R = Authority.REVOKED


def _schedule_specs():
    """Return {schedule_id: (desc, base-kwargs)}; contract fills the rest."""
    return {
        # --- denial family: provider enforces, nothing effected ---
        "S01": ("crash before dispatch; authority revoked at resume; "
                "provider rejects the dispatch",
                dict(authority=R, reconcile=R, checkpoint=Checkpoint.NOT_DISPATCHED,
                     effect=EffectTruth.NOT_EFFECTED, ledger_queryable=True,
                     provider_enforces=True, key_retained=True,
                     expected=Outcome.DENIED, family="denial")),
        "S02": ("crash after dispatch, ack lost; authority revoked; "
                "provider had rejected the dispatch",
                dict(authority=R, reconcile=R, checkpoint=Checkpoint.DISPATCHED_UNKNOWN,
                     effect=EffectTruth.NOT_EFFECTED, ledger_queryable=True,
                     provider_enforces=True, key_retained=True,
                     expected=Outcome.DENIED, family="denial")),
        "S03": ("crash after ack, before checkpoint; authority revoked; "
                "provider had rejected the dispatch",
                dict(authority=R, reconcile=R, checkpoint=Checkpoint.DISPATCHED_UNKNOWN,
                     effect=EffectTruth.NOT_EFFECTED, ledger_queryable=True,
                     provider_enforces=True, key_retained=True,
                     expected=Outcome.DENIED, family="denial")),
        "S04": ("crash after checkpoint, before reconcile; authority revoked; "
                "denial receipt acked",
                dict(authority=R, reconcile=R, checkpoint=Checkpoint.DISPATCHED_ACKED,
                     effect=EffectTruth.NOT_EFFECTED, ledger_queryable=True,
                     provider_enforces=True, key_retained=True,
                     expected=Outcome.DENIED, family="denial")),
        "S05": ("resume after a provider-side denial is recorded; "
                "authority revoked",
                dict(authority=R, reconcile=R, checkpoint=Checkpoint.NOT_DISPATCHED,
                     effect=EffectTruth.NOT_EFFECTED, ledger_queryable=True,
                     provider_enforces=True, key_retained=True,
                     expected=Outcome.DENIED, family="denial")),
        # --- unknown family: provider exposes no effect query ---
        "S06": ("crash mid-dispatch, effect uncertain; provider exposes no "
                "effect query; authority granted",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.DISPATCHED_UNKNOWN,
                     effect=EffectTruth.INCONCLUSIVE, ledger_queryable=False,
                     provider_enforces=False, key_retained=True,
                     expected=Outcome.UNKNOWN_RESERVED, family="unknown")),
        "S07": ("crash after dispatch, ack lost, effect uncertain; provider "
                "exposes no effect query; authority granted",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.DISPATCHED_UNKNOWN,
                     effect=EffectTruth.INCONCLUSIVE, ledger_queryable=False,
                     provider_enforces=False, key_retained=True,
                     expected=Outcome.UNKNOWN_RESERVED, family="unknown")),
        # --- evidence family, key retained: re-dispatch double-fires unless
        # the provider is idempotent and sees the original key ---
        "S08": ("crash after dispatch, ack lost; action effected; key "
                "retained; authority granted",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.DISPATCHED_UNKNOWN,
                     effect=EffectTruth.EFFECTED, ledger_queryable=True,
                     provider_enforces=False, key_retained=True,
                     expected=Outcome.COMPLETED, family="evidence")),
        "S09": ("crash after ack, before checkpoint; action effected; key "
                "retained; authority granted",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.DISPATCHED_UNKNOWN,
                     effect=EffectTruth.EFFECTED, ledger_queryable=True,
                     provider_enforces=False, key_retained=True,
                     expected=Outcome.COMPLETED, family="evidence")),
        # --- evidence family, key lost: cached/revalidation replays a fresh
        # key and double-fires even on an idempotent provider; stable-key
        # re-derives the original key and is safe there ---
        "S10": ("crash after checkpoint, before reconcile; action effected; "
                "cache lost the key; authority granted",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.DISPATCHED_UNKNOWN,
                     effect=EffectTruth.EFFECTED, ledger_queryable=True,
                     provider_enforces=False, key_retained=False,
                     expected=Outcome.COMPLETED, family="keylost")),
        # --- all-pass completion family ---
        "S11": ("crash before dispatch; nothing effected; authority granted",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.NOT_DISPATCHED,
                     effect=EffectTruth.NOT_EFFECTED, ledger_queryable=True,
                     provider_enforces=False, key_retained=True,
                     expected=Outcome.COMPLETED, family="pass")),
        "S12": ("crash after reconcile, before settle; action effected and "
                "acked; reconcile permission held",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.DISPATCHED_ACKED,
                     effect=EffectTruth.EFFECTED, ledger_queryable=True,
                     provider_enforces=False, key_retained=True,
                     expected=Outcome.COMPLETED, family="pass")),
        "S13": ("crash mid-dispatch; nothing effected; ledger confirms; "
                "authority granted",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.DISPATCHED_UNKNOWN,
                     effect=EffectTruth.NOT_EFFECTED, ledger_queryable=True,
                     provider_enforces=False, key_retained=True,
                     expected=Outcome.COMPLETED, family="pass")),
        "S14": ("crash before dispatch; nothing effected; reservation "
                "requirement satisfied; authority granted",
                dict(authority=G, reconcile=G, checkpoint=Checkpoint.NOT_DISPATCHED,
                     effect=EffectTruth.NOT_EFFECTED, ledger_queryable=True,
                     provider_enforces=False, key_retained=True,
                     expected=Outcome.COMPLETED, family="pass")),
    }


def build_campaign():
    """All 42 histories: 14 schedules x 3 contracts, deterministic order."""
    histories = []
    for sid, (desc, base) in _schedule_specs().items():
        for contract in Contract:
            kwargs = dict(base)
            # S10's AMBIGUOUS cell: the provider never effected the action
            # (dispatch crashed before effecting); the ledger confirms it,
            # so a re-dispatch is a legitimate fresh dispatch for everyone.
            if sid == "S10" and contract == Contract.AMBIGUOUS:
                kwargs["effect"] = EffectTruth.NOT_EFFECTED
                kwargs["family"] = "pass"
            histories.append(History(
                hid=f"{sid}-{contract.name}",
                schedule=sid, schedule_desc=desc, contract=contract, **kwargs))
    return histories
