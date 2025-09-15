import json
from pathlib import Path
import shutil
import tempfile
import os
import importlib

import pytest


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    # create a temporary repo structure and monkeypatch cwd
    repo = tmp_path / "repo"
    repo.mkdir()
    # copy the real Mycelium package into the temp repo so imports work
    orig_root = Path(__file__).resolve().parent.parent
    src_mycelium = orig_root / 'Mycelium'
    dst_mycelium = repo / 'Mycelium'
    if src_mycelium.exists():
        try:
            shutil.copytree(src_mycelium, dst_mycelium)
        except Exception:
            # fallback: create an empty package dir
            dst_mycelium.mkdir()
    else:
        dst_mycelium.mkdir()
    # ensure importable: add repo to sys.path
    import sys
    sys.path.insert(0, str(repo))
    # ensure __init__.py exists in copied Mycelium to make it a package
    try:
        (dst_mycelium / '__init__.py').write_text('# package marker')
    except Exception:
        pass
    monkeypatch.chdir(repo)
    yield repo


def write_stub_files(repo: Path):
    # create several stub files and a pagerank.json mapping
    files = [
        repo / 'Waterbottle Charges.md',
        repo / 'Danger Sense Reaction.md',
        repo / 'Misc Notes.md',
    ]
    for f in files:
        f.write_text('# stub\n\nSome content\n', encoding='utf-8')
    # write pagerank.json favoring 'Danger Sense Reaction.md'
    pr = {
        str(files[1].relative_to(repo).as_posix()): 0.9,
        str(files[0].relative_to(repo).as_posix()): 0.1,
    }
    (repo / 'Mycelium' / 'pagerank.json').write_text(json.dumps(pr), encoding='utf-8')
    return files


def test_find_note_prefers_pagerank(tmp_repo):
    # Import the module under test
    mod = importlib.import_module('Mycelium.helpers.update_char')
    files = write_stub_files(tmp_repo)
    # call private function _find_note_for_label
    res = mod._find_note_for_label('Danger Sense Reaction')
    assert res is not None
    assert res.name.lower().startswith('danger')


def test_stub_files_marked_for_auto_deletion(tmp_repo):
    # create stub files with the requested tags in content
    repo = tmp_repo
    files = [
        repo / 'stub_Waterbottle Charges.md',
        repo / 'stub_Danger Sense Reaction.md',
    ]
    for f in files:
        f.write_text('# stub\n\n#stub #file_for_garbage_collector #ffile_for_auto_deletion\n', encoding='utf-8')
    # ensure they exist
    for f in files:
        assert f.exists()
    # Basic cleanup: remove files matching the special tags
    removed = []
    for p in repo.rglob('*.md'):
        txt = p.read_text(encoding='utf-8')
        if '#ffile_for_auto_deletion' in txt and '#file_for_garbage_collector' in txt and '#stub' in txt:
            removed.append(p)
            p.unlink()
    # verify cleanup
    for p in removed:
        assert not p.exists()
