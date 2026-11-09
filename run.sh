#!/usr/bin/env bash
# Starts the controller and runs until the scenario finishes. Safe to re-run after a kill: it resumes from
# the SQLite store (CONTROLLER_DB, default state/controller.db).
set -euo pipefail
SIM_URL="${1:?usage: ./run.sh <SIM_URL>}"
cd "$(dirname "$0")"
exec python -m controller --url "$SIM_URL" --db "${CONTROLLER_DB:-state/controller.db}"
