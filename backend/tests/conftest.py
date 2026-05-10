"""
Test database strategy
----------------------
Integration-style tests import the FastAPI app, which runs startup (DDL + seed)
against whatever database `DATABASE_URL` selects.

Pytest forces `DATABASE_URL` to a dedicated Postgres database (`fleet_test` by
default) so tests never touch the normal development database (`fleet`).

Prerequisites: Postgres reachable at the URL below; create `fleet_test` once if
needed (Docker Compose mounts `docker/postgres/init-test-db.sql` on first volume
init). Override credentials or host with `TEST_DATABASE_URL`.

E2E smoke: ``tests/e2e/test_fleet_ingestion_smoke.py`` simulates 50 vehicles at 1 Hz for 3
logical seconds (concurrent POST /telemetry per tick). It checks correctness under concurrent
ingestion, not throughput; run with the same ``pytest`` command as other tests.
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://localuser-fleet:localpass-fleet@127.0.0.1:5432/fleet_test",
)

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import AsyncSessionLocal, init_db
from app.main import app
from app.services.seed import seed_database


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database() -> None:
    """Mirror application startup (DDL + idempotent seed) for the isolated test DB.

    httpx ``ASGITransport`` does not run ASGI lifespan events, so tests must set
    up the schema explicitly if they rely on Postgres.
    """
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_database(session)
        await session.commit()


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
