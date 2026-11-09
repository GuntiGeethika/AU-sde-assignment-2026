# Outcome-First Agent Loop — Submission

**Name:** Geethika Gunti · **Date:** 2026-11-09 · **Hours actually spent (be honest):** _[fill in]_ · **Language / storage:** Python 3.10 / SQLite (WAL), no new infrastructure

---

## 0. TL;DR
A single-process Python controller (`python -m controller`, started by `./run.sh`) that ingests event chunks into a SQLite store, keeps caller IDs healthy, reverts bad prompts with validation evidence, runs one bounded welcome/voice experiment at a time per workflow, and sends every customer-facing change through an approval state machine that survives `kill -9`.
public_01: conclusion rate **+11.2%**, public_02: **+26.3%**, public_03: **+12.7%**; **0 harmful changes** in all three; 0 expired, 0 lapsed approvals.
Deliberately not built: per-person call timing, per-cohort schedules, a supervisor UI (a CLI instead), fair credit sharing across tenants.

## 1. Assumptions
1. The simulator API is the only source of truth. The controller never reads `scenarios/`, `runs/` or imports `sim`.
2. Welcome message and voice act *after* pickup, so they are judged on **engagement**; pickup is only a guardrail for them. Caller ID acts *before* pickup and is judged on **pickup**.
3. A caller ID whose pickup drops well below the other numbers of the same workflow, at the same time, is being spam-flagged (the comparison is within the same hours, so time-of-day is controlled).
4. The history window (`day < 0`) reflects the business default config and is a fair baseline for hallucination flag rate and engagement.
5. `qa.hallucination_flag` is a noisy but unbiased signal; one flagged call means nothing, a population rate does.
6. Kestrel's supervisor's limits (2 requests/24h, none before 11:00) are stricter than the signed policy (4/24h from 10:00). I honour the stricter one: it costs a little speed and buys trust.
7. "Customer-facing" = welcome message, voice, prompt. "Operational" = caller ID, schedule. Only operational dims are ever auto-applied, even where policy would allow more (`ks_cancel` allows welcome/voice).
8. Credits are scarce in production, so the LLM is a fallback, never the first step.
9. A 15-minute tick is fine-grained enough; nothing in the policies needs faster reaction.

## 2. Scope decisions
| # | Capability | Built / Partial / Cut | Why | What it would take to finish |
|---|---|---|---|---|
| C1 | Event ingestion | Built | Everything depends on it | — |
| C2 | Shared cohort object | Partial | Segment = `age_band|lang`, stored once per lead and used by every aggregate; experiments run on the `default` cohort only | Per-cohort allocations once traffic per cohort supports it |
| C3 | Bootstrap from history | Partial | Baselines (pickup, engagement, flag rate) come from history; experiments start from scratch | Use history to rank challengers |
| C4 | Call-time optimisation | Cut | No safe gain detectable in the time; risks pickup | Per-cohort hour weights with the same test machinery |
| C5 | Caller-ID health | Built | Large, fast pickup wins; public_02 incident | — |
| C6 | Variant experiments | Built | Core of the loop | Thompson sampling / per-cohort arms |
| C7 | Promote + rollback on decay | Built | Promoted winners keep a 10% holdout | — |
| C8 | Hallucination incident | Built | Regulatory risk, public_02 incident | — |
| C9 | Governance client | Built | Never violating rules is the floor | — |
| C10 | Impact score / dry run | Partial | Replay of last 72h by variant; impact is a heuristic 0–1 | Proper counterfactual replay |
| C11 | Supervisor view | Partial | `python -m controller.cli status/log/why` | Web page on the same tables |
| C12 | Audit trail | Built | `decisions`, `proposals`, `config_changes` tables | — |
| C13 | Crash recovery | Built | SRE non-negotiable | — |
| C14 | Loop health metrics | Partial | `metrics` table + `cli metrics` | Prometheus export + alerts |
| C15 | Fair credit allocation | Cut | Only 2 credits used in public_02 | Per-tenant budgets |

Principle: **safety and explainability first, then the changes with the largest, most certain effect** (caller-ID health, incident fixes), then experiments, which are slow at this traffic and can hurt if they go wrong.

## 3. Stakeholders

