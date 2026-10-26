# PREREGISTRATION — permission-to-retry (project #81)

**Paper:** arXiv 2610.31916, "Permission to Retry: A Study of Authorization and
Recovery in AI Agent Workflows" (Deekshith Marla, Kushagra Bhatnagar).
**Replication type:** open re-implementation of the paper's conformance design, NOT
a re-run of the authors' code (no author code exists: G1 verified 2026-10-26 —
arXiv abs page carries zero code links; authenticated GitHub repo search for the
exact title returns 0; distinctive-phrase code searches return only generic word
matches / unrelated tooling).
**Frozen:** 2026-10-26, before the full campaign run. Bars below are fixed;
if measured numbers miss them, the gate verdict is KILL, not a revised bar.

## 1. Claim under test

A durable agent resuming a consequential action while its authority changes must
satisfy four distinct obligations that naive retry logic conflates:

1. **Checkpoint state** — resume from the recorded checkpoint, not from a stale cache.
2. **Permission to dispatch** — any (re)dispatch requires *current* authority.
3. **Evidence of an external effect** — completion requires ledger evidence of the effect.
4. **Permission to reconcile** — marking an action complete/settled requires current
   reconcile permission.

Outcomes are scored against a **provider effect ledger hidden from the recovering
application**. The study isolates recovery decisions from LM behavior: **zero LLM,
fully deterministic, CPU only, $0**.

## 2. Harness (G0)

- **Provider effect ledger** (hidden): ground truth per action — effect EFFECTED /
  NOT_EFFECTED / INCONCLUSIVE (ambiguous contract, effect unqueryable). Strategies
  other than retained-ledger reconciliation never see it.
- **Provider contracts (3):** IDEMPOTENT (same key → same effect), NON_IDEMPOTENT
  (key ignored → re-dispatch fires a second effect), AMBIGUOUS (dispatch may have
  effected despite a lost ack; re-dispatch may double-fire; effect queryable or not).
- **Hosts (2):** LangGraph-style (checkpoint-restore resume) and Temporal-style
  (replay-based resume). Different resume mechanics, same strategy evaluation.
  Paper property to reproduce: **identical checked outcomes across hosts**.
- **Strategies (4):** cached-retry (naive: replays cached request, no authority check,
  no ledger query, fresh key), revalidation-before-retry (checks current dispatch
  authority; holds as UNKNOWN rather than retrying an unknowable action; otherwise
  replays like cached), stable-key retry (same idempotency key, no authority check,
  no ledger query), retained-ledger reconciliation (checks checkpoint + current
  authority + ledger evidence + reconcile permission; never re-dispatches an effected
  action; never completes without evidence; retains reservations).
- **Violation taxonomy:** UNAUTHORIZED_DISPATCH, DOUBLE_FIRE, SILENT_COMPLETION
  (completion without evidence/permission), DROPPED_OBLIGATION (unknown resolved as
  done or discarded without a retained reservation).

## 3. Campaign (prospectively fixed)

- **42 histories per host** = 14 schedules × 3 provider contracts, one matched
  application-policy slice (the paper's full per-host campaign is 42 × 4 policies =
  168; this replication runs the 42-history slice per host, 84 runs total).
- **14 schedules:** crash before dispatch / after dispatch with ack lost / after ack
  before checkpoint / after checkpoint before reconcile / after reconcile before
  settle / mid-dispatch with uncertain effect / resume after a provider-side denial /
  resume with a stale checkpoint (key lost) — each crossed with authority
  stable-granted vs revoked-at-resume where applicable.
- **Oracle outcome mix per host (paper):** 21 checked COMPLETED, 15 DENIED,
  6 UNKNOWN_WITH_RESERVATION.
- **Paper-calibrated targets:** retained-ledger 42/42; cached-retry 30/42;
  revalidation-before-retry 36/42; stable-key retry 31/42.
- **Mechanism note (derived from the paper's numbers, stated before the run):**
  naive failures concentrate on evidence/uncertainty cases (re-dispatch double-fires
  and unknowable effects); in-campaign denials are enforced at the provider layer,
  so every strategy passes them. Authority-change *sensitivity* is therefore proven
  by a separate G3 probe, not by the campaign counts.

## 4. Kill gates (fixed bars, no bar-moving)

- **G0:** fake-ledger + host harness runs on CPU, deterministic, zero LLM.
- **G1:** author-code recheck at dispatch (abs links + authenticated GitHub
  repo/code search). Official author code found → STOP, write KILLED.md.
- **G2:** on matched histories, naive cached retry passes **≤36/42** AND
  retained-ledger reconciliation passes **42/42** (paper: 30/42 vs 42/42).
  Otherwise KILL with an honest negative writeup.
- **G3 (authority-change probe, separate from campaign counts):** flipping authority
  GRANTED→REVOKED at resume must change the retained-ledger decision
  (COMPLETED→DENIED, or dispatch→denial); the 15 denials and 6 unknowns per host
  must be retained (DENIED / UNKNOWN_WITH_RESERVATION), NEVER silently completed,
  by the retained-ledger strategy; naive strategies must be shown violating on the
  flipped histories (unauthorized dispatch). Otherwise KILL.

## 5. Scope exclusions (stated, not silently dropped)

- The paper's separate 16-case InfinityOS component study exercises proprietary
  enterprise-platform code over repository fakes; it is NOT replicated here
  (no such code is available, and inventing it would be fabrication).
- No real LangGraph/Temporal runtimes are used; hosts are faithful fake
  implementations of their resume mechanics (checkpoint-restore vs replay).
  The claim under test is the recovery-decision logic, which the paper itself
  isolates from runtime and LM behavior.

## 6. Ship criteria (all must hold)

Tests green; seed-rerun determinism check (identical result hash across runs);
README + PAPER.md with measured numbers only; LinkedIn draft; staged payload
under repo_staging/ (no push — parent flow creates the repo via browser).
