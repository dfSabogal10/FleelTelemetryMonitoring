# AI Interaction Log

Plain markdown log of AI-assisted work: **prompts**, **summarized outputs**, **corrections**, and a short **reflection**. Prompts are listed in **rough chronological order**; wording is **faithful paraphrase** where exact copy-paste was not retained.

---

## Part 1 — Rubric coverage (challenge instructions)

### 1. Meaningful prompts issued

| # | Prompt (summary / paraphrase) |
|---|-------------------------------|
| 1 | Decompose the challenge into backend domains (telemetry ingestion, zones, fleet reads, anomalies), data model, and API surface; call out concurrency and ordering risks. |
| 2 | Model missions when telemetry has **no** mission identifier—how to cancel on fault without inventing payload fields. |
| 3 | Design concurrency strategy for concurrent `POST /telemetry`: zone increments and fault transitions must stay correct. |
| 4 | Implement `POST /telemetry`: persist events, update vehicle snapshot with **stale telemetry protection** (`timestamp >= last_seen_at`). |
| 5 | Define deterministic anomaly rules from telemetry (battery, speed, fault, error codes); wire into ingestion. |
| 6 | Add **impossible position jump** detection: successive lat/lon + timestamps, haversine distance, implied speed vs threshold (human-proposed rule—see corrections). |
| 7 | Implement atomic zone entry increments safe under concurrent ingestion. |
| 8 | On transition to fault: cancel active mission, create maintenance record; keep transactional consistency with telemetry. |
| 9 | Add E2E-style concurrent ingestion across many vehicles (correctness, not throughput benchmarking). |
| 10 | Build React + TypeScript + Material UI dashboard: fetch fleet, vehicles, zones, anomalies; poll for updates. |
| 11 | Add polling **backoff** when the API fails; keep last good data visible; non-intrusive error banner. |
| 12 | Refine dashboard to a **single-page operational** view—fleet cards, vehicle table, zone counts, recent anomalies—avoid enterprise admin patterns. |
| 13 | Generate README, ADR-style decisions, and AI interaction documentation grounded in **actual** stack and tradeoffs (no invented tech). |
| 14 | **Author-led:** Add lightweight **production-readiness** hardening—centralized logging, request logging middleware, domain event logs, **consistent JSON API errors**, safe rollback on ingestion failure, global handlers for unexpected exceptions—not pushed proactively by AI in early implementation prompts. |

*Additional iteration prompts (representative):* narrow UI scope (remove pagination/search/multi-page admin); align layout with operational monitoring; adjust anomaly thresholds/constants as needed; fix Docker/env/test DB wiring during local validation.

**Note:** Initial scaffolding prompts focused on features and correctness; **logging, structured errors, and transactional rollback discipline** were **not enforced upfront by the AI**. The author **intervened later** with an explicit request to strengthen observability and API error handling for the take-home submission.

### 2. Output received (summary — full paste not required)

- **Early:** Module/layout suggestions (FastAPI routers, SQLAlchemy models), Docker Compose skeleton, endpoint list, initial React component tree.
- **Backend:** Service-layer patterns; locking/increment discussions; seed/mission assumptions; pytest fixtures and integration-style tests; concurrent HTTP smoke harness.
- **Frontend:** MUI layout ideas, API client, hooks; initial layouts skewed toward generic admin dashboards until redirected.
- **Docs:** Draft README/ADR/log markdown from agreed decisions.

### 3. Corrections and redirections when the AI missed the mark

- **Transactional boundaries:** Required explicit **monotonic timestamp** rule for vehicle snapshot; **all telemetry rows persisted** even when state does not advance.
- **Idempotency:** Rejected heuristic dedupe without `event_id`; documented honest duplicate behavior.
- **Concurrency:** Insisted on **Postgres authority**, **atomic increments**, **short transactions**, validated with tests—not only narrative locking advice.
- **Fault handling:** Kept fault side effects **inside ingestion**; avoided a separate public status API (dual-write risk).
- **E2E smoke:** Framed as **correctness under concurrency**, not performance claims.
- **Anomalies:** Author provided the **impossible jump** concept; AI assisted implementation/wording after intent was fixed.
- **Frontend:** Pushed back on enterprise-dashboard drift (**pagination**, **search**, **multi-page admin**); iterated to single-page operational dashboard; added polling backoff and degraded UX behavior.
- **Documentation:** Stripped invented tech, exaggerated scale, and fake benchmarks.
- **Logging & errors:** The AI did **not** bake in centralized logging, consistent JSON error bodies, or ingestion rollback/error-handler wiring from the **first** implementation prompts; the author **followed up explicitly** to add lightweight operational hardening appropriate to the MVP.

### 4. Reflection (5 bullets)

