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
rows = [json.loads(line) for line in open(args.data, encoding="utf-8") if line.strip()]
with open(args.out, "w", encoding="utf-8") as f:
    for r in rows:
        ids = tok("Command: " + r["text"] + "\nJSON:", return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=64, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        text = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        text = text.strip().split("\n")[0].strip()
        f.write(json.dumps({"id": r["id"], "prediction": text}) + "\n")
print("wrote", args.out)
