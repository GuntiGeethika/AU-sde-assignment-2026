"""Pure functions over workflow configs and intents."""
from __future__ import annotations

import copy

DIMS = ("welcome_message", "voice", "caller_id")


def dist(cfg: dict, cohort: str, dim: str) -> dict:
    return (cfg["allocations"].get(cohort) or {}).get(dim) or cfg["allocations"]["default"][dim]


def norm(d: dict) -> dict:
    s = sum(d.values())
    return {k: round(v / s, 4) for k, v in d.items() if v > 0}


def apply_intents(cfg: dict, intents: list[dict]) -> dict:
    out = copy.deepcopy(cfg)
    for it in intents:
        if it["type"] == "alloc":
            out["allocations"].setdefault(it.get("cohort", "default"), {})[it["dim"]] = norm(it["dist"])
        elif it["type"] == "prompt":
            out["prompt_version"] = it["prompt_version"]
        elif it["type"] == "schedule":
            out["cohorts"] = it["cohorts"]
            out.setdefault("schedule", {})["hour_weights"] = it["hour_weights"]
    return out


def same(a: dict, b: dict) -> bool:
    def canon(c):
        c = copy.deepcopy(c)
        for coh in c.get("allocations", {}).values():
            for d in list(coh):
                coh[d] = {k: round(v, 3) for k, v in coh[d].items() if v > 1e-9}
        return c
    return canon(a) == canon(b)


def diff(old: dict, new: dict) -> dict:
    out = {}
    for coh in set(old["allocations"]) | set(new["allocations"]):
        for d in DIMS:
            a, b = dist(old, coh, d), dist(new, coh, d)
            if {k: round(v, 3) for k, v in a.items()} != {k: round(v, 3) for k, v in b.items()}:
                out[f"allocations.{coh}.{d}"] = {"from": a, "to": b}
    if old.get("prompt_version") != new.get("prompt_version"):
        out["prompt_version"] = {"from": old.get("prompt_version"), "to": new.get("prompt_version")}
    if old.get("cohorts") != new.get("cohorts"):
        out["cohorts"] = {"from": old.get("cohorts"), "to": new.get("cohorts")}
    if (old.get("schedule") or {}).get("hour_weights") != (new.get("schedule") or {}).get("hour_weights"):
        out["schedule.hour_weights"] = {"to": (new.get("schedule") or {}).get("hour_weights")}
    return out


def changed_dims(old: dict, new: dict) -> set[str]:
    dims = set()
    for k in diff(old, new):
        if k.startswith("allocations."):
            dims.add(k.split(".")[-1])
        elif k == "schedule.hour_weights":
            dims.add("schedule")
        else:
            dims.add(k)
    return dims
