"""Regression tests for the audit corrections: primary-KPI experiments, caller-ID projection safety,
governance timing, post-change incident verification and Windows-safe memory metrics."""
import builtins
import importlib


from controller.governance import Governance
from controller.planner import Planner
from controller.store import Store


def wf(wid, primary, tenant="t", hours=(10, 19), latency=(5, 120), ttl=12, cap=4):
    guard = "engagement_rate" if primary == "pickup_rate" else "pickup_rate"
    return {"workflow_id": wid, "tenant_id": tenant, "cadence": [0, 1, 2],
            "objective": {"primary": primary, "guardrail": {f"{guard}_max_drop": 0.02}},
            "options": {"welcome_message": ["W1", "W2"], "voice": ["V1"], "caller_id": ["D1", "D2", "D3"]},
            "governance": {"approver_hours": list(hours), "approver_latency_minutes": list(latency),
                           "proposal_ttl_hours": ttl, "max_requests_per_24h": cap,
                           "auto_apply": {"enabled": False}}}


def planner(tmp_path, *wfs):
    s = Store(str(tmp_path / "c.db"))
    s.now_minute, s.now_ts = 3 * 1440 + 12 * 60, "D3 12:00"
    return Planner(s, None, {w["workflow_id"]: w for w in wfs}), s


