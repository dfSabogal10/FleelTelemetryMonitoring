# Architecture Decision Records

Concise ADRs for the Fleet Telemetry Monitoring MVP. Each entry follows: **Context → Decision → Consequences → Alternatives considered**.

---

## ADR-1: FastAPI + async SQLAlchemy (asyncpg)

**Context**  
The API must handle concurrent HTTP ingestion and read queries against Postgres with clear async I/O boundaries.

**Decision**  
Use **FastAPI** with **SQLAlchemy 2 async** and **asyncpg**.

**Consequences**  
- **+** Natural async request handlers; one session per request pattern fits FastAPI.  
- **+** Type hints and Pydantic integration align with API validation.  
- **−** Async SQLAlchemy has a steeper mental model than sync; tests must align loop/fixture scope with async engines.

**Alternatives**  
- **Sync SQLAlchemy + thread pool**: simpler mental model, less ideal under concurrent load.  
- **Django / other stacks**: heavier for a focused API-only service.

**At larger scale**  
Connection pooling tuning, read replicas, or splitting read/write paths — without changing the core “Postgres is truth” rule.

---

## ADR-2: Postgres over SQLite

**Context**  
The system must support **overlapping ingestion and reads**, **row-level locking**, and **atomic increments** under concurrency.

**Decision**  
Use **PostgreSQL** as the only database.

**Consequences**  
- **+** Mature concurrent writer semantics and transactional isolation suitable for locking patterns.  
- **+** Behavior closer to production deployments.  
- **−** Requires running Postgres locally or in Docker for dev/test (operational cost vs. SQLite file).

**Alternatives**  
- **SQLite**: attractive for a single-file demo, but a weaker fit for concurrent ingestion + explicit locking patterns used here.

**At larger scale**  
Partitioning, replicas, managed Postgres — not required for this MVP’s cardinality.

---

## ADR-3: Synchronous transactional ingestion (no queue/batch-by-default)

**Context**  
Telemetry arrives via `POST /telemetry`. Alternatives include **brokers (Kafka/RabbitMQ)**, **Celery-style workers**, **batching DB writes**, or **in-memory buffers** before flush.

**Decision**  
Process each accepted request in a **single transactional unit**: persist telemetry, update vehicle state (with stale guards), adjust zone counters, evaluate anomalies, and run fault side effects **before commit**.

**Consequences**  
- **+** **Straightforward correctness story**: one transaction boundary per event.  
- **+** Easier reasoning about ordering with DB constraints and locks.  
- **+** Lower **operational complexity** (no broker cluster) within a **5–6 hour** challenge.  
- **−** Throughput bounded by per-request transaction latency; **not** optimized for firehose-scale ingestion.

**Alternatives considered**  
- **Queue + workers**: better peak throughput and decoupling; adds delivery semantics, poison queues, and worker scaling concerns.  
- **Batching flushes**: fewer round-trips; adds latency and failure modes for partial batches.  
- **In-memory buffers**: risks data loss and split-brain vs. DB unless carefully designed.

**Rationale for MVP scale**  
Challenge assumptions imply **~50 events/sec** — **synchronous transactional ingestion** is sufficient and trades peak throughput for **clarity and transactional guarantees**.

**At larger scale**  
Durable queues, idempotent consumers, backpressure, and possibly **regional** ingestion layers — with **idempotency keys** (see README).

---

## ADR-4: Polling over WebSockets

**Context**  
The dashboard needs near-real-time visibility into fleet and zones.

**Decision**  
**HTTP polling** on a ~**1 s** interval on success; **backoff** when the API is unhealthy.

**Consequences**  
- **+** Simple client and ops story; easy to cache-bust and test.  
- **−** Not ideal for very large payloads or sub-second fan-out.

**Alternatives**  
- **WebSockets / SSE**: lower latency and push efficiency when subscription semantics matter.

**At larger scale**  
Push channels, incremental deltas, or field-level subscriptions — if the UI needs them.

---

## ADR-5: Telemetry-driven fault transitions (no separate status API)

**Context**  
Vehicles can enter **fault** and trigger mission cancellation and maintenance records.

