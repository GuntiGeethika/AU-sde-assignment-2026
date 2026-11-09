"""Governance client: proposal lifecycle against /approvals and auto-apply, persisted before every POST.

States (proposals.status):
  submitting -> pending -> approved -> applying -> applied
                        -> rejected | expired
             approved   -> lapsed | stale (base moved, e.g. a supervisor edit)
  submitting -> failed (POST refused) | abandoned (crash before the POST registered)
  auto: submitting -> applied | refused
"""
from __future__ import annotations

import json
import logging
import uuid

from . import configs
from .api import SimError
from .policy import TENANT_OVERRIDES
from .store import Store

log = logging.getLogger("controller.gov")
OPEN = ("submitting", "pending", "approved", "applying")


class Governance:
    def __init__(self, store: Store, sim, wfs: dict, on_closed):
        self.s, self.sim, self.wfs = store, sim, wfs
        self.on_closed = on_closed  # callback(proposal_row_dict, final_status)

    # ------------------------------------------------------------------ helpers
    def gov(self, wid):
        return self.wfs[wid]["governance"]

    def row(self, pid) -> dict | None:
        r = self.s.one("SELECT proposal_id, wf, path, status, base_version, config, request, intents, approval_id, "
                       "applied_version, reasons, created_minute FROM proposals WHERE proposal_id=?", (pid,))
        if not r:
            return None
        keys = ["proposal_id", "wf", "path", "status", "base_version", "config", "request", "intents",
                "approval_id", "applied_version", "reasons", "created_minute"]
        d = dict(zip(keys, r))
        d["intents"] = json.loads(d["intents"] or "[]")
        return d

    def _set(self, pid, **kw):
        sets = ", ".join(f"{k}=?" for k in kw) + ", updated_ts=?"
        self.s.db.execute(f"UPDATE proposals SET {sets} WHERE proposal_id=?", (*kw.values(), self.s.now_ts, pid))

    def open_for(self, wid, path="approval"):
        return [r[0] for r in self.s.q("SELECT proposal_id FROM proposals WHERE wf=? AND path=? AND status IN "
                                       "('submitting','pending','approved','applying')", (wid, path))]

    def requests_last_24h(self, wid) -> int:
        return self.s.one("SELECT COUNT(*) FROM proposals WHERE wf=? AND path='approval' AND status NOT IN "
                          "('failed','abandoned') AND created_minute > ?", (wid, self.s.now_minute - 1440))[0]

    def can_request(self, wid, urgent=False) -> tuple[bool, str]:
        g = self.gov(wid)
        ov = TENANT_OVERRIDES.get(self.wfs[wid]["tenant_id"], {})
        lo, hi = g["approver_hours"]
        lo = max(lo, ov.get("earliest_request_hour", lo))
        now = self.s.now_minute
        hour = (now % 1440) // 60
        cap = min(g["max_requests_per_24h"], ov.get("max_requests_per_24h", 99))
        used = self.requests_last_24h(wid)
        # keep one slot for incidents when the cap allows it
        if used >= (cap if urgent or cap < 3 else cap - 1):
            return False, f"request budget used ({used}/{cap} in 24h)"
        if not urgent and self.open_for(wid):
            return False, "a request is already open for this workflow"
        if not lo <= hour < hi:
            if not urgent:
                return False, f"outside approver hours [{lo},{hi})"
        # worst-case decision time must land before the proposal expires
        worst = now + g["approver_latency_minutes"][1]
        day, mod = divmod(worst, 1440)
        if mod < g["approver_hours"][0] * 60:
            worst = day * 1440 + g["approver_hours"][0] * 60
        elif mod >= g["approver_hours"][1] * 60:
            worst = (day + 1) * 1440 + g["approver_hours"][0] * 60
        if worst > now + g["proposal_ttl_hours"] * 60 - 15:
            return False, "approver could not decide before the request expires"
        return True, "ok"

    def auto_allowed(self, wid, dims: set[str], shift: float) -> bool:
        a = self.gov(wid)["auto_apply"]
        return bool(a.get("enabled")) and dims <= set(a.get("allowed_dims", [])) and shift <= a.get("max_shift", 0) + 1e-9

    # ------------------------------------------------------------------ submit
    def _insert(self, pid, wid, path, base_version, cfg, request, intents, parent=None):
        self.s.db.execute("INSERT INTO proposals(proposal_id, wf, path, status, base_version, config, request, intents,"
                          " created_minute, created_ts, updated_ts, parent_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                          (pid, wid, path, "submitting", base_version, json.dumps(cfg), json.dumps(request, default=str),
                           json.dumps(intents), self.s.now_minute, self.s.now_ts, self.s.now_ts, parent))

    def request(self, wid, base: dict, new_cfg: dict, intents: list[dict], meta: dict) -> str | None:
        pid = f"{wid}-{self.s.now_minute}-{uuid.uuid4().hex[:8]}"
        body = {"proposal_id": pid, "workflow_id": wid, "base_version": base["version"], "proposed_config": new_cfg,
                **meta}
        self._insert(pid, wid, "approval", base["version"], new_cfg, {k: v for k, v in body.items()
                                                                      if k != "proposed_config"}, intents)
        try:
            r = self.sim.post("/approvals", body)
        except SimError as e:
            self._set(pid, status="failed", reasons=json.dumps([e.code, e.detail], default=str))
            self.s.decide(wid, "request_failed", f"approval request refused: {e.code}", {"detail": e.detail},
                          proposal_id=pid)
            self.on_closed(self.row(pid), "failed")
            return None
        self._set(pid, status="pending", approval_id=r["approval_id"])
        self.s.decide(wid, "request_sent", meta["change_summary"],
                      {"approval_id": r["approval_id"], "expires_at": r.get("expires_at"), "intents": intents,
                       "impact_score": meta["impact_score"], "affected_leads": meta["affected_leads"],
                       "dry_run": meta["dry_run"], "rationale": meta["rationale"]}, proposal_id=pid)
        return pid

    def auto_apply(self, wid, base: dict, new_cfg: dict, intents: list[dict], rationale: str, evidence: dict):
        pid = f"{wid}-{self.s.now_minute}-auto-{uuid.uuid4().hex[:8]}"
        body = {"proposal_id": pid, "base_version": base["version"], "proposed_config": new_cfg,
                "rationale": rationale, "evidence": evidence}
        self._insert(pid, wid, "auto", base["version"], new_cfg, {"rationale": rationale, "evidence": evidence},
                     intents)
        try:
            r = self.sim.put(f"/workflows/{wid}/config", body)
        except SimError as e:
            self._set(pid, status="refused", reasons=json.dumps([e.code, e.detail], default=str))
            self.s.decide(wid, "auto_apply_refused", f"auto-apply refused: {e.code}", {"detail": e.detail},
                          proposal_id=pid)
            return None
        self._set(pid, status="applied", applied_version=r["version"])
        self.s.decide(wid, "auto_applied", rationale, {"version": r["version"], "intents": intents,
                                                       "evidence": evidence}, proposal_id=pid)
        self.on_closed(self.row(pid), "applied")
        return r["version"]

    # ------------------------------------------------------------------ poll / apply
    def poll(self):
        for (pid,) in self.s.q("SELECT proposal_id FROM proposals WHERE path='approval' AND status IN "
                               "('pending','approved','applying')"):
            p = self.row(pid)
            a = self.sim.get(f"/approvals/{p['approval_id']}")
            st = a["status"]
            if st == "pending":
                continue
            if st in ("rejected", "expired", "lapsed"):
                self._close(p, st, a.get("reasons"))
            elif st == "applied":  # we applied it but crashed before recording
                self._applied(p, a.get("applied_version"))
            elif st == "approved":
                self._apply(p)

    def _apply(self, p):
        self._set(p["proposal_id"], status="applying")
        try:
            r = self.sim.post(f"/workflows/{p['wf']}/apply", {"approval_id": p["approval_id"]})
        except SimError as e:
            if e.code == "stale_base_version":
                self._close(p, "stale", [f"config moved to v{(e.detail or {}).get('current_version')} "
                                         f"after we proposed on v{p['base_version']}"])
            elif e.code == "approval_lapsed":
                self._close(p, "lapsed", ["not applied within apply window"])
            elif e.code == "not_approved":
                a = self.sim.get(f"/approvals/{p['approval_id']}")
                if a["status"] == "applied":
                    self._applied(p, None)
                else:
                    self._close(p, a["status"], a.get("reasons"))
            else:
                raise
            return
        self._applied(p, r["version"])

    def _applied(self, p, version):
        self._set(p["proposal_id"], status="applied", applied_version=version)
        self.s.decide(p["wf"], "applied", f"applied approval {p['approval_id']} as v{version}",
                      {"intents": p["intents"]}, proposal_id=p["proposal_id"])
        p["applied_version"] = version
        self.on_closed(p, "applied")

    def _close(self, p, status, reasons):
        self._set(p["proposal_id"], status=status, reasons=json.dumps(reasons or []))
        self.s.decide(p["wf"], f"proposal_{status}", f"approval {p['approval_id']} {status}",
                      {"reasons": reasons, "intents": p["intents"]}, proposal_id=p["proposal_id"])
        self.on_closed(p, status)

    # ------------------------------------------------------------------ crash recovery
    def reconcile(self):
        """Resolve proposals left in 'submitting' by a crash, using the simulator as the source of truth."""
        for (pid,) in self.s.q("SELECT proposal_id FROM proposals WHERE status='submitting'"):
            p = self.row(pid)
            if p["path"] == "approval":
                match = [a for a in self.sim.get("/approvals", params={"workflow_id": p["wf"]})
                         if a["proposal_id"] == pid]
                if match:
                    self._set(pid, status="pending", approval_id=match[0]["approval_id"])
                    self.s.decide(p["wf"], "recovered", f"re-attached to {match[0]['approval_id']} after restart",
                                  proposal_id=pid)
                    continue
            else:
                hist = self.sim.get(f"/workflows/{p['wf']}/config/history")
                match = [h for h in hist if h["proposal_id"] == pid]
                if match:
                    self._set(pid, status="applied", applied_version=match[0]["version"])
                    self.s.decide(p["wf"], "recovered", f"auto-apply {pid} had landed as v{match[0]['version']}",
                                  proposal_id=pid)
                    p["applied_version"] = match[0]["version"]
                    self.on_closed(p, "applied")
                    continue
            self._set(pid, status="abandoned")
            self.s.decide(p["wf"], "recovered", "proposal never reached the simulator; will re-plan", proposal_id=pid)
            self.on_closed(p, "abandoned")
        for (pid,) in self.s.q("SELECT proposal_id FROM proposals WHERE status='applying'"):
            self._set(pid, status="approved")  # poll() re-checks and applies at most once
