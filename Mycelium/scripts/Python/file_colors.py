"""
File and folder color computation for file explorer.

This module extracts the color logic from Wikigraphs.py to compute
colors for files and folders based on element tags and hierarchical blending.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Set
import hashlib
import json
import math
import re


def load_element_colors() -> Dict:
    """Load element color configuration from JSON file.
    
    Returns dictionary with keys:
    - element_tag_colors: dict mapping element names to hex colors
    - tag_aliases: dict mapping element names to list of alternative tags
    
    Falls back to hardcoded values if JSON file not found.
    """
    # Try to find element_colors.json relative to this script
    script_dir = Path(__file__).parent
    # Go up two levels: Python -> scripts -> Mycelium
    json_path = script_dir.parent.parent / "element_colors.json"
    
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        # Fallback to hardcoded values
        return {
            "element_tag_colors": {
                "fire": "#ffb3b3",
                "water": "#5f81fd",
                "air": "#c3e8fa",
                "spirit": "#ffcaf4",
                "earth": "#c8f0a6"
            },
            "tag_aliases": {
                "fire": ["fire", "firebending"],
                "water": ["water", "waterbending"],
                "air": ["air", "airbending"],
                "spirit": ["spirit", "spiritbending"],
                "earth": ["earth", "earthbending"]
            }
        }


# Load element colors at module level
ELEMENT_COLORS = load_element_colors()
ELEMENT_TAG_COLORS = ELEMENT_COLORS.get('element_tag_colors', {})
TAG_ALIASES = ELEMENT_COLORS.get('tag_aliases', {})


def hsv_to_hex(h: float, s: float, v: float) -> str:
    """Convert HSV to hex color string."""
    c = v * s
    x = c * (1 - abs((h * 6) % 2 - 1))
    m = v - c
    if h < 1/6:
        r, g, b = c, x, 0
    elif h < 2/6:
        r, g, b = x, c, 0
    elif h < 3/6:
        r, g, b = 0, c, x
    elif h < 4/6:
        r, g, b = 0, x, c
    elif h < 5/6:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    r, g, b = (r + m) * 255, (g + m) * 255, (b + m) * 255
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def hex_to_rgb(hx: str) -> Tuple[float, float, float]:
    """Convert hex color to RGB tuple (0-1 range)."""
    hx = hx.lstrip('#')
    r = int(hx[0:2], 16) / 255.0
    g = int(hx[2:4], 16) / 255.0
    b = int(hx[4:6], 16) / 255.0
    return (r, g, b)


def rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    """Convert RGB tuple (0-1 range) to hex color."""
    r, g, b = rgb
    return '#{0:02x}{1:02x}{2:02x}'.format(
        int(max(0, min(1, r)) * 255),
        int(max(0, min(1, g)) * 255),
        int(max(0, min(1, b)) * 255)
    )


def blend_rgbs(rgbs: List[Tuple[float, float, float]], weights: List[float] | None = None) -> Tuple[float, float, float]:
    """Blend multiple RGB colors with optional weights."""
    if not rgbs:
        return (0.866, 0.866, 0.866)  # light gray default
    if weights is None:
        weights = [1.0] * len(rgbs)
    total = sum(weights) or len(weights)
    sx = sy = sz = 0.0
    for (r, g, b), w in zip(rgbs, weights):
        sx += r * w
        sy += g * w
        sz += b * w
    return (sx / total, sy / total, sz / total)


def build_tag_patterns() -> Dict[str, re.Pattern]:
    """Build regex patterns for element tags."""
    tag_patterns = {}
    for k, aliases in TAG_ALIASES.items():
        group = '|'.join(re.escape(a) for a in aliases)
        # Match word-boundary or underscore after the tag
        pat = rf'(?i)#(?:{group})(?:\b|_)'
        tag_patterns[k] = re.compile(pat)
    return tag_patterns


TAG_PATTERNS = build_tag_patterns()


def compute_file_colors(root: Path, exts: List[str] = ['.md'], excludes: List[str] = []) -> Dict[str, str]:
    """
    Compute colors for all files and folders under root.
    
    Returns a dict mapping relative paths to hex color strings.
    Folders end with '/'.
    """
    # Gather all files and their contents
    files_data: Dict[str, str] = {}  # relative_path -> content
    all_paths: Set[str] = set()
    
    # Walk the directory tree
    for item in root.rglob('*'):
        if item.is_file():
            # Check if we should include this file
            if exts and item.suffix not in exts:
                continue
            # Check excludes
            rel = item.relative_to(root).as_posix()
            if any(exc in rel for exc in excludes):
                continue
            
            # Read content
            try:
                content = item.read_text(encoding='utf-8', errors='replace')
                files_data[rel] = content
                all_paths.add(rel)
            except Exception:
                files_data[rel] = ''
                all_paths.add(rel)
            
            # Add all parent directories
            parts = rel.split('/')
            for i in range(1, len(parts)):
                dir_key = '/'.join(parts[:i]) + '/'
                all_paths.add(dir_key)
    
    # Add root
    all_paths.add('/')
    
    # Build parent-child relationships
    parent_children: Dict[str, List[str]] = {}
    for path in all_paths:
        if path == '/':
            continue
        parts = path.rstrip('/').split('/')
        if len(parts) == 1:
            parent = '/'
        else:
            parent = '/'.join(parts[:-1]) + '/'
        parent_children.setdefault(parent, []).append(path)
    
    # Initialize colors
    colors_by_id: Dict[str, str] = {}
    element_has: Dict[str, bool] = {}
    
    # Detect element tags in files
    element_tagged: Set[str] = set()
    for file_path, content in files_data.items():
        txt = content.lower()
        matched = []
        for tag, pat in TAG_PATTERNS.items():
            if pat.search(txt):
                matched.append(tag)
        
        if matched:
            # Blend multiple element colors if present
            rgbs = [hex_to_rgb(ELEMENT_TAG_COLORS[t]) for t in matched]
            blended = blend_rgbs(rgbs)
            colors_by_id[file_path] = rgb_to_hex(blended)
            element_tagged.add(file_path)
            element_has[file_path] = True
        else:
            # Non-element files get light grey
            colors_by_id[file_path] = '#e6e6e6'
            element_has[file_path] = False
    
    # Count descendant files for weighting
    def count_descendants(node_id: str) -> int:
        children = parent_children.get(node_id, [])
        if not children:
            return 1  # leaf file
        total = 0
        for child in children:
            total += count_descendants(child)
        return max(1, total)
    
    desc_counts = {path: count_descendants(path) for path in all_paths}
    
    # Sort children by descendant count (largest first) for consistency
    for parent, children in parent_children.items():
        children.sort(key=lambda c: (-desc_counts.get(c, 0), c))
    
    # Compute depth for each path
    depth_map: Dict[str, int] = {}
    for path in all_paths:
        if path == '/':
            depth_map[path] = 0
        else:
            depth_map[path] = path.count('/')
    
    # Sort directories by depth (deepest first) for bottom-up coloring
    dirs = [p for p in all_paths if p.endswith('/')]
    dirs_sorted = sorted(dirs, key=lambda x: -depth_map.get(x, 0))
    
    # Compute folder colors via blending
    for d in dirs_sorted:
        children = parent_children.get(d, [])
        if not children:
            colors_by_id[d] = '#e6e6e6'
            element_has[d] = False
            continue
        
        # Check if any child has element tags
        any_element = any(element_has.get(c, False) for c in children)
        
        if not any_element:
            colors_by_id[d] = '#e6e6e6'
            element_has[d] = False
            continue
        
        # Blend colors of children that have elements, weighted by descendant count
        child_rgbs: List[Tuple[float, float, float]] = []
        child_weights: List[float] = []
        
        for child in children:
            if not element_has.get(child, False):
                continue
            col = colors_by_id.get(child)
            if not col:
                continue
            try:
                rgb = hex_to_rgb(col)
                w = float(max(1, desc_counts.get(child, 1)))
                child_rgbs.append(rgb)
                child_weights.append(w)
            except Exception:
                continue
        
        if child_rgbs:
            blended_rgb = blend_rgbs(child_rgbs, child_weights)
            colors_by_id[d] = rgb_to_hex(blended_rgb)
            element_has[d] = True
        else:
            colors_by_id[d] = '#e6e6e6'
            element_has[d] = False
    
    # Propagate parent folder colors to non-element files
    id_parent: Dict[str, str] = {}
    for path in all_paths:
        if path == '/':
            continue
        parts = path.rstrip('/').split('/')
        if len(parts) == 1:
            id_parent[path] = '/'
        else:
            id_parent[path] = '/'.join(parts[:-1]) + '/'
    
    for file_path in files_data.keys():
        if file_path in element_tagged:
            continue
        parent = id_parent.get(file_path)
        if parent:
            parent_col = colors_by_id.get(parent)
            if parent_col:
                colors_by_id[file_path] = parent_col
    
    return colors_by_id
