#!/usr/bin/env bash
# Waits for the HPA to settle at 1 replica, loads for 4 min (HPA should add a 2nd replica),
# then waits until it is back at 1. Progress is logged with timestamps.
cd "$(dirname "$0")/.."
spec() { kubectl -n app get deploy parser -o jsonpath='{.spec.replicas}'; }
echo "$(date +%T) waiting for HPA to scale down to 1"
for i in $(seq 1 90); do [ "$(spec)" = "1" ] && break; sleep 10; done
echo "$(date +%T) replicas=$(spec), starting load"
LOADTEST_HEADERS_OUT=results/hpa_up_headers.json locust -f tools/locustfile.py --headless \
  --users 4 --spawn-rate 4 --run-time 4m --host http://localhost:8080 --csv results/hpa_up > results/hpa_up_console.txt 2>&1
echo "$(date +%T) load finished, replicas=$(spec); waiting for scale down to 1"
for i in $(seq 1 90); do [ "$(spec)" = "1" ] && break; sleep 10; done
echo "$(date +%T) replicas=$(spec), done"
