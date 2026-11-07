"""Package a model directory deterministically, write model.sha256, upload to the models bucket.

Usage: python scripts/upload_model.py model_out/v1 v1
Creates release/<version>/model.tar.gz (the GitHub Release asset) and release/<version>/model.sha256,
then uploads the model files and model.sha256 to s3://models/<version>/ (the tarball is NOT uploaded).
"""
import gzip
import hashlib
import os
import sys
import tarfile

import boto3
from botocore.config import Config


def build_tarball(src, dest):
    names = sorted(n for n in os.listdir(src) if os.path.isfile(os.path.join(src, n)))
    with open(dest, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for name in names:
                    info = tar.gettarinfo(os.path.join(src, name), arcname=name)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    info.mode = 0o644
                    with open(os.path.join(src, name), "rb") as f:
                        tar.addfile(info, f)
    return names


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    src, version = sys.argv[1], sys.argv[2]
    out_dir = os.path.join("release", version)
    os.makedirs(out_dir, exist_ok=True)
    tarball = os.path.join(out_dir, "model.tar.gz")
    names = build_tarball(src, tarball)
    digest = sha256_of(tarball)
    sha_path = os.path.join(out_dir, "model.sha256")
    with open(sha_path, "w") as f:
        f.write(f"{digest}  model.tar.gz\n")
    print("model.tar.gz sha256", digest)

    s3 = boto3.client(
        "s3", endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name="us-east-1", config=Config(s3={"addressing_style": "path"}))
    for name in names:
        s3.upload_file(os.path.join(src, name), "models", f"{version}/{name}")
    s3.upload_file(sha_path, "models", f"{version}/model.sha256")
    keys = [o["Key"] for o in s3.list_objects_v2(Bucket="models", Prefix=f"{version}/").get("Contents", [])]
    print("uploaded to s3://models/:", keys)


if __name__ == "__main__":
    main()