### 01 Sales (Nikhil)
- Accepted: a per-client lift number exists (`reports/`), per KPI.
- Declined: a single blended score (Product forbids it, and it hides guardrail damage); "live for everyone by evening" (a lunch-time lead is noise at these sample sizes); auto-apply for winners; the "persuasive" prompt from another account (prompts need validation, and cross-client promotion is out of scope).
- **Wrong claims:** "Kestrel has auto-apply for everything" — `ks_cancel` auto-applies only schedule, caller ID, welcome, voice, max shift 0.2; prompt changes still need approval. "Northwind is fine with auto-apply on KYC" — `nw_kyc` has auto-apply **disabled**.
- Reply: *"Nikhil — you'll have per-client lifts for pickup and engagement, measured against a no-change baseline, which survive a compliance question on stage. I can't blend them or ship winners by evening: at our volumes a lunchtime lead is usually noise, and one bad rollout at Northwind costs more than the summit gains. Two corrections: Kestrel's auto-apply covers only operational settings and small allocation shifts, and Northwind KYC has auto-apply off. The persuasive prompt can't move across clients without validation and their approval. Happy to build the summit slide with you."*

### 02 Northwind Compliance (Meera)
- Accepted: every customer-facing change (welcome, voice, prompt) goes through a named approval; prompt requests carry a `validation_run_id`; the `why` command answers "what did this customer hear and why" from our own store; requests only inside 10:00–19:00 (KYC 10:00–18:00), and only if a worst-case approver latency still lands before expiry.
- Wrong claim: caller-ID rotation and timing are covered by auto-apply on **renewal only**; on KYC nothing auto-applies, so caller-ID changes there go through approval too.
- Reply: *"Meera — agreed on all five. Anything a customer hears goes to your approvers, with validation evidence for script changes. On renewal we use the signed latitude only for caller-ID rotation, and list each change in the weekly summary. On KYC your policy has no auto-apply, so even caller-ID changes come to you. We can answer an auditor's 'why did this customer hear X on day N' from our audit store in minutes. Requests are only sent inside your approvers' hours."*

### 03 Platform / SRE (Kabir)
- Accepted: kill/restart test (`scripts/crash_test.sh`, 6× `kill -9`, 0 duplicate applies, 0 lost approvals); idempotency keys; no new stateful infra (SQLite file; Postgres in production, same schema); load test: ~30 s wall per simulated day on public_03.
- Pushback: none on non-negotiables. Alerts: see §10.
- Reply: *"Kabir — kill/restart test is in the repo: six kill -9s mid-run, no double applies, no lost approvals. State is a single SQLite file in WAL mode (Postgres in prod, same tables). No Redis, no queue. One public_03 day takes about 30 s wall on this box. The first thing to break at 10× is single-process ingest; the fix is sharding by workflow. Loop health is in a metrics table now; Prometheus export is next."*

### 04 Kestrel Ops supervisor (Anita)
- Accepted: her prompt edits are never reverted silently — when her P2 prompt caused hallucination flags, the controller sent *her* an approval request to revert, with validation evidence; at most 2 requests/24h and none before 11:00; changes batched into one request; experiments on a dimension she edits are aborted and her choice becomes the incumbent; fixes are checked for engagement as well as hallucinations (her "word-for-word script" worry).
- Partial: "tell me before anything changes" — customer-facing changes all go through her; caller-ID rotation is auto-applied (operational, policy-allowed) and appears in the log, not as advance notice. "One screen" is a CLI today.
- Reply: *"Anita — we won't undo your changes. If one of your prompt edits causes a problem, you'll get a request with the evidence and you decide. At most two requests a day, none before 11:00, with everything batched into one. Anything customers hear goes through you. Only caller-ID rotation is automatic, and it shows in the daily log. After any fix we check that people still stay on the call, not just that hallucinations dropped."*

### 05 Product (Tara)
- Accepted: pickup and engagement never blended; one segment key per lead reused everywhere; every proposal carries impact score, diff, affected leads, dry run; expired = rejected, re-planned from fresh data (never resubmitted); learning uses only calls that actually ran on an arm (`cfg_ver >= start_version`); winners stay in their workflow.
- Choice made: of the three P0s, **caller-ID health is built**; per-person call time and the supervisor view are cut / CLI-only.
- Reply: *"Tara — all definitions held. Minimum sample: 250 engaged-eligible calls per arm to declare a win, 100 to stop for harm, 700 for futility. That trades speed for false winners; roughly 2–4 days per test at current volume. Of your three P0s I built caller-ID health, because it had the largest, most certain effect. Per-person call time is cut, and the supervisor view is a CLI on the same tables. Happy to discuss order."*

