"""Tests for the permission-to-retry conformance harness.

Gate mapping: G2 = campaign scores; G3 = authority-change probe + retention.
All numbers here are measured from the harness, not asserted from the paper
except where the test name says 'paper-calibrated' (the frozen PREREG bar).
"""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from permission_to_retry.campaign import build_campaign  # noqa: E402
from permission_to_retry.hosts import LangGraphHost, TemporalHost  # noqa: E402
from permission_to_retry.model import Authority, Outcome  # noqa: E402
from permission_to_retry.run import run_campaign, summarize  # noqa: E402
from permission_to_retry.strategies import STRATEGIES  # noqa: E402


def _outcomes():
    histories, results, _ = run_campaign()
    return histories, results


def test_campaign_shape():
    histories, _ = _outcomes()
    assert len(histories) == 42  # 14 schedules x 3 contracts
    assert len({h.hid for h in histories}) == 42


def test_oracle_mix_per_host_paper_calibrated():
    histories, _ = _outcomes()
    mix = {}
    for h in histories:
        mix[h.expected.value] = mix.get(h.expected.value, 0) + 1
    assert mix == {"completed": 21, "denied": 15, "unknown-reserved": 6}


def test_scores_paper_calibrated_g2():
    histories, results = _outcomes()
    summary = summarize(histories, results)
    for host in ("langgraph", "temporal"):
        s = summary["scores"]
        assert s[f"{host}/cached-retry"]["passed"] == 30
        assert s[f"{host}/revalidation-before-retry"]["passed"] == 36
        assert s[f"{host}/stable-key-retry"]["passed"] == 31
        assert s[f"{host}/retained-ledger-reconciliation"]["passed"] == 42


def test_g2_gate_inequality():
    # The kill-gate itself: cached <= 36/42 AND ledger == 42/42.
    histories, results = _outcomes()
    summary = summarize(histories, results)
    for host in ("langgraph", "temporal"):
        assert summary["scores"][f"{host}/cached-retry"]["passed"] <= 36
        assert summary["scores"][f"{host}/retained-ledger-reconciliation"]["passed"] == 42


def test_paired_cells_identical_across_hosts():
    histories, results = _outcomes()
    summary = summarize(histories, results)
    assert summary["paired_cells_identical_across_hosts"] is True


def test_host_resume_states_equal():
    histories, _ = _outcomes()
    lg, tp = LangGraphHost(), TemporalHost()
    for h in histories:
        assert lg.resume(h).checkpoint == tp.resume(h).checkpoint
        assert lg.resume(h).key_available == tp.resume(h).key_available


def test_ledger_never_violates():
    _, results = _outcomes()
    for r in results:
        if r.strategy == "retained-ledger-reconciliation":
            assert r.passed
            assert r.outcome not in (
                Outcome.UNAUTHORIZED_DISPATCH, Outcome.DOUBLE_FIRE,
                Outcome.SILENT_COMPLETION, Outcome.DROPPED_OBLIGATION)


def test_g3_denials_and_unknowns_retained_by_ledger():
    histories, results = _outcomes()
    by_id = {(r.host, r.history_id): r for r in results
             if r.strategy == "retained-ledger-reconciliation"}
    for h in histories:
        for host in ("langgraph", "temporal"):
            r = by_id[(host, h.hid)]
            if h.expected == Outcome.DENIED:
                assert r.outcome == Outcome.DENIED, h.hid
            if h.expected == Outcome.UNKNOWN_RESERVED:
                assert r.outcome == Outcome.UNKNOWN_RESERVED, h.hid
            assert r.outcome != Outcome.SILENT_COMPLETION


def test_g3_authority_flip_changes_ledger_decision():
    """Flip GRANTED->REVOKED at resume (provider NOT enforcing, so any
    dispatch is the app's own decision). The ledger strategy must switch to
    DENIED; naive cached/stable-key retries must fail to deny (they dispatch
    or complete anyway), proving decisions track permission state."""
    histories, _ = _outcomes()
    ledger = STRATEGIES["retained-ledger-reconciliation"]
    cached = STRATEGIES["cached-retry"]
    stable = STRATEGIES["stable-key-retry"]
    lg = LangGraphHost()
    flipped = 0
    naive_failed_to_deny = 0
    for h in histories:
        if h.expected != Outcome.COMPLETED or h.authority != Authority.GRANTED:
            continue
        flipped_h = replace(h, authority=Authority.REVOKED,
                            provider_enforces=False)
        state = lg.resume(flipped_h)
        assert ledger(state) == Outcome.DENIED, h.hid
        flipped += 1
        if cached(state) != Outcome.DENIED or stable(state) != Outcome.DENIED:
            naive_failed_to_deny += 1
    assert flipped == 21
    assert naive_failed_to_deny == 21  # naive strategies never deny on flip


def test_determinism_same_digest_twice():
    _, results1 = _outcomes()
    _, results2 = _outcomes()
    key = lambda r: (r.host, r.history_id, r.strategy, r.outcome.value)
    assert sorted(map(key, results1)) == sorted(map(key, results2))
