from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.devflow import router as devflow_router
from app.core.config import get_settings
from app.db.connection import initialize_database
from app.db.store import StateStore
from app.services.devflow import DevFlowService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    initialize_database(settings.database_path)
    app.state.devflow = DevFlowService(StateStore(settings.database_path))
    yield


settings = get_settings()
app = FastAPI(
    title="DevFlow Assistant Engine",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(devflow_router)
