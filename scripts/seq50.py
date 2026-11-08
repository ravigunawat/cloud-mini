"""Send the first 50 validation commands one after another to the service and summarise."""
import json
import statistics
import time
import urllib.error
import urllib.request

URL = "http://localhost:8000/parse"
with open("data/validation.jsonl", encoding="utf-8") as f:
    texts = [json.loads(line)["text"] for line in f if line.strip()][:50]

rows = []
for text in texts:
    req = urllib.request.Request(URL, json.dumps({"text": text}).encode(),
                                 {"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, body, hdr = r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        status, body, hdr = e.code, e.read().decode(), e.headers
    except Exception as e:
        status, body, hdr = 0, str(e), {}
    rows.append({"text": text, "status": status, "seconds": round(time.time() - t0, 3),
                 "served_by": hdr.get("X-Served-By"), "version": hdr.get("X-Model-Version"), "body": body})

ok = sum(r["status"] == 200 for r in rows)
lat = sorted(r["seconds"] for r in rows)
summary = {"requests": len(rows), "http_200": ok, "failed": len(rows) - ok,
           "median_s": statistics.median(lat), "max_s": lat[-1]}
with open("results/seq50.json", "w") as f:
    json.dump({"summary": summary, "rows": rows}, f, indent=1)
print(json.dumps(summary))
print("first reply:", rows[0]["body"], rows[0]["served_by"], rows[0]["version"])
