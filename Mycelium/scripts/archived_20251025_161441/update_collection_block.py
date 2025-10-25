from pathlib import Path
import os
import re
import sys
from typing import List, Sequence, Tuple, Optional
from collections import defaultdict


def load_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        return None


def colorize(enabled: bool, text: str, *effects: str) -> str:
    return text


def write_text_with_backup(path: Path, content: str, backup_suffix: Optional[str], color: bool) -> None:
    try:
        if backup_suffix:
            backup_path = path.with_suffix(path.suffix + backup_suffix)
            copyfrom = path
            try:
                from shutil import copy2
                copy2(path, backup_path)
            except Exception:
                pass
        path.write_text(content, encoding='utf-8')
    except Exception:
        pass


def best_relative_without_suffix(path: Path, roots: Sequence[Path]) -> str:
    candidates = []
    for r in roots:
        try:
            rel = path.relative_to(r)
            candidates.append(str(rel))
        except Exception:
            pass
    if not candidates:
        candidates.append(str(path))
    chosen = min(candidates, key=len)
    return str(Path(chosen).with_suffix("")).replace("\\", "/")


def gather_backlinks(label: str, candidate_files: Sequence[Path], exclude_path: Path) -> List[Path]:
    link_pattern = re.compile(r"\[\[\s*([^\]|#]+)", re.IGNORECASE)
    results = []
    for f in candidate_files:
        if f == exclude_path or f.suffix == ".bak":
            continue
        text = load_text(f)
        if text is None:
            continue
        found = False
        for m in link_pattern.finditer(text):
            link_target = m.group(1).strip()
            if link_target.lower() == label.lower():
                found = True
                break
        if found:
            results.append(f)
    results.sort(key=lambda p: str(p).lower())
    return results


COLL_BEGIN_TMPL = "<!-- BEGIN-AUTO-COLLECTION:{label} -->"
COLL_END = "<!-- END-AUTO-COLLECTION -->"


def update_collection_block(
    target_file: Path,
    roots: Sequence[Path],
    backlinks: List[Path],
    label: str,
    dry_run: bool,
    backup_suffix: Optional[str],
    color: bool,
    compact: bool,
) -> Tuple[bool, int]:
    begin = COLL_BEGIN_TMPL.format(label=label)
    end = COLL_END
    lines = [begin, "## Backlinks", ""]
    cwd = os.path.relpath(os.getcwd(), str(roots[0]) if roots else os.getcwd())
    tree = defaultdict(dict)
    for p in backlinks:
        rel = os.path.relpath(str(p), str(roots[0]) if roots else os.getcwd())
        parts = rel.split(os.sep)
        d = tree
        for part in parts:
            if part not in d:
                d[part] = {}
            d = d[part]

    root_base = Path(roots[0]).resolve() if roots else None

    def print_tree(d, prefix="", path_parts=None):
        if path_parts is None:
            path_parts = []
        items = list(d.items())
        for idx, (name, subtree) in enumerate(items):
            connector = "└── " if idx == len(items)-1 else "├── "
            if subtree:
                lines.append(f"{prefix}{connector}{name}")
                extension = "    "
                print_tree(subtree, prefix + extension, path_parts + [name])
            else:
                try:
                    rel_path = os.path.join(*([p for p in path_parts] + [name]))
                except Exception:
                    rel_path = name
                bracket = True
                if root_base is None:
                    bracket = False
                else:
                    try:
                        full_path = (root_base / rel_path).resolve()
                        bracket = os.path.commonpath([str(full_path), str(root_base)]) == str(root_base)
                    except Exception:
                        bracket = False
                if bracket:
                    lines.append(f"{prefix}{connector}[[{name}]]")
                else:
                    lines.append(f"{prefix}{connector}{name}")

    lines.append(f"  {cwd}/")
    print_tree(tree, prefix="  ")
    lines.append("")
    lines.append(end)
    lines.append("")
    block_text = "\n".join(lines)

    if target_file.exists():
        try:
            content = target_file.read_text(encoding='utf-8')
        except Exception:
            content = ""
    else:
        content = ""

    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(content):
        new_content = pattern.sub(block_text, content, count=1)
    else:
        content = content.rstrip("\n") + "\n"
        new_content = content + block_text

    changed = new_content != content
    if changed and not dry_run:
        write_text_with_backup(target_file, new_content, backup_suffix, color)
    return changed, len(backlinks)
