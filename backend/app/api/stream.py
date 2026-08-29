"""Server-Sent Events endpoint.

The client opens this once, for the lifetime of the page. Nothing in the
frontend polls simulation state.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.broadcast import format_comment
from app.simulation.engine import engine

router = APIRouter(tags=["stream"])

#: Comment frame sent when idle, so proxies and load balancers do not time the
#: connection out during a paused simulation.
KEEPALIVE_SECONDS = 15.0

#: How often the generator wakes to re-check whether the client has gone away.
#:
#: Previously the generator blocked for a full KEEPALIVE_SECONDS on the queue,
#: so a disconnect took up to 15 seconds to notice and the subscriber queue
#: stayed registered that whole time. Polling on a short interval detects a
#: closed tab in about a second and releases the subscriber slot immediately.
DISCONNECT_POLL_SECONDS = 0.5


async def _event_source(request: Request) -> AsyncIterator[str]:
    queue = engine.broadcaster.subscribe()
    try:
        # Full state first, so the client never renders from a partial delta.
        yield (
            "event: snapshot\n"
            f"data: {json.dumps({'seq': engine.state.seq, 'tick': engine.state.clock.tick, 'type': 'snapshot', 'payload': engine.snapshot()}, separators=(',', ':'))}\n\n"
        )
        idle_seconds = 0.0
        while True:
            if await request.is_disconnected():
                break
            try:
                frame = await asyncio.wait_for(
                    queue.get(), timeout=DISCONNECT_POLL_SECONDS
                )
            except TimeoutError:
                idle_seconds += DISCONNECT_POLL_SECONDS
                if idle_seconds >= KEEPALIVE_SECONDS:
                    idle_seconds = 0.0
                    yield format_comment("keepalive")
                continue
            idle_seconds = 0.0
            yield frame
    finally:
        engine.broadcaster.unsubscribe(queue)


@router.get("/stream", summary="Live simulation event stream (SSE)")
async def stream(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _event_source(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Disables proxy buffering, which otherwise holds frames back
            # until a buffer fills and makes the console look frozen.
            "X-Accel-Buffering": "no",
        },
    )
