# Kubernetes deployment

This directory contains a Kustomize-based deployment for the app stack.
Monitoring is expected to be provided by the existing cluster monitoring namespace.

## 1) Set service image names

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

## 2) Label GPU nodes

Workers use node affinity labels defined in `k8s/workers.yaml`:

- vision worker requires `gpu-vision=true`
- llm worker requires `gpu-llm=true`

Single-node GPU host example:

```bash
kubectl label node k8s-master gpu-vision=true --overwrite
kubectl label node k8s-master gpu-llm=true --overwrite
```

## 3) Deploy

From repo root:

```bash
make k8s-up
```

Or directly:

```bash
kubectl apply -k k8s
```

## 4) Check status

```bash
make k8s-status
```

If pods were already failing with `ImagePullBackOff`, restart deployments after creating the secret:

```bash
kubectl rollout restart deployment -n ai-orchestrator \
	api-gateway dispatch-worker frontend vision-worker llm-worker
```

## 5) Access services (NodePort)

- Frontend: `http://<node-ip>:30080`
- API gateway: `http://<node-ip>:30081`

## 6) Remove

```bash
make k8s-down
```

## Notes

- GPU workers mount `/dev/dri` from the host and run privileged to access Intel/AMD render devices.
- Ensure your cluster policy allows privileged pods and hostPath volumes.
- PersistentVolumeClaims rely on your default StorageClass.
