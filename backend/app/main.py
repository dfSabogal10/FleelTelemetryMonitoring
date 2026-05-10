from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import AsyncSessionLocal, init_db
from app.routers.health import router as health_router
from app.routers.telemetry import router as telemetry_router
from app.services.seed import seed_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_database(session)
        await session.commit()
    yield


app = FastAPI(
    title="Fleet Telemetry Monitoring API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(telemetry_router)
