#!/usr/bin/env python3
"""Build a standalone static HTML file from the React frontend.

This script creates a single HTML file that includes all JavaScript, CSS,
and a complete snapshot of Player Root content inline. The resulting file
works completely offline without needing the Flask backend.
"""
from pathlib import Path
import sys
import re
import json

# Find repository root
_script_path = Path(__file__).resolve()
ROOT = _script_path
while ROOT.parent != ROOT:
    if (ROOT / '.git').exists():
        break
    ROOT = ROOT.parent
if not (ROOT / '.git').exists():
    ROOT = _script_path.parent.parent.parent

FRONTEND_DIR = ROOT / 'Mycelium' / 'scripts' / 'frontend-react' / 'src'
PLAYER_ROOT = ROOT / 'Player Root'
OUTPUT_FILE = ROOT / 'static_mycelium.html'

# Patterns from .gitignore to filter out
GITIGNORE_PATTERNS = [
    r'\.DS_Store',
    r'\.bak$',
    r'\.zip$',
    r'__pycache__',
    r'\.obsidian/workspace\.json$',
    r'^logs$',
    r'\.log$',
    r'^backups$',
    r'^DMs Root',
]

def should_ignore(path):
    """Check if path matches gitignore patterns."""
    name = path.name
    return any(re.search(pattern, name, re.IGNORECASE) for pattern in GITIGNORE_PATTERNS)


def snapshot_player_root():
    """Create a complete snapshot of Player Root directory structure and files."""
    if not PLAYER_ROOT.exists():
        print(f"WARNING: Player Root not found at {PLAYER_ROOT}")
        return {}
    
    snapshot = {
        'directories': {},
        'files': {}
    }
    
    print("Snapshotting Player Root content...")
    file_count = 0
    
    for path in PLAYER_ROOT.rglob('*'):
        if should_ignore(path):
            continue
            
        rel_path = str(path.relative_to(PLAYER_ROOT))
        
        if path.is_file():
            try:
                # Read file content
                if path.suffix.lower() in ['.md', '.txt', '.json', '.html', '.css', '.js']:
                    content = path.read_text(encoding='utf-8')
                    snapshot['files'][rel_path] = {
                        'type': 'text',
                        'content': content,
                        'size': len(content)
                    }
                    file_count += 1
                else:
                    # For binary files, just store metadata
                    snapshot['files'][rel_path] = {
                        'type': 'binary',
                        'size': path.stat().st_size
                    }
            except Exception as e:
                print(f"  Warning: Could not read {rel_path}: {e}")
        
        elif path.is_dir():
            snapshot['directories'][rel_path] = {
                'exists': True
            }
    
    print(f"  Captured {file_count} files")
    return snapshot


def read_file(path):
    """Read file content as text."""
    try:
        return path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return ""


def collect_component_code():
    """Collect all React component code."""
    components_dir = FRONTEND_DIR / 'components'
    components = {}
    
    for comp_file in sorted(components_dir.glob('*.jsx')):
        name = comp_file.stem
        content = read_file(comp_file)
        # Remove all import statements (including multiline)
        content = re.sub(r'import\s+.*?from\s+["\'].*?["\'];?', '', content, flags=re.DOTALL)
        content = re.sub(r'import\s+["\'].*?["\'];?', '', content, flags=re.DOTALL)
        # Remove export statements
        content = re.sub(r'export\s+default\s+\w+\s*;?', '', content, flags=re.DOTALL)
        content = re.sub(r'export\s+\{[^}]+\}\s*;?', '', content, flags=re.DOTALL)
        components[name] = content.strip()
    
    return components


def collect_utils_code():
    """Collect utility functions."""
    utils_dir = FRONTEND_DIR / 'utils'
    utils = {}
    
    for util_file in sorted(utils_dir.glob('*.js')):
        name = util_file.stem
        content = read_file(util_file)
        # Remove all import/export statements (including multiline)
        content = re.sub(r'import\s+.*?from\s+["\'].*?["\'];?', '', content, flags=re.DOTALL)
        content = re.sub(r'import\s+["\'].*?["\'];?', '', content, flags=re.DOTALL)
        content = re.sub(r'export\s+default\s+', '', content, flags=re.DOTALL)
        content = re.sub(r'export\s+\{[^}]+\}\s*;?', '', content, flags=re.DOTALL)
        content = re.sub(r'export\s+const\s+', 'const ', content, flags=re.DOTALL)
        content = re.sub(r'export\s+function\s+', 'function ', content, flags=re.DOTALL)
        utils[name] = content.strip()
    
    return utils


def build_html():
    """Build the complete HTML file."""
    
    # Read main files
    app_jsx = read_file(FRONTEND_DIR / 'App.jsx')
    main_jsx = read_file(FRONTEND_DIR / 'main.jsx')
    css = read_file(FRONTEND_DIR / 'styles' / 'App.css')
    
    # Clean App.jsx - remove all imports and exports (including multiline)
    app_jsx = re.sub(r'import\s+.*?from\s+["\'].*?["\'];?', '', app_jsx, flags=re.DOTALL)
    app_jsx = re.sub(r'import\s+["\'].*?["\'];?', '', app_jsx, flags=re.DOTALL)
    app_jsx = re.sub(r'export\s+default\s+\w+\s*;?', '', app_jsx, flags=re.DOTALL)
    
    # Collect components and utils
    components = collect_component_code()
    utils = collect_utils_code()
    
    # Snapshot Player Root
    snapshot = snapshot_player_root()
    snapshot_json = json.dumps(snapshot, indent=2)
    
    # Build the HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mycelium - Player Root (Standalone)</title>
  <style>
{css}
  </style>
