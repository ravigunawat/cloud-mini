"""Summarise a Locust run. Usage: python scripts/summ.py results/rollout"""
import csv
import json
import sys

prefix = sys.argv[1]
with open(prefix + "_stats.csv") as f:
    r = [x for x in csv.DictReader(f) if x["Name"] == "/parse"][0]
n, fails = int(r["Request Count"]), int(r["Failure Count"])
print(f"requests {n} failures {fails} ({100 * fails / n:.2f}%) | p50 {r['50%']} ms | "
      f"p95 {r['95%']} ms | rps {float(r['Requests/s']):.2f}")
try:
    with open(prefix + "_headers.json") as f:
        print(json.dumps(json.load(f), indent=1))
except OSError as e:
    print("no headers file:", e)
