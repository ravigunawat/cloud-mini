import json, os, threading
import boto3
import torch
from botocore.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_URI = os.environ.get("MODEL_URI", "s3://models/v1/")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://seaweedfs.data.svc.cluster.local:8333")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "64"))
FAULT_INJECT = os.environ.get("FAULT_INJECT", "0") == "1"
POD = os.environ.get("HOSTNAME", "local")
LOCAL_DIR = "/tmp/model"

INTENTS = {"alarm_set", "alarm_query", "calendar_set", "calendar_query",
           "calendar_remove", "weather_query", "datetime_query", "recommendation_events"}
KEYS = {"intent", "date", "time", "place"}

state = {"tok": None, "model": None, "ready": False}
lock = threading.Lock()
app = FastAPI()


def download_model():
    bucket, _, prefix = MODEL_URI.replace("s3://", "").partition("/")
    s3 = boto3.client(
        "s3", endpoint_url=S3_ENDPOINT,
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name="us-east-1", config=Config(s3={"addressing_style": "path"}))
    os.makedirs(LOCAL_DIR, exist_ok=True)
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
    for page in pages:
        for obj in page.get("Contents", []):
            name = obj["Key"][len(prefix):].lstrip("/")
            if name:
                s3.download_file(bucket, obj["Key"], os.path.join(LOCAL_DIR, name))
                print("downloaded", obj["Key"], flush=True)


def load():
    torch.set_num_threads(1)
    download_model()
    state["tok"] = AutoTokenizer.from_pretrained(LOCAL_DIR)
    state["model"] = AutoModelForCausalLM.from_pretrained(LOCAL_DIR).eval()
    state["ready"] = True
    print("model ready", flush=True)


@app.on_event("startup")
def startup():
    threading.Thread(target=load, daemon=True).start()
