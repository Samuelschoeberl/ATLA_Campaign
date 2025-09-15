import os
from pathlib import Path
import pytest

from Mycelium.scripts.Python.ensure_tags_on_file import ensure_tags_on_file, load_text


def test_dry_run_does_not_modify(tmp_path: Path):
    p = tmp_path / "note.md"
    original = "This is a file.\n"
    p.write_text(original, encoding='utf-8')

    changed = ensure_tags_on_file(p, ['newtag'], dry_run=True, backup_suffix='~', color=False)
    assert changed is True
    assert p.read_text(encoding='utf-8') == original
    # backup should not be created on dry-run
    assert not (tmp_path / 'note.md~').exists()


def test_writes_and_creates_backup(tmp_path: Path):
    p = tmp_path / "note2.md"
    original = "Line one\n"
    p.write_text(original, encoding='utf-8')

    changed = ensure_tags_on_file(p, ['addedtag'], dry_run=False, backup_suffix='~', color=False)
    assert changed is True
    # file should now contain the appended tag line
    content = p.read_text(encoding='utf-8')
    assert content.endswith('\n#addedtag\n')
    # backup file should exist and contain the original
    bak = tmp_path / 'note2.md~'
    assert bak.exists()
    assert bak.read_text(encoding='utf-8') == original


def test_no_missing_returns_false(tmp_path: Path):
    p = tmp_path / "note3.md"
    original = "Intro\n#tag1 #tag2\n"
    p.write_text(original, encoding='utf-8')

    changed = ensure_tags_on_file(p, ['tag1'], dry_run=False, backup_suffix='~', color=False)
    assert changed is False
    # content unchanged
    assert p.read_text(encoding='utf-8') == original
    # no backup created
    assert not (tmp_path / 'note3.md~').exists()
