"""Event ingestion: chunk -> aggregates, committed atomically with the chunk cursor (idempotent, restartable)."""
from __future__ import annotations

import json
import time
from collections import defaultdict

from .store import Store
from .timeutil import ts_to_minute

AGG_UPSERT = ("INSERT INTO agg(wf, day, hour, seg, wm, voice, did, prompt, cfg_ver, dials, conn, eng, flags) "
              "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(wf, day, hour, seg, wm, voice, did, prompt, cfg_ver) "
              "DO UPDATE SET dials=dials+excluded.dials, conn=conn+excluded.conn, eng=eng+excluded.eng, "
              "flags=flags+excluded.flags")


def seg_of(features: dict) -> str:
    return f"{features.get('age_band', '?')}|{features.get('lang', '?')}"


class Ingestor:
    def __init__(self, store: Store, sim):
        self.s = store
        self.sim = sim
        self.lead_seg: dict[str, str] = {}
        self._warm()

    def _warm(self):
        # leads are only dialled within their cadence (a few days); keep the recent ones in memory
        r = self.s.one("SELECT MAX(campaign_day) FROM leads")
        if r and r[0] is not None:
            for lid, seg in self.s.q("SELECT lead_id, seg FROM leads WHERE campaign_day >= ?", (r[0] - 7,)):
                self.lead_seg[lid] = seg

    def done(self, n: int) -> bool:
        return self.s.one("SELECT 1 FROM chunks_done WHERE chunk=?", (n,)) is not None

    def ingest_chunk(self, meta: dict, on_event=None) -> int:
        """Fetch and fold one chunk. Returns number of events. Safe to call twice for the same chunk."""
        n = meta["chunk"]
        if self.done(n):
            return 0
        body = self.sim.text(f"/events/chunks/{n}")
        agg = defaultdict(lambda: [0, 0, 0, 0])
        leads = []
        others = []
        count = 0
        for line in body.splitlines():
            if not line:
                continue
            ev = json.loads(line)
            count += 1
            t = ev["type"]
            if t == "call":
                m = ts_to_minute(ev["ts"])
                day, hour = divmod(m, 1440)[0], (m % 1440) // 60
                v = ev["variant"]
                seg = self.lead_seg.get(ev["lead_id"], "?|?")
                k = (ev["workflow_id"], day, hour, seg, v["welcome_message"], v["voice"], v["caller_id"],
                     v["prompt_version"], ev["config_version"])
                a = agg[k]
                a[0] += 1
                if ev["connected"]:
                    a[1] += 1
                    a[2] += ev["engaged"]
                    a[3] += bool((ev.get("qa") or {}).get("hallucination_flag"))
            elif t == "lead":
                seg = seg_of(ev["features"])
                self.lead_seg[ev["lead_id"]] = seg
                day = ts_to_minute(ev["ts"]) // 1440
                leads.append((ev["lead_id"], ev["workflow_id"], ev["person_id"], seg,
                              json.dumps(ev["features"]), day))
            else:
                others.append(ev)
        self.s.begin()
        try:
            self.s.db.executemany("INSERT OR IGNORE INTO leads VALUES(?,?,?,?,?,?)", leads)
            self.s.db.executemany(AGG_UPSERT, [(*k, *v) for k, v in agg.items()])
            for ev in others:
                if ev["type"] == "config_changed":
                    self.s.db.execute("INSERT OR IGNORE INTO config_changes VALUES(?,?,?,?,?,?,?,?)",
                                      (ev["workflow_id"], ev["version"], ev["ts"], ts_to_minute(ev["ts"]),
                                       ev["actor"], json.dumps(ev["changed_dims"]), ev.get("proposal_id"),
                                       ev.get("approval_id")))
                if on_event:
                    on_event(ev, meta["kind"])
            self.s.db.execute("INSERT INTO chunks_done VALUES(?,?,?,?)", (n, meta["kind"], count, time.time()))
            self.s.commit()
        except BaseException:
            self.s.db.execute("ROLLBACK")
            raise
        self._evict()
        return count

    def _evict(self):
        if len(self.lead_seg) > 3_000_000:
            r = self.s.one("SELECT MAX(campaign_day) FROM leads")
            self.lead_seg.clear()
            for lid, seg in self.s.q("SELECT lead_id, seg FROM leads WHERE campaign_day >= ?", (r[0] - 4,)):
                self.lead_seg[lid] = seg
