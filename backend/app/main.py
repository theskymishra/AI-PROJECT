"""AI-DERS backend application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000

IMPORTANT: this application must run with a SINGLE worker process. From Phase 2
onward the entire simulation lives in memory in one process; multiple workers
would produce multiple divergent simulations with clients randomly attached to
each. The lifespan handler below warns loudly if it detects otherwise.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    ai,
    disaster,
    emergencies,
    health,
    resources,
    simulation,
    stream,
)
from app.config import settings
from app.simulation.engine import run_engine_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aiders")


def _warn_if_multi_worker() -> None:
    """Detect the multi-worker misconfiguration described in Phase 0 section 9."""
    raw = os.getenv("WEB_CONCURRENCY", "")
    if raw.isdigit() and int(raw) > 1:
        logger.warning(
            "WEB_CONCURRENCY=%s. AI-DERS holds all simulation state in memory in a "
            "single process. Running multiple workers will produce divergent "
            "simulations. Run with exactly one worker.",
            raw,
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _warn_if_multi_worker()
    logger.info(
        "%s v%s starting | phase %d/%d | seed %d",
        settings.app_name,
        settings.version,
        settings.phase,
        settings.total_phases,
        settings.seed,
    )
    logger.info("CORS origins allowed: %s", ", ".join(settings.cors_origins))

    # The simulation clock. One task, one process, one world.
    loop_task = asyncio.create_task(run_engine_loop(), name="aiders-engine")
    try:
        yield
    finally:
        loop_task.cancel()
        with suppress(asyncio.CancelledError):
            await loop_task
        logger.info("%s shutting down", settings.app_name)


def create_app() -> FastAPI:
    """Build the FastAPI application.

    A factory rather than a module-level constant so tests can build isolated
    instances, and so a future Phase can pass in an alternative configuration
    without monkeypatching imports.
    """
    app = FastAPI(
        title=settings.app_full_name,
        summary=settings.app_tagline,
        description=(
            "Academic AI simulation. This system is NOT an operational "
            "emergency-management tool and its output must not be used to make "
            "real emergency decisions."
        ),
        version=settings.version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(ai.router, prefix=settings.api_prefix)
    app.include_router(simulation.router, prefix=settings.api_prefix)
    app.include_router(disaster.router, prefix=settings.api_prefix)
    app.include_router(emergencies.router, prefix=settings.api_prefix)
    app.include_router(resources.router, prefix=settings.api_prefix)
    app.include_router(stream.router, prefix=settings.api_prefix)

    return app


app = create_app()
