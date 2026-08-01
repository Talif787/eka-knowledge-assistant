# Deployment

The service ships with a Helm chart and a Terraform configuration that stand it
up on Kubernetes. Everything here runs locally at no cost: a kind cluster runs
Kubernetes in Docker, and the chart can run its own in-cluster Postgres and Redis
so nothing external is needed. The same chart targets a real cluster in
production by pointing at managed services instead.

## Prerequisites

All free and open source: Docker, kind, kubectl, Helm, and (for the Terraform
path) Terraform. In Codespaces, Docker is already present; install the rest from
their official instructions.

## Layout

- `deploy/helm/eka`: the Helm chart (API, worker, migration hook, Service,
  Ingress, HPA, PodDisruptionBudget, NetworkPolicy, and toggleable in-cluster
  Postgres and Redis).
- `deploy/helm/eka/values.yaml`: production-leaning defaults (external database
  and Redis, dev token endpoint off, JWT secret and DSN required).
- `deploy/helm/eka/values-local.yaml`: local overrides (in-cluster Postgres and
  Redis, single replica, autoscaling off, dev token on).
- `deploy/kind/kind-config.yaml`: local cluster definition.
- `deploy/terraform`: provisions a kind cluster and installs the chart.

## Quick path: Make, kind, and Helm

```bash
make kind-up          # create the local cluster
make deploy-local     # build the image, load it into kind, install the chart
```

`deploy-local` waits for a healthy rollout. Then reach the API:

```bash
kubectl port-forward -n eka svc/eka 8000:8000
curl -sf http://localhost:8000/health/ready && echo OK
```

Because the local values enable the dev token endpoint, you can mint a token:

```bash
curl -s -X POST http://localhost:8000/v1/auth/token
```

Tear down with `make k8s-down`.

## Terraform path

Terraform provisions the cluster and installs the release as one managed unit.
The application image must be loaded into the cluster before the release starts
(the local values set an image pull policy of Never), and Terraform cannot build
and load the image mid-apply, so the first run is two steps:

```bash
make tf-init
terraform -chdir=deploy/terraform apply -target=kind_cluster.this
make image
kind load docker-image eka:local --name eka-local
make tf-apply
```

Later runs are a single `make tf-apply` as long as the image is loaded. Remove
everything with `make tf-destroy`.

Note on provider configuration: the Helm provider is configured from the kind
cluster resource. If the first apply reports a provider connection error, the
targeted apply above (creating the cluster first) resolves it. The Helm provider
is pinned to the v2 line to match the configuration syntax.

## Migrations

Two patterns, selected by values:

- Local (`migrations.initContainer: true`): the API pod runs `alembic upgrade
  head` in an init container after waiting for the in-cluster database. Keep API
  replicas at 1 in this mode so migrations do not run concurrently.
- Production (`migrations.hook: true`): a Helm pre-install and pre-upgrade hook
  Job runs the migration against the external database before the new pods roll
  out. This fits the expand-then-contract, backward-compatible migration style
  the service uses, so rollouts and rollbacks stay safe.

## Production

Point at managed data services and supply secrets rather than using the
in-cluster defaults:

```bash
helm upgrade --install eka deploy/helm/eka \
  --namespace eka --create-namespace \
  --set environment=production \
  --set postgresql.enabled=false \
  --set externalDatabase.dsn='postgresql+asyncpg://USER:PASS@HOST:5432/eka' \
  --set redis.enabled=false \
  --set externalRedis.url='redis://HOST:6379/0' \
  --set auth.devTokenEnabled=false \
  --set jwt.secret='REPLACE_WITH_A_STRONG_32_BYTE_SECRET'
```

The JWT secret and external DSN are required and have no defaults, so an install
that forgets them fails rather than shipping something insecure. In a real
setup, source the secret from a secret manager (for example External Secrets or a
sealed secret) rather than passing it on the command line. The image would come
from a registry (for example GitHub Container Registry, free for public repos)
rather than a local build, with `image.repository` and `image.tag` set
accordingly and the pull policy left at IfNotPresent.

## Validation in CI

`.github/workflows/deploy.yml` runs on changes under `deploy/` or `docker/`. It
lints the chart, renders both the local and production shapes and validates every
manifest against the Kubernetes schema with kubeconform, runs `terraform
validate`, and then creates a real kind cluster, loads the image, installs the
chart, and curls `/health/ready`. That last job is the end-to-end proof that the
chart deploys and serves traffic.
