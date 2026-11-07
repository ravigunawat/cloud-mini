"""Run a model (local dir or HF id) over validation.jsonl and write predictions for score.py."""
import argparse
import json

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--data", default="data/validation.jsonl")
ap.add_argument("--out", required=True)
args = ap.parse_args()

tok = AutoTokenizer.from_pretrained(args.model)
model = AutoModelForCausalLM.from_pretrained(args.model).eval()
with open(args.data, encoding="utf-8") as f:
    rows = [json.loads(line) for line in f if line.strip()]
with open(args.out, "w", encoding="utf-8") as out_f:
    for r in rows:
        ids = tok("Command: " + r["text"] + "\nJSON:", return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=64, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        text = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        text = (text.strip().splitlines() or [""])[0].strip()
        out_f.write(json.dumps({"id": r["id"], "prediction": text}) + "\n")
print("wrote", args.out)
