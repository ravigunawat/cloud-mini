#!/usr/bin/env bash
# Cold start: delete all parser pods three times; measure Pod creation -> Ready (slowest pod per run).
cd "$(dirname "$0")/.."
: > results/coldstart_times.txt
: > results/coldstart_logs.txt
for run in 1 2 3; do
  echo "$(date +%T) run $run: deleting all parser pods" | tee -a results/coldstart_times.txt
  kubectl -n app delete pod -l app=parser --wait=false > /dev/null
  sleep 20
  for i in $(seq 1 90); do
    want=$(kubectl -n app get deploy parser -o jsonpath='{.spec.replicas}')
    have=$(kubectl -n app get deploy parser -o jsonpath='{.status.readyReplicas}')
    [ "$have" = "$want" ] && break
    sleep 5
  done
  kubectl -n app get pods -l app=parser -o json | python3 -c '
import json, sys
from datetime import datetime
def t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
secs = []
for p in json.load(sys.stdin)["items"]:
    if p["metadata"].get("deletionTimestamp"):
        continue
    ok = [c for c in p["status"]["conditions"] if c["type"] == "Ready" and c["status"] == "True"]
    if ok:
        secs.append((t(ok[0]["lastTransitionTime"]) - t(p["metadata"]["creationTimestamp"])).total_seconds())
print("creation->Ready seconds per pod:", secs, "max:", max(secs) if secs else "n/a")
' | tee -a results/coldstart_times.txt
  P=$(kubectl -n app get pods -l app=parser --no-headers | grep -v Terminating | head -1 | cut -d' ' -f1)
  echo "== run $run pod $P" >> results/coldstart_logs.txt
  kubectl -n app logs "$P" | grep -E "downloaded|ready" >> results/coldstart_logs.txt
done
python3 - <<'PY' | tee -a results/coldstart_times.txt
import re
import statistics
vals = [float(m) for m in re.findall(r"max: ([0-9.]+)", open("results/coldstart_times.txt").read())]
print("per-run times:", vals, "median:", statistics.median(vals) if vals else "n/a")
PY
