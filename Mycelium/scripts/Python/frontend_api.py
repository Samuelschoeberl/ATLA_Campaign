"""Flask blueprint exposing helper endpoints for the React frontend.

This used to be one 3000-line file holding every route. It's now just the
Blueprint definition plus the imports that register each domain's routes
onto it — see `routes_files.py` (generic vault file/dir I/O),
`routes_sheets.py` (character sheets, customization, stat overview,
environmental variables), `routes_generation.py` (Wikigraphs, move
analysis), `routes_initiative.py` / `routes_battlemap.py` (the hot-spot
PATCH endpoints backed by `db.py`), and `routes_events.py` (the SSE stream).
Shared helpers live in `sheet_helpers.py`; the versioned file cache/locking
lives in `resource_cache.py`; the in-process pub/sub lives in `events.py`.
"""
from flask import Blueprint

bp = Blueprint("frontend_api", __name__)

# Re-exported for backward compatibility: full_analysis_tuner.py imports
# `get_player_root_base` and `parse_move_content` directly from this module.
from sheet_helpers import REPO_ROOT, PLAYER_ROOT_PREFIX, get_player_root_base  # noqa: E402,F401

# Import route modules for their registration side effect (each does
# `from frontend_api import bp` and adds `@bp.route(...)` handlers). Order
# doesn't matter functionally, but routes_files.py registers a catch-all
# `/<path:seg>` route, so it's imported last to avoid shadowing more
# specific routes registered by the others.
import routes_events  # noqa: E402,F401
import routes_sheets  # noqa: E402,F401
import routes_initiative  # noqa: E402,F401
import routes_battlemap  # noqa: E402,F401
import routes_generation  # noqa: E402,F401
import routes_files  # noqa: E402,F401

from routes_generation import parse_move_content  # noqa: E402,F401
