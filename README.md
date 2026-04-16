# Dual GPU AI Orchestrator

This repository contains a multi-service, GPU-enabled AI orchestration platform designed for learning, experimentation, and research. It features a modern web frontend, multiple backend microservices, and full Kubernetes deployment manifests for running on clusters with both NVIDIA and AMD/Intel GPUs.

## Features
- **Web Frontend**: React + Vite UI for submitting jobs, monitoring status, and visualizing metrics
- **API Gateway**: FastAPI service for routing, job management, and orchestration
- **LLM Service**: Handles large language model inference jobs
- **Vision Service**: Handles computer vision inference jobs
- **Job Queue**: Distributed job management and scheduling
- **GPU Support**: Designed for clusters with multiple GPU types (NVIDIA, AMD, Intel)
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
2. Start services with Docker Compose (for local dev):
   ```sh
   docker-compose up --build
   ```
3. Access the frontend at http://localhost:3000

### Kubernetes Deployment
1. Apply manifests in the `k8s/` directory:
   ```sh
   kubectl apply -k k8s/
   ```
2. Monitor pods and services:
   ```sh
   kubectl get pods -n ai-orchestrator
   ```

## Learning Resources
- Explore the `frontend/` for modern React patterns
- Review `services/` for FastAPI, job queue, and ML inference code
- Study `k8s/` for real-world multi-service Kubernetes deployments
- Use `infra/` to learn about Prometheus/Grafana monitoring

## Key Skills Demonstrated

- **Full-Stack Cloud-Native Engineering**: Modern React (Vite, Tailwind) frontend, FastAPI microservices, and distributed Celery job queue.
- **Multi-GPU & Heterogeneous Compute**: Dynamic inference on both NVIDIA and AMD/Intel GPUs, with backend selection and hardware fallback.
- **Kubernetes DevOps**: End-to-end containerization, k8s manifests, kustomize support, and infrastructure-as-code patterns.
- **Distributed Systems**: Asynchronous job dispatch, scalable microservices, and robust queue-based architecture.
- **Machine Learning MLOps**: LLM inference (llama-cpp-python, Vulkan), vision inference (ONNX/OpenVINO, YOLOv8, MobileNet), and model management.
- **Observability & Monitoring**: Prometheus metrics endpoints, Grafana dashboards, and real-time frontend visualizations.
- **API-First & Automation**: RESTful APIs, OpenAPI docs, Makefile automation, and Docker Compose for local dev.
- **Testing & Reliability**: Integration and health tests, priority job scheduling, and graceful error handling.
- **Clean Code & Modularity**: Well-structured, commented, and maintainable codebase for rapid learning and onboarding.
- **Team-Ready Practices**: Clear separation of concerns, scalable architecture, and documentation for collaboration.

## License
MIT (or specify your license)

---
This project is for educational and research purposes. Contributions and questions are welcome!
