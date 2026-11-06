import json, os, time, urllib.request
import boto3
from botocore.config import Config

SHARD_INDEX = int(os.environ["SHARD_INDEX"])
SHARD_COUNT = int(os.environ["SHARD_COUNT"])
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://seaweedfs.data.svc.cluster.local:8333")
OLLAMA_URL = os.environ["OLLAMA_URL"]
MODEL = os.environ.get("TEACHER_MODEL", "phi3.5")
PROMPT_FILE = os.environ.get("PROMPT_FILE", "/app/prompts/teacher_prompt.txt")
OUT_KEY = f"teacher/shard-{SHARD_INDEX}.jsonl"
FLUSH_EVERY = 25

PROMPT = open(PROMPT_FILE, encoding="utf-8").read().rstrip("\n")

s3 = boto3.client(
    "s3", endpoint_url=S3_ENDPOINT,
    aws_access_key_id=os.environ["S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    region_name="us-east-1", config=Config(s3={"addressing_style": "path"}),
)


def ask_teacher(text):
    body = {
        "model": MODEL, "stream": False,
        "prompt": PROMPT.replace("{COMMAND}", text),
        "options": {"temperature": 0, "seed": 42, "num_predict": 80, "stop": ["\n"]},
    }
    for attempt in range(5):
        try:
            req = urllib.request.Request(OLLAMA_URL + "/api/generate",
                                         json.dumps(body).encode(),
                                         {"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=600))["response"]
        except Exception as e:
            print("ollama error, retry:", e, flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("teacher unreachable")


def upload(lines):
    s3.put_object(Bucket="datasets", Key=OUT_KEY,
                  Body=("\n".join(lines) + "\n").encode("utf-8"))


def main():
    pool = s3.get_object(Bucket="datasets", Key="commands_pool.jsonl")["Body"].read().decode("utf-8")
    all_lines = pool.splitlines()
    mine = [json.loads(l) for i, l in enumerate(all_lines) if l.strip() and i % SHARD_COUNT == SHARD_INDEX]

    out_lines, done = [], set()
    try:
        old = s3.get_object(Bucket="datasets", Key=OUT_KEY)["Body"].read().decode("utf-8")
        for l in old.splitlines():
            if l.strip():
                out_lines.append(l)
                done.add(json.loads(l)["id"])
        print(f"resuming with {len(done)} already done", flush=True)
    except Exception:
        pass

    todo = [r for r in mine if r["id"] not in done]
    print(f"shard {SHARD_INDEX}/{SHARD_COUNT}: {len(mine)} commands, {len(todo)} to do", flush=True)
    t0 = time.time()
    for n, r in enumerate(todo, 1):
        raw = ask_teacher(r["text"])
        out_lines.append(json.dumps({"id": r["id"], "text": r["text"], "teacher_raw": raw}, ensure_ascii=False))
        if n % FLUSH_EVERY == 0:
            upload(out_lines)
            print(f"{n}/{len(todo)} done, {(time.time()-t0)/n:.1f}s each", flush=True)
    upload(out_lines)
    print("finished shard", SHARD_INDEX, flush=True)


if __name__ == "__main__":
    main()
