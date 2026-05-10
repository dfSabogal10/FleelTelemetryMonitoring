from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import AsyncSessionLocal, init_db
from app.error_handlers import domain_error_handler, internal_server_error_handler
from app.exceptions import DomainError
from app.logging_conf import configure_logging
from app.middleware.request_logging import register_request_logging
from app.routers.anomalies import router as anomalies_router
from app.routers.fleet import router as fleet_router
from app.routers.health import router as health_router
from app.routers.telemetry import router as telemetry_router
from app.routers.zones import router as zones_router
from app.services.seed import seed_database

configure_logging()


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

app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(Exception, internal_server_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_request_logging(app)

app.include_router(health_router)
app.include_router(telemetry_router)
app.include_router(zones_router)
app.include_router(anomalies_router)
app.include_router(fleet_router)