**Decision**  
Apply fault-related transitions **inside telemetry ingestion** — **no** separate public “update vehicle status” endpoint.

**Consequences**  
- **+** **Single write path** for operational state derived from edge telemetry.  
- **+** Avoids dual-write ambiguity between “manual status” and telemetry.  
- **−** All fault transitions must go through the ingestion path (by design).

**Alternatives**  
- **Dedicated transition endpoint**: flexible for operators but invites inconsistency with telemetry unless heavily coordinated.

**At larger scale**  
Operator overrides might warrant workflow APIs — still ideally reconciled with telemetry and audit logs.

---

## ADR-6: No in-memory authoritative counters or fleet state

**Context**  
Zone counts and fleet aggregates could be mirrored in process memory for speed.

**Decision**  
**Do not** treat in-memory structures as authoritative. Counters and aggregates **read from Postgres**; increments use **database atomicity**.

**Consequences**  
- **+** Horizontal scaling story does not depend on a magic single writer process.  
- **+** Restarts do not silently reset “truth.”  
- **−** Read paths hit the DB every time (acceptable at this cardinality).

**Alternatives**  
- **Redis counters**: fast but adds synchrony and failure modes with the DB unless carefully designed.

**At larger scale**  
Caching **non-authoritative** read models with TTL invalidation — **after** correctness in DB is unquestioned.

---

## ADR-7: Deterministic anomaly heuristics

**Context**  
“Anomaly detection” could mean ML pipelines, rules engines, or external scoring services.

**Decision**  
Implement **deterministic, explainable heuristics** tied to telemetry fields and persisted as anomaly rows.

**Implemented rules (MVP)** — evaluated on each accepted telemetry payload (see `app/services/anomaly.py`):

| Rule | Trigger | Severity | Notes |
|------|---------|----------|--------|
| **Fault status** | `status == fault` | **critical** | Operator-visible fault declaration from the edge. |
| **Low battery** | `battery_pct < 15` | warning | Fixed threshold; illustrative for industrial bots. |
| **Excessive speed** | `speed_mps > 5.0` | warning | Single threshold in m/s; not tuned per vehicle class. |
| **Error codes reported** | `error_codes` non-empty | warning | Any reported code list raises an anomaly (payload is trusted). |
| **Impossible position jump** | Implied speed between **previous** and **current** event `> 8.0` m/s | warning | Haversine distance between successive `(lat, lon)` divided by positive elapsed time (`current.timestamp − previous.timestamp`); skipped if there is no prior event for the vehicle or elapsed time `≤ 0`. |

The **impossible jump** rule encodes “teleportation” / bad GPS / clock skew sanity-checking without claiming physical vehicle dynamics modeling. Thresholds are **constants** for transparency and tests, not learned parameters. **Rule intent** for this check came from **author feedback** during design (see **AI_INTERACTION_LOG.md**); implementation followed in code review.

**Consequences**  
- **+** Reproducible tests and debugging.  
- **−** Not adaptive “learning” detection.

**Alternatives**  
- **ML models**: powerful; needs training data, deployment, and governance — out of MVP scope.

---

## ADR-8: Direct aggregate queries over materialized views

**Context**  
Fleet totals and zone counts could be served from **materialized views** or **projection tables** refreshed asynchronously.

**Decision**  
Use **direct SQL aggregates / simple reads** against base tables for fleet and zone endpoints.

**Consequences**  
- **+** **Strong consistency** relative to committed writes; no refresh lag policy to argue about.  
- **+** Minimal moving parts for **~50** vehicles and **~20** zones.  
- **−** Heavier read queries if cardinality grows without new indexing or projections.

**Alternatives**  
- **Materialized views**: can speed heavy aggregates; introduce **staleness** and **refresh** operational rules.

**At larger scale**  
Indexed projections, MVs with controlled refresh, or CQRS-style read models — when query cost justifies them.

---

## Summary

The MVP optimizes for **transactional clarity**, **Postgres as source of truth**, and **honest scope** for a timeboxed exercise. Throughput-oriented and distribution-heavy patterns are **explicitly deferred** until requirements justify the complexity.
