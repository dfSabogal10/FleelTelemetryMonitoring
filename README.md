# Fleet Telemetry Monitoring

Single-service stack for ingesting telemetry from **50 autonomous industrial vehicles**, persisting events in **Postgres**, applying **deterministic anomaly rules**, maintaining **zone entry counts** and **fleet aggregates**, handling **fault transitions** (including mission cancellation and maintenance records) inside transactional ingestion, and exposing a **React + Material UI** operational dashboard with **polling-based** live updates.

This repository is a **take-home MVP**: correctness and clear reasoning over hyperscale features.

---

## Architecture summary

| Layer | Choice |
|--------|--------|
| API | **FastAPI** with **async SQLAlchemy** and **asyncpg** |
| Data | **PostgreSQL** — authoritative state lives in rows, not process memory |
| UI | **React**, **TypeScript**, **Vite**, **Material UI** |
| Live updates | **HTTP polling** (~1s on success; exponential backoff on failures) |
| Deploy (local) | **Docker Compose** — Postgres, backend, frontend |

---

## Why polling instead of WebSockets

- Fleet size is **50 vehicles** at **~1 Hz** in the challenge scenario; refreshing aggregates roughly **once per second** is sufficient for an operational overview.
- **Polling reduces coordination complexity** (no connection lifecycle, reconnect logic, or sticky routing for this MVP).
- **Easier to test and debug** (plain HTTP, repeatable curl/scripts).
- Fits a **5–6 hour** scope; WebSockets would add surface area without changing core correctness goals.

At larger scale or for sub-second UX, **SSE or WebSockets** with selective subscriptions would be reasonable next steps.

---

## Why Postgres instead of SQLite

- **Concurrent writers**: ingestion and reads overlap; Postgres handles concurrent sessions predictably.
- **Transactional semantics**: fault transitions rely on **short transactions** and **row-level locking**; SQLite’s concurrency model is a poorer fit for this pattern.
- **Aggregates and constraints**: fleet and zone reads are derived from persisted rows; Postgres matches production-style behavior for this exercise.

---

## Running locally

### Full stack (recommended)

From the repository root:

```bash
docker compose up --build
```

- **API**: `http://localhost:8000` (override with `BACKEND_PORT`)
- **UI**: `http://localhost:5173` (override with `FRONTEND_PORT`; `VITE_API_BASE_URL` targets the backend)

Ensure Postgres credentials in `.env` (or defaults) match `docker-compose.yml`. The test database `fleet_test` is created on **first** Postgres volume init via `docker/postgres/init-test-db.sql`.

### Backend tests

Requires **PostgreSQL** reachable at the URL used by tests (see `backend/tests/conftest.py`). Override with `TEST_DATABASE_URL` if your compose credentials differ from defaults.

```bash
cd backend
pip install -e ".[dev]"
pytest
```

E2E-style ingestion smoke (`tests/e2e/test_fleet_ingestion_smoke.py`) exercises concurrent `/telemetry` traffic against the test DB — **correctness under concurrency**, not a throughput benchmark.

### Testing strategy

Tests deliberately emphasize **backend correctness**: transactional behavior, **concurrency**, and **E2E ingestion smoke** coverage. **Frontend-heavy** test suites were deprioritized relative to timebox and risk — the highest-impact unknowns for this challenge live in **data races and transactional boundaries**, not React component logic.

### Frontend (without Docker)

```bash
cd frontend
npm ci
npm run dev
```

Point `VITE_API_BASE_URL` at your API if not using the Compose default.

---

