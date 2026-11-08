#!/usr/bin/env bash
# Builds and deploys the whole system. Needs: docker, k3d, kubectl, python3 with boto3 (pip install boto3==1.35.36).
set -euo pipefail
cd "$(dirname "$0")/.."

k3d cluster create --config cluster/k3d.yaml || true
for ns in data pipeline app; do
  kubectl create ns "$ns" --dry-run=client -o yaml | kubectl apply -f -
done

# Credentials are generated locally and never committed (.env is git-ignored).
if [ ! -f .env ]; then
  printf 'S3_ACCESS_KEY=%s\nS3_SECRET_KEY=%s\n' "$(openssl rand -hex 8)" "$(openssl rand -hex 16)" > .env
fi
set -a; . ./.env; set +a

cat > /tmp/s3.json <<JSON
{"identities":[{"name":"admin","credentials":[{"accessKey":"$S3_ACCESS_KEY","secretKey":"$S3_SECRET_KEY"}],"actions":["Admin","Read","Write","List","Tagging"]}]}
JSON
kubectl -n data create secret generic seaweed-s3-config --from-file=s3.json=/tmp/s3.json \
  --dry-run=client -o yaml | kubectl apply -f -
rm -f /tmp/s3.json
for ns in pipeline app; do
  kubectl -n "$ns" create secret generic s3-credentials \
    --from-literal=S3_ACCESS_KEY="$S3_ACCESS_KEY" --from-literal=S3_SECRET_KEY="$S3_SECRET_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -
done

kubectl apply -f k8s/seaweedfs.yaml
kubectl -n data rollout status deploy/seaweedfs --timeout=300s

( while true; do kubectl -n data port-forward svc/seaweedfs 8333:8333 >/tmp/pf-up.log 2>&1; sleep 2; done ) &
PF_PID=$!
trap 'pkill -P $PF_PID 2>/dev/null || true; kill $PF_PID 2>/dev/null || true' EXIT
ok=0
for i in $(seq 1 40); do
  if python3 scripts/init_buckets.py; then ok=1; break; fi
  echo "waiting for object storage ($i/40)"; sleep 5
done
[ "$ok" = 1 ] || { echo "object storage not reachable"; exit 1; }

# Model weights are not in Git. Get them from the GitHub Release if they are not on disk yet.
REPO_URL=$(git config --get remote.origin.url 2>/dev/null | sed -e 's#\.git$##' -e 's#git@github.com:#https://github.com/#' || true)
for v in v1 v2; do
  if [ ! -d "model_out/$v" ] && [ -n "$REPO_URL" ]; then
    mkdir -p "model_out/$v"
    if curl -fsSL --retry 5 --retry-all-errors --retry-delay 5 -o "/tmp/model-$v.tar.gz" "$REPO_URL/releases/download/$v/model.tar.gz"; then
      tar -xzf "/tmp/model-$v.tar.gz" -C "model_out/$v"
    else
      rmdir "model_out/$v" 2>/dev/null || true
      echo "no release asset for $v, skipping"
    fi
  fi
  if [ -d "model_out/$v" ]; then
    python3 scripts/upload_model.py "model_out/$v" "$v"
  fi
done

docker build -f service/Dockerfile -t parser-service:1 .
k3d image import parser-service:1 -c cloudmini
kubectl apply -f k8s/app.yaml
kubectl -n app rollout status deploy/parser --timeout=600s || true
echo "up done: curl -X POST localhost:8080/parse -H 'Content-Type: application/json' -d '{\"text\": \"what is the weather in london\"}'"
