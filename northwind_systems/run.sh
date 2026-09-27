#!/usr/bin/env bash
# Start the five simulated Northwind systems, each on its own port. Ctrl+C stops them all.
#   ./northwind_systems/run.sh
cd "$(dirname "$0")/.."
[ -f northwind_systems/data/helix.sqlite ] || ./.venv/bin/python -m northwind_systems.generate
trap 'kill 0' EXIT
for pair in aurora:9001 casetrack:9002 callcentre:9003 connect:9004 helix:9005; do
  ./.venv/bin/uvicorn "northwind_systems.${pair%%:*}:app" --port "${pair##*:}" --log-level warning &
done
echo "Aurora :9001  CaseTrack :9002  CallCentre One :9003  Connect :9004  Helix :9005"
wait
