# AI Interaction Log

This log documents how **AI assistance** was used during the Fleet Telemetry Monitoring take-home, where it **accelerated** delivery, and where **human review, correction, and architectural judgment** were required. The challenge values **systematic reasoning** and honest assessment of tools alongside code.

---

## How AI was used (overview)

- **Scaffolding**: project layout, Docker Compose wiring, FastAPI router stubs, SQLAlchemy models, React component structure, and repetitive test boilerplate.
- **Iteration**: refactors after feedback (e.g. polling backoff, UI scope narrowing).
- **Documentation**: drafting README/ADR-style material from agreed decisions **after** those decisions were established in implementation and review.

AI did **not** replace validation of **concurrency**, **transaction boundaries**, or **end-to-end behavior** — those were checked against Postgres-backed tests and manual reasoning.

---

## Chronological stages

### 1. Requirements decomposition

**Prompts (representative)**  
Break the challenge into backend domains (ingestion, zones, anomalies, fleet reads), data model, and API surface; identify risks (concurrency, ordering).

**AI output**  
High-level module split, suggested endpoints, and initial schema sketches.

**Corrections / human judgment**  
Mapped requirements to **explicit transactional boundaries** (what must happen atomically with telemetry vs. what can be read-only). Trimmed speculative features not implied by the prompt.

---

### 2. Mission modeling assumptions

**Prompts**  
Handle mission cancellation on fault when telemetry does **not** include mission identifiers.

**AI output**  
Possible patterns (infer missions from DB, separate mission API, etc.).

**Corrections**  
Adopted **documented assumptions**: **at most one active mission per vehicle**, missions **seeded** at startup, **telemetry drives** operational vehicle state. Avoided inventing mission fields in payloads.

---

### 3. Concurrency strategy

**Prompts**  
Ensure zone increments and fault transitions stay correct under concurrent `/telemetry` calls.

**AI output**  
Suggestions around locking, isolation, and patterns (e.g. `SELECT … FOR UPDATE` usage concepts).

**Corrections**  
Standardized on **Postgres as sole source of truth**, **no in-memory authoritative counters**, **atomic increments**, **short transactions**, and **row-level locking** only where needed. **Race-prone paths** were verified by reading code paths and **concurrency-focused tests**, not by trusting prose alone.

---

### 4. Telemetry ingestion

**Prompts**  
Implement `POST /telemetry`, persist events, update vehicle snapshot with **stale telemetry protection**.

**AI output**  
Service-layer structure, SQLAlchemy patterns, exception mapping.

**Corrections**  
Enforced **monotonic update rule** for vehicle “current” state (`incoming timestamp >= last_seen_at`). Confirmed **all events remain persisted** even when state does not move forward. Discussed **duplicate / idempotency** explicitly (see README): **no fake uniqueness** without `event_id`.

---

### 5. Anomaly detection heuristics

**Prompts**  
Define deterministic anomaly rules from telemetry (battery, speed, faults, error codes, etc.).

**AI output**  
Initial rule suggestions and wiring into ingestion.

**Human feedback (author)**  
The author **provided explicit feedback** during design: among other refinements, the **`impossible position jump`** rule (**compare successive positions and timestamps; flag implied speed above a fixed m/s cap using haversine distance**) was **proposed by the human**, not originated by the AI — the AI helped implement and phrase it once the intent was clear.

---

### 6. Zone counting

**Prompts**  
Increment per-zone entry counts safely under concurrency.

**AI output**  
Atomic increment idioms, potential race explanations.

**Corrections**  
Chose **database-side atomic increments** on persisted rows; rejected process-local caches as authoritative.

---

### 7. Fault transition transaction handling

**Prompts**  
On transition to fault: cancel active mission, create maintenance record; keep consistency with telemetry.

**AI output**  
Transactional ordering sketches and helper modules.

**Corrections**  
Placed fault side effects **inside the same ingestion transaction** as vehicle updates where appropriate; avoided a **separate public status endpoint** to prevent dual writes. Validated behavior with tests that stress **overlapping** ingestion.

---

### 8. E2E / load-style smoke testing

**Prompts**  
Add a concurrent ingestion scenario across many vehicles.

**AI output**  
A multi-vehicle, multi-tick test harness using concurrent HTTP calls.

**Corrections**  
Framed the test as **correctness under concurrency**, **not** a benchmark — **no fabricated throughput claims**. Assertions focus on **invariants** (counts, records, side effects) after concurrent ticks.

---

### 9. Frontend architecture

**Prompts**  
React + TypeScript + Material UI; fetch fleet, vehicles, zones, anomalies; poll for updates.

**AI output**  
Component breakdown, API client, hooks, layout ideas.

**Corrections**  
Chose **lightweight local state** and a **polling hook** — **no Redux** or global store libraries. Added **polling backoff** on API failure (2s → 4s → 8s cap) so a failing backend is not hammered every second; **preserve last good data** and show a **warning** banner instead of wiping the dashboard.

---

### 10. Dashboard UI refinement

**Prompts**  
Single-page operational dashboard: fleet summary cards, vehicle table, zone counts, recent anomalies.

**AI output**  
Initial layouts tended toward a **generic enterprise admin** pattern.

**Corrections**  
**Important:** During frontend generation, the **initial AI-generated UI diverged** from the intended **operational monitoring** layout and introduced **unnecessary enterprise-dashboard patterns** (e.g. **pagination**, **search**, **multi-page / admin-oriented structure**). The implementation was **iteratively corrected** through **additional prompts** and **manual adjustments** to align with a **single-page operational dashboard**: fleet state cards, vehicle table, zone entry counts, recent anomalies — **without** excess admin chrome.

---

### 11. Documentation generation

**Prompts**  
Produce README, ADRs, and this log reflecting **real** tradeoffs (queues, MVs, idempotency, polling).

**AI output**  
Draft markdown aligned to implementation and prior decisions.

**Corrections**  
Removed **invented** tech and **unfair** scale claims; ensured **honest** MVP boundaries and **explicitly deferred** production items.

---

## Reflection

- AI was **effective** for **scaffolding**, **boilerplate**, and **speeding up test and API wiring** once directions were clear.
- **Human feedback** shaped product behavior in concrete ways — for example the **impossible position jump** anomaly rule was **authored as a human proposal**, with AI assisting implementation after the idea was set.
- AI sometimes proposed **overengineered** UI or infrastructure **misaligned with challenge scope**; **active constraint** (especially on the frontend) saved time and complexity.
- **Architectural tradeoffs** (sync ingestion vs. queues, Postgres vs. SQLite, MVs vs. direct queries) required **manual reasoning**; AI suggestions were **inputs**, not verdicts.
- **Transactional correctness** and **concurrency** concerns were validated by **code review** and **tests**, not by assuming AI-generated locking prose was sufficient.
- **UI generation** initially **drifted** toward generic enterprise patterns; **supervision and iteration** were necessary to match the **intended operational dashboard**.

---

## Closing note

AI assistance was **encouraged** for this challenge and used **deliberately**. The submitted **ADR**, **README**, and this **log** are meant to show **how** that assistance was **directed**, **corrected**, and **grounded** in real engineering constraints — not to imply unsupervised autopilot delivery.
