# Outcome-First Agent Loop — Submission

**Name:** Geethika Gunti · **Date:** 2026-11-09 · **Hours actually spent (be honest):** _[fill in]_ · **Language / storage:** Python 3.10 / SQLite (WAL), no new infrastructure

---

## 0. TL;DR
A single-process Python controller (`python -m controller`, started by `./run.sh`) that ingests event chunks into a SQLite store, keeps caller IDs healthy, reverts bad prompts with validation evidence, runs one bounded welcome/voice experiment at a time per workflow, and sends every customer-facing change through an approval state machine that survives `kill -9`.
public_01: conclusion rate **+12.1%**, public_02: **+26.0%**, public_03: **+18.7%**; **0 harmful changes** in all three; 0 expired, 0 lapsed approvals.
Deliberately not built: per-person call timing, per-cohort schedules, a supervisor UI (a CLI instead), fair credit sharing across tenants.

## 1. Assumptions
1. The simulator API is the only source of truth. The controller never reads `scenarios/`, `runs/` or imports `sim`.
2. Every decision is judged on the workflow's declared **primary** KPI (`objective.primary`), and the other KPI is a guardrail with the declared max drop (`objective.guardrail.<kpi>_max_drop`). Pickup = connected / dials; engagement = engaged / connected; they are never blended. Business conclusion rate is not observable per decision in time, so it is the outcome the grader scores, not a signal the controller optimises directly.
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
- **Deciding a winner:** two-proportion z-test on the workflow's **primary KPI** since the arm's config version: engaged / connected when engagement is primary, connected / dials when pickup is primary. Sample thresholds are in the primary KPI's trials (connected calls for engagement; dials, ×3, for pickup). Win: challenger ≥ 250 trials, one-sided z ≥ Bonferroni critical value (α = 0.05 / number of challengers) **and** the guardrail KPI passes. Guardrail check (independent): the challenger's guardrail rate is not more than the declared max drop below control, and no significant guardrail drop (z ≤ −2); missing guardrail data counts as a fail. Harm stop: ≥ 100 trials and primary z ≤ −2, or a guardrail breach beyond the max drop with z ≤ −3 (stricter, because it is checked every tick and a moderate breach already blocks promotion). Futility: 700 trials with no win. The LLM never decides.
- **Decay and rollback:** a promoted winner keeps a 10% holdout of the old incumbent; if over the last 36h the holdout beats it on the primary KPI with z ≤ −2 (≥ 150 holdout trials), a rollback is proposed, unless the holdout is more than the guardrail max drop below the winner on the guardrail KPI (`rollback_blocked`): a rollback is a promotion of the holdout and must pass the same guardrail.
- **Caller ID:** per number, pickup vs. the other numbers in the same 6h window (z ≤ −3 and < 75% of their rate) → flagged, probed at 2%. Unseen numbers explored at 10% until shown healthy over 24h. Healthy numbers share the rest. Changes capped at the policy `max_shift`. Flagged numbers come back once their 24h pickup returns to ≥ 90% of the others. **Projection gate:** before any caller-ID change, projected pickup and engagement under the new mix are computed from per-number rates shrunk toward the pooled workflow rate (200 pseudo-dials, so a number with few calls counts as average, not best or worst). The change is blocked if the primary KPI is projected to fall more than 0.5 pt plus 2 standard errors of the projection, or the guardrail more than its max drop. Except for a newly flagged number, a change also needs the 120-min cooldown and ≥ 150 new workflow dials since the last caller-ID change took effect: the clock starts when the change is applied, not when it is requested, so calls made while an approval is pending never count as evidence about the new mix. A rejected or expired request starts no clock. While a caller-ID approval is pending no other non-urgent caller-ID change is planned, and if a crash lands between the apply and recording the clock, it is rebuilt from the last applied caller-ID proposal.
- **Guardrail:** the non-primary KPI, checked independently on every experiment step and every caller-ID change; prompt fixes are checked on engagement after applying.

