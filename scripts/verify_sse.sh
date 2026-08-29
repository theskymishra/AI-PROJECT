#!/usr/bin/env bash
# Verify the live SSE endpoint against a real uvicorn process.
#
# The endpoint cannot be tested through Starlette's TestClient -- an infinite
# generator deadlocks it (see tests/integration/test_simulation_api.py). This
# drives it the way a browser does: a real HTTP client holding a real
# connection open.
#
# SUBSCRIBER CLEANUP IS MEASURED AS A DELTA, NOT AGAINST ZERO.
#
# An earlier version asserted `subscribers == 0`, which is a property of the
# whole server rather than of the connection under test. Any other legitimate
# client -- most obviously this app open in a browser tab, which is the normal
# state while developing -- makes a CORRECT server report 1, and the check
# failed for a server behaving perfectly. Opening a stream, confirming the
# count rises, closing it and confirming it returns to where it started proves
# the thing that actually matters, and is true no matter who else is connected.
#
# Usage:  ./scripts/verify_sse.sh          (backend must be running on :8000)
set -u
BASE="${1:-http://127.0.0.1:8000}"
fail=0
check() { if [ "$2" = "1" ]; then echo "  PASS  $1"; else echo "  FAIL  $1"; fail=1; fi; }

subscribers() {
  curl -s "$BASE/api/simulation/stream-health" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['subscribers'])" 2>/dev/null \
    || echo "-1"
}

echo "Verifying SSE at $BASE/api/stream"

HDRS=$(curl -s -N -m 3 -D - -o /dev/null "$BASE/api/stream" 2>/dev/null || true)
echo "$HDRS" | grep -qi "content-type: text/event-stream" \
  && check "content-type is text/event-stream" 1 || check "content-type is text/event-stream" 0
echo "$HDRS" | grep -qi "cache-control: no-cache" \
  && check "cache-control: no-cache" 1 || check "cache-control: no-cache" 0

BODY=$(curl -s -N -m 3 "$BASE/api/stream" 2>/dev/null || true)
echo "$BODY" | head -1 | grep -q "^event: snapshot$" \
  && check "first frame is 'event: snapshot'" 1 || check "first frame is 'event: snapshot'" 0
echo "$BODY" | sed -n '2p' | grep -q "^data: {" \
  && check "second line is a data payload" 1 || check "second line is a data payload" 0
echo "$BODY" | sed -n '2p' | sed 's/^data: //' | python3 -c "
import json,sys
e=json.load(sys.stdin)
assert e['type']=='snapshot', e['type']
assert e['payload']['stats']['total_roads']==38
assert len(e['payload']['nodes'])==24
print('    snapshot: %d nodes, %d roads, scenario %s'%(len(e['payload']['nodes']),e['payload']['stats']['total_roads'],e['payload']['scenario']['name']))
" 2>/dev/null && check "snapshot payload is complete (24 nodes, 38 roads)" 1 \
  || check "snapshot payload is complete (24 nodes, 38 roads)" 0

curl -s -X POST "$BASE/api/simulation/reset" -o /dev/null
curl -s -X POST "$BASE/api/simulation/start" -o /dev/null
LIVE=$(curl -s -N -m 4 "$BASE/api/stream" 2>/dev/null || true)
echo "$LIVE" | grep -q "^event: tick$" \
  && check "live tick frames are pushed while running" 1 \
  || check "live tick frames are pushed while running" 0
curl -s -X POST "$BASE/api/simulation/pause" -o /dev/null

# --- subscriber cleanup, measured as a delta -------------------------------

# Let connections from the checks above finish closing before sampling.
sleep 1
BASELINE=$(subscribers)
if [ "$BASELINE" != "0" ]; then
  echo "    note: $BASELINE other client(s) already connected (a browser tab on"
  echo "          the app?). Cleanup is measured as a delta, not against zero."
fi

# Open a stream and hold it. curl is backgrounded so the connection stays up
# while the count is sampled.
curl -s -N "$BASE/api/stream" > /dev/null 2>&1 &
PROBE=$!
sleep 1
DURING=$(subscribers)
[ "$DURING" = "$((BASELINE + 1))" ] \
  && check "opening a stream registers a subscriber ($BASELINE -> $DURING)" 1 \
  || check "opening a stream registers a subscriber (expected $((BASELINE + 1)), got $DURING)" 0

kill "$PROBE" 2>/dev/null || true
wait "$PROBE" 2>/dev/null || true

# Cleanup crosses a socket, so it is not instantaneous. Measured at 3-9 ms
# locally; the bound is generous so a loaded machine does not flake.
RELEASED=0
for _ in $(seq 1 40); do
  NOW=$(subscribers)
  if [ "$NOW" -le "$BASELINE" ] 2>/dev/null; then RELEASED=1; break; fi
  sleep 0.05
done
[ "$RELEASED" = "1" ] \
  && check "the subscriber this script opened was released (back to $BASELINE)" 1 \
  || check "the subscriber this script opened was released (still $(subscribers) after 2s)" 0

FINAL=$(subscribers)
[ "$FINAL" = "$BASELINE" ] \
  && check "no subscribers leaked across the whole run" 1 \
  || check "no subscribers leaked across the whole run (baseline $BASELINE, now $FINAL)" 0

echo ""
[ "$fail" = "0" ] && echo "SSE verification PASSED" || echo "SSE verification FAILED"
exit $fail
