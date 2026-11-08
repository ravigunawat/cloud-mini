#!/usr/bin/env bash
# Delete one pod while a load test is running and watch Kubernetes restore the replica count.
cd "$(dirname "$0")/.."
ready() { kubectl -n app get deploy parser -o jsonpath='{.status.readyReplicas}'; }
LOADTEST_HEADERS_OUT=results/recovery_headers.json locust -f tools/locustfile.py --headless \
  --users 4 --spawn-rate 4 --run-time 4m --host http://localhost:8080 --csv results/recovery > results/recovery_console.txt 2>&1 &
LPID=$!
echo "$(date +%T) load started, waiting for 2 ready replicas"
for i in $(seq 1 60); do [ "$(ready)" = "2" ] && break; sleep 5; done
sleep 30
POD=$(kubectl -n app get pods -l app=parser --no-headers | grep Running | head -1 | cut -d' ' -f1)
echo "$(date +%T) before: $(kubectl -n app get pods -l app=parser --no-headers | wc -l) pods, ready=$(ready)"
echo "$(date +%T) deleting $POD"
kubectl -n app delete pod "$POD" --wait=false
sleep 3
for i in $(seq 1 40); do
  echo "$(date +%T) ready=$(ready) pods=$(kubectl -n app get pods -l app=parser --no-headers | wc -l)"
  [ "$(ready)" = "2" ] && break; sleep 5
done
wait $LPID
echo "$(date +%T) done"
