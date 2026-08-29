"""Broadcaster fan-out, backpressure and cleanup.

Tested in process rather than over HTTP. The SSE endpoint is an infinite
generator and Starlette's TestClient deadlocks unwinding one (see the note in
tests/integration/test_simulation_api.py); the live endpoint is covered by
scripts/verify_sse.sh instead. Everything that can actually go wrong in the
fan-out is logic, and logic is testable here.
"""

import asyncio
import json

import pytest

from app.services.broadcast import QUEUE_MAXSIZE, Broadcaster, format_comment


@pytest.fixture
def broadcaster():
    return Broadcaster()


def test_starts_with_no_subscribers(broadcaster):
    assert broadcaster.subscriber_count == 0
    assert broadcaster.dropped_frames == 0


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe_are_symmetric(broadcaster):
    queue = broadcaster.subscribe()
    assert broadcaster.subscriber_count == 1
    broadcaster.unsubscribe(queue)
    assert broadcaster.subscriber_count == 0


@pytest.mark.asyncio
async def test_unsubscribing_twice_is_harmless(broadcaster):
    queue = broadcaster.subscribe()
    broadcaster.unsubscribe(queue)
    broadcaster.unsubscribe(queue)
    assert broadcaster.subscriber_count == 0


@pytest.mark.asyncio
async def test_publish_reaches_every_subscriber(broadcaster):
    a = broadcaster.subscribe()
    b = broadcaster.subscribe()

    broadcaster.publish(seq=7, tick=42, type="tick", payload={"x": 1})

    for queue in (a, b):
        frame = queue.get_nowait()
        assert frame.startswith("event: tick\n")
        envelope = json.loads(frame.split("data: ", 1)[1].strip())
        assert envelope == {"seq": 7, "tick": 42, "type": "tick", "payload": {"x": 1}}


@pytest.mark.asyncio
async def test_publish_with_no_subscribers_is_a_noop(broadcaster):
    broadcaster.publish(seq=1, tick=1, type="tick", payload={})
    assert broadcaster.dropped_frames == 0


@pytest.mark.asyncio
async def test_unsubscribed_client_stops_receiving(broadcaster):
    queue = broadcaster.subscribe()
    broadcaster.unsubscribe(queue)
    broadcaster.publish(seq=1, tick=1, type="tick", payload={})
    assert queue.empty()


@pytest.mark.asyncio
async def test_slow_client_drops_oldest_rather_than_growing_without_bound(broadcaster):
    """A client that stops reading must not be able to exhaust memory."""
    queue = broadcaster.subscribe()

    overflow = QUEUE_MAXSIZE + 25
    for seq in range(overflow):
        broadcaster.publish(seq=seq, tick=seq, type="tick", payload={})

    assert queue.qsize() <= QUEUE_MAXSIZE
    assert broadcaster.dropped_frames > 0

    # The frames retained are the NEWEST ones: a reconnecting client should see
    # current state, not a backlog from a minute ago.
    newest = None
    while not queue.empty():
        newest = json.loads(queue.get_nowait().split("data: ", 1)[1].strip())
    assert newest is not None
    assert newest["seq"] == overflow - 1


@pytest.mark.asyncio
async def test_one_stalled_client_does_not_block_a_healthy_one(broadcaster):
    stalled = broadcaster.subscribe()
    healthy = broadcaster.subscribe()

    for seq in range(QUEUE_MAXSIZE + 10):
        broadcaster.publish(seq=seq, tick=seq, type="tick", payload={})
        # The healthy client keeps up.
        healthy.get_nowait()

    assert healthy.empty()
    assert stalled.qsize() <= QUEUE_MAXSIZE


@pytest.mark.asyncio
async def test_publish_never_awaits(broadcaster):
    """The tick loop calls publish synchronously; it must not yield control."""
    broadcaster.subscribe()

    async def _publish_and_flag():
        broadcaster.publish(seq=1, tick=1, type="tick", payload={})
        return "done"

    # If publish awaited anything, this would need more than one loop step.
    task = asyncio.ensure_future(_publish_and_flag())
    await asyncio.sleep(0)
    assert task.done()
    assert await task == "done"


def test_sse_frame_format_is_wire_correct(broadcaster):
    queue = broadcaster.subscribe()
    broadcaster.publish(seq=1, tick=2, type="road_status", payload={"road_id": "R17"})
    frame = queue.get_nowait()

    # Event name line, data line, blank line terminator.
    assert frame.endswith("\n\n")
    lines = frame.split("\n")
    assert lines[0] == "event: road_status"
    assert lines[1].startswith("data: ")
    assert "\n" not in lines[1].removeprefix("data: ")


def test_comment_frame_is_a_valid_keepalive():
    assert format_comment("keepalive") == ": keepalive\n\n"