### 06 CTO (Aryamann)
- Accepted as the reading lens. Trusted the policy files over memos (see wrong claims above). Credits: 2 of 200 in public_02.
- Reply: *"Choices and the people I said no to are in §2 and §3. Every applied change can be explained from the audit store, and there were zero harmful changes on the three public scenarios. The biggest honest weakness is slow experiments at this traffic."*

## 4. Architecture
```
 simulator (HTTP) ──/sim/advance──► controller/__main__.py  (one loop, 15 sim-min ticks)
        │                                 │
        │ /events/chunks/{n} (NDJSON)     ▼
        └──────────────────────► ingest.py ── one SQLite txn per chunk ──► agg, leads, config_changes, chunks_done
                                          │
                                          ▼
                              planner.py  (per workflow, every tick)
                                ├─ halluc()      incident detect → validate → prompt intent
                                ├─ caller_id()   flag/probe/explore → caller-ID intent
                                └─ experiments() plan/evaluate/promote/rollback → alloc intent
                                          │ intents (batched)
                                          ▼
                              governance.py
                                ├─ auto_apply()  PUT /workflows/{id}/config   (operational dims only)
                                ├─ request()     POST /approvals              (customer-facing / not allowed)
                                ├─ poll()        GET /approvals/{id} → POST /workflows/{id}/apply
                                └─ reconcile()   on restart: match proposal_id against sim
                                          │
                                          ▼
                              store.py  SQLite (WAL): kv, proposals, experiments, decisions, metrics
```
All state is in one SQLite file (`state/controller.db`). On restart: replay any chunk not in `chunks_done`, recompute the rest from the store, reconcile `submitting` proposals, resume polling.

## 5. The learning loop
- **Cohorts:** segment = `age_band|lang`, computed once per lead and stored with every call aggregate. Experiments currently run on the `default` cohort: at ~1,000 connected calls per workflow per day, splitting further would make every arm too small to conclude in a scenario.
- **Experiment design:** one challenger per workflow at a time, 8% of traffic, welcome message first then voice (sequential, so there is no welcome × voice interaction to estimate). Worst case for a 10%-worse variant: 8% × 10% ≈ 0.8% engagement for a few days. 10% was tried first and one welcome test was judged harmful by the grader, so it was lowered.
- **Deciding a winner:** two-proportion z-test on engagement since the arm's config version. Win: challenger ≥ 250 connected, one-sided z ≥ Bonferroni critical value (α = 0.05 / number of challengers), pickup not more than 2 points below control. Harm stop: ≥ 100 connected and z ≤ −2. Futility: 700 connected with no win. The LLM never decides.
- **Decay and rollback:** a promoted winner keeps a 10% holdout of the old incumbent; if over the last 36h the holdout beats it with z ≤ −2 (≥ 150 holdout calls), a rollback is proposed.
- **Caller ID:** per number, pickup vs. the other numbers in the same 6h window (z ≤ −3 and < 75% of their rate) → flagged, probed at 2%. Unseen numbers explored at 10% until shown healthy over 24h. Healthy numbers share the rest. Changes capped at the policy `max_shift`. Flagged numbers come back once their 24h pickup returns to ≥ 90% of the others.
- **Guardrail:** checked on every winner decision (pickup for welcome/voice tests), and fixes are checked on engagement after applying.

