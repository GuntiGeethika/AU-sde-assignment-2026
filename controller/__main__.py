"""Controller entry point: python -m controller --url http://127.0.0.1:8700 [--db state/controller.db]"""
from __future__ import annotations

import argparse
import logging
import os
import resource
import shutil
import time

from .api import Sim, SimError
from .ingest import Ingestor
from .planner import Planner
from .store import Store
from .timeutil import label

log = logging.getLogger("controller")


def open_store(path: str, state: dict) -> Store:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path):
        s = Store(path)
        ident = s.get("sim_identity")
        if ident and (ident["scenario"] != state["scenario"] or state["sim_minute"] < ident.get("minute", 0)):
            s.db.close()
            dst = f"{path}.{int(time.time())}.old"
            for suf in ("", "-wal", "-shm"):
                if os.path.exists(path + suf):
                    shutil.move(path + suf, dst + suf)
            log.warning("store belonged to a different simulator world; archived to %s", dst)
        else:
            return s
    s = Store(path)
    s.set("sim_identity", {"scenario": state["scenario"], "minute": state["sim_minute"]})
    return s


def catch_up(sim, ing, planner):
    n = 0
    for kind in ("history", "events"):
        for meta in sorted(sim.get("/events/chunks", params={"kind": kind}), key=lambda m: m["chunk"]):
            if not ing.done(meta["chunk"]):
                n += ing.ingest_chunk(meta, planner.on_event)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8700")
    ap.add_argument("--db", default=os.environ.get("CONTROLLER_DB", "state/controller.db"))
    ap.add_argument("--step", type=int, default=15, help="sim minutes per advance")
    ap.add_argument("--stop-at", type=int, default=None, help="exit at this sim minute (crash tests)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    sim = Sim(a.url)
    sim.wait_ready()
    state = sim.get("/sim/state")
    store = open_store(a.db, state)
    store.now_minute, store.now_ts = state["sim_minute"], label(state["sim_minute"])
    wfs = {w["workflow_id"]: w for w in sim.get("/workflows")}
    planner = Planner(store, sim, wfs)
    planner.end_minute = state["end_minute"]
    ing = Ingestor(store, sim)
    t0 = time.time()
    n = catch_up(sim, ing, planner)
    log.info("caught up %d events in %.1fs (resuming at %s)", n, time.time() - t0, label(state["sim_minute"]))
    planner.bootstrap()
    planner.gov.reconcile()
    if store.get("started") is None:
        store.set("started", state["sim_minute"])
    else:
        store.decide(None, "restart", f"controller restarted at {label(state['sim_minute'])}; resumed from store",
                     {"events_replayed": n})
    while not state["finished"]:
        if a.stop_at is not None and state["sim_minute"] >= a.stop_at:
            log.info("stop-at reached")
            return
        w0 = time.time()
        try:
            adv = sim.post("/sim/advance", {"minutes": a.step})
        except SimError as e:
            if e.code != "finished":
                raise
            break
        store.now_minute, store.now_ts = adv["sim_minute"], label(adv["sim_minute"])
        store.set("sim_identity", {"scenario": state["scenario"], "minute": adv["sim_minute"]})
        events = 0
        for meta in adv["new_chunks"]:
            events += ing.ingest_chunk(meta, planner.on_event)
        events += catch_up(sim, ing, planner) if not adv["new_chunks"] else 0
        w1 = time.time()
        state = sim.get("/sim/state")
        planner.gov.poll()
        hourly = adv["sim_minute"] % 60 == 0
        for wid in wfs:
            planner.tick(wid, hourly, state["credits_remaining"])
        w2 = time.time()
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        store.db.execute("INSERT OR REPLACE INTO metrics VALUES(?,?,?,?,?,?,?,?)",
                         (adv["sim_minute"], store.now_ts, w2, events, w1 - w0, w2 - w1,
                          state["credits_remaining"], rss))
        if adv["sim_minute"] % 1440 == 0:
            log.info("%s events=%d ingest=%.2fs decide=%.2fs credits=%s rss=%.0fMB", store.now_ts, events,
                     w1 - w0, w2 - w1, state["credits_remaining"], rss)
    store.decide(None, "finished", f"scenario finished at {label(state['sim_minute'])}")
    log.info("finished")


if __name__ == "__main__":
    main()
