"""SQLite-backed store for the 3 hot-contention domains: character vitals,
initiative state, and battlemap tokens.

Why a real database for just these three: they're the fields that change
many times per minute during a live session (HP ticks, turn advances, token
drags) and are exactly where the old "read whole file -> mutate in Python ->
overwrite whole file" approach caused lost updates between concurrent
players. SQLite's transactions (`BEGIN IMMEDIATE` + an optimistic `version`
column) serialize concurrent writers properly instead of relying on a
hand-rolled lock + content-hash comparison. Everything else (sheet prose,
backstory, moves text) stays markdown-only, per "keep the basic data in .md
files."

The database is a fully-regenerable runtime cache, not a second source of
truth: `rebuild_database.py` populates it from the vault (same idempotent
"authoritative source -> derived store" pattern as `recreate_pcs.py`), and
every write here immediately mirrors back to the backing `.md`/`.json` file
(see `routes_sheets.py` / `routes_initiative.py` / `routes_battlemap.py`),
so Obsidian is never stale and the DB file itself can be deleted and rebuilt
at any time with no data loss.

Scale note: single SQLite file, WAL mode, short-lived per-call connections.
This is a LAN app for a handful of concurrent players, not a service that
needs a connection pool.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "mycelium_runtime.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pc_vitals (
    pc_name TEXT PRIMARY KEY,
    current_hp INTEGER,
    max_hp INTEGER,
    ready INTEGER NOT NULL DEFAULT 0,
    conditions_json TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    source_file TEXT,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS initiative_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    round_number INTEGER NOT NULL DEFAULT 1,
    current_turn_index INTEGER NOT NULL DEFAULT 0,
    order_json TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    source_file TEXT,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS battlemap_tokens (
    map_file TEXT NOT NULL,
    token_id TEXT NOT NULL,
    row INTEGER,
    col INTEGER,
    current_hp INTEGER,
    max_hp INTEGER,
    conditions_json TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    updated_at REAL,
    PRIMARY KEY (map_file, token_id)
);
"""


class VersionConflict(Exception):
    """Raised when a PATCH's expected_version doesn't match the DB row."""

    def __init__(self, current: Optional[dict]):
        super().__init__("version conflict")
        self.current = current


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't already exist. Safe to call repeatedly."""
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# pc_vitals
# ---------------------------------------------------------------------------

def _row_to_pc_vitals(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "pcName": row["pc_name"],
        "currentHp": row["current_hp"],
        "maxHp": row["max_hp"],
        "ready": bool(row["ready"]),
        "conditions": json.loads(row["conditions_json"] or "[]"),
        "version": row["version"],
        "sourceFile": row["source_file"],
        "updatedAt": row["updated_at"],
    }