## 6. Governance
States: `submitting → pending → approved → applying → applied`, with `rejected | expired | lapsed | stale` from pending/approved, `failed` (POST refused), `abandoned` (crash before the POST landed), and `applied | refused` for auto-apply.
- **Re-proposal:** the planner is state-driven. An expired, lapsed, stale, rejected or abandoned proposal just returns the experiment/incident to "wanting" that change; the next eligible tick builds a *new* proposal on the *current* config with fresh data.
- **Timing:** requests only inside approver hours (Kestrel ≥ 11:00), only if worst-case latency lands before TTL, at most one open request per workflow, under the 24h cap with one slot reserved for incidents. Changes are batched into one request.
- **Auto-apply:** only caller ID, and only where policy allows it, within `max_shift`. Welcome/voice on `ks_cancel` could be auto-applied but go to the supervisor, who asked to be told.
- **Impact / affected / dry run:** impact is a 0–1 heuristic (start test 0.15, stop 0.2, promote 0.3 + 3 × lift, rollback 0.7, flagged caller ID 0.6, prompt fix 0.9). Affected leads = leads still inside their campaign × the share of traffic that moves. Dry run = last-72h replay of observed rates per variant; unseen variants assumed equal to the incumbent, which the dry run says.
- **Supervisor edits:** a `config_changed` from `supervisor` is logged; an experiment on that dimension is aborted and the edit becomes the incumbent; any approved proposal on the old base fails with `stale_base_version` and is re-planned. This is the source of the 3 "apply conflicts" on public_03: the simulator refused the apply, nothing was overwritten.

## 7. Incidents
- **Hallucination:** QA-flag rate on the live prompt over 8h; open when ≥ 150 connected, rate > max(2 × baseline, baseline + 1 pt) and binomial z ≥ 3 (one-sided FP ≈ 0.1% per check). For a prompt with a long clean record the bar is z ≥ 5: an earlier version raised a false alarm on P1 and "fixed" it with an LLM prompt that cut engagement, which the grader marked harmful.
- **Fix:** validate the best-engaging known-good prompt (2 credits); only if none passes, ask the LLM (3 credits) and validate up to its suggestions. Request goes out as urgent with the `validation_run_id`.
- **Verify:** after 300 connected calls on the fix, check flag rate and that engagement is not significantly below baseline; otherwise reopen.
- **public_02 timeline (ks_cancel):** D3 11:30 supervisor ships P2 → D3 13:00 incident opened (9/161 = 5.6% vs 1.4%), P1 validated (0.985), revert requested → D3 14:45 applied → D3 18:15 verified (flags 1.95%, engagement 53.2% vs 50.4% baseline). Credits used: 2.
- **Caller ID (public_02):** D2 10:45 D2 flagged (19.3% vs 32.6%, z = −3.7) → traffic moved off it in two auto-applied steps (policy max shift) → 2% probe from D3 on.

## 8. Scale
Measured on public_03_load (12 workflows, ~840k events/sim day), 8 vCPU box:
| metric | value |
|---|---|
| History catch-up | 5.54M events in 107 s (~51k events/s) |
| Wall time per simulated day (advance + ingest + decide) | 16–35 s (target < 600 s) |
| Decide time per day | 3–7 s |
| Peak RSS | 868 MB |
| Store size after 5 days | ~415 MB |
What breaks first at 10×: single-process JSON parsing in ingest (~50k events/s). Next: SQLite writes. Partitioning: workflows are independent, so shard ingest + planner by workflow (or tenant) into separate processes each with its own store; governance limits are per workflow so no cross-shard coordination is needed.

## 9. Reliability
- **Test:** `scripts/crash_test.sh` starts public_02, kills the controller with `kill -9` six times at random moments, restarts it each time, then lets it finish. Result (`reports/crash_test.log`): 0 duplicate applies of a proposal, all approvals tracked, 0 left pending, 0 expired, 0 lapsed; 6 restarts recorded in the audit log.
- **Idempotency:** chunk ingest is one transaction including the `chunks_done` marker; proposal IDs are written *before* the POST and sent as `proposal_id`; restart re-attaches by `proposal_id`; an `applying` proposal is reset to `approved` and re-checked before applying.
- **Lost state:** the in-memory lead → segment cache (rebuilt from `leads`) and at most the current tick's decisions.
- **4xx/5xx:** transport errors and 5xx retried with backoff (8 tries); 4xx are typed (`SimError.code`) and handled (stale, lapsed, not approved, refused).

