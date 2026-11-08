#!/usr/bin/env bash
# Rolling update v1 -> v2 and rollback, both while a load test is running.
cd "$(dirname "$0")/.."
ready() { kubectl -n app get deploy parser -o jsonpath='{.status.readyReplicas}'; }
LOADTEST_HEADERS_OUT=results/rollout_headers.json locust -f tools/locustfile.py --headless \
  --users 4 --spawn-rate 4 --run-time 9m --host http://localhost:8080 --csv results/rollout > results/rollout_console.txt 2>&1 &
LPID=$!
echo "$(date +%T) load started, waiting for 2 ready replicas"
for i in $(seq 1 60); do [ "$(ready)" = "2" ] && break; sleep 5; done
sleep 30
echo "$(date +%T) switching MODEL_VERSION and MODEL_URI to v2"
kubectl -n app set env deploy/parser MODEL_VERSION=v2 MODEL_URI=s3://models/v2/
kubectl -n app rollout status deploy/parser --timeout=400s
sleep 45
echo "$(date +%T) rolling back with kubectl rollout undo"
kubectl -n app rollout undo deploy/parser
kubectl -n app rollout status deploy/parser --timeout=400s
sleep 45
echo "$(date +%T) waiting for load test to finish"
wait $LPID
echo "$(date +%T) done"
