"""Unit tests for the controller's pure pieces and its crash-safe ingestion (no simulator internals imported)."""
import json

from controller import configs
from controller.ingest import Ingestor
from controller.stats import binom_z, norm_ppf, tv, two_prop_z
from controller.store import Store

CFG = {"version": 1, "prompt_version": "P1", "cohorts": {},
       "allocations": {"default": {"welcome_message": {"W1": 1.0}, "voice": {"V1": 1.0},
                                   "caller_id": {"D1": 0.5, "D2": 0.5}}}}


def test_stats():
    assert abs(norm_ppf(0.975) - 1.95996) < 1e-3
    assert two_prop_z(60, 100, 50, 100) > 1.4
    assert binom_z(10, 100, 0.02) > 5
    assert tv({"a": 1.0}, {"a": 0.9, "b": 0.1}) == 0.1 or abs(tv({"a": 1.0}, {"a": 0.9, "b": 0.1}) - 0.1) < 1e-9


def test_apply_intents_and_diff():
    new = configs.apply_intents(CFG, [{"type": "alloc", "dim": "voice", "cohort": "default",
                                       "dist": {"V1": 0.92, "V2": 0.08}}])
    assert configs.changed_dims(CFG, new) == {"voice"}
    assert CFG["allocations"]["default"]["voice"] == {"V1": 1.0}  # input not mutated
    assert not configs.same(CFG, new)
    assert configs.same(CFG, configs.apply_intents(CFG, []))


class FakeSim:
    def __init__(self, body):
        self.body = body

    def text(self, path):
        return self.body


def test_ingest_is_idempotent(tmp_path):
    lead = {"type": "lead", "lead_id": "L1", "workflow_id": "w", "person_id": "p",
            "features": {"age_band": "60+", "lang": "ta"}, "campaign_day": 0, "ts": "2027-01-04T09:00:00+05:30"}
    call = {"type": "call", "lead_id": "L1", "workflow_id": "w", "ts": "2027-01-04T10:05:00+05:30",
            "connected": True, "engaged": True, "qa": {"hallucination_flag": False}, "config_version": 1,
            "variant": {"welcome_message": "W1", "voice": "V1", "caller_id": "D1", "prompt_version": "P1"}}
    body = "\n".join(json.dumps(e) for e in (lead, call))
    s = Store(str(tmp_path / "c.db"))
    ing = Ingestor(s, FakeSim(body))
    meta = {"chunk": 0, "kind": "events", "url": "/events/chunks/0"}
    ing.ingest_chunk(meta)
    ing.ingest_chunk(meta)  # replay after a crash must not double count
    assert Ingestor(s, FakeSim(body)).done(0)
    assert s.one("SELECT SUM(dials), SUM(conn), SUM(eng) FROM agg")[:3] == (1, 1, 1)
