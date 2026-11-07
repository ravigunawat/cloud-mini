"""Run the teacher (same prompt and settings as Task 1) on validation.jsonl -> results/teacher_predictions.jsonl."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from teacher_test import ask  # noqa: E402

os.makedirs("results", exist_ok=True)
with open("data/validation.jsonl", encoding="utf-8") as f:
    rows = [json.loads(line) for line in f if line.strip()]
with open("results/teacher_predictions.jsonl", "w", encoding="utf-8") as out:
    for r in rows:
        out.write(json.dumps({"id": r["id"], "prediction": ask(r["text"]).strip()}) + "\n")
print("done")
