# Dual GPU AI Orchestrator

This repository contains a multi-service AI inference orchestrator designed for learning, experimentation, and platform engineering practice. The implemented topology routes LLM work to an AMD GPU worker and vision work to an Intel iGPU worker through a shared API, queue, and job model.

The repository is intentionally presented as a self-managed engineering system, not as a production AI platform. CI verifies the API/queue contract, frontend build, Compose configuration, and container builds without requiring GPU hardware or downloading model weights into image layers.

## Features
- **Web Frontend**: React + Vite UI for submitting jobs, monitoring status, and visualizing metrics
- **API Gateway**: FastAPI service for routing, job management, and orchestration
- **LLM Service**: Handles large language model inference jobs
- **Vision Service**: Handles computer vision inference jobs
- **Job Queue**: Distributed job management and scheduling
- **Heterogeneous GPU Support**: Explicit Intel iGPU and AMD render-device workers with CPU/provider fallback in the service code
- **Kubernetes Native**: All deployments, services, and configs as YAML (k8s/)
- **Monitoring**: Prometheus and Grafana integration (infra/)
- **Test Suite**: Basic integration and health tests (tests/)

## Directory Structure
- `frontend/` — React web UI (Vite, Tailwind, TypeScript)
- `services/` — Microservices: `api-gateway`, `llm-service`, `vision-service`
- `k8s/` — Kubernetes manifests for all components
- `infra/` — Monitoring and observability configs (Prometheus, Grafana)
- `scripts/` — Utility scripts for setup and benchmarking
- `tests/` — Integration and smoke tests

## Quick Start
### Prerequisites
- Docker & Docker Compose
- Kubernetes cluster (with GPU nodes)
- `kubectl` configured for your cluster

### Local Development
1. Clone the repo:
   ```sh
   git clone https://github.com/korabcenaj/dual-gpu-ai-orchestrator.git
   cd dual-gpu-ai-orchestrator
   ```
2. Create local configuration and set unique passwords:
   ```sh
   cp .env.example .env
   ```
3. Start services with Docker Compose:
   ```sh
   docker compose up --build
   ```
4. Access the frontend at http://localhost:3000. Grafana uses http://localhost:3001.

Model files are runtime data and are not embedded in container images. Set
`VISION_BOOTSTRAP_MODELS=1` or `LLM_BOOTSTRAP_MODELS=1` deliberately in `.env`
to download configured demonstration models at startup. MobileNet and
TinyLlama have configured sources; object detection additionally requires an
operator-reviewed `YOLO_ONNX_URL`.

### Kubernetes Deployment

The Kustomize bundle requires an operator-created Secret and labeled GPU
nodes. Follow the deployment and secret-management steps in
[`k8s/README.md`](k8s/README.md).

## Learning Resources
- Explore the `frontend/` for modern React patterns
- Review `services/` for FastAPI, job queue, and ML inference code
- Study `k8s/` for real-world multi-service Kubernetes deployments
- Use `infra/` to learn about Prometheus/Grafana monitoring

## Key Skills Demonstrated

- **Full-Stack Cloud-Native Engineering**: Modern React (Vite, Tailwind) frontend, FastAPI microservices, and distributed Celery job queue.
- **Heterogeneous Compute**: Separate AMD LLM and Intel vision workers, explicit queue routing, provider selection, and hardware fallback boundaries.
- **Kubernetes DevOps**: End-to-end containerization, k8s manifests, kustomize support, and infrastructure-as-code patterns.
- **Distributed Systems**: Asynchronous job dispatch, scalable microservices, and robust queue-based architecture.
- **Machine Learning MLOps**: LLM inference (llama-cpp-python, Vulkan), vision inference (ONNX/OpenVINO, optional YOLO ONNX, MobileNet), and model management.
- **Observability & Monitoring**: Prometheus metrics endpoints, Grafana dashboards, and real-time frontend visualizations.
- **API-First & Automation**: RESTful APIs, OpenAPI docs, Makefile automation, and Docker Compose for local dev.
- **Testing & Reliability**: Integration and health tests, priority job scheduling, and graceful error handling.
- **Clean Code & Modularity**: Well-structured, commented, and maintainable codebase for rapid learning and onboarding.
- **Team-Ready Practices**: Clear separation of concerns, scalable architecture, and documentation for collaboration.

## Verified repository checks

- FastAPI liveness and job-queue routing tests run without live Postgres, Redis, or GPU hardware.
- The React/TypeScript frontend builds from a clean `npm ci` installation.
- Docker Compose configuration is validated with CI-only credentials.
- Container images are built from clean contexts; generated frontend output, dependencies, Python caches, and model weights are excluded from Git.
- API and vision dependencies have no known advisories in the current `pip-audit` database.
- Live cluster queue tests remain opt-in through `RUN_LIVE_SMOKE=1`.

## Current evidence boundary

- The repository does not claim NVIDIA execution or production-scale scheduling.
- GPU inference requires compatible host devices, drivers, model files, and runtime permissions that hosted CI cannot prove.
- The Compose defaults are for isolated local development. Shared environments must provide unique passwords and reviewed network exposure.
- Kubernetes manifests require operator-created Secrets and labeled GPU nodes;
  immutable image digests and signed-release promotion remain future hardening work.
- `llama-cpp-python` currently brings in `diskcache` 5.6.3, whose
  [unsafe-deserialization advisory](https://github.com/advisories/GHSA-w8v5-vhqr-4h9v)
  has no fixed release. The application does not use DiskCache APIs; deployments
  should still prevent untrusted writes to the worker filesystem and model volume.

See [SECURITY.md](SECURITY.md) for reporting and support expectations.

## License

[MIT](LICENSE)

---
This project is for educational and research purposes. Contributions and questions are welcome!
