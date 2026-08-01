.PHONY: install lint type test test-unit eval migrate run worker up down \
        image helm-lint helm-template kind-up kind-load deploy-local k8s-down \
        tf-init tf-apply tf-destroy

install:
	pip install -e ".[dev]"

lint:
	ruff check src tests scripts
	ruff format --check src tests scripts

type:
	mypy src

test-unit:
	pytest tests/unit

test:
	pytest

eval:
	python scripts/run_eval.py

migrate:
	alembic upgrade head

run:
	uvicorn eka.main:app --reload

worker:
	python -m eka.worker

up:
	docker compose up --build

down:
	docker compose down -v

# --- Deployment (Phase 7): all local, all free ---

IMAGE ?= eka:local
KIND_CLUSTER ?= eka-local

image:
	docker build -f docker/Dockerfile -t $(IMAGE) .

helm-lint:
	helm lint deploy/helm/eka -f deploy/helm/eka/values-local.yaml

helm-template:
	helm template eka deploy/helm/eka -f deploy/helm/eka/values-local.yaml

kind-up:
	kind create cluster --config deploy/kind/kind-config.yaml

kind-load:
	kind load docker-image $(IMAGE) --name $(KIND_CLUSTER)

# Full local loop: build, load, install. Requires an existing kind cluster
# (run "make kind-up" first, or use the Terraform path).
deploy-local: image kind-load
	helm upgrade --install eka deploy/helm/eka \
	  -f deploy/helm/eka/values-local.yaml \
	  --namespace eka --create-namespace --wait --timeout 300s

k8s-down:
	kind delete cluster --name $(KIND_CLUSTER)

tf-init:
	terraform -chdir=deploy/terraform init

tf-apply:
	terraform -chdir=deploy/terraform apply

tf-destroy:
	terraform -chdir=deploy/terraform destroy