def get_pc_vitals(pc_name: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM pc_vitals WHERE pc_name = ?", (pc_name,)).fetchone()
        return _row_to_pc_vitals(row) if row else None
    finally:
        conn.close()


def upsert_pc_vitals_from_vault(
    pc_name: str, current_hp, max_hp, ready: bool, conditions: List[str], source_file: str
) -> Dict[str, Any]:
    """Used by rebuild_database.py: refresh a row from the vault's current content."""
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT version FROM pc_vitals WHERE pc_name = ?", (pc_name,)).fetchone()
        version = (existing["version"] + 1) if existing else 1
        conn.execute(
            """
            INSERT INTO pc_vitals (pc_name, current_hp, max_hp, ready, conditions_json, version, source_file, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pc_name) DO UPDATE SET
                current_hp=excluded.current_hp,
                max_hp=excluded.max_hp,
                ready=excluded.ready,
                conditions_json=excluded.conditions_json,
                version=excluded.version,
                source_file=excluded.source_file,
                updated_at=excluded.updated_at
            """,
            (pc_name, current_hp, max_hp, int(bool(ready)), json.dumps(conditions or []), version, source_file, time.time()),
        )
        conn.execute("COMMIT")
        return get_pc_vitals(pc_name)
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def update_pc_vitals_fields(pc_name: str, expected_version: Optional[int], fields: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a partial update (currentHp/maxHp/ready/conditions) under an
    optimistic-concurrency transaction. Raises VersionConflict on mismatch."""
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM pc_vitals WHERE pc_name = ?", (pc_name,)).fetchone()
        if row is None:
            # First write for a PC not yet seeded by rebuild_database.py.
            current = None
        else:
            current = _row_to_pc_vitals(row)
        if expected_version is not None and (current is None or current["version"] != expected_version):
            conn.execute("ROLLBACK")
            raise VersionConflict(current)

        current_hp = fields["currentHp"] if "currentHp" in fields else (current["currentHp"] if current else None)
        max_hp = fields["maxHp"] if "maxHp" in fields else (current["maxHp"] if current else None)
        ready = fields["ready"] if "ready" in fields else (current["ready"] if current else False)
        conditions = fields["conditions"] if "conditions" in fields else (current["conditions"] if current else [])
        source_file = fields.get("sourceFile") or (current["sourceFile"] if current else None)
        new_version = (current["version"] + 1) if current else 1

        conn.execute(
            """
            INSERT INTO pc_vitals (pc_name, current_hp, max_hp, ready, conditions_json, version, source_file, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pc_name) DO UPDATE SET
                current_hp=excluded.current_hp,
                max_hp=excluded.max_hp,
                ready=excluded.ready,
                conditions_json=excluded.conditions_json,
                version=excluded.version,
                source_file=excluded.source_file,
                updated_at=excluded.updated_at
            """,
            (pc_name, current_hp, max_hp, int(bool(ready)), json.dumps(conditions or []), new_version, source_file, time.time()),
        )
        conn.execute("COMMIT")
        return get_pc_vitals(pc_name)
    except VersionConflict:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# initiative_state (single row, id=1)
# ---------------------------------------------------------------------------

def _row_to_initiative(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "roundNumber": row["round_number"],
        "currentTurnIndex": row["current_turn_index"],
        "order": json.loads(row["order_json"] or "[]"),
        "version": row["version"],
        "sourceFile": row["source_file"],
        "updatedAt": row["updated_at"],
    }


def get_initiative_state() -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM initiative_state WHERE id = 1").fetchone()
        return _row_to_initiative(row) if row else None
    finally:
        conn.close()


def upsert_initiative_state_from_vault(round_number: int, current_turn_index: int, order: list, source_file: str) -> Dict[str, Any]:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT version FROM initiative_state WHERE id = 1").fetchone()
        version = (existing["version"] + 1) if existing else 1
        conn.execute(
            """
            INSERT INTO initiative_state (id, round_number, current_turn_index, order_json, version, source_file, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                round_number=excluded.round_number,
                current_turn_index=excluded.current_turn_index,
                order_json=excluded.order_json,
                version=excluded.version,
                source_file=excluded.source_file,
                updated_at=excluded.updated_at
            """,
            (round_number, current_turn_index, json.dumps(order or []), version, source_file, time.time()),
        )
        conn.execute("COMMIT")
        return get_initiative_state()
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def update_initiative_state(expected_version: Optional[int], fields: Dict[str, Any]) -> Dict[str, Any]:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM initiative_state WHERE id = 1").fetchone()
        current = _row_to_initiative(row) if row else None
        if expected_version is not None and (current is None or current["version"] != expected_version):
            conn.execute("ROLLBACK")
            raise VersionConflict(current)

        round_number = fields["roundNumber"] if "roundNumber" in fields else (current["roundNumber"] if current else 1)
        current_turn_index = fields["currentTurnIndex"] if "currentTurnIndex" in fields else (current["currentTurnIndex"] if current else 0)
        order = fields["order"] if "order" in fields else (current["order"] if current else [])
        # `characters` lets callers patch just the HP of specific combatants
        # within the existing order without resending the whole array.
        if "characters" in fields and order:
            deltas = {c["name"]: c for c in fields["characters"] if "name" in c}
            order = [
                {**entry, **{k: v for k, v in deltas.get(entry.get("name"), {}).items() if k != "name"}}
                for entry in order
            ]
        source_file = fields.get("sourceFile") or (current["sourceFile"] if current else None)
        new_version = (current["version"] + 1) if current else 1

        conn.execute(
            """
            INSERT INTO initiative_state (id, round_number, current_turn_index, order_json, version, source_file, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                round_number=excluded.round_number,
                current_turn_index=excluded.current_turn_index,
                order_json=excluded.order_json,
                version=excluded.version,
                source_file=excluded.source_file,
                updated_at=excluded.updated_at
            """,
            (round_number, current_turn_index, json.dumps(order or []), new_version, source_file, time.time()),
        )
        conn.execute("COMMIT")
        return get_initiative_state()
    except VersionConflict:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# battlemap_tokens
# ---------------------------------------------------------------------------

def _row_to_token(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "mapFile": row["map_file"],
        "tokenId": row["token_id"],
        "row": row["row"],
        "col": row["col"],
        "currentHp": row["current_hp"],
        "maxHp": row["max_hp"],
        "conditions": json.loads(row["conditions_json"] or "[]"),
        "version": row["version"],
        "updatedAt": row["updated_at"],
    }


def get_battlemap_token(map_file: str, token_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM battlemap_tokens WHERE map_file = ? AND token_id = ?", (map_file, token_id)
        ).fetchone()
        return _row_to_token(row) if row else None
    finally:
        conn.close()


def get_battlemap_tokens_for_map(map_file: str) -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM battlemap_tokens WHERE map_file = ?", (map_file,)).fetchall()
        return [_row_to_token(r) for r in rows]
    finally:
        conn.close()


def upsert_battlemap_token_from_vault(map_file: str, token_id: str, row_pos, col_pos, current_hp, max_hp, conditions: List[str]) -> Dict[str, Any]:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT version FROM battlemap_tokens WHERE map_file = ? AND token_id = ?", (map_file, token_id)
        ).fetchone()
        version = (existing["version"] + 1) if existing else 1
        conn.execute(
            """
            INSERT INTO battlemap_tokens (map_file, token_id, row, col, current_hp, max_hp, conditions_json, version, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(map_file, token_id) DO UPDATE SET
                row=excluded.row, col=excluded.col, current_hp=excluded.current_hp, max_hp=excluded.max_hp,
                conditions_json=excluded.conditions_json,
                version=excluded.version, updated_at=excluded.updated_at
            """,
            (map_file, token_id, row_pos, col_pos, current_hp, max_hp, json.dumps(conditions or []), version, time.time()),
        )
        conn.execute("COMMIT")
        return get_battlemap_token(map_file, token_id)
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def delete_battlemap_tokens_for_map(map_file: str, keep_token_ids: Optional[List[str]] = None) -> None:
    """Used by rebuild_database.py to drop tokens that no longer exist in the vault file."""
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if keep_token_ids:
            placeholders = ",".join("?" for _ in keep_token_ids)
            conn.execute(
                f"DELETE FROM battlemap_tokens WHERE map_file = ? AND token_id NOT IN ({placeholders})",
                (map_file, *keep_token_ids),
            )
        else:
            conn.execute("DELETE FROM battlemap_tokens WHERE map_file = ?", (map_file,))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def update_battlemap_token_fields(map_file: str, token_id: str, expected_version: Optional[int], changes: Dict[str, Any]) -> Dict[str, Any]:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM battlemap_tokens WHERE map_file = ? AND token_id = ?", (map_file, token_id)
        ).fetchone()
        current = _row_to_token(row) if row else None
        if expected_version is not None and (current is None or current["version"] != expected_version):
            conn.execute("ROLLBACK")
            raise VersionConflict(current)

        position = changes.get("position") or {}
        row_pos = position.get("row", current["row"] if current else None)
        col_pos = position.get("col", current["col"] if current else None)
        current_hp = changes["hp"] if "hp" in changes else (current["currentHp"] if current else None)
        max_hp = changes["maxHp"] if "maxHp" in changes else (current["maxHp"] if current else None)
        conditions = changes["conditions"] if "conditions" in changes else (current["conditions"] if current else [])
        new_version = (current["version"] + 1) if current else 1

        conn.execute(
            """
            INSERT INTO battlemap_tokens (map_file, token_id, row, col, current_hp, max_hp, conditions_json, version, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(map_file, token_id) DO UPDATE SET
                row=excluded.row, col=excluded.col, current_hp=excluded.current_hp, max_hp=excluded.max_hp,
                conditions_json=excluded.conditions_json,
                version=excluded.version, updated_at=excluded.updated_at
            """,
            (map_file, token_id, row_pos, col_pos, current_hp, max_hp, json.dumps(conditions or []), new_version, time.time()),
        )
        conn.execute("COMMIT")
        return get_battlemap_token(map_file, token_id)
    except VersionConflict:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
