# Kubernetes deployment

This directory contains a Kustomize-based deployment for the app stack.
Monitoring is expected to be provided by the existing cluster monitoring namespace.

## 1) Create runtime secrets

The repository does not contain deployable passwords. Create the namespace and
the required Secret locally before applying the Kustomize bundle:

```bash
kubectl apply -f k8s/namespace.yaml

POSTGRES_PASSWORD="$(openssl rand -hex 24)"
GRAFANA_PASSWORD="$(openssl rand -hex 24)"

kubectl create secret generic app-secrets \
  --namespace ai-orchestrator \
  --from-literal=POSTGRES_USER=orchestrator \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --from-literal=POSTGRES_DB=orchestrator \
  --from-literal=DATABASE_URL_ASYNC="postgresql+asyncpg://orchestrator:${POSTGRES_PASSWORD}@postgres:5432/orchestrator" \
  --from-literal=DATABASE_URL_SYNC="postgresql+psycopg2://orchestrator:${POSTGRES_PASSWORD}@postgres:5432/orchestrator" \
  --from-literal=DATA_SOURCE_NAME="postgresql://orchestrator:${POSTGRES_PASSWORD}@postgres:5432/orchestrator?sslmode=disable" \
  --from-literal=GRAFANA_PASSWORD="${GRAFANA_PASSWORD}" \
  --dry-run=client -o yaml | kubectl apply -f -
```

For a shared environment, manage this Secret through SOPS, Sealed Secrets, or
your cluster's external secret provider instead of shell history.

## 2) Set service image names

Edit `k8s/kustomization.yaml` and replace the placeholder registry paths under `images`:

- `ghcr.io/korabcenaj/dual-gpu-api-gateway`
- `ghcr.io/korabcenaj/dual-gpu-vision-worker`
- `ghcr.io/korabcenaj/dual-gpu-llm-worker`
- `ghcr.io/korabcenaj/dual-gpu-frontend`

If your GitHub owner is different, replace `korabcenaj` with your owner name.

These images must be reachable by your Kubernetes nodes.

Create an image pull secret (required for private GHCR packages):

```bash
kubectl create secret docker-registry ghcr-creds \
	--namespace ai-orchestrator \
	--docker-server=ghcr.io \
	--docker-username=<github-username> \
	--docker-password=<github-token-with-read-packages> \
	--dry-run=client -o yaml | kubectl apply -f -
```

## 3) Label GPU nodes

Workers use node affinity labels defined in `k8s/workers.yaml`:

- vision worker requires `gpu-vision=true`
- llm worker requires `gpu-llm=true`

Single-node GPU host example:

```bash
kubectl label node <gpu-node-name> gpu-vision=true --overwrite
kubectl label node <gpu-node-name> gpu-llm=true --overwrite
```

The worker deployments use those labels rather than a hard-coded hostname.

## 4) Deploy

From repo root:

```bash
make k8s-up
```

Or directly:

```bash
kubectl apply -k k8s
```

## 5) Check status

```bash
make k8s-status
```

If pods were already failing with `ImagePullBackOff`, restart deployments after creating the secret:

```bash
kubectl rollout restart deployment -n ai-orchestrator \
	api-gateway dispatch-worker frontend vision-worker llm-worker
```

The first GPU-worker startup downloads demonstration model files into the
`vision-models` and `llm-models` PVCs. Subsequent starts reuse those files.
For restricted clusters, populate the PVCs through an approved artifact path
and set the corresponding bootstrap environment variable to `"0"`.

## 6) Access services

Ingress is available through the existing `ingress-nginx` controller using:

- App: `http://ai-orchestrator.local.lan/`
- API: `http://ai-orchestrator.local.lan/api/v1/health`

NodePort remains available as a fallback:

- Frontend: `http://<node-ip>:30080`
- API gateway: `http://<node-ip>:30081`

## 7) Remove

```bash
make k8s-down
```

## Notes

- GPU workers mount `/dev/dri` from the host, drop Linux capabilities, and
  disable privilege escalation. The device group permissions on the target
  node must still permit access.
- PersistentVolumeClaims currently request the `local-path` StorageClass;
  change it for clusters using a different storage provisioner.
- Replace mutable image tags with tested immutable digests before promoting
  this deployment beyond a lab.
