#!/usr/bin/env bash
# Kill -9 the controller repeatedly mid-run, restart it each time, then let it finish and grade the run.
# Usage: scripts/crash_test.sh [scenario] [port] [kills]
set -uo pipefail
cd "$(dirname "$0")/.."
SC="${1:-scenarios/public_02_incidents.yaml}"; PORT="${2:-8710}"; KILLS="${3:-6}"
URL="http://127.0.0.1:$PORT"; DB=state/crash.db; LOG=reports/crash_test.log
mkdir -p reports state; rm -f "$DB"*; : > "$LOG"
python -m sim serve --scenario "$SC" --run-dir runs/crash --force --port "$PORT" > /tmp/crash_sim.log 2>&1 &
SIM=$!; trap 'kill $SIM 2>/dev/null' EXIT
for i in $(seq 1 60); do curl -sf "$URL/health" >/dev/null && break; sleep 1; done
for k in $(seq 1 "$KILLS"); do
  secs=$(python -c "import random; print(round(random.uniform(1.5, 4.0), 1))")
  python -m controller --url "$URL" --db "$DB" >> /tmp/crash_ctl.log 2>&1 &
  PID=$!; sleep "$secs"; kill -9 "$PID" 2>/dev/null; wait "$PID" 2>/dev/null
  echo "kill #$k after ${secs}s at $(curl -s "$URL/sim/state" | python -c 'import sys,json;print(json.load(sys.stdin)["ts"])')" | tee -a "$LOG"
done
python -m controller --url "$URL" --db "$DB" >> /tmp/crash_ctl.log 2>&1
echo "final run exit=$?" | tee -a "$LOG"
python - "$URL" "$DB" <<'PY' | tee -a "$LOG"
import json, sqlite3, sys, collections, httpx
url, db = sys.argv[1], sqlite3.connect(sys.argv[2])
dup = 0
for (wf,) in db.execute("SELECT DISTINCT wf FROM proposals"):
    hist = httpx.get(f"{url}/workflows/{wf}/config/history").json()
    c = collections.Counter(h["proposal_id"] for h in hist if h.get("proposal_id"))
    dup += sum(n - 1 for n in c.values() if n > 1)
apps = httpx.get(f"{url}/approvals").json()
mine = {r[0] for r in db.execute("SELECT approval_id FROM proposals WHERE approval_id IS NOT NULL")}
print("duplicate applies of one proposal:", dup)
print("approvals in sim:", len(apps), "| tracked by controller:", len(mine & {a['approval_id'] for a in apps}))
print("approvals left pending/approved-unapplied:", [a["approval_id"] for a in apps if a["status"] in ("pending", "approved")])
print("restarts recorded in audit log:", db.execute("SELECT COUNT(*) FROM decisions WHERE kind='restart'").fetchone()[0])
print("recoveries:", db.execute("SELECT summary FROM decisions WHERE kind='recovered'").fetchall())
PY
python -m sim grade --run runs/crash --baseline runs/base_02 --out reports/crash_public_02.md > /dev/null
sed -n '/## Governance/,/^```$/p' reports/crash_public_02.md | head -0
grep -E "applied —|apply_conflicts|lapsed|expired" reports/crash_public_02.md | tee -a "$LOG"
