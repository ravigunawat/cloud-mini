#!/usr/bin/env bash
set -euo pipefail
k3d cluster create --config cluster/k3d.yaml || true
for ns in data pipeline app; do
  kubectl create ns $ns --dry-run=client -o yaml | kubectl apply -f -
done
if [ ! -f .env ]; then
  printf 'S3_ACCESS_KEY=%s\nS3_SECRET_KEY=%s\n' "$(openssl rand -hex 8)" "$(openssl rand -hex 16)" > .env
fi
set -a; . ./.env; set +a
cat > /tmp/s3.json <<JSON
{"identities":[{"name":"admin","credentials":[{"accessKey":"$S3_ACCESS_KEY","secretKey":"$S3_SECRET_KEY"}],"actions":["Admin","Read","Write","List","Tagging"]}]}
JSON
kubectl -n data create secret generic seaweed-s3-config --from-file=s3.json=/tmp/s3.json --dry-run=client -o yaml | kubectl apply -f -
rm -f /tmp/s3.json
for ns in pipeline app; do
  kubectl -n $ns create secret generic s3-credentials \
    --from-literal=S3_ACCESS_KEY="$S3_ACCESS_KEY" --from-literal=S3_SECRET_KEY="$S3_SECRET_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -
done
kubectl apply -f k8s/seaweedfs.yaml
kubectl -n data rollout status deploy/seaweedfs --timeout=180s
(kubectl -n data port-forward svc/seaweedfs 8333:8333 >/tmp/pf.log 2>&1 &)
sleep 5
python3 scripts/init_buckets.py
docker build -f service/Dockerfile -t parser-service:1 .
k3d image import parser-service:1 -c cloudmini
kubectl apply -f k8s/app.yaml
echo "up done. Upload the model with: make model-upload"
