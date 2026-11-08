"""Cost per 1,000 requests and SLO error budget for one load-test run. Usage: python scripts/cost.py [replicas]"""
import csv
import json
import math
import sys

replicas = int(sys.argv[1]) if len(sys.argv) > 1 else 2
cpu_limit, mem_limit_gib = 1.0, 1.0  # from k8s/app.yaml limits
rate = json.load(open("data/rate_card.json"))
row = [r for r in csv.DictReader(open("results/loadtest_stats.csv")) if r["Name"] == "/parse"][0]
n, fails, rps = int(row["Request Count"]), int(row["Failure Count"]), float(row["Requests/s"])

per_replica = cpu_limit * rate["vcpu_hour"] + mem_limit_gib * rate["gib_memory_hour"]
hourly = replicas * per_replica
per_hour = rps * 3600
cost = hourly / per_hour * 1000
slo = 0.99
budget = math.floor(n * (1 - slo))
out = [
    f"cost per replica per hour = {cpu_limit} vCPU x {rate['vcpu_hour']} + {mem_limit_gib} GiB x {rate['gib_memory_hour']} = {per_replica:.2f} INR",
    f"hourly cost of {replicas} replicas = {replicas} x {per_replica:.2f} = {hourly:.2f} INR",
    f"requests served per hour = {rps:.4f} req/s x 3600 = {per_hour:.1f}",
    f"cost per 1000 requests = {hourly:.2f} / {per_hour:.1f} x 1000 = {cost:.4f} INR",
    f"SLO: {slo*100:.0f}% of requests succeed (window = one load-test run of {n} requests)",
    f"error budget = floor({n} x {1-slo:.2f}) = {budget} failed requests; used = {fails} ({100*fails/n:.2f}% of budget {'n/a' if budget == 0 else f'{100*fails/budget:.0f}%'})",
]
print("\n".join(out))
open("results/task7_cost_slo.txt", "w").write("\n".join(out) + "\n")
