"""Audit queries over the controller store.

  python -m controller.cli why    --db state/p02.db --wf ks_cancel --at "D3 14:00" [--hours 6]
  python -m controller.cli log    --db state/p02.db [--wf ks_cancel] [--kind applied]
  python -m controller.cli status --db state/p02.db
  python -m controller.cli metrics --db state/p03.db
"""
import argparse
import json
import sqlite3



def minute_of(s: str) -> int:
    d, hm = s.strip().lstrip("D").split()
    h, m = hm.split(":")
    return int(d) * 1440 + int(h) * 60 + int(m)


def show(db, rows):
    for ts, wf, kind, summary, details, pid in rows:
        print(f"{ts:>10}  {wf or '-':<11} {kind:<20} {summary}" + (f"  [{pid}]" if pid else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["why", "log", "status", "metrics"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--wf")
    ap.add_argument("--at")
    ap.add_argument("--kind")
    ap.add_argument("--hours", type=float, default=6)
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    cols = "ts, wf, kind, summary, details, proposal_id"
    if a.cmd == "why":
        t = minute_of(a.at)
        ch = db.execute("SELECT version, ts, actor, changed_dims, proposal_id, approval_id FROM config_changes "
                        "WHERE wf=? AND sim_minute<=? ORDER BY sim_minute DESC LIMIT 1", (a.wf, t)).fetchone()
        if not ch:
            print("no config change at or before that time")
            return
        v, ts, actor, dims, pid, aid = ch
        print(f"== {a.wf} v{v} at {ts} by {actor}, dims {dims}, approval {aid or '-'}")
        if pid:
            p = db.execute("SELECT status, path, request, intents, reasons, created_ts FROM proposals "
                           "WHERE proposal_id=?", (pid,)).fetchone()
            if p:
                req = json.loads(p[2] or "{}")
                print(f"proposal {pid} via {p[1]} created {p[5]}, final status {p[0]}")
                for k in ("change_summary", "rationale", "impact_score", "affected_leads", "dry_run", "evidence"):
                    if k in req:
                        print(f"  {k}: {json.dumps(req[k], default=str)[:600]}")
            print("-- decision trail for this proposal")
            show(db, db.execute(f"SELECT {cols} FROM decisions WHERE proposal_id=? ORDER BY id", (pid,)))
        else:
            print("not a controller change (supervisor edit or system)")
        start = db.execute("SELECT MIN(sim_minute) FROM config_changes WHERE wf=? AND version=?", (a.wf, v)).fetchone()[0]
        print(f"-- what happened next (until +{a.hours:g}h)")
        show(db, db.execute(f"SELECT {cols} FROM decisions WHERE wf=? AND sim_minute>? AND sim_minute<=? AND "
                            "kind NOT IN ('deferred') ORDER BY id", (a.wf, start, start + a.hours * 60)))
        print("-- KPIs on this config version vs previous")
        for ver in (v - 1, v):
            d, c, e = db.execute("SELECT SUM(dials), SUM(conn), SUM(eng) FROM agg WHERE wf=? AND cfg_ver=?",
                                 (a.wf, ver)).fetchone()
            if d:
                print(f"  v{ver}: dials {d}, pickup {c / d:.3f}, engagement {e / max(c, 1):.3f}")
    elif a.cmd == "log":
        sql, args = f"SELECT {cols} FROM decisions WHERE kind!='deferred'", []
        if a.wf:
            sql += " AND wf=?"; args.append(a.wf)
        if a.kind:
            sql += " AND kind=?"; args.append(a.kind)
        show(db, db.execute(sql + " ORDER BY id", args))
    elif a.cmd == "status":
        for r in db.execute("SELECT wf, path, status, COUNT(*) FROM proposals GROUP BY 1,2,3"):
            print("proposal", *r)
        for r in db.execute("SELECT wf, dim, control, challenger, status FROM experiments ORDER BY start_minute"):
            print("experiment", *r)
        for k, v in db.execute("SELECT k, v FROM kv WHERE k LIKE 'incident:%' OR k LIKE 'did_status:%'"):
            print(k, v[:300])
    else:
        rows = db.execute("SELECT sim_minute/1440, SUM(events), SUM(ingest_s), SUM(decide_s), MAX(rss_mb), "
                          "MIN(wall_ts), MAX(wall_ts), MIN(credits) FROM metrics GROUP BY 1").fetchall()
        print("day  events     ingest_s  decide_s  wall_s  peak_rss_mb  credits")
        prev = None
        for d, ev, i, dc, rss, w0, w1, cr in rows:
            wall = w1 - (prev if prev else w0)
            prev = w1
            print(f"D{d:<3} {ev:<10} {i:8.1f} {dc:9.1f} {wall:7.1f} {(f'{rss:.0f}' if rss is not None else 'n/a'):>11}  {cr}")


if __name__ == "__main__":
    main()