## API overview

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/telemetry` | Ingest one telemetry event; transactional vehicle update, zone increments, anomalies, fault side effects |
| `GET` | `/vehicles` | Vehicle snapshots (status, zone, timestamps, …) |
| `GET` | `/fleet/state` | Aggregate counts by operational status |
| `GET` | `/zones/counts` | Per-zone entry counters |
| `GET` | `/anomalies` | Recent anomalies (optional filters; `limit` capped server-side) |
| `GET` | `/health` | Liveness |

### Request & query validation

Validation uses **Pydantic** (`422` on validation failure). Domain rules (unknown vehicle, DB constraints) return **application errors** (e.g. `404` for unknown `vehicle_id` on ingest).

#### `POST /telemetry` (JSON body)

| Field | Validation |
|--------|------------|
| `vehicle_id` | Required string, **min length 1**. Unknown IDs → **404** after validation. |
| `timestamp` | ISO **datetime** (parsed by Pydantic/FastAPI). |
| `lat` | **−90 ≤ lat ≤ 90** |
| `lon` | **−180 ≤ lon ≤ 180** |
| `battery_pct` | **integer 0–100** |
| `speed_mps` | **float ≥ 0** |
| `status` | Enum: **`idle`**, **`moving`**, **`charging`**, **`fault`** |
| `error_codes` | **array of strings** (may be empty). |
| `zone_entered` | **`null`** or a **known zone id** string. Unknown zone strings → **422**. Known zones are the constants in `app/constants/zones.py` (e.g. `charging_bay_1`, `maintenance_bay`, `aisle_a`, docks, etc.). |

#### `GET /anomalies` (query parameters)

| Parameter | Validation |
|-----------|------------|
| `vehicle_id` | Optional string; **no format validation** — filters anomalies for that id if provided. |
| `start_time` | Optional ISO **datetime** — **`created_at ≥ start_time`**. |
| `end_time` | Optional ISO **datetime** — **`created_at ≤ end_time`**. |
| `limit` | Optional integer, default **100**, **min 1**, **max 1000** |

#### Read endpoints without query/body validation

`GET /vehicles`, `GET /fleet/state`, `GET /zones/counts`, and `GET /health` take **no query parameters** in this MVP; responses are derived entirely from persisted DB state.

---

## Assumptions

- **Missions**: Each vehicle has **at most one active** mission; missions are **seeded at startup** and belong to **one vehicle**. Telemetry payloads do not carry mission IDs; behavior follows persisted mission rows.
- **Telemetry as source of truth** for **vehicle operational state** from the edge client’s perspective in this MVP (no separate public “set status” API).
- **Timestamps** on incoming telemetry are **trusted** for ordering against `last_seen_at` (stale protection).
- **`zone_entered`** is **trusted** from the edge client for incrementing zone counters.
- **Anomalies** follow **deterministic, heuristic rules** — illustrative, not ML-based “ground truth.”

---

## Duplicate telemetry / idempotency

Every accepted `POST /telemetry` is stored as a **distinct** telemetry row **even if the body duplicates** a prior request.

**Reasoning**

- The challenge schema does not define an **`event_id`** or idempotency key.
- Collapsing “duplicates” using timestamp or payload hash risks **dropping legitimate repeated states** (retries vs. true repeats cannot be distinguished safely without an edge idempotency contract).

**Production evolution**

- Require a **stable `event_id`** from the edge.
- Enforce **uniqueness** (e.g. `(vehicle_id, event_id)`) and make ingestion **idempotent** under retries.

---

## Concurrency correctness strategy

- **Postgres is the source of truth** — no authoritative in-memory fleet or zone counters in the API process.
- **Zone counts**: **atomic SQL increments** on persisted counter rows.
- **Stale telemetry**: vehicle “current” state updates only if the incoming timestamp is **≥** stored `last_seen_at`; older events are still persisted as history where modeled.
- **Fault transitions**: handled inside **ingestion transactions** with **row-level locking** where needed so concurrent telemetry cannot corrupt mission/maintenance side effects.
- **Aggregate reads** (`/fleet/state`, `/zones/counts`, `/vehicles`): computed from **current DB rows**, not from caches.

---

## Frontend notes

- **Local component state** and a **polling hook** — no Redux/global store for this scope.
- On polling failure, the UI shows a **non-intrusive** warning (e.g. “Backend unavailable. Retrying…”), applies **exponential backoff**, and **keeps the last successful snapshot** on screen when possible.

---

## Materialized views / aggregate projections

**Materialized views** and **read-optimized projections** were considered for fleet and zone aggregates.

**Deferred for this MVP** because vehicle and zone cardinality is small (**~50** vehicles, **~20** zones): **direct aggregate queries** stay simple and **strongly consistent**. Materialized views add **refresh policies** and **staleness** tradeoffs without proportional benefit here.

At **much higher scale** or read/write imbalance, projections or MVs with explicit refresh or incremental maintenance could make sense.

---

## Deferred production-grade improvements

Not in scope for this challenge; listed for transparency:

- Message **queues** / **Celery**-style workers, **batched** ingestion flushes  
- **Redis** or similar caching layers  
- **WebSockets** / **SSE** for push updates  
- **CQRS**, **event sourcing**, **Kubernetes**, **distributed tracing**  
- **ML** anomaly detection, **distributed locking** beyond DB transactions  
- **Materialized views** / heavy **CQRS read models** (see above)

---

## Further reading

- **[ADR.md](./ADR.md)** — architectural decisions and alternatives  
- **[AI_INTERACTION_LOG.md](./AI_INTERACTION_LOG.md)** — how AI assistance was used and corrected (valued alongside code for this challenge)
