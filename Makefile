SHELL := /bin/bash
COMPOSE := docker compose
PROJECT := dual-gpu-ai-orchestrator

.PHONY: setup deps build up down logs ps test benchmark gpu-check frontend-install frontend-build

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
