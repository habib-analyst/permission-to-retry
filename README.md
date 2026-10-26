# permission-to-retry

**Open replication of arXiv 2610.31916, "Permission to Retry: A Study of
Authorization and Recovery in AI Agent Workflows" (Deekshith Marla, Kushagra
Bhatnagar).**

## One line

Your agent's retry button is an authorization decision: naive retries silently
complete, double-fire, or drop obligations that a ledger-checked retry keeps.

## The four obligations

A durable agent resuming a consequential action while its authority changes must
separately satisfy: (1) checkpoint state, (2) permission to dispatch,
(3) evidence of an external effect, and (4) permission to reconcile. Outcomes are
scored against a provider effect ledger hidden from the recovering application.

## What this is (and is not)

- **Deterministic, zero LLM, CPU only, $0.** The paper explicitly isolates
  recovery decisions from language-model behavior, so this replication needs no
  model at all: a scripted provider-effect ledger, two fake hosts
  (LangGraph-style checkpoint-restore, Temporal-style replay), and four retry
  strategies.
- **Not the authors' code.** No official author code exists (verified 2026-10-26:
  arXiv abs page carries zero code links; authenticated GitHub repo search for
  the exact title returns 0). This is an independent re-implementation of the
  paper's conformance design, calibrated to its published bars.
- **Scope note.** The paper's separate 16-case InfinityOS component study
  exercises proprietary enterprise-platform code and is not replicated here.

## Measured results (frozen campaign: 42 histories/host = 14 schedules x 3 contracts)

| Strategy | LangGraph-style host | Temporal-style host | Paper |
|---|---|---|---|
| Retained-ledger reconciliation | **42/42** | **42/42** | 42/42 |
| Cached retry (naive) | 30/42 | 30/42 | 30/42 |
| Revalidation before retry | 36/42 | 36/42 | 36/42 |
| Stable-key retry | 31/42 | 31/42 | 31/42 |

Oracle mix per host: 21 checked completions, 15 denials, 6 unknown outcomes with
reservations retained. Checked outcomes are identical across hosts (the paper's
paired-cell property). Naive failures: cached retry double-fires 6x and silently
completes 6x; stable-key retry double-fires 5x and silently completes 6x;
revalidation fails only on 6 double-fires (it holds, rather than retries, when
an effect is unknowable).

## The artifact: the four-obligation conformance protocol

`src/permission_to_retry/strategies.py::retained_ledger_reconciliation` is the
reference implementation. Its rule, in order:

1. Current dispatch authority revoked -> **DENIED** (never dispatch).
2. Provider exposes no effect query -> **UNKNOWN_RESERVED** (retain the
   reservation; never silently complete).
3. Ledger confirms the effect and reconcile permission is held ->
   **COMPLETED** (checked, no re-dispatch, no double-fire).
4. Ledger confirms nothing was effected and dispatch is permitted -> dispatch
   fresh and complete checked.

## Run it

```bash
python3 src/permission_to_retry/run.py     # full campaign, writes results/
python3 -m pytest tests/ -q               # 10 tests: gates, hosts, G3 probe
```

Re-running the campaign reproduces the identical result digest
(`a267801e9951972998fe80a472b2a239d6e615b8c6fae623b6dfbc168df6feed`).

## Layout

- `src/permission_to_retry/model.py` — types: contracts, authority, checkpoint, ledger truth, outcomes
- `src/permission_to_retry/campaign.py` — the frozen 42-history campaign
- `src/permission_to_retry/hosts.py` — LangGraph-style / Temporal-style fake hosts
- `src/permission_to_retry/strategies.py` — the four retry strategies
- `src/permission_to_retry/run.py` — campaign runner + gate scoreboard
- `tests/test_campaign.py` — gate tests incl. the G3 authority-flip probe
- `PREREG.md` — preregistration, locked before the full run
- `results/campaign.json` — all 336 scored strategy/host/history outcomes (84 histories x 4 strategies)
