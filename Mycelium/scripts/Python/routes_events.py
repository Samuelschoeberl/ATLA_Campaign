"""SSE routes: the shared `/api/events` push stream, plus the Wikigraphs log
tail rewritten onto the same subscribe/generator pattern instead of its old
time.sleep(0.2) busy-poll (see `events.py`)."""
from __future__ import annotations

from flask import Response, request

import events
from frontend_api import bp
from sheet_helpers import WIKIGRAPHS_LOG


@bp.route('/api/events')
def sse_events():
    """Shared SSE stream. Clients get a `file_changed` event whenever any
    write happens elsewhere in the app, instead of each component polling
    the same files on its own timer."""
    try:
        q = events.subscribe()
    except events.TooManySubscribers as e:
        return {'error': str(e)}, 503

    def generate():
        try:
            for chunk in events.sse_stream(q):
                yield chunk
        finally:
            events.unsubscribe(q)

    resp = Response(generate(), mimetype='text/event-stream')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['X-Accel-Buffering'] = 'no'  # in case this ever sits behind nginx
    return resp


@bp.route('/api/tail-wikigraphs')
def tail_wikigraphs():
    """Stream the latest Wikigraphs log as Server-Sent Events.

    Previously a bespoke generator that re-opened the log file and polled it
    with time.sleep(0.2) forever, pinning one worker thread per open tab with
    active CPU spin. Now just another subscriber on the shared pub/sub,
    filtered to 'wikigraphs_log' events (see resource_cache/routes_generation,
    which call events.publish_log_line() as lines are produced).
    """
    try:
        q = events.subscribe()
    except events.TooManySubscribers as e:
        return {'error': str(e)}, 503

    def generate():
        try:
            for event_type, data in _iter_wikigraphs_events(q):
                yield f'data: {data}\n\n'
        finally:
            events.unsubscribe(q)

    def _iter_wikigraphs_events(q):
        import json as _json
        while True:
            try:
                event_type, data = q.get(timeout=15)
            except Exception:
                yield ('keepalive', _json.dumps({'type': 'keepalive'}))
                continue
            if event_type == 'wikigraphs_log':
                yield (event_type, data)

    return Response(generate(), mimetype='text/event-stream')
