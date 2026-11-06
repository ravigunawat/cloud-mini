import json, time, urllib.request

PROMPT = open("prompts/teacher_prompt.txt", encoding="utf-8").read().rstrip("\n")

def ask(text, host="http://localhost:11434"):
    body = {
        "model": "phi3.5", "stream": False,
        "prompt": PROMPT.replace("{COMMAND}", text),
        "options": {"temperature": 0, "seed": 42, "num_predict": 80, "stop": ["\n"]},
    }
    req = urllib.request.Request(host + "/api/generate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))["response"]

if __name__ == "__main__":
    rows = [json.loads(l) for l in open("data/validation.jsonl")][:10]
    t0 = time.time()
    for r in rows:
        t = time.time()
        print(f"{time.time()-t:5.1f}s" if False else "", end="")
        out = ask(r["text"])
        print(f"[{time.time()-t:5.1f}s] {r['text']}\n   -> {out.strip()}")
    print(f"\nAverage: {(time.time()-t0)/len(rows):.1f} s per command")
