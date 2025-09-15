from pathlib import Path
import re
from typing import List, Optional, Sequence


def load_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        try:
            return path.read_text(encoding='latin-1')
        except Exception:
            return None


def write_text_with_backup(path: Path, text: str, backup_suffix: Optional[str], color: bool) -> None:
    # minimal safe writer with optional backup
    if backup_suffix:
        bak = path.with_name(path.name + backup_suffix)
        try:
            path.replace(bak)
        except Exception:
            pass
    path.write_text(text, encoding='utf-8')


def extract_hashtags(text: str) -> List[str]:
    if not text:
        return []
    tags = re.findall(r"(?<!\w)#([A-Za-z0-9_\-/']+)", text)
    return [t.strip() for t in tags if t.strip()]


def ensure_tags_on_file(path: Path, tags: Sequence[str], dry_run: bool, backup_suffix: Optional[str], color: bool) -> bool:
    """Ensure each tag (without leading '#') appears somewhere in the file. Return True if file was changed."""
    text = load_text(path)
    if text is None:
        return False
    existing = set(t.lower() for t in extract_hashtags(text))
    wanted = [t.lstrip('#') for t in tags]
    missing = [t for t in wanted if t.lower() not in existing]
    if not missing:
        return False
    tag_line = "".join([f" #{t}" for t in missing]).lstrip()
    new_text = text
    if not new_text.endswith("\n"):
        new_text += "\n"
    new_text += tag_line + "\n"
    if not dry_run:
        write_text_with_backup(path, new_text, backup_suffix, color)
    return True
