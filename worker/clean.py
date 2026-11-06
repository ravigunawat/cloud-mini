"""Clean teacher shard outputs -> datasets/v1/train.jsonl + train.sha256.

Each record is counted once, in this order of checks:
  (a) not valid JSON  (b) keys != intent,date,time,place  (c) intent not one of 8
  (d) a slot is not null / not text that appears in the command
then (e) duplicate command text among the remaining records (smallest id kept).
Usage: python worker/clean.py [--dry]   (--dry: do not upload)
"""
import hashlib, json, os, sys
import boto3
from botocore.config import Config

INTENTS = {"alarm_set", "alarm_query", "calendar_set", "calendar_query",
           "calendar_remove", "weather_query", "datetime_query", "recommendation_events"}
KEYS = {"intent", "date", "time", "place"}
SLOTS = ("date", "time", "place")

s3 = boto3.client(
    "s3", endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
    aws_access_key_id=os.environ["S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    region_name="us-east-1", config=Config(s3={"addressing_style": "path"}))


def read_shards():
    recs, pages = [], s3.list_objects_v2(Bucket="datasets", Prefix="teacher/").get("Contents", [])
    for obj in sorted(pages, key=lambda o: o["Key"]):
        if not obj["Key"].endswith(".jsonl"):
            continue
        body = s3.get_object(Bucket="datasets", Key=obj["Key"])["Body"].read().decode("utf-8")
        for line in body.splitlines():
            if line.strip():
                recs.append(json.loads(line))
        print("read", obj["Key"])
    return recs


def reject_reason(rec):
    try:
        obj = json.loads(rec["teacher_raw"])
    except Exception:
        return "a"
    if not isinstance(obj, dict) or set(obj.keys()) != KEYS:
        return "b"
    if obj["intent"] not in INTENTS:
        return "c"
    for s in SLOTS:
        v = obj[s]
        if v is not None and not (isinstance(v, str) and v in rec["text"]):
            return "d"
    return None


def main():
    dry = "--dry" in sys.argv
    recs = sorted(read_shards(), key=lambda r: r["id"])
    ids = [r["id"] for r in recs]
    assert len(ids) == len(set(ids)), "an id appears more than once across shards"

    counts = {"input": len(recs), "a": 0, "b": 0, "c": 0, "d": 0, "duplicates": 0, "kept": 0}
    kept, seen = [], set()
    for r in recs:
        why = reject_reason(r)
        if why:
            counts[why] += 1
        elif r["text"] in seen:
            counts["duplicates"] += 1
        else:
            seen.add(r["text"])
            kept.append(r)
    counts["kept"] = len(kept)
    assert counts["input"] == sum(counts[k] for k in ("a", "b", "c", "d", "duplicates", "kept"))

    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    print(json.dumps(counts, indent=2)); print("sha256", digest)

    os.makedirs("results", exist_ok=True)
    with open("results/clean_counts.json", "w") as f:
        json.dump(counts, f, indent=2)
    with open("train.jsonl", "wb") as f:
        f.write(data)
    if not dry:
        s3.put_object(Bucket="datasets", Key="v1/train.jsonl", Body=data)
        s3.put_object(Bucket="datasets", Key="v1/train.sha256",
                      Body=f"{digest}  train.jsonl\n".encode())
        print("uploaded datasets/v1/train.jsonl and train.sha256")


if __name__ == "__main__":
    main()
