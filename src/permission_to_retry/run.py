"""Campaign runner: executes all strategies on all histories on both hosts,
writes results JSON + summary, and prints the gate scoreboard."""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from permission_to_retry.campaign import build_campaign  # noqa: E402
from permission_to_retry.hosts import LangGraphHost, TemporalHost  # noqa: E402
from permission_to_retry.model import Outcome, StrategyResult  # noqa: E402
from permission_to_retry.strategies import STRATEGIES  # noqa: E402

HOSTS = [LangGraphHost(), TemporalHost()]
ROOT = Path(__file__).resolve().parent.parent.parent


def run_campaign():
    histories = build_campaign()
    results = []
    host_states = {}
    for host in HOSTS:
        for h in histories:
            state = host.resume(h)
            host_states[(host.name, h.hid)] = state.checkpoint.value
            for name, fn in STRATEGIES.items():
                outcome = fn(state)
                results.append(StrategyResult(
                    history_id=h.hid, strategy=name, host=host.name,
                    outcome=outcome, passed=(outcome == h.expected)))
    return histories, results, host_states


def summarize(histories, results):
    by_host_strategy = {}
    for r in results:
        by_host_strategy.setdefault((r.host, r.strategy), []).append(r)
    scores = {}
    for (host, strat), rs in sorted(by_host_strategy.items()):
        scores[f"{host}/{strat}"] = {
            "passed": sum(1 for r in rs if r.passed),
            "total": len(rs),
            "violations": Counter(
                r.outcome.value for r in rs if not r.passed),
        }
    oracle = Counter(h.expected.value for h in histories)
    # Paired-cell property: identical outcomes across hosts per history+strategy.
    paired_identical = True
    for h in histories:
        for strat in STRATEGIES:
            outs = {r.outcome for r in results
                    if r.history_id == h.hid and r.strategy == strat}
            if len(outs) != 1:
                paired_identical = False
    ledger_violations = [r for r in results
                         if r.strategy == "retained-ledger-reconciliation"
                         and not r.passed]
    return {
        "histories_per_host": len(histories),
        "oracle_mix_per_host": dict(oracle),
        "scores": {k: {"passed": v["passed"], "total": v["total"],
                        "violations": dict(v["violations"])}
                   for k, v in scores.items()},
        "paired_cells_identical_across_hosts": paired_identical,
        "ledger_violations": len(ledger_violations),
    }


def main() -> int:
    histories, results, host_states = run_campaign()
    summary = summarize(histories, results)
    payload = {
        "summary": summary,
        "results": [{"history": r.history_id, "strategy": r.strategy,
                     "host": r.host, "outcome": r.outcome.value,
                     "passed": r.passed} for r in results],
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    digest = hashlib.sha256(blob).hexdigest()
    outdir = ROOT / "results"
    outdir.mkdir(exist_ok=True)
    (outdir / "campaign.json").write_text(json.dumps(payload, indent=1))
    (outdir / "campaign.sha256").write_text(digest + "\n")
    print(json.dumps(summary, indent=1))
    print("digest:", digest)
    # Gate scoreboard.
    for host in ("langgraph", "temporal"):
        for strat in STRATEGIES:
            s = summary["scores"][f"{host}/{strat}"]
            print(f"GATE {host}/{strat}: {s['passed']}/{s['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
