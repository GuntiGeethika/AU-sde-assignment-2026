"""SQLite state + audit store. Everything the controller knows or decided lives here."""
from __future__ import annotations

import json
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS chunks_done (chunk INTEGER PRIMARY KEY, kind TEXT, events INTEGER, wall_ts REAL);
-- lead features, keyed by lead_id; seg = "<age_band>|<lang>"
CREATE TABLE IF NOT EXISTS leads (lead_id TEXT PRIMARY KEY, workflow_id TEXT, person_id TEXT, seg TEXT,
    features TEXT, campaign_day INTEGER);
-- call aggregates: one row per (workflow, day, hour, seg, variant, config version)
CREATE TABLE IF NOT EXISTS agg (wf TEXT, day INTEGER, hour INTEGER, seg TEXT, wm TEXT, voice TEXT, did TEXT,
    prompt TEXT, cfg_ver INTEGER, dials INTEGER, conn INTEGER, eng INTEGER, flags INTEGER,
    PRIMARY KEY (wf, day, hour, seg, wm, voice, did, prompt, cfg_ver));
CREATE INDEX IF NOT EXISTS agg_wf_day ON agg (wf, day);
CREATE TABLE IF NOT EXISTS config_changes (wf TEXT, version INTEGER, ts TEXT, sim_minute INTEGER, actor TEXT,
    changed_dims TEXT, proposal_id TEXT, approval_id TEXT, PRIMARY KEY (wf, version));
CREATE TABLE IF NOT EXISTS proposals (proposal_id TEXT PRIMARY KEY, wf TEXT, path TEXT, status TEXT,
    base_version INTEGER, config TEXT, request TEXT, intents TEXT, approval_id TEXT, applied_version INTEGER,
    reasons TEXT, created_minute INTEGER, created_ts TEXT, updated_ts TEXT, parent_id TEXT);
CREATE INDEX IF NOT EXISTS proposals_wf ON proposals (wf, status);
CREATE TABLE IF NOT EXISTS experiments (exp_id TEXT PRIMARY KEY, wf TEXT, dim TEXT, control TEXT, challenger TEXT,
    share REAL, status TEXT, start_version INTEGER, start_minute INTEGER, end_minute INTEGER, result TEXT);
CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, sim_minute INTEGER, ts TEXT,
    wall_ts REAL, wf TEXT, kind TEXT, summary TEXT, details TEXT, proposal_id TEXT);
CREATE INDEX IF NOT EXISTS decisions_wf ON decisions (wf, sim_minute);
CREATE TABLE IF NOT EXISTS metrics (sim_minute INTEGER PRIMARY KEY, ts TEXT, wall_ts REAL, events INTEGER,
    ingest_s REAL, decide_s REAL, credits REAL, rss_mb REAL);
"""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        self.now_minute = 0
        self.now_ts = ""

    # ---- transactions
    def begin(self):
        self.db.execute("BEGIN IMMEDIATE")

    def commit(self):
        self.db.execute("COMMIT")

    def q(self, sql, args=()):
        return self.db.execute(sql, args).fetchall()

    def one(self, sql, args=()):
        return self.db.execute(sql, args).fetchone()

    # ---- kv
    def get(self, k, default=None):
        r = self.one("SELECT v FROM kv WHERE k=?", (k,))
        return json.loads(r[0]) if r else default

    def set(self, k, v):
        self.db.execute("INSERT INTO kv(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                        (k, json.dumps(v)))

    # ---- audit
    def decide(self, wf, kind, summary, details=None, proposal_id=None):
        self.db.execute("INSERT INTO decisions(sim_minute, ts, wall_ts, wf, kind, summary, details, proposal_id) "
                        "VALUES(?,?,?,?,?,?,?,?)",
                        (self.now_minute, self.now_ts, time.time(), wf, kind, summary,
                         json.dumps(details or {}, default=str), proposal_id))
