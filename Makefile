SHELL := /bin/bash
COMPOSE := docker compose
KUBECTL ?= kubectl
PROJECT := dual-gpu-ai-orchestrator
K8S_NAMESPACE ?= ai-orchestrator

.PHONY: setup deps build up down logs ps test benchmark gpu-check frontend-install frontend-build k8s-up k8s-down k8s-status k8s-logs k8s-rebuild-vision k8s-restart-vision

setup:
	./scripts/setup_host.sh

deps:
	cd frontend && npm install

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

test:
	pytest -q

benchmark:
	./scripts/benchmark_gpu.sh

gpu-check:
	./scripts/check_gpu_stack.sh

k8s-up:
	$(KUBECTL) apply -k k8s

k8s-down:
	$(KUBECTL) delete -k k8s --ignore-not-found=true

k8s-status:
	$(KUBECTL) get all -n $(K8S_NAMESPACE)

k8s-logs:
	$(KUBECTL) logs -n $(K8S_NAMESPACE) deployment/api-gateway --tail=200 -f

k8s-rebuild-vision:
	$(KUBECTL) delete job -n $(K8S_NAMESPACE) vision-image-build --ignore-not-found=true
	$(KUBECTL) apply -f k8s/vision-image-build-job.yaml
	$(KUBECTL) logs -n $(K8S_NAMESPACE) -l job-name=vision-image-build -f

k8s-restart-vision:
	$(KUBECTL) rollout restart deployment -n $(K8S_NAMESPACE) vision-worker
