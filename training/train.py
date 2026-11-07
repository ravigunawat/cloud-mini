import argparse, csv, json, os, random
import numpy as np
import torch, yaml
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="training/config.yaml")
ap.add_argument("--subset", type=int, default=0)
ap.add_argument("--out", default="")
args = ap.parse_args()
cfg = yaml.safe_load(open(args.config))

seed = cfg["seed"]
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
torch.set_num_threads(4)

tok = AutoTokenizer.from_pretrained(os.environ.get("MODEL_DIR", cfg["model_name"]))
model = AutoModelForCausalLM.from_pretrained(os.environ.get("MODEL_DIR", cfg["model_name"]))
eos = tok.eos_token_id

n = args.subset if args.subset > 0 else cfg["train_records"]
rows = [json.loads(l) for l in open(cfg["data_path"], encoding="utf-8") if l.strip()][:n]
print("training on", len(rows), "records")

def encode(r):
    prefix = tok("Command: " + r["text"] + "\nJSON:")["input_ids"]
    target = tok(" " + r["teacher_raw"].strip())["input_ids"] + [eos]
    ids = (prefix + target)[: cfg["max_length"]]
    labels = ([-100] * len(prefix) + target)[: cfg["max_length"]]
    return ids, labels

data = [encode(r) for r in rows]
opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"])
bs = cfg["batch_size"]
gen = torch.Generator().manual_seed(seed)
os.makedirs(os.path.dirname(cfg["loss_csv"]), exist_ok=True)
losses = []
model.train()
for epoch in range(1, cfg["epochs"] + 1):
    order = torch.randperm(len(data), generator=gen).tolist()
    total, steps = 0.0, 0
    for i in range(0, len(order), bs):
        batch = [data[j] for j in order[i:i + bs]]
        L = max(len(x[0]) for x in batch)
        ids = torch.tensor([x[0] + [eos] * (L - len(x[0])) for x in batch])
        att = torch.tensor([[1] * len(x[0]) + [0] * (L - len(x[0])) for x in batch])
        lab = torch.tensor([x[1] + [-100] * (L - len(x[1])) for x in batch])
        loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
        loss.backward(); opt.step(); opt.zero_grad()
        total += loss.item(); steps += 1
    avg = total / steps
    losses.append(avg)
    print(f"epoch {epoch} loss {avg:.4f}", flush=True)

with open(cfg["loss_csv"], "w", newline="") as f:
    w = csv.writer(f); w.writerow(["epoch", "loss"])
    for e, l in enumerate(losses, 1):
        w.writerow([e, f"{l:.6f}"])

out = args.out or cfg["output_dir"]
if args.subset > 0:
    out = out + "_subset"
os.makedirs(out, exist_ok=True)
model.save_pretrained(out); tok.save_pretrained(out)
print("saved to", out)
