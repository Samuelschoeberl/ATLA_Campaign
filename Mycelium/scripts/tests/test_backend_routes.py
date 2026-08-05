"""Tests for the Phase 1/2 backend rework: the route-module split, the
nested-route-registration bug fix, the safer path-containment check, the
versioned resource cache/locking, and the SQLite-backed hot-spot endpoints.

Run with: pytest Mycelium/scripts/tests/test_backend_routes.py -q
"""
import json
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_PYTHON = REPO_ROOT / 'Mycelium' / 'scripts' / 'Python'
if str(SCRIPTS_PYTHON) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PYTHON))

import resource_cache  # noqa: E402
import db as vault_db  # noqa: E402


@pytest.fixture()
def flask_app():
    """Build a real Flask app with the frontend_api blueprint registered,
    the same way run_backend.py does, without starting a server.

    Deletes frontend_api/routes_*/sheet_helpers from sys.modules *before*
    importing, forcing one single fresh, consistent import chain -- frontend_api
    creates exactly one Blueprint object, and every routes_* module's
    `from frontend_api import bp` binds to that same instance. (An earlier
    version of this fixture called importlib.reload() *after* importing,
    which re-ran frontend_api.py's body a second time and created an orphaned
    second Blueprint with zero routes on it, while routes_* stayed bound to
    the first -- every request 404'd and several assertions below passed
    vacuously. Don't reintroduce that.)
    """
    for name in list(sys.modules):
        if name == 'frontend_api' or name.startswith('routes_') or name == 'sheet_helpers':
            del sys.modules[name]
    import frontend_api
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(frontend_api.bp)
    return app


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()


# ---------------------------------------------------------------------------
# Route-module split / nested-route bug
# ---------------------------------------------------------------------------

def test_no_duplicate_routes_after_repeated_update_sheet_calls(client):
    """The old bug: player_root_wikigraphs was defined *inside*
    update_sheet()'s function body, so every POST re-registered a deferred
    Flask route. Assert the app's route count is stable across repeated
    calls to update_sheet (using a PC folder that won't exist, so the call
    404s quickly without touching real data)."""
    app = client.application
    before = len(list(app.url_map.iter_rules()))
    for _ in range(5):
        client.post('/update_sheet/__DefinitelyNotARealPC__', json={'content': None})
    after = len(list(app.url_map.iter_rules()))
    assert after == before, "route count grew -- nested-route registration bug is back"


def test_wikigraphs_route_registered_once(client):
    app = client.application
    matches = [r for r in app.url_map.iter_rules() if r.rule == '/api/wikigraphs']
    assert len(matches) == 1


# ---------------------------------------------------------------------------
# list_directory path-containment fix
# ---------------------------------------------------------------------------

def test_list_directory_rejects_path_traversal(client):
    resp = client.get('/api/list_directory', query_string={'path': '../../../etc'})
    # Either resolves outside the repo (403) or the resolved path simply
    # doesn't exist as a directory under REPO_ROOT (404) -- both are safe;
    # what must NOT happen is a 200 listing something outside the repo.
    assert resp.status_code in (400, 403, 404)


def test_list_directory_accepts_real_subdir(client):
    resp = client.get('/api/list_directory', query_string={'path': 'Mycelium/scripts/Python'})
    assert resp.status_code == 200
    data = resp.get_json()
    names = {item['name'] for item in data['items']}
    assert 'db.py' in names


# ---------------------------------------------------------------------------
# resource_cache: versioned writes + locking
# ---------------------------------------------------------------------------

def test_write_with_version_check_conflict(tmp_path):
    p = tmp_path / 'thing.md'
    v1 = resource_cache.write_with_version_check(p, 'hello', expected_version=None)
    with pytest.raises(resource_cache.VersionConflict):
        resource_cache.write_with_version_check(p, 'world', expected_version='stale-version')
    # correct version succeeds
    v2 = resource_cache.write_with_version_check(p, 'world', expected_version=v1)
    assert v2 != v1
    assert p.read_text() == 'world'


def test_concurrent_writes_to_same_path_are_serialized(tmp_path):
    """Two threads racing to write the same file under the same lock: both
    complete, and the file ends up as exactly one of their two contents --
    never truncated/interleaved garbage."""
    p = tmp_path / 'race.md'
    p.write_text('start')
    results = []

    def writer(tag):
        try:
            resource_cache.write_with_version_check(p, f'from-{tag}', expected_version=None)
            results.append(tag)
        except Exception:
            pass

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = p.read_text()
    assert final.startswith('from-')
    assert len(results) == 8


# ---------------------------------------------------------------------------
# db.py: SQLite hot-contention tables
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """Point db.py at a throwaway SQLite file so these tests never touch the
    real mycelium_runtime.db."""
    monkeypatch.setattr(vault_db, 'DB_PATH', tmp_path / 'test_runtime.db')
    vault_db.init_db()
    return vault_db


def test_pc_vitals_upsert_and_patch_roundtrip(isolated_db):
    row = isolated_db.upsert_pc_vitals_from_vault('Anju', 20, 30, False, [], 'Player Root/PCs/Anju/Anju.md')
    assert row['currentHp'] == 20
    assert row['version'] == 1

    updated = isolated_db.update_pc_vitals_fields('Anju', row['version'], {'currentHp': 15})
    assert updated['currentHp'] == 15
    assert updated['version'] == 2