## 10. Audit & observability
```
$ python -m controller.cli why --db state/p02.db --wf ks_cancel --at "D3 14:45"
== ks_cancel v8 at 2027-01-07T14:45:00+05:30 by controller_approved, dims ["prompt_version"], approval apr_00006
proposal ks_cancel-5100-efa51725 via approval created D3 13:00, final status applied
  change_summary: "revert prompt P2 -> P1 (hallucination incident)"
  rationale: "QA hallucination flags on P2 at 5.59% vs baseline 1.37% ...; P1 is the last known-good prompt ...; validation pass rate 0.985"
-- decision trail for this proposal
  D3 13:00  ks_cancel   request_sent   revert prompt P2 -> P1 (hallucination incident)
  D3 14:45  ks_cancel   applied        applied approval apr_00006 as v8
-- what happened next
  D3 18:15  ks_cancel   incident_verified  after fix P1: QA flag rate 1.95% (limit 2.74%), engagement 53.2% (baseline 50.4%)
```
Also: `cli log --wf X`, `cli status`, `cli metrics`.
- **Page on:** controller not advancing for > 30 min; a hallucination incident open > 4h with no request sent; credits < 10; repeated 5xx from the simulator.
- **Don't page on:** rejections, expiries, a flagged caller ID (handled automatically), experiment results — those go in the daily summary.

## 11. Results
public_01:
| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ |
|---|---|---|---|---|---|---|
| ks_cancel | 0.365 | +9.5% | 0.260 | +9.0% | 0.490 | -0.2% |
| nw_kyc | 0.459 | +26.3% | 0.294 | +21.6% | 0.593 | +0.4% |
| nw_renewal | 0.440 | +4.8% | 0.276 | +4.8% | 0.544 | -0.4% |
| ALL | 0.410 | +11.2% | 0.272 | +9.8% | 0.530 | +0.1% |
13 changes applied — 5 beneficial, 8 neutral, 0 harmful.

public_02:
| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ |
|---|---|---|---|---|---|---|
| ks_cancel | 0.365 | +47.3% | 0.248 | +35.1% | 0.503 | +5.6% |
| nw_kyc | 0.463 | +23.6% | 0.297 | +22.7% | 0.585 | -1.2% |
| nw_renewal | 0.475 | +11.3% | 0.286 | +9.1% | 0.556 | +1.4% |
| ALL | 0.422 | +26.3% | 0.271 | +21.9% | 0.540 | +1.8% |
16 changes applied — 8 beneficial, 8 neutral, 0 harmful.

public_03: ALL +12.7% conclusion rate, 78 changes, 0 harmful.

Interpretation: almost all the gain is **pickup**, from spreading volume over healthy caller IDs and moving off the flagged one. Engagement moved little: experiments at 8% need days to conclude and most challengers showed no effect. `nw_kyc` engagement −1.2% is within the guardrail but is a real cost of caller-ID moves (different people answer). Earlier iterations were harmful twice (a false hallucination alarm; a 10% challenger that was ~10% worse); both were fixed, see §5 and §7. Results vary run to run because approver latency and rejections are random (public_02 MTTR was 165–360 min across runs).

## 12. Trade-offs & rejected alternatives
| Option | Why considered | Why rejected / what instead |
|---|---|---|
| Thompson sampling bandit | Faster convergence | Harder to explain to compliance; allocation moves need approvals anyway. Fixed-share test + z-test instead |
| Per-cohort experiments | Larger possible gains | Arms too small to conclude within a scenario |
| LLM-first incident fix | Fast | Costs credits, and its prompt can hurt engagement (seen in testing). Known-good revert first |
| Postgres / Redis | Production standard | No new infra for the take-home; same schema ports to Postgres |
| Store every raw call | Full replay | 850k events/day; aggregates by (hour, segment, variant, config version) are enough |
| Auto-apply welcome/voice on ks_cancel | Policy allows it | Supervisor asked to be told first; approval route instead |

## 13. Known weaknesses
- Experiments are slow; on 8–10 day scenarios most tests end in "no effect". Engagement gains are small.
- No call-time optimisation at all.
- The impact score is a heuristic, not calibrated.
- Caller-ID flagging can flap (seen once in public_02: a number flagged right after recovering).
- The hallucination detector's baseline is fixed at history; a slowly drifting prompt would be caught late.
- One process; a crash mid-tick loses that tick's decisions (they are recomputed, not lost permanently).
- Supervisor "one screen" is a CLI.

## 14. If this went to production at Formi next month
1. Move the store to Postgres (same tables) and run one process per tenant.
2. Ship metrics + the four pages in §10.
3. Shadow mode for a week: log proposals, send none; compare to what supervisors did.
4. Turn on caller-ID health first (largest, safest win), then incident response, then experiments.
5. A supervisor web page over `decisions`/`proposals`/`experiments`.
6. Calibrate the impact score against approver decisions.
