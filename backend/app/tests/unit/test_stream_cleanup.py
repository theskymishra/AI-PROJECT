"""SSE subscriber cleanup.

WHY THIS FILE EXISTS
--------------------
A verification run reported `subscribers=1` after disconnect and looked like a
leak. It was not: the assertion compared against ZERO, which is a property of
the whole server rather than of the connection under test. One other
legitimate client -- the app open in a browser tab, the normal state while
developing -- makes a correct server report 1.

Two lessons are encoded here:

  1. Cleanup is asserted as a DELTA against a baseline, never against zero.
     A test that only passes when nothing else is connected is measuring the
     wrong thing, and it fails loudly for a server that is behaving perfectly.

  2. The cleanup path itself -- the `finally` in `_event_source` -- is
     exercised directly. The endpoint cannot be driven through TestClient (an
     infinite generator deadlocks it), but the generator is an ordinary async
     generator and can be driven and closed here, which is exactly what
     Starlette does when a client goes away.
"""

import asyncio

import pytest

from app.api.stream import _event_source
from app.services.broadcast import Broadcaster
from app.simulation.engine import engine


class FakeRequest:
    """Minimal stand-in for starlette.Request.

    Only `is_disconnected` is consulted by the event source. Making it
    controllable is what lets the disconnect path be tested without a socket.
    """

    def __init__(self, disconnected: bool = False) -> None:
        self._disconnected = disconnected

    def disconnect(self) -> None:
        self._disconnected = True

    async def is_disconnected(self) -> bool:
        return self._disconnected


@pytest.fixture
def broadcaster_baseline():
    """Subscriber count before the test, so assertions are deltas."""
    return engine.broadcaster.subscriber_count

@pytest.mark.asyncio
class TestEventSourceCleanup:
    async def test_opening_the_stream_registers_exactly_one_subscriber(
        self, broadcaster_baseline
    ):
        request = FakeRequest()
        source = _event_source(request)
        try:
            await source.__anext__()  # opening snapshot
            assert engine.broadcaster.subscriber_count == broadcaster_baseline + 1
        finally:
            await source.aclose()

    async def test_closing_the_generator_releases_the_subscriber(
        self, broadcaster_baseline
    ):
        """The exact path Starlette takes when a client disconnects."""
        request = FakeRequest()
        source = _event_source(request)
        await source.__anext__()
        assert engine.broadcaster.subscriber_count == broadcaster_baseline + 1

        await source.aclose()

        assert engine.broadcaster.subscriber_count == broadcaster_baseline, (
            "the finally block in _event_source did not unsubscribe"
        )

    async def test_client_disconnect_ends_the_stream_and_releases_the_slot(
        self, broadcaster_baseline
    ):
        """is_disconnected() going true must end the loop, not just be polled."""
        request = FakeRequest()
        source = _event_source(request)
        await source.__anext__()

        request.disconnect()

        with pytest.raises(StopAsyncIteration):
            # The next pull observes the disconnect, breaks, runs finally.
            await asyncio.wait_for(source.__anext__(), timeout=5.0)

        assert engine.broadcaster.subscriber_count == broadcaster_baseline

    async def test_cleanup_runs_even_if_the_generator_is_abandoned_mid_stream(
        self, broadcaster_baseline
    ):
        """A client that vanishes between frames must not strand a slot."""
        request = FakeRequest()
        source = _event_source(request)
        await source.__anext__()

        engine.broadcaster.publish(seq=1, tick=1, type="tick", payload={})
        await source.__anext__()  # consume the published frame

        await source.aclose()
        assert engine.broadcaster.subscriber_count == broadcaster_baseline

    async def test_many_connect_disconnect_cycles_leak_nothing(
        self, broadcaster_baseline
    ):
        """A leak of one per connection would be invisible in a single cycle."""
        for _ in range(25):
            request = FakeRequest()
            source = _event_source(request)
            await source.__anext__()
            await source.aclose()

        assert engine.broadcaster.subscriber_count == broadcaster_baseline

    async def test_concurrent_clients_are_counted_and_released_independently(
        self, broadcaster_baseline
    ):
        """The multi-tab case that produced the false failure."""
        sources = [_event_source(FakeRequest()) for _ in range(3)]
        for source in sources:
            await source.__anext__()
        assert engine.broadcaster.subscriber_count == broadcaster_baseline + 3

        # Closing one must release exactly one, not all and not none.
        await sources[0].aclose()
        assert engine.broadcaster.subscriber_count == broadcaster_baseline + 2

        for source in sources[1:]:
            await source.aclose()
        assert engine.broadcaster.subscriber_count == broadcaster_baseline

    async def test_a_second_client_does_not_disturb_the_first(
        self, broadcaster_baseline
    ):
        """Why the verification check must be a delta.

        With one client already connected, a correct server reports 1 -- not 0
        -- after a second client disconnects. Asserting zero here would fail
        against perfectly correct behaviour.
        """
        long_lived = _event_source(FakeRequest())
        await long_lived.__anext__()
        with_tab = engine.broadcaster.subscriber_count
        assert with_tab == broadcaster_baseline + 1

        transient = _event_source(FakeRequest())
        await transient.__anext__()
        assert engine.broadcaster.subscriber_count == with_tab + 1
        await transient.aclose()

        assert engine.broadcaster.subscriber_count == with_tab, (
            "the long-lived client must survive the transient one disconnecting"
        )
        assert engine.broadcaster.subscriber_count != 0, (
            "a global 'subscribers == 0' assertion would wrongly fail here"
        )

        await long_lived.aclose()
        assert engine.broadcaster.subscriber_count == broadcaster_baseline

@pytest.mark.asyncio
class TestBroadcasterSymmetry:
    """Cleanup guarantees at the broadcaster level, independent of HTTP."""

    async def test_unsubscribe_is_idempotent(self):
        broadcaster = Broadcaster()
        queue = broadcaster.subscribe()
        broadcaster.unsubscribe(queue)
        broadcaster.unsubscribe(queue)
        assert broadcaster.subscriber_count == 0

    async def test_an_unsubscribed_queue_stops_receiving(self):
        broadcaster = Broadcaster()
        queue = broadcaster.subscribe()
        broadcaster.unsubscribe(queue)
        broadcaster.publish(seq=1, tick=1, type="tick", payload={})
        assert queue.empty()

    async def test_publishing_to_a_released_slot_does_not_resurrect_it(self):
        broadcaster = Broadcaster()
        queue = broadcaster.subscribe()
        broadcaster.unsubscribe(queue)
        for seq in range(10):
            broadcaster.publish(seq=seq, tick=seq, type="tick", payload={})
        assert broadcaster.subscriber_count == 0
