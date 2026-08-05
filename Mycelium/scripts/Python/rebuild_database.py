#!/usr/bin/env python3
"""Rebuild the SQLite runtime database (mycelium_runtime.db) from the vault.

Mirrors the idempotent "authoritative source -> derived store" pattern of
`recreate_pcs.py`, but populates the 3 hot-contention SQLite tables (see
`db.py`) instead of regenerating markdown files: `pc_vitals`,
`initiative_state`, `battlemap_tokens`.

The database is a fully-regenerable runtime cache, not a second source of
truth — deleting `mycelium_runtime.db` and re-running this script reconstructs
it entirely from the vault's `.md`/`.json` files. Run automatically once at
`run_backend.py` startup, and available standalone for a manual re-sync
(e.g. after hand-editing sheets in Obsidian while the server wasn't running):

    python3 Mycelium/scripts/Python/rebuild_database.py
    python3 Mycelium/scripts/Python/rebuild_database.py --pc Anju
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from . import db
    from . import sheet_helpers as sh
except ImportError:  # running as a script, not a package
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import db
    import sheet_helpers as sh

REPO_ROOT = sh.REPO_ROOT


def _iter_pc_dirs():
    pcs_dir = sh.get_player_root_base() / 'PCs'
    if not pcs_dir.exists():
        return
    for p in sorted(pcs_dir.iterdir()):
        if p.is_dir():
            yield p


def rebuild_pc_vitals(only_pc: str | None = None) -> int:
    """Sync pc_vitals from each PC's character sheet. Returns count synced."""
    count = 0
    for pc_dir in _iter_pc_dirs():
        pcname = pc_dir.name
        if only_pc and pcname.lower() != only_pc.lower():
            continue
        sheet = sh.find_sheet_file(pc_dir, pcname)
        if not sheet:
            continue
        try:
            text = sheet.read_text(encoding='utf-8')
        except Exception as e:
            print(f'  [skip] {pcname}: could not read sheet ({e})')
            continue
        parsed = sh.parse_vitals_and_conditions(text)
        try:
            rel = str(sheet.relative_to(REPO_ROOT).as_posix())
        except Exception:
            rel = str(sheet)
        db.upsert_pc_vitals_from_vault(
            pcname,
            parsed['current_hp'],
            parsed['max_hp'],
            parsed['ready'],
            parsed['conditions'],
            rel,
        )
        count += 1
        print(f'  synced pc_vitals: {pcname} (hp {parsed["current_hp"]}/{parsed["max_hp"]}, ready={parsed["ready"]}, conditions={parsed["conditions"]})')
    return count


_INIT_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(-?\d*\.?\d*)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$")


def rebuild_initiative_state() -> bool:
    """Sync initiative_state from Initiative Tracker.md. Returns True if found."""
    tracker = sh.get_player_root_base() / 'Initiative Tracker.md'
    if not tracker.exists():
        print('  [skip] Initiative Tracker.md not found')
        return False
    try:
        text = tracker.read_text(encoding='utf-8')
    except Exception as e:
        print(f'  [skip] could not read Initiative Tracker.md ({e})')
        return False

    order = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith('|') or '---' in s:
            continue
        cols = [c.strip() for c in s.split('|')[1:-1]]
        if len(cols) < 2:
            continue
        name = cols[0]
        if name.lower() in ('character', 'end of round'):
            continue
        try:
            initiative = float(cols[1]) if cols[1] else 0
        except Exception:
            initiative = 0
        is_enemy = bool(cols[2]) if len(cols) > 2 else False
        manual_hp = cols[3] if len(cols) > 3 and cols[3] else None
        damage_mode = cols[4] if len(cols) > 4 and cols[4] else None
        order.append({
            'name': name,
            'initiative': initiative,
            'isEnemy': is_enemy,
            'manualCurrentHp': manual_hp,
            'damageMode': damage_mode,
        })

    turn_match = re.search(r"\*\*Current Turn:\*\*.*?\(Index:\s*(\d+)\)", text)
    current_turn_index = int(turn_match.group(1)) if turn_match else 0
    round_match = re.search(r"\*\*Round:\*\*\s*(\d+)", text)
    round_number = int(round_match.group(1)) if round_match else 1

    rel = str(tracker.relative_to(REPO_ROOT).as_posix())
    db.upsert_initiative_state_from_vault(round_number, current_turn_index, order, rel)
    print(f'  synced initiative_state: round={round_number}, turn_index={current_turn_index}, {len(order)} combatant(s)')
    return True


def rebuild_battlemap_tokens() -> int:
    """Sync battlemap_tokens from every Player Root/Maps/*.json that has a
    top-level 'tokens' array (distinguishes actual battlemap state files from
    the per-background-image hex-grid definition files that live alongside
    them). Returns the number of map files synced."""
    maps_dir = sh.get_player_root_base() / 'Maps'
    if not maps_dir.exists():
        return 0
    synced = 0
    for path in sorted(maps_dir.glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(data, dict) or 'tokens' not in data:
            continue
        rel = str(path.relative_to(REPO_ROOT).as_posix())
        tokens = data.get('tokens') or []
        kept_ids = []
        for tok in tokens:
            token_id = tok.get('id')
            if not token_id:
                continue
            kept_ids.append(token_id)
            db.upsert_battlemap_token_from_vault(
                rel, token_id,
                tok.get('row'), tok.get('col'),
                tok.get('currentHp'), tok.get('maxHp'),
                tok.get('conditions') or [],
            )
        db.delete_battlemap_tokens_for_map(rel, keep_token_ids=kept_ids)
        synced += 1
        print(f'  synced battlemap_tokens: {rel} ({len(kept_ids)} token(s))')
    return synced


def rebuild_all(only_pc: str | None = None) -> None:
    db.init_db()
    print('Rebuilding pc_vitals from Player Root/PCs/*/...')
    pc_count = rebuild_pc_vitals(only_pc=only_pc)
    if only_pc:
        print(f'Done: {pc_count} PC(s) synced (--pc filter active, initiative/battlemap skipped)')
        return
    print('Rebuilding initiative_state from Initiative Tracker.md...')
    rebuild_initiative_state()
    print('Rebuilding battlemap_tokens from Player Root/Maps/*.json...')
    map_count = rebuild_battlemap_tokens()
    print(f'Done: {pc_count} PC(s), initiative state, {map_count} map(s) synced')


def main() -> None:
    parser = argparse.ArgumentParser(description='Rebuild the SQLite runtime database from the vault')
    parser.add_argument('--pc', default=None, help='Only sync a single PC by name (skips initiative/battlemap)')
    args = parser.parse_args()
    rebuild_all(only_pc=args.pc)


if __name__ == '__main__':
    main()