def add(s, wf_, wm, dials, conn, eng, flags=0, day=3, hour=10, did="D1", prompt="P1", ver=2):
    s.db.execute("INSERT INTO agg VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (wf_, day, hour, "x|y", wm, "V1", did, prompt, ver, dials, conn, eng, flags))


# ---------------------------------------------------------------- 1. experiment KPI
def test_pickup_primary_is_tested_on_pickup(tmp_path):
    pl, s = planner(tmp_path, wf("k", "pickup_rate"))
    add(s, "k", "W1", 10000, 2500, 1500)   # pickup 25%, engagement 60%
    add(s, "k", "W2", 3000, 900, 540)      # pickup 30%, engagement 60%
    st = pl._arm_stats("k", "welcome_message", "W1", "W2", 1)
    assert st["primary_kpi"] == "pickup_rate" and st["challenger_n"] == 3000
    assert st["challenger_rate"] == 0.3 and st["z"] > 4
    assert st["guardrail_kpi"] == "engagement_rate" and pl.guardrail_ok(st)


def test_engagement_primary_is_tested_on_engagement(tmp_path):
    pl, s = planner(tmp_path, wf("e", "engagement_rate"))
    add(s, "e", "W1", 4000, 1000, 500)
    add(s, "e", "W2", 4000, 1000, 600)
    st = pl._arm_stats("e", "welcome_message", "W1", "W2", 1)
    assert st["challenger_n"] == 1000 and st["challenger_rate"] == 0.6 and st["z"] > 4


def test_guardrail_breach_blocks_promotion(tmp_path):
    pl, s = planner(tmp_path, wf("e", "engagement_rate"))
    add(s, "e", "W1", 4000, 1200, 600)     # pickup 30%, engagement 50%
    add(s, "e", "W2", 4000, 1000, 600)     # pickup 25% (-5 pts), engagement 60%
    s.db.execute("INSERT INTO experiments(exp_id, wf, dim, control, challenger, share, status, start_version) "
                 "VALUES('x','e','welcome_message','W1','W2',0.08,'running',1)")
    it = pl._exp_step("e", None, "x", "welcome_message", "W1", "W2", 0.08, "running", 1, None)
    assert it["action"] == "stop"
    assert s.one("SELECT status FROM experiments WHERE exp_id='x'")[0] == "want_stop"


def test_moderate_guardrail_breach_blocks_promotion_without_stopping(tmp_path):
    pl, s = planner(tmp_path, wf("e", "engagement_rate"))
    add(s, "e", "W1", 4000, 1200, 600)     # pickup 30%, engagement 50%
    add(s, "e", "W2", 1000, 260, 180)      # pickup 26% (z about -2.5), engagement 69%: would win on primary
    s.db.execute("INSERT INTO experiments(exp_id, wf, dim, control, challenger, share, status, start_version) "
                 "VALUES('x','e','welcome_message','W1','W2',0.08,'running',1)")
    assert pl._exp_step("e", None, "x", "welcome_message", "W1", "W2", 0.08, "running", 1, None) is None
    assert s.one("SELECT status FROM experiments WHERE exp_id='x'")[0] == "running"


def test_rollback_blocked_when_holdout_breaks_guardrail(tmp_path):
    pl, s = planner(tmp_path, wf("k", "pickup_rate"))
    add(s, "k", "W1", 3000, 1050, 525)     # holdout: pickup 35%, engagement 50%
    add(s, "k", "W2", 9000, 2700, 1800)    # winner: pickup 30%, engagement 67%
    res = '{"promote_version": 1}'
    s.db.execute("INSERT INTO experiments(exp_id, wf, dim, control, challenger, share, status, start_version, result) "
                 "VALUES('x','k','welcome_message','W1','W2',0.9,'promoted',1,?)", (res,))
    assert pl._exp_step("k", None, "x", "welcome_message", "W1", "W2", 0.9, "promoted", 1, res) is None
    assert s.one("SELECT status FROM experiments WHERE exp_id='x'")[0] == "promoted"
    assert s.one("SELECT COUNT(*) FROM decisions WHERE kind='rollback_blocked'")[0] == 1


def test_missing_guardrail_data_blocks_promotion():
    st = {"guardrail_control": None, "guardrail_challenger": 0.3, "guardrail_max_drop": 0.02}
    assert not Planner.guardrail_ok(st)


# ---------------------------------------------------------------- 2. caller-ID projection
def test_did_projection_blocks_damaging_mix(tmp_path):
    pl, _ = planner(tmp_path, wf("k", "pickup_rate"))
    per = {"D1": (3000, 1050, 600), "D2": (3000, 600, 360)}      # D1 35% pickup, D2 20%
    pooled = (6000, 1650, 960)
    bad = pl.did_projection("k", {"D1": 0.8, "D2": 0.2}, {"D1": 0.3, "D2": 0.7}, per, pooled)
    good = pl.did_projection("k", {"D1": 0.3, "D2": 0.7}, {"D1": 0.8, "D2": 0.2}, per, pooled)
    assert not bad["ok"] and good["ok"]


def test_did_projection_ignores_differences_within_noise(tmp_path):
    pl, _ = planner(tmp_path, wf("k", "engagement_rate"))
    per = {"D1": (700, 210, 112), "D2": (700, 210, 100)}       # 53% vs 48% engagement on ~200 calls each: noise
    pr = pl.did_projection("k", {"D1": 0.7, "D2": 0.3}, {"D1": 0.4, "D2": 0.6}, per, (1400, 420, 212))
    assert pr["ok"], pr["why"]


def test_did_projection_uses_pooled_rate_for_unseen_numbers(tmp_path):
    pl, _ = planner(tmp_path, wf("k", "engagement_rate"))
    per = {"D1": (3000, 900, 450)}
    pooled = (3000, 900, 450)
    pr = pl.did_projection("k", {"D1": 1.0}, {"D1": 0.9, "D3": 0.1}, per, pooled)
    assert pr["ok"] and abs(pr["pickup_projected"] - pr["pickup_now"]) < 1e-9


def test_did_projection_blocks_guardrail_violation(tmp_path):
    pl, _ = planner(tmp_path, wf("k", "pickup_rate"))
    per = {"D1": (5000, 1500, 900), "D2": (5000, 1600, 400)}     # D2 more pickup, much lower engagement
    pr = pl.did_projection("k", {"D1": 1.0}, {"D2": 1.0}, per, (10000, 3100, 1300))
    assert not pr["ok"] and "engagement_rate drop" in pr["why"]


def test_no_repeat_caller_id_change_without_new_dials(tmp_path):
    w = wf("k", "engagement_rate")
    pl, s = planner(tmp_path, w)
    s.set("did_status:k", {"D1": "healthy", "D2": "healthy", "D3": "healthy"})
    total = 600
    add(s, "k", "W1", 200, 60, 30, did="D1", hour=11)
    add(s, "k", "W1", 200, 60, 30, did="D2", hour=11)
    add(s, "k", "W1", 200, 60, 30, did="D3", hour=11)
    s.set("did_last_change:k", {"minute": s.now_minute - 1000, "dials": total - 10})
    cur = {"config": {"allocations": {"default": {"caller_id": {"D1": 1.0}}}}}
    assert pl.caller_id("k", cur) is None          # only 10 new dials since the last change
    s.set("did_last_change:k", {"minute": s.now_minute - 1000, "dials": 0})
    it = pl.caller_id("k", cur)
    assert it["dim"] == "caller_id"
    assert s.get("did_last_change:k")["dials"] == 0       # a computed-but-unsent change does not reset the clock
    pl.on_closed({"wf": "k", "proposal_id": "p1", "intents": [it]}, "rejected")
    assert s.get("did_last_change:k")["dials"] == 0       # a rejected request changed nothing
    s.now_minute += 240
    add(s, "k", "W1", 800, 240, 120, did="D1", hour=12)    # calls made while the approval was pending
    pl.on_closed({"wf": "k", "proposal_id": "p2", "intents": [it]}, "applied")
    mark = s.get("did_last_change:k")
    assert mark["minute"] == s.now_minute and mark["dials"] == total + 800   # clock starts at apply, not request
    assert pl.caller_id("k", cur) is None


def test_caller_id_suppressed_while_its_approval_is_pending(tmp_path):
    pl, s = planner(tmp_path, wf("k", "engagement_rate"))
    s.set("did_status:k", {"D1": "healthy", "D2": "healthy", "D3": "healthy"})
    for d in ("D1", "D2", "D3"):
        add(s, "k", "W1", 200, 60, 30, did=d, hour=11)
    cur = {"config": {"allocations": {"default": {"caller_id": {"D1": 1.0}}}}}
    it = pl.caller_id("k", cur)
    pl.gov._insert("p1", "k", "approval", 1, {}, {}, [it])
    pl.gov._set("p1", status="pending")
    assert pl.caller_id("k", cur) is None


def test_lost_caller_id_marker_recovered_from_applied_proposal(tmp_path):
    pl, s = planner(tmp_path, wf("k", "engagement_rate"))
    s.set("did_status:k", {"D1": "healthy", "D2": "healthy", "D3": "healthy"})
    for d in ("D1", "D2", "D3"):
        add(s, "k", "W1", 200, 60, 30, did=d, hour=11)
    cur = {"config": {"allocations": {"default": {"caller_id": {"D1": 1.0}}}}}
    it = pl.caller_id("k", cur)
    pl.gov._insert("p1", "k", "approval", 1, {}, {}, [it])
    pl.gov._set("p1", status="applied", applied_version=2)    # crashed before on_closed recorded the change
    assert pl.caller_id("k", cur) is None
    assert s.get("did_last_change:k") == {"minute": s.now_minute, "dials": 600, "proposal_id": "p1"}


# ---------------------------------------------------------------- 3. governance
def gov(tmp_path, minute, **kw):
    s = Store(str(tmp_path / "g.db"))
    s.now_minute, s.now_ts = minute, "t"
    w = wf("w", "engagement_rate", **kw)
    return Governance(s, None, {"w": w}, lambda p, st: None), s


def test_urgent_request_respects_approver_hours(tmp_path):
    g, _ = gov(tmp_path, 1440 + 8 * 60)
    ok, why = g.can_request("w", urgent=True)
    assert not ok and "approver hours" in why


def test_only_one_open_request_per_workflow(tmp_path):
    g, s = gov(tmp_path, 1440 + 11 * 60)
    g._insert("p1", "w", "approval", 1, {}, {}, [])
    s.db.execute("UPDATE proposals SET status='pending' WHERE proposal_id='p1'")
    for urgent in (False, True):
        ok, why = g.can_request("w", urgent=urgent)
        assert not ok and "already open" in why


def test_feasibility_uses_tenant_hours(tmp_path):
    s = Store(str(tmp_path / "k.db"))
    s.now_minute, s.now_ts = 1440 + 10 * 60 + 30, "t"
    w = wf("w", "engagement_rate", tenant="kestrel_finance")
    g = Governance(s, None, {"w": w}, lambda p, st: None)
    assert g.effective_hours("w") == (11, 19)
    ok, why = g.can_request("w")
    assert not ok and "approver hours" in why


def test_decision_deadline_follows_approver_hours():
    # 16:00 + 240 min = 20:00, after hours [10, 19) -> next day 10:00; within hours it is just now + latency
    assert Governance.decision_deadline(16 * 60, 240, 10, 19) == 1440 + 10 * 60
    assert Governance.decision_deadline(12 * 60, 30, 10, 19) == 12 * 60 + 30
    assert Governance.decision_deadline(9 * 60, 30, 10, 19) == 10 * 60


def test_request_refused_when_approver_cannot_decide_before_expiry(tmp_path):
    g, _ = gov(tmp_path, 1440 + 18 * 60 + 30, latency=(5, 240), ttl=4)
    ok, why = g.can_request("w")
    assert not ok and "expires" in why


# ---------------------------------------------------------------- 4. incident verification
def test_verification_ignores_pre_change_and_partial_buckets(tmp_path):
    pl, s = planner(tmp_path, wf("e", "engagement_rate"))
    applied = 3 * 1440 + 9 * 60 + 30                          # fix applied at 09:30, now 12:00
    add(s, "e", "W1", 900, 300, 100, flags=50, hour=9, prompt="P1", ver=5)    # same hour as apply: partial
    add(s, "e", "W1", 900, 300, 100, flags=50, hour=8, prompt="P1", ver=4)    # before the change
    add(s, "e", "W1", 900, 300, 150, flags=3, hour=10, prompt="P1", ver=5)
    add(s, "e", "W1", 900, 300, 150, flags=3, hour=11, prompt="P1", ver=5)
    add(s, "e", "W1", 900, 300, 100, flags=50, hour=12, prompt="P1", ver=5)   # current hour: incomplete
    assert pl.post_change("e", "P1", applied, 5) == (1800, 600, 300, 6)


def test_failed_verification_reopens_with_new_candidate(tmp_path):
    pl, s = planner(tmp_path, wf("e", "engagement_rate"))
    s.set("baseline:e", {"pickup": 0.3, "engage": 0.5, "flag_rate": 0.01})
    s.set("incident:e", {"status": "verifying", "bad_prompt": "P2", "tried": ["P2"], "candidate": {"prompt": "P1"},
                         "applied_minute": 3 * 1440 + 9 * 60, "applied_version": 5,
                         "detected": {"rate": 0.05, "z": 4}})
    add(s, "e", "W1", 1200, 400, 200, flags=40, hour=10, prompt="P1", ver=5)  # still 10% flags
    pl._pick_fix = lambda *a: None
    cur = {"config": {"prompt_version": "P1"}}
    assert pl.halluc("e", cur, 100) is None
    inc = s.get("incident:e")
    assert inc["status"] == "open" and "candidate" not in inc and "P1" in inc["tried"]
    assert inc["reopened"] == 1 and inc["escalated"]


# ---------------------------------------------------------------- 5. Windows
def test_controller_imports_without_resource_module(monkeypatch):
    import controller.__main__ as m
    real = builtins.__import__

    def fake(name, *a, **k):
        if name in ("resource", "psutil"):
            raise ImportError(name)
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    m2 = importlib.reload(m)
    assert m2.resource is None and m2.peak_rss_mb() is None
    monkeypatch.setattr(builtins, "__import__", real)
    importlib.reload(m)


class FakeSim:
    def __init__(self, version):
        self.version, self.posts = version, []

    def get(self, path):
        return {"version": self.version}

    def post(self, path, body):
        self.posts.append(path)
        return {"version": self.version + 1}


def test_approved_change_on_moved_config_is_not_applied(tmp_path):
    s = Store(str(tmp_path / "a.db"))
    s.now_minute, s.now_ts = 1440 + 11 * 60, "t"
    sim, closed = FakeSim(version=7), []
    g = Governance(s, sim, {"w": wf("w", "engagement_rate")}, lambda p, st: closed.append(st))
    g._insert("p1", "w", "approval", 6, {}, {}, [])
    s.db.execute("UPDATE proposals SET status='approved', approval_id='a1' WHERE proposal_id='p1'")
    g._apply(g.row("p1"))
    assert sim.posts == [] and closed == ["stale"]
    assert s.one("SELECT status FROM proposals WHERE proposal_id='p1'")[0] == "stale"


def test_approved_change_on_current_config_is_applied_once(tmp_path):
    s = Store(str(tmp_path / "b.db"))
    s.now_minute, s.now_ts = 1440 + 11 * 60, "t"
    sim, closed = FakeSim(version=6), []
    g = Governance(s, sim, {"w": wf("w", "engagement_rate")}, lambda p, st: closed.append(st))
    g._insert("p1", "w", "approval", 6, {}, {}, [])
    s.db.execute("UPDATE proposals SET status='approved', approval_id='a1' WHERE proposal_id='p1'")
    g._apply(g.row("p1"))
    assert sim.posts == ["/workflows/w/apply"] and closed == ["applied"]
    assert s.one("SELECT status, applied_version FROM proposals WHERE proposal_id='p1'") == ("applied", 7)