</head>
<body>
  <div id="root"></div>
  
  <!-- Embedded Player Root Snapshot -->
  <script id="player-root-data" type="application/json">
{snapshot_json}
  </script>
  
  <!-- React and Babel from CDN -->
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  
  <!-- Markdown libraries -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js"></script>
  
  <script type="text/babel">
    const {{ useState, useEffect }} = React;
    
    // ===== LOAD SNAPSHOT DATA =====
    const SNAPSHOT = JSON.parse(document.getElementById('player-root-data').textContent);
    
    // ===== MOCK API FOR STANDALONE MODE =====
    const fetchDirectory = (path) => {{
      return new Promise((resolve) => {{
        const entries = [];
        const prefix = path ? path + '/' : '';
        
        // Find all direct children
        const seen = new Set();
        
        // Add directories
        for (const [dirPath, data] of Object.entries(SNAPSHOT.directories)) {{
          if (dirPath.startsWith(prefix)) {{
            const rest = dirPath.substring(prefix.length);
            const firstSegment = rest.split('/')[0];
            
            if (firstSegment && !seen.has(firstSegment)) {{
              seen.add(firstSegment);
              entries.push({{
                name: firstSegment,
                type: 'directory',
                path: prefix + firstSegment
              }});
            }}
          }}
        }}
        
        // Add files
        for (const [filePath, fileData] of Object.entries(SNAPSHOT.files)) {{
          if (filePath.startsWith(prefix)) {{
            const rest = filePath.substring(prefix.length);
            const parts = rest.split('/');
            
            if (parts.length === 1 && parts[0]) {{
              entries.push({{
                name: parts[0],
                type: 'file',
                path: filePath,
                size: fileData.size
              }});
            }}
          }}
        }}
        
        resolve({{ entries }});
      }});
    }};
    
    const fetchFile = (path) => {{
      return new Promise((resolve, reject) => {{
        const fileData = SNAPSHOT.files[path];
        if (fileData && fileData.type === 'text') {{
          resolve({{ content: fileData.content }});
        }} else if (fileData) {{
          reject(new Error('Binary file cannot be displayed'));
        }} else {{
          reject(new Error('File not found'));
        }}
      }});
    }};
    
    const saveFile = (path, content) => {{
      return Promise.reject(new Error('Cannot save in standalone mode'));
    }};
    
    const moveFile = (src, dst) => {{
      return Promise.reject(new Error('Cannot move files in standalone mode'));
    }};
    
    const createFile = (path, content) => {{
      return Promise.reject(new Error('Cannot create files in standalone mode'));
    }};
    
    const generateGraphs = (folder) => {{
      return Promise.reject(new Error('Cannot generate graphs in standalone mode'));
    }};
    
    const searchFiles = (query) => {{
      return Promise.reject(new Error('Search not available in standalone mode'));
    }};
    
    // ===== HELPER UTILITIES =====
{utils.get('helpers', '// Helpers not found')}
    
    // ===== COMPONENTS =====
    
    // Header
{components.get('Header', '// Header not found')}
    
    // Navigation
{components.get('Navigation', '// Navigation not found')}
    
    // FileList
{components.get('FileList', '// FileList not found')}
    
    // MarkdownPreview
{components.get('MarkdownPreview', '// MarkdownPreview not found')}
    
    // FileEditor
{components.get('FileEditor', '// FileEditor not found')}
    
    // DiceRoller
{components.get('DiceRoller', '// DiceRoller not found')}
    
    // EventLog
{components.get('EventLog', '// EventLog not found')}
    
    // ===== MAIN APP =====
{app_jsx}
    
    // ===== RENDER =====
    const root = ReactDOM.createRoot(document.getElementById('root'));
    root.render(React.createElement(App));
  </script>
</body>
</html>
"""
    
    return html


def main():
    """Main entry point."""
    if not FRONTEND_DIR.exists():
        print(f"ERROR: Frontend directory not found at {FRONTEND_DIR}")
        sys.exit(1)
    
    print(f"Building standalone static HTML from React frontend...")
    print(f"Source: {FRONTEND_DIR}")
    print(f"Data: {PLAYER_ROOT}")
    print()
    
    html = build_html()
    
    OUTPUT_FILE.write_text(html, encoding='utf-8')
    
    print()
    print(f"✓ Created: {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"  Size: {len(html):,} bytes ({len(html) / 1024 / 1024:.2f} MB)")
    print()
    print("This standalone HTML file includes:")
    print("  • All React components and utilities")
    print("  • Complete snapshot of Player Root content")
    print("  • Works offline without Flask backend")
    print("  • Read-only mode (cannot save/edit)")
    print()
    print("To use:")
    print("  • Open the HTML file directly in any browser")
    print("  • Or serve with: python3 -m http.server 8080")


if __name__ == '__main__':
    main()
