"""Detectors, experiments and incident response. State-driven: every tick recomputes what it wants from the
store, so a crash, an expiry or a stale base simply leads to a fresh proposal on the next eligible tick."""
from __future__ import annotations

import json
import logging
import math

from . import configs, policy as P
from .api import SimError
from .governance import Governance
from .stats import binom_z, norm_ppf, rate, tv, two_prop_z
from .store import Store

log = logging.getLogger("controller.plan")
ACTIVE = ("want_start", "start_req", "running", "want_promote", "promote_req", "want_stop", "stop_req")
AGENT_DIMS = ("welcome_message", "voice")


class Planner:
    def __init__(self, store: Store, sim, wfs: dict):
        self.s, self.sim, self.wfs = store, sim, wfs
        self.gov = Governance(store, sim, wfs, self.on_closed)
        self.cfg: dict[str, dict] = {}
        self.end_minute = None

    # ------------------------------------------------------------------ data access
    def config(self, wid, refresh=False) -> dict:
        if refresh or wid not in self.cfg:
            self.cfg[wid] = self.sim.get(f"/workflows/{wid}/config")
        return self.cfg[wid]

    def window(self, wid, hours, group, where="", args=()):
        h0 = self.s.now_minute // 60 - hours
        sql = (f"SELECT {group}, SUM(dials), SUM(conn), SUM(eng), SUM(flags) FROM agg WHERE wf=? AND day>=? "
               f"AND day*24+hour>=? {where} GROUP BY {group}")
        return {r[0]: r[1:] for r in self.s.q(sql, (wid, h0 // 24 - 1, h0, *args))}

    def since_version(self, wid, dim_col, version, hours=None):
        where, args = "AND cfg_ver>=?", (version,)
        if hours is None:
            hours = 24 * 400
        return self.window(wid, hours, dim_col, where, args)

    def active_leads(self, wid) -> int:
        days = len(self.wfs[wid]["cadence"])
        today = self.s.now_minute // 1440
        return self.s.one("SELECT COUNT(*) FROM leads WHERE workflow_id=? AND campaign_day>?",
                          (wid, today - days))[0]

    def kv(self, key, default=None):
        return self.s.get(key, default)

    # ------------------------------------------------------------------ bootstrap
    def bootstrap(self):
        for wid in self.wfs:
            if self.kv(f"baseline:{wid}"):
                continue
            r = self.s.one("SELECT SUM(dials), SUM(conn), SUM(eng), SUM(flags) FROM agg WHERE wf=? AND day<0", (wid,))
            d, c, e, f = (x or 0 for x in r)
            b = {"pickup": rate(c, d) or 0.3, "engage": rate(e, c) or 0.5,
                 "flag_rate": max(rate(f, c) or 0.02, 0.005), "dials": d, "connected": c}
            self.s.set(f"baseline:{wid}", b)
            self.s.decide(wid, "bootstrap", f"history baseline: pickup {b['pickup']:.3f}, engagement "
                          f"{b['engage']:.3f}, QA flag rate {b['flag_rate']:.4f}", b)

    # ------------------------------------------------------------------ events
    def on_event(self, ev, kind):
        if ev["type"] != "config_changed" or kind != "events":
            return
        wid = ev["workflow_id"]
        self.cfg.pop(wid, None)
        if ev["actor"] != "supervisor":
            return
        dims = set(ev["changed_dims"])
        self.s.decide(wid, "supervisor_edit", f"supervisor changed {sorted(dims)} (v{ev['version']}); "
                      "respecting it", {"event": ev})
        for exp_id, dim, st in self.s.q("SELECT exp_id, dim, status FROM experiments WHERE wf=?", (wid,)):
            if dim in dims and (st in ACTIVE or st == "promoted"):
                self.s.db.execute("UPDATE experiments SET status='aborted', end_minute=? WHERE exp_id=?",
                                  (self.s.now_minute, exp_id))
                self.s.set(f"cooldown:{wid}:{dim}", self.s.now_minute + 1440)
                self.s.decide(wid, "experiment_aborted", f"{exp_id}: supervisor edited {dim} mid-experiment; "
                              "stopping and adopting their choice as the new incumbent", {"exp_id": exp_id})

    # ------------------------------------------------------------------ proposal outcomes
    def on_closed(self, p, status):
        self.cfg.pop(p["wf"], None)
        if status == "applied" and any(it.get("key") == "caller_id" for it in p["intents"]):
            self._mark_did_change(p["wf"], p["proposal_id"])
        for it in p["intents"]:
            if it.get("exp_id"):
                self._exp_closed(it, status, p.get("applied_version"))
            if it["type"] == "prompt":
                inc = self.kv(f"incident:{p['wf']}")
                if inc and inc.get("proposal_id") == p["proposal_id"]:
                    if status == "applied":
                        inc.update(status="verifying", applied_minute=self.s.now_minute,
                                   applied_version=p.get("applied_version"))
                    else:
                        inc.update(status="open", proposal_id=None)
                    self.s.set(f"incident:{p['wf']}", inc)

    def _exp_closed(self, it, status, version):
        exp_id, action = it["exp_id"], it["action"]
        r = self.s.one("SELECT status, result FROM experiments WHERE exp_id=?", (exp_id,))
        if not r or r[0] == "aborted":
            return
        res = json.loads(r[1] or "{}")
        if status == "applied":
            new = {"start": "running", "promote": "promoted", "stop": "closed", "rollback": "rolled_back"}[action]
            if action == "start":
                self.s.db.execute("UPDATE experiments SET status=?, start_version=?, start_minute=? WHERE exp_id=?",
                                  (new, version, self.s.now_minute, exp_id))
                return
            if action == "promote":
                res["promote_version"], res["promote_minute"] = version, self.s.now_minute
            self.s.db.execute("UPDATE experiments SET status=?, result=?, end_minute=? WHERE exp_id=?",
                              (new, json.dumps(res), self.s.now_minute, exp_id))
        elif status == "rejected" and action == "start":
            self.s.db.execute("UPDATE experiments SET status='rejected', end_minute=? WHERE exp_id=?",
                              (self.s.now_minute, exp_id))
        else:
            back = "promoted" if action == "rollback" and status == "rejected" else f"want_{action}"
            self.s.db.execute("UPDATE experiments SET status=? WHERE exp_id=?", (back, exp_id))

    # ------------------------------------------------------------------ main entry
    def tick(self, wid, hourly: bool, credits: float):
        cur = self.config(wid)
        urgent = self.halluc(wid, cur, credits)
        did_intent = self.caller_id(wid, cur)
        batch = []
        if did_intent:
            batch.append(did_intent)
        if hourly and self.s.now_minute >= 0:
            exp_intent = self.experiments(wid, cur)
            if exp_intent:
                batch.append(exp_intent)
        if urgent:
            self.propose(wid, [urgent], urgent=True)
        if batch:
            self.propose(wid, batch)

    # ------------------------------------------------------------------ proposals
    def propose(self, wid, intents, urgent=False):
        cur = self.config(wid)
        new = configs.apply_intents(cur["config"], intents)
        if configs.same(new, cur["config"]):
            return
        dims = configs.changed_dims(cur["config"], new)
        shift = max((tv(configs.dist(cur["config"], "default", d), configs.dist(new, "default", d))
                     for d in configs.DIMS), default=0)
        # Only operational dims (caller ID, schedule) ever take the auto-apply path.
        operational = dims <= {"caller_id", "schedule"}
        if operational and self.gov.auto_allowed(wid, dims, shift):
            self.gov.auto_apply(wid, cur, new, intents, "; ".join(i["summary"] for i in intents),
                                {"stats": [i.get("evidence") for i in intents]})
            return
        ok, why = self.gov.can_request(wid, urgent=urgent)
        if not ok:
            key = f"deferred:{wid}:{why}"
            if not self.kv(key):
                self.s.set(key, 1)
                self.s.decide(wid, "deferred", f"holding {len(intents)} change(s): {why}",
                              {"intents": [i["summary"] for i in intents]})
            return
        affected = self.active_leads(wid)
        aff = int(round(affected * max(shift, 1.0 if "prompt_version" in dims else 0)))
        meta = {"change_summary": " + ".join(i["summary"] for i in intents),
                "diff": configs.diff(cur["config"], new),
                "affected_leads": max(aff, 0),
                "dry_run": {i["key"]: i.get("dry_run") or {"note": "no historical replay for this change"}
                            for i in intents},
                "impact_score": round(min(max(max(i["impact"] for i in intents), 0.0), 1.0), 3),
                "rationale": " | ".join(i["rationale"] for i in intents),
                "evidence": {k: v for i in intents for k, v in (i.get("api_evidence") or {}).items()} or None,
                "expires_in_hours": self.wfs[wid]["governance"]["proposal_ttl_hours"]}
        if meta["evidence"] is None:
            meta.pop("evidence")
        pid = self.gov.request(wid, cur, new, intents, meta)
        for k in [r[0] for r in self.s.q("SELECT k FROM kv WHERE k LIKE ?", (f"deferred:{wid}:%",))]:
            self.s.db.execute("DELETE FROM kv WHERE k=?", (k,))
        if pid:
            for it in intents:
                if it.get("exp_id"):
                    self.s.db.execute("UPDATE experiments SET status=? WHERE exp_id=?",
                                      (f"{it['action']}_req", it["exp_id"]))
                if it["type"] == "prompt":
                    inc = self.kv(f"incident:{wid}")
                    inc.update(status="fix_req", proposal_id=pid)
                    self.s.set(f"incident:{wid}", inc)

    def _mark_did_change(self, wid, pid):
        """Start the caller-ID cooldown / new-evidence clock when a caller-ID change actually takes effect, so calls
        made while an approval was pending never count as evidence about the new mix."""
        total = self.s.one("SELECT SUM(dials) FROM agg WHERE wf=?", (wid,))[0] or 0
        mark = {"minute": self.s.now_minute, "dials": total, "proposal_id": pid}
        self.s.set(f"did_last_change:{wid}", mark)
        return mark

    def _did_pending(self, wid) -> bool:
        return any(any(it.get("key") == "caller_id" for it in self.gov.row(pid)["intents"])
                   for pid in self.gov.open_for(wid))

    # ------------------------------------------------------------------ caller ID health (C5)
    def caller_id(self, wid, cur):
        opts = self.wfs[wid]["options"]["caller_id"]
        cur_d = configs.dist(cur["config"], "default", "caller_id")
        status = self.kv(f"did_status:{wid}") or {}
        w6 = self.window(wid, P.DID_WINDOW_HOURS, "did")
        w24 = self.window(wid, 24, "did")
        new_flag = []
        for d in opts:
            st = status.get(d) or ("healthy" if d in cur_d else "unknown")
            for win, min_n in ((w6, P.DID_MIN_DIALS), (w24, 100 if st == "bad" else 300)):
                dd, dc = (win.get(d) or (0, 0))[:2]
                od = sum(v[0] for k, v in win.items() if k != d)
                oc = sum(v[1] for k, v in win.items() if k != d)
                if dd < min_n or od < 100:
                    continue
                z = two_prop_z(dc, dd, oc, od)
                ratio = (dc / dd) / (oc / od) if oc else 1
                if st != "bad" and z <= P.DID_FLAG_Z and ratio < P.DID_FLAG_RATIO:
                    st = "bad"
                    new_flag.append({"did": d, "pickup": round(dc / dd, 3), "others": round(oc / od, 3),
                                     "z": round(z, 2), "dials": dd})
                elif win is w24 and st == "bad" and ratio >= 0.9 and z > -1:
                    st = "healthy"
                    self.s.decide(wid, "did_recovered", f"caller ID {d} pickup back to {ratio:.0%} of others")
                elif win is w24 and st == "unknown" and z > -2 and ratio > 0.85:
                    st = "healthy"
            status[d] = st
        self.s.set(f"did_status:{wid}", status)
        for f in new_flag:
            self.s.decide(wid, "did_flagged", f"caller ID {f['did']} pickup {f['pickup']:.1%} vs {f['others']:.1%} "
                          f"on other numbers (z={f['z']}, n={f['dials']})", f)
        bad = [d for d in opts if status[d] == "bad"]
        unknown = [d for d in opts if status[d] == "unknown"]
        healthy = [d for d in opts if status[d] == "healthy"] or [d for d in opts if d not in bad]
        if not healthy:
            return None
        target = {d: P.DID_PROBE_SHARE for d in bad}
        target.update({d: P.DID_EXPLORE_SHARE for d in unknown if d not in healthy})
        rest = 1 - sum(target.values())
        target.update({d: rest / len(healthy) for d in healthy})
        target = configs.norm(target)
        dist_tv = tv(cur_d, target)
        last = self.kv(f"did_last_change:{wid}")
        if not isinstance(last, dict):
            last = {"minute": last if last is not None else -10**9, "dials": None}
        total = self.s.one("SELECT SUM(dials) FROM agg WHERE wf=?", (wid,))[0] or 0
        applied = self.s.one("SELECT proposal_id FROM proposals WHERE wf=? AND status='applied' AND intents LIKE ? "
                             "ORDER BY rowid DESC LIMIT 1", (wid, '%"key": "caller_id"%'))
        if applied and last.get("proposal_id") != applied[0]:
            # applied but the clock was never started (crash between apply and on_closed): start it now
            last = self._mark_did_change(wid, applied[0])
        if dist_tv < P.DID_MIN_TV_TO_ACT:
            return None
        if not new_flag and self._did_pending(wid):
            return None
        if not new_flag and (self.s.now_minute - last["minute"] < P.DID_COOLDOWN_MIN or
                             (last["dials"] is not None and total - last["dials"] < P.DID_MIN_NEW_DIALS)):
            return None
        mx = self.wfs[wid]["governance"]["auto_apply"].get("max_shift", 0) if \
            self.wfs[wid]["governance"]["auto_apply"].get("enabled") else 1.0
        step = target
        if "caller_id" in self.wfs[wid]["governance"]["auto_apply"].get("allowed_dims", []) and dist_tv > mx:
            f = mx / dist_tv * 0.999
            step = configs.norm({d: cur_d.get(d, 0) + (target.get(d, 0) - cur_d.get(d, 0)) * f
                                 for d in set(cur_d) | set(target)})
        per_did = {d: (w6 if status[d] == "bad" else w24).get(d) for d in opts}
        pooled = tuple(sum(v[i] for v in w24.values()) for i in range(3))
        proj = self.did_projection(wid, cur_d, step, per_did, pooled)
        if not proj["ok"]:
            key = f"did_blocked:{wid}:{self.s.now_minute // 1440}"
            if not self.kv(key):
                self.s.set(key, 1)
                self.s.decide(wid, "did_change_blocked", f"caller-ID mix {cur_d} -> {step} held: {proj['why']}", proj)
            return None
        pick = {d: round((w24.get(d) or (0, 0))[1] / max((w24.get(d) or (1, 0))[0], 1), 3) for d in opts}
        return {"type": "alloc", "dim": "caller_id", "cohort": "default", "dist": step, "key": "caller_id",
                "summary": f"caller-ID mix {cur_d} -> {step}",
                "rationale": f"status {status}; spread volume over healthy numbers, probe flagged ones at "
                             f"{P.DID_PROBE_SHARE:.0%}, explore unseen ones at {P.DID_EXPLORE_SHARE:.0%}",
                "impact": 0.6 if new_flag else 0.3,
                "dry_run": {"pickup_by_caller_id_24h": pick, "dials_24h": {d: (w24.get(d) or (0,))[0] for d in opts},
                            "flagged": new_flag, "projection": proj},
                "evidence": {"status": status, "flags": new_flag}}

    def did_projection(self, wid, cur_d, new_d, per_did: dict, pooled: tuple) -> dict:
        """Project pickup and engagement under a caller-ID mix. Each number's rates are shrunk toward the pooled
        workflow rate, so numbers with few (or no) observations count as average rather than as best or worst."""
        dials, conn, eng = pooled[:3]
        p_pick = conn / dials if dials else 0.3
        p_eng = eng / conn if conn else 0.5
        k = P.DID_PRIOR_DIALS

        def rates(d):
            dd, dc, de = (per_did.get(d) or (0, 0, 0))[:3]
            return (dc + k * p_pick) / (dd + k), (de + k * p_pick * p_eng) / (dc + k * p_pick)

        def mix(dist):
            r = {d: rates(d) for d in dist}
            pick = sum(p * r[d][0] for d, p in dist.items())
            return pick, (sum(p * r[d][0] * r[d][1] for d, p in dist.items()) / pick if pick else 0)

        def se(i):
            """Standard error of the projected change in KPI i (0 pickup, 1 engagement) from per-number noise."""
            v = 0.0
            for d in set(cur_d) | set(new_d):
                dd, dc, _ = (per_did.get(d) or (0, 0, 0))[:3]
                n = dd + k if i == 0 else dc + k * p_pick
                r = rates(d)[i]
                v += (new_d.get(d, 0) - cur_d.get(d, 0)) ** 2 * r * (1 - r) / n
            return v ** 0.5

        (pk0, en0), (pk1, en1) = mix(cur_d), mix(new_d)
        primary, guard, max_drop = self.objective(wid)
        now = {"pickup_rate": pk0, "engagement_rate": en0}
        new = {"pickup_rate": pk1, "engagement_rate": en1}
        noise = {"pickup_rate": se(0), "engagement_rate": se(1)}
        out = {"pickup_now": round(pk0, 4), "pickup_projected": round(pk1, 4), "engagement_now": round(en0, 4),
               "engagement_projected": round(en1, 4),
               "se": {k_: round(v, 4) for k_, v in noise.items()},
               "pooled": {"pickup": round(p_pick, 4), "engagement": round(p_eng, 4)},
               "primary_kpi": primary, "guardrail_kpi": guard, "ok": True, "why": "ok"}
        if new[primary] < now[primary] - P.DID_PRIMARY_TOL - P.DID_PROJ_Z * noise[primary]:
            out.update(ok=False, why=f"projected {primary} {new[primary]:.3f} < {now[primary]:.3f} "
                                     f"(beyond {P.DID_PROJ_Z:g} SE = {noise[primary]:.3f})")
        elif new[guard] < now[guard] - max_drop:
            out.update(ok=False, why=f"projected {guard} drop {now[guard] - new[guard]:.3f} > max {max_drop}")
        return out

    # ------------------------------------------------------------------ hallucination incidents (C8)
    def halluc(self, wid, cur, credits):
        base = self.kv(f"baseline:{wid}")
        inc = self.kv(f"incident:{wid}")
        cp = cur["config"]["prompt_version"]
        p0 = base["flag_rate"]
        limit = max(2 * p0, p0 + 0.01)
        w = self.window(wid, P.HALLUC_WINDOW_HOURS, "prompt")
        _, conn, eng, flags = w.get(cp) or (0, 0, 0, 0)
        if inc and inc["status"] == "verifying":
            since = self.post_change(wid, cp, inc["applied_minute"], inc.get("applied_version"))
            if since and since[1] >= P.VERIFY_MIN_CONNECTED:
                fr, er = since[3] / since[1], since[2] / since[1]
                ez = binom_z(since[2], since[1], base["engage"])
                drop = self.objective(wid)[2] if self.objective(wid)[1] == "engagement_rate" else P.GUARDRAIL_SLACK
                ok_flags = fr <= limit
                # fail only on a drop that is both material (beyond the guardrail) and statistically clear
                ok_eng = not (er < base["engage"] - drop and ez <= -2)
                inc.update(status="resolved" if ok_flags and ok_eng else "open", verify={
                    "flag_rate": round(fr, 4), "engagement": round(er, 3), "engage_z_vs_baseline": round(ez, 2),
                    "connected": since[1], "ok_flags": ok_flags, "ok_engagement": ok_eng})
                if inc["status"] == "open":
                    inc.setdefault("tried", []).append(cp)
                    inc["bad_prompt"] = cp
                    inc["reopened"] = inc.get("reopened", 0) + 1
                    inc.pop("candidate", None)
                self.s.set(f"incident:{wid}", inc)
                self.s.decide(wid, "incident_verified" if inc["status"] == "resolved" else "incident_reopened",
                              f"after fix {cp}: QA flag rate {fr:.2%} (limit {limit:.2%}), engagement {er:.1%} "
                              f"(baseline {base['engage']:.1%})", inc)
            if inc["status"] != "open":
                return None
        if not inc or inc["status"] == "resolved":
            if conn < P.HALLUC_MIN_CONNECTED or flags / conn <= limit or binom_z(flags, conn, p0) < P.HALLUC_Z:
                return None
            # An 8h spike on a prompt with a long clean record is usually noise: demand a much stronger signal.
            ac, af = self.s.one("SELECT SUM(conn), SUM(flags) FROM agg WHERE wf=? AND prompt=?", (wid, cp))
            if ac and ac >= 3 * conn and af / ac <= limit and binom_z(flags, conn, p0) < P.HALLUC_Z_ESTABLISHED:
                key = f"halluc_noise:{wid}:{self.s.now_minute // 1440}"
                if not self.kv(key):
                    self.s.set(key, 1)
                    self.s.decide(wid, "incident_suppressed", f"{cp} spike {flags}/{conn} in {P.HALLUC_WINDOW_HOURS}h "
                                  f"but {af}/{ac} = {af / ac:.2%} over its whole run; watching",
                                  {"window": [flags, conn], "lifetime": [af, ac]})
                return None
            inc = {"status": "open", "bad_prompt": cp, "opened_minute": self.s.now_minute, "tried": [cp],
                   "detected": {"flags": flags, "connected": conn, "rate": round(flags / conn, 4), "baseline": p0,
                                "z": round(binom_z(flags, conn, p0), 2)}}
            self.s.set(f"incident:{wid}", inc)
            self.s.decide(wid, "incident_opened", f"hallucination flags on {cp}: {flags}/{conn} = "
                          f"{flags / conn:.2%} vs baseline {p0:.2%} over {P.HALLUC_WINDOW_HOURS}h", inc)
        if inc["status"] != "open":
            return None
        if cp != inc["bad_prompt"]:
            inc["bad_prompt"] = cp
        cand = inc.get("candidate")
        if not cand:
            cand = self._pick_fix(wid, inc, credits)
            if not cand:
                if not inc.get("escalated"):
                    inc["escalated"] = self.s.now_minute
                    self.s.decide(wid, "incident_escalated", f"no validated fix for {cp} (tried {inc.get('tried')}); "
                                  "needs a human: supervisor / on-call notified via the daily summary", inc)
                self.s.set(f"incident:{wid}", inc)
                return None
            inc["candidate"] = cand
            self.s.set(f"incident:{wid}", inc)
        return {"type": "prompt", "prompt_version": cand["prompt"], "key": "prompt",
                "summary": f"revert prompt {cp} -> {cand['prompt']} (hallucination incident)",
                "rationale": f"QA hallucination flags on {cp} at {inc['detected']['rate']:.2%} vs baseline "
                             f"{p0:.2%} (z={inc['detected']['z']}); {cand['prompt']} {cand['why']}; "
                             f"validation pass rate {cand['pass_rate']:.3f}",
                "impact": 0.9, "api_evidence": {"validation_run_id": cand["validation_run_id"]},
                "dry_run": {"observed_flag_rate": cand.get("observed"), "validation": cand},
                "evidence": inc["detected"]}

    def post_change(self, wid, prompt, applied_minute, applied_version):
        """(dials, conn, eng, flags) for `prompt` using only complete hourly buckets that start at or after the
        change was applied and calls made on the applied config version or later."""
        first_h = -(-applied_minute // 60)
        r = self.s.one("SELECT SUM(dials), SUM(conn), SUM(eng), SUM(flags) FROM agg WHERE wf=? AND prompt=? "
                       "AND day*24+hour>=? AND day*24+hour<? AND cfg_ver>=?",
                       (wid, prompt, first_h, self.s.now_minute // 60, applied_version or 0))
        return None if r[0] is None else r

    def _validate(self, wid, pv, credits):
        cache = self.kv(f"validations:{wid}") or {}
        if pv in cache:
            return cache[pv]
        cost = math.ceil(P.VALIDATION_N / 100)
        if credits - cost < 0:
            return None
        try:
            r = self.sim.post("/validation/runs", {"workflow_id": wid, "prompt_version": pv, "n": P.VALIDATION_N})
        except SimError as e:
            self.s.decide(wid, "validation_failed", f"validation of {pv} failed: {e.code}")
            return None
        cache[pv] = {"validation_run_id": r["validation_run_id"], "pass_rate": r["pass_rate"], "n": r["n"]}
        self.s.set(f"validations:{wid}", cache)
        self.s.decide(wid, "validation_run", f"validated {pv}: pass rate {r['pass_rate']:.3f} on n={r['n']} "
                      f"({cost} credits)", r)
        return cache[pv]

    def _pick_fix(self, wid, inc, credits):
        base = self.kv(f"baseline:{wid}")
        need = self.wfs[wid]["governance"].get("min_validation_pass_rate", 0.97)
        tried = set(inc.get("tried", []))
        # 1) prompts we have actually run, with a clean QA record, best engagement first
        rows = self.s.q("SELECT prompt, SUM(conn), SUM(eng), SUM(flags) FROM agg WHERE wf=? GROUP BY prompt", (wid,))
        good = sorted([(e / c, p, f / c) for p, c, e, f in rows
                       if p not in tried and c >= 300 and f / c <= max(1.3 * base["flag_rate"], base["flag_rate"] + 0.005)],
                      reverse=True)
        for er, p, fr in good:
            v = self._validate(wid, p, credits)
            if v and v["pass_rate"] >= need:
                return {"prompt": p, "why": f"is the last known-good prompt (observed flag rate {fr:.2%}, "
                        f"engagement {er:.1%})", "observed": round(fr, 4), **v}
        # 2) ask the LLM for alternatives, validate them, pick the safest
        if inc.get("llm_asked"):
            return None
        if credits < 3 + 2:
            self.s.decide(wid, "credits_low", "not enough credits for LLM + validation; incident stays open")
            return None
        inc["llm_asked"] = True
        try:
            r = self.sim.post("/llm/suggest-fixes", {"workflow_id": wid, "problem":
                              f"hallucination flag rate {inc['detected']['rate']:.2%} on {inc['bad_prompt']}"})
        except SimError as e:
            self.s.decide(wid, "llm_failed", f"suggest-fixes failed: {e.code}")
            return None
        self.s.decide(wid, "llm_suggest", f"LLM suggested {[x['prompt_version'] for x in r['suggestions']]}", r)
        best = None
        for sug in r["suggestions"]:
            if sug["prompt_version"] in tried:
                continue
            v = self._validate(wid, sug["prompt_version"], credits - 3)
            if v and v["pass_rate"] >= need and (not best or v["pass_rate"] > best["pass_rate"]):
                best = {"prompt": sug["prompt_version"], "why": f"was suggested by the LLM ({sug['summary']})",
                        **v}
        return best

    # ------------------------------------------------------------------ experiments (C6, C7)
    def experiments(self, wid, cur):
        if (self.kv(f"incident:{wid}") or {}).get("status") in ("open", "fix_req", "verifying"):
            return None
        for row in self.s.q("SELECT exp_id, dim, control, challenger, share, status, start_version, result "
                            "FROM experiments WHERE wf=? AND status IN ('running','promoted','want_start',"
                            "'want_promote','want_stop','want_rollback')", (wid,)):
            it = self._exp_step(wid, cur, *row)
            if it:
                return it
        if self.s.one("SELECT 1 FROM experiments WHERE wf=? AND status IN (%s)" % ",".join("?" * len(ACTIVE)),
                      (wid, *ACTIVE)):
            return None
        if self.end_minute is not None and self.end_minute - self.s.now_minute < 2 * 1440:
            return None
        return self._new_experiment(wid, cur)

    def _new_experiment(self, wid, cur):
        for dim in AGENT_DIMS:
            if self.kv(f"cooldown:{wid}:{dim}", -1) > self.s.now_minute:
                continue
            if self.s.one("SELECT 1 FROM experiments WHERE wf=? AND dim=? AND status IN ('promoted','want_rollback',"
                          "'rollback_req')", (wid, dim)):
                continue
            d = configs.dist(cur["config"], "default", dim)
            if len(d) != 1:
                continue
            inc = next(iter(d))
            tested = {r[0] for r in self.s.q("SELECT challenger FROM experiments WHERE wf=? AND dim=? AND control=?",
                                             (wid, dim, inc))}
            for ch in self.wfs[wid]["options"][dim]:
                if ch == inc or ch in tested:
                    continue
                exp_id = f"{wid}:{dim}:{ch}-vs-{inc}:{self.s.now_minute}"
                self.s.db.execute("INSERT INTO experiments(exp_id, wf, dim, control, challenger, share, status, "
                                  "start_minute) VALUES(?,?,?,?,?,?,?,?)",
                                  (exp_id, wid, dim, inc, ch, P.EXPLORE_SHARE, "want_start", self.s.now_minute))
                self.s.decide(wid, "experiment_planned", f"plan {dim} test: {ch} at {P.EXPLORE_SHARE:.0%} vs "
                              f"incumbent {inc}", {"exp_id": exp_id})
                return self._exp_intent(wid, exp_id, dim, inc, ch, "start")
        return None

    def _exp_intent(self, wid, exp_id, dim, control, ch, action, stats=None):
        dists = {"start": {control: 1 - P.EXPLORE_SHARE, ch: P.EXPLORE_SHARE},
                 "promote": {ch: 1 - P.HOLDOUT_SHARE, control: P.HOLDOUT_SHARE},
                 "stop": {control: 1.0}, "rollback": {control: 1.0}}
        lift = (stats or {}).get("rel_lift", 0) or 0
        impact = {"start": 0.15, "stop": 0.2, "rollback": 0.7, "promote": min(1.0, 0.3 + 3 * max(lift, 0))}[action]
        words = {"start": f"try {dim} {ch} on {P.EXPLORE_SHARE:.0%} of calls (control {control})",
                 "promote": f"promote {dim} {ch} to {1 - P.HOLDOUT_SHARE:.0%}, keep {control} as {P.HOLDOUT_SHARE:.0%} "
                            "holdout",
                 "stop": f"stop {dim} test of {ch}, back to {control}",
                 "rollback": f"roll back {dim} {ch} -> {control} (winner stopped winning)"}[action]
        rationale = {"start": f"bounded exploration: one challenger, {P.EXPLORE_SHARE:.0%} of traffic, worst case "
                              f"for a 10% worse variant is ~{P.EXPLORE_SHARE * 10:.0f}% x 10% = 1% engagement",
                     "promote": f"challenger beat control on the primary KPI "
                                f"({self.wfs[wid]['objective']['primary']}) with a Bonferroni-corrected one-sided "
                                "z-test; guardrail KPI within its configured max drop",
                     "stop": "challenger did not beat control on the primary KPI (harm, guardrail or futility stop)",
                     "rollback": "after promotion the holdout now beats the promoted variant"}[action]
        return {"type": "alloc", "dim": dim, "cohort": "default", "dist": dists[action], "exp_id": exp_id,
                "action": action, "key": f"exp:{dim}", "summary": words, "rationale": rationale, "impact": impact,
                "dry_run": stats or self._replay(wid, dim, dists[action]), "evidence": stats}

    def _replay(self, wid, dim, new_dist):
        col = {"welcome_message": "wm", "voice": "voice"}[dim]
        w = self.window(wid, 72, col)
        cur = configs.dist(self.config(wid)["config"], "default", dim)
        inc_rate = None
        rates = {}
        for v, (d, c, e, f) in w.items():
            rates[v] = {"connected": c, "engagement": round(e / c, 4) if c else None}
        inc = max(cur, key=cur.get)
        inc_rate = (rates.get(inc) or {}).get("engagement")
        proj = sum(p * ((rates.get(v) or {}).get("engagement") or inc_rate or 0) for v, p in new_dist.items())
        now = sum(p * ((rates.get(v) or {}).get("engagement") or inc_rate or 0) for v, p in cur.items())
        return {"window": "last 72h", "observed": rates, "engagement_now": round(now, 4),
                "engagement_projected": round(proj, 4),
                "assumption": "unseen variants assumed equal to the incumbent"}

    def objective(self, wid) -> tuple[str, str, float]:
        """(primary KPI, guardrail KPI, max allowed absolute drop of the guardrail) from the workflow's objective."""
        obj = self.wfs[wid]["objective"]
        primary = obj["primary"]
        guard = obj.get("guardrail") or {}
        other = "engagement_rate" if primary == "pickup_rate" else "pickup_rate"
        return primary, other, float(guard.get(f"{other}_max_drop", P.GUARDRAIL_SLACK))

    @staticmethod
    def kpi(name, dials, conn, eng):
        """(successes, trials) for a KPI: pickup = connected / dials, engagement = engaged / connected."""
        return (conn, dials) if name == "pickup_rate" else (eng, conn)

    def _arm_stats(self, wid, dim, control, ch, version, hours=None):
        col = {"welcome_message": "wm", "voice": "voice"}[dim]
        w = self.since_version(wid, col, version, hours)
        cd, cc, ce, _ = w.get(control) or (0, 0, 0, 0)
        xd, xc, xe, _ = w.get(ch) or (0, 0, 0, 0)
        primary, guard, max_drop = self.objective(wid)
        cs, cn = self.kpi(primary, cd, cc, ce)
        xs, xn = self.kpi(primary, xd, xc, xe)
        gcs, gcn = self.kpi(guard, cd, cc, ce)
        gxs, gxn = self.kpi(guard, xd, xc, xe)
        z = two_prop_z(xs, xn, cs, cn)
        g_ctl, g_ch = rate(gcs, gcn), rate(gxs, gxn)
        return {"control": control, "challenger": ch, "primary_kpi": primary, "guardrail_kpi": guard,
                "guardrail_max_drop": max_drop,
                "control_n": cn, "control_x": cs, "challenger_n": xn, "challenger_x": xs,
                "control_rate": round(cs / cn, 4) if cn else None,
                "challenger_rate": round(xs / xn, 4) if xn else None, "z": round(z, 3),
                "rel_lift": round((xs / xn) / (cs / cn) - 1, 4) if cn and xn and cs else None,
                "guardrail_control": round(g_ctl, 4) if g_ctl is not None else None,
                "guardrail_challenger": round(g_ch, 4) if g_ch is not None else None,
                "guardrail_z": round(two_prop_z(gxs, gxn, gcs, gcn), 3),
                "control_conn": cc, "challenger_conn": xc, "control_dials": cd, "challenger_dials": xd}

    @staticmethod
    def guardrail_ok(st) -> bool:
        """The challenger's guardrail KPI must be measurable and not more than max_drop below control."""
        if st["guardrail_control"] is None or st["guardrail_challenger"] is None:
            return False
        return st["guardrail_challenger"] >= st["guardrail_control"] - st["guardrail_max_drop"]

    def _exp_step(self, wid, cur, exp_id, dim, control, ch, share, status, start_version, result):
        if status.startswith("want_"):
            action = status[5:]
            res = json.loads(result or "{}")
            return self._exp_intent(wid, exp_id, dim, control, ch, action, res.get("stats"))
        if status == "running":
            st = self._arm_stats(wid, dim, control, ch, start_version)
            k = max(len(self.wfs[wid]["options"][dim]) - 1, 1)
            zc = norm_ppf(1 - P.FAMILY_ALPHA / k)
            # sample sizes are counted in the primary KPI's trials (dials for pickup, connected calls for engagement)
            scale = P.PICKUP_TRIALS_FACTOR if st["primary_kpi"] == "pickup_rate" else 1
            n = st["challenger_n"]
            guard_ok = self.guardrail_ok(st)
            verdict = None
            if n >= P.HARM_MIN_CONNECTED * scale and st["z"] <= P.HARM_Z:
                verdict, action = "harm", "stop"
            elif n >= P.HARM_MIN_CONNECTED * scale and st["guardrail_z"] <= P.GUARD_STOP_Z and not guard_ok:
                verdict, action = "guardrail_breach", "stop"
            elif n >= P.MIN_ARM_CONNECTED * scale and st["z"] >= zc and guard_ok:
                verdict, action = "win", "promote"
            elif n >= P.FUTILITY_CONNECTED * scale:
                verdict, action = "no_effect", "stop"
            if not verdict:
                return None
            st["z_crit"] = round(zc, 3)
            self.s.db.execute("UPDATE experiments SET status=?, result=? WHERE exp_id=?",
                              (f"want_{action}", json.dumps({"verdict": verdict, "stats": st}), exp_id))
            self.s.decide(wid, f"experiment_{verdict}", f"{exp_id}: {ch} {st['challenger_rate']} vs {control} "
                          f"{st['control_rate']} on {st['primary_kpi']} (z={st['z']}, crit {st['z_crit']}, n={n}); guardrail "
                          f"{st['guardrail_kpi']} {st['guardrail_challenger']} vs {st['guardrail_control']}", st)
            return self._exp_intent(wid, exp_id, dim, control, ch, action, st)
        if status == "promoted":
            res = json.loads(result or "{}")
            st = self._arm_stats(wid, dim, control, ch, res.get("promote_version") or start_version,
                                 P.DECAY_WINDOW_HOURS)
            scale = P.PICKUP_TRIALS_FACTOR if st["primary_kpi"] == "pickup_rate" else 1
            if st["control_n"] >= P.DECAY_MIN_CONNECTED * scale and st["z"] <= P.DECAY_Z:
                # rolling back moves traffic to the holdout, so the holdout must pass the guardrail against the winner
                g_hold, g_win = st["guardrail_control"], st["guardrail_challenger"]
                if g_hold is not None and g_win is not None and g_hold < g_win - st["guardrail_max_drop"]:
                    if not res.get("rollback_blocked"):
                        res["rollback_blocked"] = st
                        self.s.db.execute("UPDATE experiments SET result=? WHERE exp_id=?", (json.dumps(res), exp_id))
                        self.s.decide(wid, "rollback_blocked", f"{exp_id}: holdout {control} leads on {st['primary_kpi']} "
                                      f"(z={st['z']}) but its {st['guardrail_kpi']} {g_hold} is more than "
                                      f"{st['guardrail_max_drop']} below {ch} {g_win}; keeping {ch}", st)
                    return None
                res["decay"] = st
                self.s.db.execute("UPDATE experiments SET status='want_rollback', result=? WHERE exp_id=?",
                                  (json.dumps(res), exp_id))
                self.s.decide(wid, "decay_detected", f"{exp_id}: promoted {ch} now {st['challenger_rate']} vs "
                              f"holdout {control} {st['control_rate']} on {st['primary_kpi']} over {P.DECAY_WINDOW_HOURS}h (z={st['z']})", st)
                return self._exp_intent(wid, exp_id, dim, control, ch, "rollback", st)
        return None