def test_pc_vitals_stale_version_raises_conflict(isolated_db):
    row = isolated_db.upsert_pc_vitals_from_vault('Anju', 20, 30, False, [], 'x.md')
    with pytest.raises(isolated_db.VersionConflict) as exc_info:
        isolated_db.update_pc_vitals_fields('Anju', row['version'] + 99, {'currentHp': 1})
    assert exc_info.value.current['currentHp'] == 20  # untouched


def test_pc_vitals_concurrent_patch_only_one_wins_without_conflict_info(isolated_db):
    """Simulates two clients that both read version N and then both try to
    PATCH: exactly one should succeed on the first attempt; the other must
    get a VersionConflict rather than silently losing the first client's
    write (the bug this whole rework targets)."""
    row = isolated_db.upsert_pc_vitals_from_vault('Blimp', 50, 54, False, [], 'x.md')
    base_version = row['version']

    outcomes = {'ok': 0, 'conflict': 0}
    lock = threading.Lock()

    def patcher(hp_value):
        try:
            isolated_db.update_pc_vitals_fields('Blimp', base_version, {'currentHp': hp_value})
            with lock:
                outcomes['ok'] += 1
        except isolated_db.VersionConflict:
            with lock:
                outcomes['conflict'] += 1

    threads = [threading.Thread(target=patcher, args=(v,)) for v in (10, 20, 30, 40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes['ok'] == 1
    assert outcomes['conflict'] == 3


def test_initiative_state_characters_delta_patch(isolated_db):
    isolated_db.upsert_initiative_state_from_vault(
        1, 0, [{'name': 'Leif', 'initiative': 24, 'isEnemy': False}], 'Initiative Tracker.md'
    )
    state = isolated_db.get_initiative_state()
    updated = isolated_db.update_initiative_state(
        state['version'], {'currentTurnIndex': 1, 'characters': [{'name': 'Leif', 'manualCurrentHp': 5}]}
    )
    assert updated['currentTurnIndex'] == 1
    assert updated['order'][0]['manualCurrentHp'] == 5
    assert updated['order'][0]['initiative'] == 24  # untouched fields preserved


def test_battlemap_token_patch(isolated_db):
    row = isolated_db.upsert_battlemap_token_from_vault('map.json', 'tok-1', 5, 5, 10, 10, [])
    updated = isolated_db.update_battlemap_token_fields(
        'map.json', 'tok-1', row['version'], {'position': {'row': 6, 'col': 7}, 'hp': 8}
    )
    assert updated['row'] == 6 and updated['col'] == 7
    assert updated['currentHp'] == 8
    assert updated['maxHp'] == 10  # untouched


# ---------------------------------------------------------------------------
# PATCH /api/sheets/<pc>/fields -- HTTP-level, against a scratch PC folder
# ---------------------------------------------------------------------------

@pytest.fixture()
def scratch_pc(monkeypatch, tmp_path):
    """Create a throwaway PC folder under a temp REPO_ROOT-shaped tree and
    point sheet_helpers/db at it, so this test never touches real campaign
    data."""
    import sheet_helpers
    pc_dir = tmp_path / 'Player Root' / 'PCs' / 'ZzzTestPC'
    pc_dir.mkdir(parents=True)
    sheet = pc_dir / 'ZzzTestPC character sheet.md'
    sheet.write_text(
        "## Vitals\n\n\n\n"
        "| key               |                 value |\n"
        "| ----------------- | --------------------: |\n"
        "| max_hp            |                    30 |\n"
        "| current_hp        |                    30 |\n"
        "| ready             |                    no |\n"
    )
    monkeypatch.setattr(sheet_helpers, 'REPO_ROOT', tmp_path)
    monkeypatch.setattr('routes_sheets.REPO_ROOT', tmp_path)
    monkeypatch.setattr('routes_files.REPO_ROOT', tmp_path)
    return tmp_path, pc_dir, sheet


def test_patch_sheet_fields_updates_db_and_mirrors_to_file(client, isolated_db, scratch_pc):
    repo_root, pc_dir, sheet = scratch_pc
    resp = client.patch('/api/sheets/ZzzTestPC/fields', json={'fields': {'currentHp': 12}})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['vitals']['currentHp'] == 12

    text = sheet.read_text()
    assert '| current_hp        | 12 |' in text or '12' in text.split('current_hp')[1].split('\n')[0]


def test_patch_sheet_fields_conflict_returns_409(client, isolated_db, scratch_pc):
    resp1 = client.patch('/api/sheets/ZzzTestPC/fields', json={'fields': {'currentHp': 5}})
    v1 = resp1.get_json()['vitals']['version']
    resp2 = client.patch('/api/sheets/ZzzTestPC/fields', json={'expected_version': v1, 'fields': {'currentHp': 6}})
    assert resp2.status_code == 200
    # stale retry with the now-outdated v1
    resp3 = client.patch('/api/sheets/ZzzTestPC/fields', json={'expected_version': v1, 'fields': {'currentHp': 7}})
    assert resp3.status_code == 409
    assert resp3.get_json()['current']['currentHp'] == 6
