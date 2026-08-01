# Scaling

The architecture was built to scale horizontally, and the deployment reflects
that. This document explains what scales, how, and where the limits are.

## API tier

The API is stateless: every request carries its own bearer token, and no session
state lives in the process. That means it scales horizontally by adding
replicas. The chart ships a HorizontalPodAutoscaler that scales the API
deployment on CPU utilization between a floor and ceiling set in values. A
PodDisruptionBudget keeps a minimum number of replicas available during node
drains and rolling updates.

Autoscaling needs a metrics-server in the cluster. Managed clusters generally
include one; a bare kind cluster does not, which is why the local values disable
autoscaling and pin a single replica.

## Worker tier

The ingestion worker scales horizontally too, and safely, because the job queue
claims work with `SELECT ... FOR UPDATE SKIP LOCKED`. Multiple workers pull from
the same queue without stepping on each other: each row is claimed by exactly one
worker, and contended rows are skipped rather than blocked. Each worker gets a
unique identity from its pod name (injected as `EKA_WORKER_ID`), so claimed jobs
are attributable. To process more ingestion throughput, raise the worker replica
count.

## Data tier

Postgres is the stateful anchor and the usual scaling bottleneck. The service
keeps it healthy in a few ways: a bounded async connection pool per API replica
(`EKA_DATABASE_POOL_SIZE`), so total connections stay predictable as replicas
grow; hybrid search backed by HNSW and GIN indexes, so retrieval stays fast as
the corpus grows; and expand-then-contract migrations, so schema changes do not
require downtime. In production this is a managed Postgres with pgvector. Read
scaling would come from read replicas for the retrieval path, since search is
read-only, while writes stay on the primary.

Redis serves the search cache. It reduces repeated-query latency and takes read
load off Postgres. The cache is ACL-aware, so scaling it does not risk crossing
tenant boundaries. Cache misses degrade to a live search rather than an error, so
Redis is not on the critical path for correctness.

## Resource management

Every workload sets CPU and memory requests and limits, so the scheduler can bin-
pack pods and the autoscaler has a signal to act on. Requests are modest and
limits leave headroom; tune them from real usage. The hardened pod security
context (non-root, read-only root filesystem, dropped capabilities, seccomp)
adds no scaling cost and is a sensible default at any size.

## Where to go next

The pieces that would come with real production load, beyond the scope of a free
local setup: a metrics-server and tuned HPA targets, managed Postgres with read
replicas, a managed Redis, an ingress controller with TLS, and horizontal
autoscaling on custom metrics (for example queue depth for the worker rather than
CPU). The chart already exposes the knobs for most of these through values.
