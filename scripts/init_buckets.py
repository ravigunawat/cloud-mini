import os, boto3
from botocore.config import Config
s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
                  aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                  aws_secret_access_key=os.environ["S3_SECRET_KEY"],
                  region_name="us-east-1", config=Config(s3={"addressing_style": "path"}))
for b in ("datasets", "models"):
    try:
        s3.create_bucket(Bucket=b)
    except Exception as e:
        print("bucket", b, "->", e)
s3.upload_file("data/commands_pool.jsonl", "datasets", "commands_pool.jsonl")
print({b["Name"] for b in s3.list_buckets()["Buckets"]})
print([o["Key"] for o in s3.list_objects_v2(Bucket="datasets").get("Contents", [])])
