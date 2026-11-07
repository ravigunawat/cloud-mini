import json
import os
import threading
import time
from contextlib import asynccontextmanager

import boto3
import torch
from botocore.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import Response
from transformers import AutoModelForCausalLM, AutoTokenizer

from validate import parse_output

MODEL_URI = os.environ.get("MODEL_URI", "s3://models/v1/")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://seaweedfs.data.svc.cluster.local:8333")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "64"))
POD = os.environ.get("HOSTNAME", "local")
LOCAL_DIR = "/tmp/model"

state = {"tok": None, "model": None, "ready": False}
gen_lock = threading.Lock()


def download_model():
    bucket, _, prefix = MODEL_URI.replace("s3://", "").partition("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    s3 = boto3.client(
        "s3", endpoint_url=S3_ENDPOINT,
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name="us-east-1", config=Config(s3={"addressing_style": "path"}))
    os.makedirs(LOCAL_DIR, exist_ok=True)
    count = 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            name = obj["Key"][len(prefix):]
            if name and not name.endswith("/"):
                s3.download_file(bucket, obj["Key"], os.path.join(LOCAL_DIR, name))
                print(f"downloaded s3://{bucket}/{obj['Key']}", flush=True)
                count += 1
    if count == 0:
        raise RuntimeError(f"no model files under {MODEL_URI}")


def load():
    torch.set_num_threads(1)
    for attempt in range(1, 61):
        try:
            download_model()
            break
        except Exception as exc:
            print(f"model download failed (attempt {attempt}): {exc}", flush=True)
            time.sleep(5)
    else:
        print("giving up on model download", flush=True)
        return
    state["tok"] = AutoTokenizer.from_pretrained(LOCAL_DIR)
    state["model"] = AutoModelForCausalLM.from_pretrained(LOCAL_DIR).eval()
    state["ready"] = True
    print(f"model {MODEL_VERSION} ready", flush=True)


@asynccontextmanager
async def lifespan(_app):
    threading.Thread(target=load, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)


def JSONResponse(obj, status_code=200, headers=None):  # noqa: N802
    """JSON with the exact default separators, e.g. {"error": "invalid_model_output"}."""
    return Response(content=json.dumps(obj), status_code=status_code,
                    media_type="application/json", headers=headers)


def generate(text):
    tok, model = state["tok"], state["model"]
    ids = tok("Command: " + text + "\nJSON:", return_tensors="pt")
    with gen_lock, torch.inference_mode():
        out = model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                             pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)


@app.get("/healthz")
def healthz():
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    if state["ready"]:
        return {"status": "ready"}
    return JSONResponse({"status": "loading"}, status_code=503)


@app.post("/parse")
async def parse(request: Request):
    headers = {"X-Model-Version": MODEL_VERSION, "X-Served-By": POD}
    if not state["ready"]:
        return JSONResponse({"error": "model_not_ready"}, status_code=503, headers=headers)
    try:
        body = await request.json()
        text = body["text"]
        if not isinstance(text, str):
            raise ValueError("text must be a string")
    except Exception:
        return JSONResponse({"error": "bad_request"}, status_code=400, headers=headers)
    raw = generate(text[:500])
    if os.environ.get("FAULT_INJECT", "0") == "1":
        raw = "not json"
    obj = parse_output(raw)
    if obj is None:
        return JSONResponse({"error": "invalid_model_output"}, status_code=500, headers=headers)
    return JSONResponse(obj, headers=headers)
