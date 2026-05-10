# Architecture Decision Record

This file answers the take-home rubric first, then adds **extended ADRs** for readers who want topic-by-topic depth.

---

## 1. What were the two or three most important decisions, and why?

**Decision A — PostgreSQL as the only source of truth (no in-memory authoritative fleet or zone counters)**  
Concurrency-sensitive behavior (atomic zone increments, transactional fault side effects, aggregate reads) depends on **durable rows and locks**. Keeping “truth” out of process memory avoids split-brain across instances and makes restarts safe.

**Decision B — Synchronous, transactional ingestion per `POST /telemetry` (no queue/broker as the default path)**  
Each event is handled in **one commit boundary**: persist telemetry, apply stale guards, update vehicle snapshot, increment zones, record anomalies, run fault transitions. That trades peak throughput for a **simple correctness story** appropriate to ~50 vehicles / ~50 events/sec and a short timebox.

**Decision C — Telemetry-driven operational state (no separate public “set vehicle status” API)**  
Vehicle status and fault handling stay on the **same write path** as ingestion to avoid dual-write ambiguity between operators and the edge.

---

## 2. What was unclear in the spec, and what did we assume?

| Gap | Deliberate assumption |
|-----|------------------------|
| **Missions** — payloads did not include mission IDs | At most **one active mission per vehicle**; missions **seeded at startup**; cancellation targets that row. |
| **Idempotency** — no `event_id` | Every accepted POST is a **distinct** persisted event; we **do not** dedupe by timestamp or payload hash (could drop legitimate repeats). |
| **Anomaly semantics** — “detection” undefined | **Deterministic rules** over telemetry fields (see `app/services/anomaly.py`); not ML. **Impossible position jump** rule intent came from **author feedback** during design (see AI interaction log). |
| **Trust boundaries** | **Timestamps** trusted for ordering vs. `last_seen_at`; **`zone_entered`** trusted for zone increments when present and valid. |

---

## 3. What would need to change if scale grew significantly?

**“Significantly” here means:** roughly **10×+** sustained ingestion rate or fleet size, **multi-region** deployment, or **read-heavy** dashboards where Postgres CPU/IO becomes the bottleneck—not marginal growth within a single modest fleet.

Likely changes (incremental, not all-or-nothing):

- **Ingestion**: durable **queues**, **idempotent** consumers, **batch writes** or partitioned writers; **edge `event_id`** + uniqueness constraints.
- **Reads**: **read replicas**, **caching** (Redis) for non-authoritative aggregates, **materialized views** or projections with explicit staleness SLAs.
- **Dashboard**: **WebSockets/SSE** or incremental deltas if polling cost or latency dominates.

Core principle that should survive: **Postgres remains authoritative** until a deliberate CQRS/event-sourcing split is justified.

---

## 4. What was deliberately left out, and why?

| Omitted | Why (MVP / timebox) |
|---------|---------------------|
| Kafka/RabbitMQ/Celery-style ingestion | Operational cost; sync path sufficient for stated scale |
| Batched-only ingestion buffers | Complexity vs. correctness wins |
| Redis / MVs / CQRS read models | Cardinality small; strong consistency simpler |
| WebSockets | Polling sufficient for 50 vehicles @ ~1 Hz UI refresh |
| ML anomaly detection | Out of scope; rules are testable |
| Kubernetes, tracing, exactly-once semantics | Not required to demonstrate transactional correctness |

---

## Appendix A — Extended ADRs (topic-by-topic)

*Optional depth; same decisions as above, split for readers who prefer ADR-style sections.*

### A.1 FastAPI + async SQLAlchemy (asyncpg)

**Context:** Concurrent HTTP + async DB I/O.  
**Decision:** FastAPI + SQLAlchemy 2 async + asyncpg.  
**Tradeoff:** Async SQLAlchemy complexity vs. sync + threads; chosen for natural async handlers.  
**Larger scale:** Pool tuning, replicas (see §3).

### A.2 Postgres over SQLite

**Context:** Overlapping writers, `SELECT … FOR UPDATE`, atomic increments.  
**Decision:** Postgres only.  
**Tradeoff:** Ops overhead vs. SQLite file simplicity.  
**Larger scale:** Managed Postgres, partitioning if row counts explode.

### A.3 Synchronous transactional ingestion

**Context:** Alternative patterns—brokers, Celery workers, periodic DB flushes, in-memory buffers.  
**Decision:** One transaction per accepted telemetry request (see Decision B above).  
**Larger scale:** Queues + idempotent workers (see §3).

### A.4 Polling over WebSockets

**Decision:** HTTP polling ~1s on success, backoff on failure.  
**Larger scale:** Push channels if UI/latency demands it.

### A.5 Telemetry-driven fault transitions

**Decision:** Fault side effects inside ingestion; no separate status mutation API (see Decision C above).

### A.6 No in-memory authoritative counters

**Decision:** Zone/fleet truth in DB rows; atomic SQL increments.  
**Larger scale:** Cache **non-authoritative** read models only after DB correctness is solid.

### A.7 Deterministic anomaly heuristics

**Decision:** Explainable rules persisted as anomaly rows.

**Implemented rules (MVP)** — `app/services/anomaly.py`:

| Rule | Trigger | Severity |
|------|---------|----------|
| Fault status | `status == fault` | critical |
| Low battery | `battery_pct < 15` | warning |
| Excessive speed | `speed_mps > 5.0` | warning |
| Error codes reported | `error_codes` non-empty | warning |
| Impossible position jump | Haversine implied speed between successive events `> 8.0` m/s | warning |

Skipped when no prior event or elapsed time ≤ 0. **Impossible jump** rule intent: author feedback during design (see AI_INTERACTION_LOG.md).

**Larger scale:** ML or external scoring—only with data and ops maturity.

### A.8 Direct aggregates vs materialized views

**Decision:** Query base tables for `/fleet/state`, `/zones/counts`, `/vehicles`.  
**Tradeoff:** Simplicity vs. refresh policies for MVs.  
**Larger scale:** Indexed projections or MVs when query cost warrants.

---

## Appendix B — Summary line

The MVP optimizes **transactional clarity**, **Postgres as source of truth**, and **honest scope** for a timeboxed exercise; distribution-heavy patterns are **explicitly deferred** until §3 triggers apply.
