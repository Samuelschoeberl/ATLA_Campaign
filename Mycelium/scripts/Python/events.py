"""In-process pub/sub used to push "a file changed" notifications to clients.

This module has no Flask dependency so it can be imported from anywhere that
performs a write (route handlers, ``watch_and_regen.py``, the folded-in
``sync_variables_direct_edit`` background thread) without pulling the web
framework into scripts that don't otherwise need it. The actual `/api/events`
SSE route lives in ``routes_events.py`` and just calls into ``sse_stream()``
below.

Scale note: this app runs on a LAN for a handful of players (roughly 3-10),
not at web scale — a simple list of queues guarded by one lock is plenty; no
external broker is warranted.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Optional

# Cap concurrent SSE subscribers so a runaway number of open tabs/log-viewers
# can't exhaust the server's thread pool (each open stream pins one worker
# thread for its lifetime). Generous headroom over the expected 3-10 players.
MAX_SUBSCRIBERS = 25

# Cap how many pending events we'll buffer for one slow subscriber before we
# start dropping the oldest ones, so a stalled client can't grow memory
# unboundedly.
MAX_QUEUE_SIZE = 200

# How long a subscriber's `get()` blocks before we send a keep-alive comment.
# Well under typical proxy/browser idle-connection timeouts.
KEEPALIVE_SECONDS = 15

import queue

_subscribers: "list[queue.Queue]" = []
_lock = threading.Lock()


class TooManySubscribers(Exception):
    """Raised by subscribe() when the concurrent-connection cap is reached."""


def subscribe() -> queue.Queue:
    """Register a new subscriber queue. Raises TooManySubscribers past the cap."""
    with _lock:
        if len(_subscribers) >= MAX_SUBSCRIBERS:
            raise TooManySubscribers(f"{MAX_SUBSCRIBERS} concurrent /api/events connections already open")
        q: "queue.Queue" = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        _subscribers.append(q)
        return q


def unsubscribe(q: "queue.Queue") -> None:
    """Remove a subscriber queue (call from a stream's cleanup/finally)."""
    with _lock:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def subscriber_count() -> int:
    """Return the current number of connected SSE subscribers."""
    with _lock:
        return len(_subscribers)


def publish(event_type: str, **fields) -> None:
    """Broadcast an event to every connected subscriber.

    Example: publish("file_changed", path="Player Root/PCs/Anju/...", version="a1b2c3")
    """
    payload = dict(fields)
    payload["type"] = event_type
    payload.setdefault("ts", time.time())
    data = json.dumps(payload)
    with _lock:
        subs = list(_subscribers)
    for q in subs:
        try:
            q.put_nowait((event_type, data))
        except queue.Full:
            # Drop the oldest pending event for this slow subscriber, then retry once.
            try:
                q.get_nowait()
                q.put_nowait((event_type, data))
            except Exception:
                pass


def sse_stream(subscriber_queue: "queue.Queue"):
    """Generator yielding SSE-formatted text for a single subscriber's connection.

    Sends a `: keep-alive` comment line on idle timeouts instead of the
    time.sleep()-based busy-poll pattern this app used to have (see
    /api/tail-wikigraphs before this rework) — no wasted CPU, no thread-pinning
    surprises beyond the one thread the open connection itself already holds.
    """
    try:
        while True:
            try:
                event_type, data = subscriber_queue.get(timeout=KEEPALIVE_SECONDS)
                yield f"event: {event_type}\ndata: {data}\n\n"
            except queue.Empty:
                yield ": keep-alive\n\n"
    except GeneratorExit:
        return


def publish_log_line(line: str, severity: str = "info") -> None:
    """Convenience wrapper for the Wikigraphs log tail, replacing the old
    time.sleep(0.2) file-polling implementation of /api/tail-wikigraphs."""
    publish("wikigraphs_log", line=line, severity=severity)
