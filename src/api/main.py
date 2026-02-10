"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import admin, health, webhooks

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("orchestrator_starting")
    yield
    logger.info("orchestrator_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Aetos Orchestrator",
        description="Lifecycle orchestrator for camera buy/resell operations.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(webhooks.router)
    app.include_router(admin.router)

    return app


app = create_app()