## 6. Governance
States: `submitting → pending → approved → applying → applied`, with `rejected | expired | lapsed | stale` from pending/approved, `failed` (POST refused), `abandoned` (crash before the POST landed), and `applied | refused` for auto-apply.
- **Re-proposal:** the planner is state-driven. An expired, lapsed, stale, rejected or abandoned proposal just returns the experiment/incident to "wanting" that change; the next eligible tick builds a *new* proposal on the *current* config with fresh data.
- **Timing:** requests only inside the *effective* approver hours (policy hours narrowed by the tenant's stricter ask: Kestrel ≥ 11:00, 2/24h). Urgent incident requests obey hours too; they only get the reserved cap slot. A request is sent only if the worst-case decision time (max latency, pushed to the next working window as the simulator documents) lands before TTL. At most one open request per workflow, urgent or not. Changes are batched into one request.
- **Auto-apply:** only caller ID, and only where policy allows it, within `max_shift`. Welcome/voice on `ks_cancel` could be auto-applied but go to the supervisor, who asked to be told.
- **Impact / affected / dry run:** impact is a 0–1 heuristic (start test 0.15, stop 0.2, promote 0.3 + 3 × lift, rollback 0.7, flagged caller ID 0.6, prompt fix 0.9). Affected leads = leads still inside their campaign × the share of traffic that moves. Dry run = last-72h replay of observed rates per variant; unseen variants assumed equal to the incumbent, which the dry run says.
- **Supervisor edits:** a `config_changed` from `supervisor` is logged; an experiment on that dimension is aborted and the edit becomes the incumbent; before applying an approved proposal the controller re-reads the config version; if it moved (e.g. a supervisor edit), the proposal is closed as `stale` without calling apply, and re-planned on the new config. A `stale_base_version` from the simulator is handled the same way.

## 7. Incidents
- **Hallucination:** QA-flag rate on the live prompt over 8h; open when ≥ 150 connected, rate > max(2 × baseline, baseline + 1 pt) and binomial z ≥ 3 (one-sided FP ≈ 0.1% per check). For a prompt with a long clean record the bar is z ≥ 5: an earlier version raised a false alarm on P1 and "fixed" it with an LLM prompt that cut engagement, which the grader marked harmful.
- **Fix:** validate the best-engaging known-good prompt (2 credits); only if none passes, ask the LLM (3 credits) and validate up to its suggestions. Request goes out as urgent with the `validation_run_id`.
- **Verify:** counts only *complete* hourly buckets that start at or after the apply time, on the applied config version or later (no pre-change or partial-hour calls). After ≥ 300 connected calls, the fix passes if the QA flag rate is under the incident limit **and** engagement is within the guardrail of baseline. Otherwise the incident is reopened (`incident_reopened`), the fix is marked tried, and the next candidate is validated; with none left it is escalated (`incident_escalated`).
- **public_02 timeline (ks_cancel), final run:** D3 11:30 supervisor ships P2 (controller sees v7 at D3 11:45 and respects it) → D3 14:30 incident opened (11/316 = 3.48% vs 1.37%), P1 validated (pass rate 0.985, 2 credits), revert requested (inside approver hours) → D3 15:30 approved and applied as v8 → D3 19:00 verified on complete post-change hours only: flags 0.64% (limit 2.74%), engagement 49.8% (baseline 50.4%, within the guardrail). Grader MTTR 240 min, fixed by `controller_approved`. The supervisor's D5 15:00 edit on nw_renewal was left alone.
- **Caller ID (public_02), final run:** D2 11:30 D2 flagged (16.3% vs 26.2% on other numbers, z = −3.56, n = 355) → traffic moved off it in two auto-applied steps (D2 11:30 to 15%, D2 13:30 to the 2% probe; policy max shift) → grader flagged share 10.8% on D2, 1.7–2.4% per day from D3 on.

## 8. Scale
Measured on public_03_load (12 workflows, ~840k events/sim day), 8 vCPU box:
| metric | value |
|---|---|
| Whole run incl. history catch-up (`/usr/bin/time`, `./run.sh`) | 4 min 44 s |
| Wall time per simulated day (advance + ingest + decide, `cli metrics`) | 27–40 s (target < 600 s) |
| Decide time per day | 3.4–8.8 s |
| Peak RSS | 867 MB (controller), 888 MB max for the run |
| Store size after 5 days | ~457 MB |
What breaks first at 10×: single-process JSON parsing in ingest (~50k events/s). Next: SQLite writes. Partitioning: workflows are independent, so shard ingest + planner by workflow (or tenant) into separate processes each with its own store; governance limits are per workflow so no cross-shard coordination is needed.

## 9. Reliability
- **Test:** `scripts/crash_test.sh` starts public_02, kills the controller with `kill -9` six times at random moments, restarts it each time, then lets it finish. Final-code result (`reports/crash_test.log`): final exit 0, 0 duplicate applies of a proposal, 16/16 approvals tracked, 0 left pending or approved-unapplied, 0 expired, 0 lapsed, 0 apply conflicts, 19 changes applied (0 harmful). One approval (`apr_00006`) was approved after the config had moved, so the controller closed it as `stale` without applying (it never overwrites a newer config) and re-planned. The audit log shows 5 restarts for 6 kills: a kill that lands in the first seconds, before the controller writes its startup record, leaves no restart row.
- **Idempotency:** chunk ingest is one transaction including the `chunks_done` marker; proposal IDs are written *before* the POST and sent as `proposal_id`; restart re-attaches by `proposal_id`; an `applying` proposal is reset to `approved` and re-checked before applying.
- **Lost state:** the in-memory lead → segment cache (rebuilt from `leads`) and at most the current tick's decisions.
- **4xx/5xx:** transport errors and 5xx retried with backoff (8 tries); 4xx are typed (`SimError.code`) and handled (stale, lapsed, not approved, refused).

## 10. Audit & observability
```
$ python -m controller.cli why --db state/public_02.db --wf ks_cancel --at "D3 15:30"
== ks_cancel v8 at 2027-01-07T15:30:00+05:30 by controller_approved, dims ["prompt_version"], approval apr_00007
proposal ks_cancel-5190-f5bea70e via approval created D3 14:30, final status applied
  change_summary: "revert prompt P2 -> P1 (hallucination incident)"
  rationale: "QA hallucination flags on P2 at 3.48% vs baseline 1.37% (z=3.23); P1 is the last known-good prompt (observed flag rate 1.35%, engagement 50.4%); validation pass rate 0.985"
  impact_score: 0.9
  affected_leads: 4500
  dry_run: {"prompt": {"observed_flag_rate": 0.0135, "validation": {"prompt": "P1", "why": "is the last known-good prompt (observed flag rate 1.35%, engagement 50.4%)", "observed": 0.0135, "validation_run_id": "val_00001", "pass_rate": 0.985, "n": 200}}}
  evidence: {"validation_run_id": "val_00001"}
-- decision trail for this proposal
  D3 14:30  ks_cancel   request_sent         revert prompt P2 -> P1 (hallucination incident)  [ks_cancel-5190-f5bea70e]
  D3 15:30  ks_cancel   applied              applied approval apr_00007 as v8  [ks_cancel-5190-f5bea70e]
-- what happened next (until +6h)
  D3 19:00  ks_cancel   incident_verified    after fix P1: QA flag rate 0.64% (limit 2.74%), engagement 49.8% (baseline 50.4%)
-- KPIs on this config version vs previous
  v7: dials 1600, pickup 0.246, engagement 0.442
  v8: dials 19500, pickup 0.246, engagement 0.482
```
Also: `cli log --wf X`, `cli status`, `cli metrics`.
- **Page on:** controller not advancing for > 30 min; a hallucination incident open > 4h with no request sent; credits < 10; repeated 5xx from the simulator.
- **Don't page on:** rejections, expiries, a flagged caller ID (handled automatically), experiment results — those go in the daily summary.

## 11. Results
All numbers below are copied from the grader reports generated by the final code (`reports/public_0*.md`); runs vary a little because approver latency and rejections are random.

public_01 (`reports/public_01.md`):
| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.373 | +12.1% | 0.260 | +9.0% | 0.500 | +1.8% | 1% | 54 (47) |
| nw_kyc | 0.454 | +25.0% | 0.291 | +20.3% | 0.594 | +0.5% | 3% | 27 (21) |
| nw_renewal | 0.440 | +4.9% | 0.276 | +4.9% | 0.543 | -0.5% | -1% | 52 (42) |
| ALL | 0.413 | +12.1% | 0.271 | +9.6% | 0.534 | +0.9% | 1% | 133 (110) |
26 applied — neutral: 19, beneficial: 7.

public_02 (`reports/public_02.md`):
| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.359 | +45.1% | 0.250 | +36.1% | 0.495 | +3.9% | 32% | 83 (330) |
| nw_kyc | 0.465 | +24.1% | 0.300 | +23.8% | 0.585 | -1.3% | -5% | 37 (31) |
| nw_renewal | 0.477 | +11.9% | 0.292 | +11.6% | 0.548 | +0.0% | 5% | 68 (55) |
| ALL | 0.421 | +26.0% | 0.274 | +23.5% | 0.533 | +0.7% | 15% | 188 (416) |
19 applied — beneficial: 8, neutral: 11.

public_03 (`reports/public_03.md`):
| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.363 | +6.3% | 0.262 | +7.1% | 0.495 | -1.1% | -1% | 426 (408) |
| arav_kyc_1 | 0.475 | +34.1% | 0.274 | +27.6% | 0.595 | -0.1% | 1% | 451 (370) |
| arav_renewal_0 | 0.462 | +14.9% | 0.280 | +6.1% | 0.582 | +7.2% | 31% | 448 (440) |
| kest_cancel_2 | 0.365 | +7.7% | 0.262 | +7.7% | 0.497 | -0.3% | -0% | 440 (411) |
| kest_kyc_1 | 0.472 | +33.6% | 0.273 | +27.5% | 0.594 | +0.0% | 2% | 446 (339) |
| kest_renewal_0 | 0.445 | +11.4% | 0.281 | +6.6% | 0.561 | +3.5% | 15% | 469 (433) |
| nort_cancel_2 | 0.377 | +11.3% | 0.263 | +8.4% | 0.510 | +2.1% | 14% | 429 (393) |
| nort_kyc_1 | 0.449 | +26.6% | 0.259 | +21.5% | 0.598 | +0.5% | 2% | 399 (323) |
| nort_renewal_0 | 0.471 | +16.5% | 0.282 | +6.9% | 0.589 | +7.5% | 35% | 453 (411) |
| tide_cancel_2 | 0.387 | +14.1% | 0.261 | +7.1% | 0.524 | +4.9% | 35% | 388 (407) |
| tide_kyc_1 | 0.471 | +33.2% | 0.274 | +27.5% | 0.592 | +0.1% | 1% | 498 (356) |
| tide_renewal_0 | 0.465 | +16.0% | 0.279 | +5.8% | 0.588 | +8.5% | 39% | 452 (438) |
| ALL | 0.433 | +18.7% | 0.271 | +12.6% | 0.561 | +3.2% | 15% | 5299 (4729) |
85 applied — neutral: 56, beneficial: 29.

Interpretation: almost all the gain is **pickup**, from spreading volume over healthy caller IDs and moving off flagged ones; conclusion rate follows pickup because more leads are reached before their campaign ends. Engagement moved little: experiments at 8% need days to conclude and most challengers showed no effect. `nw_kyc` engagement fell slightly (within its 0.02 guardrail); that is the cost of caller-ID moves (different people answer), and the caller-ID projection gate now caps it. Hallucinated calls are counted in absolute terms, so they rise a little on workflows that connect more calls.

**Reported public_02 regression (−2.5% overall, nw_kyc −11.6%, nw_renewal −12.7%).** Not reproduced: every complete public_02 run I graded (4 on the merged `main` code, 3 on this branch) gave between +21.7% and +29.1% overall, with nw_kyc and nw_renewal positive every time. The reported report is consistent with an *incomplete* run rather than a controller regression: pickup (+17.8%) and engagement (+1.3%) are up, but the grader's `leads_uploaded` counts every campaign in the scenario (`sim/world.py` `_write_truth`), so a run graded before day 10 has late leads that were never called; it also shows far fewer hallucinated calls than a full run (95 vs 177–208). Check: a no-op controller stopped at day 8 of 10 grades at −2.1% conclusion with pickup +0.8% and engagement −0.3%. Always grade after `./run.sh` exits 0 (the simulator reports `finished: true`). What was checked in the controller anyway: experiments now use each workflow's declared primary KPI and an independent guardrail; caller-ID moves are gated on projected primary and guardrail KPIs; no promotion happened with a guardrail breach (every `experiment_win` row logs both); rollback logic unchanged.

**Reported public_02 regression (−2.5% overall, nw_kyc −11.6%, nw_renewal −12.7%).** Not reproduced: every complete public_02 run I graded (4 on the merged `main` code, 3 on this branch) gave between +21.7% and +29.1% overall, with nw_kyc and nw_renewal positive every time. The reported report is consistent with an *incomplete* run rather than a controller regression: pickup (+17.8%) and engagement (+1.3%) are up, but the grader's `leads_uploaded` counts every campaign in the scenario (`sim/world.py` `_write_truth`), so a run graded before day 10 has late leads that were never called; it also shows far fewer hallucinated calls than a full run (95 vs 177–208). Check: a no-op controller stopped at day 8 of 10 grades at −2.1% conclusion with pickup +0.8% and engagement −0.3%. Always grade after `./run.sh` exits 0 (the simulator reports `finished: true`). What was checked in the controller anyway: experiments now use each workflow's declared primary KPI and an independent guardrail; caller-ID moves are gated on projected primary and guardrail KPIs; no promotion happened with a guardrail breach (every `experiment_win` row logs both); rollback logic unchanged.

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
- The controller optimises pickup and engagement (the declared KPIs), not conclusion rate directly; caller-ID moves can change *who* answers, and the projection gate models pickup/engagement per number, not lead mix per segment.
- The caller-ID projection uses the last 24h (6h for flagged numbers) per number; a number whose health changes faster than that is judged on stale data.
- Native Windows is handled in code (no hard dependency on `resource`; memory metrics optional) and unit-tested by simulating a missing module, but not run on a Windows machine.
- Results are from the simulator only; approver randomness moves public_02 by a few points between runs.

## 14. If this went to production at Formi next month
1. Move the store to Postgres (same tables) and run one process per tenant.
2. Ship metrics + the four pages in §10.
3. Shadow mode for a week: log proposals, send none; compare to what supervisors did.
4. Turn on caller-ID health first (largest, safest win), then incident response, then experiments.
5. A supervisor web page over `decisions`/`proposals`/`experiments`.
6. Calibrate the impact score against approver decisions.