- **Good at:** Scaffolding (Compose, routers, models), repetitive boilerplate, test harness patterns, and speeding up first drafts of UI and docs.
- **Failed or misaligned when:** Proposing **overbroad** UI (generic admin) or **overengineered** infra relative to a **5–6 hour** MVP scope; also **not** proactively layering in **logging and consistent API error handling** until the author **asked for that hardening explicitly** (it was not a default in early prompts).
- **Double-checked manually:** **Transaction ordering**, **row-level locking** paths, **atomic zone increments**, and **race behavior** against Postgres-backed tests—not AI prose alone.
- **Required human ownership:** **Architectural tradeoffs** (sync ingestion vs queues, MVs vs direct queries) and **explicit assumptions** (missions, idempotency, anomaly semantics).
- **Human-led product detail:** The **impossible position jump** rule was **proposed by the author**; AI helped encode and integrate it.

---

## Part 2 — Chronological narrative (extra context)

Stages below mirror the same work as the table, with slightly more narrative.

### 1. Requirements decomposition

**Prompt:** Break the challenge into domains, data model, API surface; identify concurrency and ordering risks.  
**Output:** High-level module split, endpoints, schema sketches.  
**Correction:** Mapped features to **explicit transactional boundaries**; trimmed scope not implied by the prompt.

### 2. Mission modeling assumptions

**Prompt:** Handle mission cancellation when telemetry lacks mission IDs.  
**Output:** Patterns (infer from DB vs separate API).  
**Correction:** **One active mission per vehicle**, **seeded** missions, **telemetry drives** vehicle state; no invented payload fields.

### 3. Concurrency strategy

**Prompt:** Keep zones and fault transitions correct under concurrent `/telemetry`.  
**Output:** Locking/isolation suggestions.  
**Correction:** **Postgres sole source of truth**, **no authoritative in-memory counters**, **atomic increments**, verify with **concurrency tests**.

### 4. Telemetry ingestion

**Prompt:** Implement ingestion with stale protection.  
**Output:** Service patterns, SQLAlchemy wiring.  
**Correction:** Enforced **`timestamp >= last_seen_at`** for snapshot updates; persist **all** events; documented **duplicate** behavior without `event_id`.

### 5. Anomaly detection heuristics

**Prompt:** Deterministic rules from telemetry fields.  
**Output:** Initial rules + wiring.  
**Correction:** Author proposed **`impossible_position_jump`** (successive positions/timestamps, haversine, implied speed cap); AI implemented once intent was clear.

### 6. Zone counting

**Prompt:** Safe increments under concurrency.  
**Output:** Atomic increment patterns.  
**Correction:** **Database-side** increments only; no authoritative process-local caches.

### 7. Fault transition handling

**Prompt:** Fault → cancel mission, maintenance record; stay consistent.  
**Output:** Transactional ordering sketches.  
**Correction:** Same **ingestion transaction**; no separate public status endpoint.

### 8. E2E / load-style smoke testing

**Prompt:** Multi-vehicle concurrent ingestion scenario.  
**Output:** Concurrent HTTP multi-tick harness.  
**Correction:** **Correctness** focus; **no** fabricated throughput claims.

### 9. Frontend architecture

**Prompt:** React + MUI; poll fleet/vehicles/zones/anomalies.  
**Output:** Components, client, hooks.  
**Correction:** **Local state + polling hook**, **no Redux**; **backoff** on failure; **last snapshot** retained.

### 10. Dashboard UI refinement

**Prompt:** Single-page operational dashboard.  
**Output:** Initial **enterprise-style** leanings.  
**Correction:** Removed **pagination/search/multi-page admin** drift; manual/layout tweaks toward **operational** monitoring.

### 11. Documentation generation

**Prompt:** README, ADR, AI log reflecting real tradeoffs.  
**Output:** Draft markdown.  
**Correction:** Removed invented tech and unfair scale claims; aligned with implementation.

### 12. Logging and API error-handling hardening

**Context:** Early prompts prioritized functional behavior (ingestion, concurrency, UI) rather than cross-cutting operational concerns.

**Author intervention:** The author **explicitly requested** later-step hardening: centralized Python logging, HTTP request logging (method/path/status/duration), concise domain logs (telemetry accepted, stale telemetry, zones, anomalies, fault transitions), **consistent `{ "error": { "code", "message" } }` responses** for domain and unexpected failures, safe **`rollback()`** on telemetry errors, and regression tests. This was **not** something the AI insisted on from the initial implementation phase without that prompt.

**Output:** Implemented lightweight logging middleware (avoiding Starlette `BaseHTTPMiddleware` pitfalls), `DomainError` vs generic `Exception` handler registration aligned with FastAPI/Starlette behavior, and documentation updates in the README.

---

## Closing note

AI assistance was used **deliberately** and **supervised**. This log is intended to show **direction, correction, and validation**—not unattended generation.
