from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from pathlib import Path
import os
import sys
from urllib.parse import unquote
import fnmatch
# Determine repository root and ensure it's on sys.path so package-style
# imports work regardless of how this script is invoked.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Try to import the blueprint from a few sensible locations so running
# the launcher as a script, module, or from a different cwd still works.
bp = None
try:
    # Prefer package-style import when available
    from Mycelium.scripts.Python.frontend_api import bp as _bp
    bp = _bp
except Exception:
    try:
        # Fallback to same-directory import (when running this file directly)
        from frontend_api import bp as _bp2  # file is in same directory
        bp = _bp2
    except Exception:
        # Final attempt: add the scripts/Python dir to sys.path and import
        scripts_python_dir = Path(__file__).resolve().parent
        if str(scripts_python_dir) not in sys.path:
            sys.path.insert(0, str(scripts_python_dir))
        from frontend_api import bp as _bp3
        bp = _bp3

# Ensure the current working directory is the repository root. This makes
# subprocess invocations performed by the API (for example the Wikigraphs
# generator) run with a predictable cwd so output files end up in the
# expected repository-relative locations.
try:
    os.chdir(str(REPO_ROOT))
except Exception:
    # non-fatal; continue without changing cwd
    pass

# create app without default static folder to serve our frontend dir explicitly
app = Flask(__name__, static_folder=None)
CORS(app)  # allow requests from the frontend served from file:// or another host
app.register_blueprint(bp)

# serve the lightweight frontend files from scripts/frontend
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
STATIC_SNAPSHOT_FILENAME = "static_mycelium.html"

# ---- Targeted static asset helpers and routes (favicon/logo fallbacks) ----
def _safe_send_path(candidate_path: Path):
    """Return a response for candidate_path if it exists and is a file, else None."""
    try:
        if candidate_path.exists() and candidate_path.is_file():
            return send_file(str(candidate_path))
    except Exception:
        pass
    return None

@app.route('/favicon.ico')
def serve_favicon():
    # Try a few common locations; fall back to the repository logo
    candidates = [
        FRONTEND_DIR / 'favicon.ico',
        REPO_ROOT / 'favicon.ico',
        REPO_ROOT / 'Mycelium' / 'favicon.ico',
        REPO_ROOT / 'Mycelium' / 'Mycelium Logo.png',
        REPO_ROOT / 'Mycelium' / 'Logo.png',
    ]
    for c in candidates:
        resp = _safe_send_path(c)
        if resp:
            return resp
    from werkzeug.exceptions import NotFound
    raise NotFound()

@app.route('/Logo.png')
@app.route('/Mycelium/Logo.png')
def serve_logo_png():
    # Map generic Logo.png requests to the canonical repo logo file when present
    candidates = [
        REPO_ROOT / 'Mycelium' / 'Mycelium Logo.png',
        REPO_ROOT / 'Mycelium' / 'Logo.png',
        FRONTEND_DIR / 'Logo.png',
        REPO_ROOT / 'Logo.png',
    ]
    for c in candidates:
        resp = _safe_send_path(c)
        if resp:
            return resp
    from werkzeug.exceptions import NotFound
    raise NotFound()

def _ensure_static_index_at_repo_root():
        """Create a small landing `index.html` and a client-side `disconnected_mycelium.html`
        that embeds a manifest of small text files from the repo for offline
        browsing. This function is intentionally conservative about what it embeds
        (skips large files and ignored directories) to avoid creating huge HTML
        blobs.
        """
        try:
                src = FRONTEND_DIR.joinpath("index.html")
                if not src.exists():
                        print(f"_ensure_static_index_at_repo_root: source not found: {src}", flush=True)
                        return

                # Build manifest
                import json
                import textwrap

                def is_ignored_dir(name: str) -> bool:
                        lower = name.lower()
                        return lower in (
                                '.git', '__pycache__', 'node_modules', '.venv', '.venv3', '.idea', '.pytest_cache', '.tox'
                        )

                # Load .gitignore patterns if present and provide a matcher for them.
                gitignore_path = REPO_ROOT.joinpath('.gitignore')
                gitignore_patterns = []
                gitignore_negations = []
                if gitignore_path.exists():
                    try:
                        for ln in gitignore_path.read_text(encoding='utf-8').splitlines():
                            s = ln.strip()
                            if not s or s.startswith('#'):
                                continue
                            if s.startswith('!'):
                                gitignore_negations.append(s[1:])
                            else:
                                gitignore_patterns.append(s)
                    except Exception:
                        # If reading fails, just treat as no patterns
                        gitignore_patterns = []
                        gitignore_negations = []

                def is_ignored_by_gitignore(rel_path: str) -> bool:
                    """Return True if rel_path (posix, relative to repo root) matches .gitignore patterns.

                    This implements a conservative subset of .gitignore semantics sufficient for
                    the project's patterns (wildcards, simple directory prefixes, and filename
                    patterns). Negation patterns beginning with '!' are supported.
                    """
                    # Normalize to posix
                    p = rel_path
                    # Check negations first: if any negation matches, do not ignore
                    for neg in gitignore_negations:
                        try:
                            if '/' in neg:
                                if fnmatch.fnmatch(p, neg) or p.startswith(neg.rstrip('/')):
                                    return False
                            else:
                                if fnmatch.fnmatch(Path(p).name, neg):
                                    return False
                        except Exception:
                            continue

                    for pat in gitignore_patterns:
                        try:
                            # directory pattern like 'foo/' or 'foo/*' should match any path under foo/
                            if pat.endswith('/') or pat.endswith('/*'):
                                prefix = pat.rstrip('/*').rstrip('/')
                                if p == prefix or p.startswith(prefix + '/'):
                                    return True
                            elif '/' in pat:
                                # pattern contains a path component; match against the relative path
                                if fnmatch.fnmatch(p, pat):
                                    return True
                                # also allow prefix match
                                if p.startswith(pat.rstrip('*')):
                                    return True
                            else:
                                # filename-level pattern like '*.bak' or 'Mycelium_*'
                                if fnmatch.fnmatch(Path(p).name, pat):
                                    return True
                        except Exception:
                            continue
                    return False

                max_size = 100 * 1024  # only embed files up to 100KB
                manifest = {}
                file_count = 0
                max_files = 5000

                for root, dirs, files in os.walk(str(REPO_ROOT)):
                        dirs[:] = [d for d in dirs if not is_ignored_dir(d)]
                        for fn in files:
                                if file_count >= max_files:
                                        break
                                abs_path = Path(root).joinpath(fn)
                                rel = abs_path.relative_to(REPO_ROOT).as_posix()
                                if rel in ('index.html', STATIC_SNAPSHOT_FILENAME):
                                        continue
                                # Respect .gitignore patterns: skip files that match
                                try:
                                    if is_ignored_by_gitignore(rel):
                                        continue
                                except Exception:
                                    pass
                                try:
                                        size = abs_path.stat().st_size
                                except Exception:
                                        continue
                                entry = {'size': size}
                                if size > max_size:
                                        entry['type'] = 'large'
                                        entry['note'] = 'file too large to embed in static snapshot'
                                else:
                                        try:
                                                text = abs_path.read_text(encoding='utf-8')
                                                entry['type'] = 'text'
                                                entry['text'] = text
                                        except Exception:
                                                entry['type'] = 'binary'
                                manifest[rel] = entry
                                file_count += 1
                        if file_count >= max_files:
                                break

                static_title = 'Mycelium — Static Repo Browser'
                manifest_json = json.dumps(manifest)
                # Prevent the embedded JSON from containing the sequence '</' which would
                # prematurely close the surrounding <script> tag when rendered by a browser.
                manifest_json = manifest_json.replace('</', '<\\/')

                # Read the real frontend index.html and inject a small static-only
                # helper script that embeds the manifest and provides fetchPath /
                # fetchPathWithHash implementations backed by the manifest. This keeps
                # the full original layout and styles while disabling backend calls.
                try:
                    frontend_html = src.read_text(encoding='utf-8')
                except Exception:
                    frontend_html = None

                if frontend_html:
                    injection = textwrap.dedent(r"""
                    <script>
                    // Lightweight inline replacements for marked.parse and DOMPurify.sanitize
                    // to allow the static snapshot to work offline without external CDNs.

                    // Very small Markdown -> HTML converter (subset of marked).
                    const marked = {
                        parse: function(md){
                            if(md == null) return '';
                            let s = String(md);
                            // escape HTML
                            s = s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                            // code blocks ```
                            s = s.replace(/```([\s\S]*?)```/g, function(m, code){ return '<pre><code>'+code.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</code></pre>'; });
                            // headings
                            s = s.replace(/^###\s*(.+)$/gm, '<h3>$1</h3>');
                            s = s.replace(/^##\s*(.+)$/gm, '<h2>$1</h2>');
                            s = s.replace(/^#\s*(.+)$/gm, '<h1>$1</h1>');
                            // bold and italic
                            s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
                            s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
                            // inline code
                            s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
                            // links [text](url)
                            s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(m,t,u){ return '<a href="'+u.replace(/"/g,'&quot;')+'">'+t+'</a>'; });
                            // unordered lists: convert lines starting with - into <ul>
                            s = s.replace(/(^|\n)(?:-\s+(.+))(?:\n|$)/g, function(_,pre,item){ return pre+'<ul><li>'+item+'</li></ul>'; });
                            // paragraphs: two or more newlines => paragraph breaks
                            s = s.replace(/\n{2,}/g, '</p><p>');
                            // wrap remaining single newlines with <br>
                            s = s.replace(/\n/g, '<br>');
                            // ensure top-level paragraphs
                            if(!/^\s*<h|^\s*<ul|^\s*<pre/.test(s)){
                                s = '<p>' + s + '</p>';
                            }
                            return s;
                        }
                    };

                    // Simple DOMPurify-like sanitizer implemented using DOM APIs.
                    const DOMPurify = {
                        sanitize: function(html){
                            if(html == null) return '';
                            try{
                                const template = document.createElement('template');
                                template.innerHTML = String(html);
                                const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_ELEMENT, null, false);
                                const nodes = [];
                                while(walker.nextNode()) nodes.push(walker.currentNode);
                                // iterate from leaves up
                                nodes.reverse().forEach(node=>{
                                    try{
                                        const tag = (node.tagName || '').toLowerCase();
                                        if(tag === 'script' || tag === 'iframe' || tag === 'object' || tag === 'embed'){
                                            node.parentNode && node.parentNode.removeChild(node);
                                            return;
                                        }
                                        // remove event handler attributes and dangerous URIs
                                        for(const attr of Array.from(node.attributes || [])){
                                            const name = (attr.name||'').toLowerCase();
                                            const val = (attr.value||'').toLowerCase().trim();
                                            if(name.startsWith('on')){
                                                node.removeAttribute(attr.name);
                                            } else if((name === 'href' || name === 'src' || name === 'xlink:href') && val.startsWith('javascript:')){
                                                node.removeAttribute(attr.name);
                                            }
                                        }
                                    }catch(e){}
                                });
                                return template.innerHTML;
                            }catch(e){
                                // fallback: escape
                                return String(html).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                            }
                        }
                    };

                    // Embedded static manifest for offline browsing
                    const MANIFEST = __MANIFEST_JSON__;

                    // Normalize helper: accept either 'Player Root/...' or relative paths
                    function _normPath(p){
                        if(!p && p!=="") return "";
                        p = String(p || "");
                        if(/^Player Root\//i.test(p)) p = p.replace(/^Player Root\//i, "");
                        return p.replace(/^\/+|\/+$/g, "");
                    }

                    // Build a lightweight folder view from MANIFEST for the given relative path.
                    async function static_fetchPath(p){
                        const rel = _normPath(p);
                        const entriesMap = Object.create(null);
                        for(const k of Object.keys(MANIFEST)){
                            const key = k.replace(/^\/+/,"");
                            if(!rel){
                                // top-level: take first segment
                                const seg = key.split('/')[0];
                                entriesMap[seg] = entriesMap[seg] || { name: seg, path: seg, type: 'dir' };
                                // if key has no slash, it's a file at top-level
                                if(key.indexOf('/')===-1){
                                    entriesMap[seg] = { name: seg, path: seg, type: 'file' };
                                }
                            } else {
                                if(key === rel) {
                                    const name = rel.split('/').pop();
                                    entriesMap[name] = { name, path: rel, type: 'file' };
                                } else if(key.startsWith(rel + '/')){
                                    const rest = key.slice((rel + '/').length);
                                    const first = rest.split('/')[0];
                                    const isDir = rest.indexOf('/') !== -1;
                                    if(isDir){
                                        entriesMap[first] = entriesMap[first] || { name: first, path: (rel? rel + '/'+ first: first), type: 'dir' };
                                    } else {
                                        entriesMap[first] = { name: first, path: (rel? rel + '/'+ first: first), type: 'file' };
                                    }
                                }
                            }
                        }
                        const entries = Object.keys(entriesMap).sort().map(k=>entriesMap[k]);
                        return { path: (rel? 'Player Root/' + rel : 'Player Root'), entries };
                    }

                    async function static_fetchPathWithHash(p){
                        const rel = _normPath(p);
                        const key = rel;
                        if(MANIFEST[key] && MANIFEST[key].type === 'text'){
                            return { json: { content: MANIFEST[key].text }, hash: null };
                        }
                        return { json: { content: '' }, hash: null };
                    }

                    async function static_resolveHtmlUrl(seg){
                        if(!seg) return null;
                        return '/' + seg.replace(/^\/+/, '');
                    }

                    // Helper to remove the 'new-file' input and Create button from the
                    // static view since those require a backend.
                    function removeCreateControls(){
                        try{
                            const entriesWrap = document.getElementById('entries-wrap');
                            if(!entriesWrap) return;
                            // remove input containers that look like the new-file control
                            const inputs = entriesWrap.querySelectorAll('input[placeholder]');
                            inputs.forEach(inp=>{
                                const ph = (inp.getAttribute('placeholder')||'').toLowerCase();
                                if(ph.indexOf('new-file')!==-1){
                                    const parent = inp.closest('div');
                                    if(parent && entriesWrap.contains(parent)) parent.remove();
                                }
                            });
                            // hide any Create buttons inside entriesWrap
                            const createBtns = Array.from(entriesWrap.querySelectorAll('button'));
                            createBtns.forEach(btn=>{
                                if((btn.textContent||'').trim().toLowerCase()==='create'){
                                    btn.disabled = true;
                                    btn.style.display = 'none';
                                }
                            });
                        }catch(e){}
                    }

                    // If the original frontend defines fetchPath/renderDir later in
                    // its script, patch them when they appear so our static helpers
                    // are used. We poll briefly for the original functions and then
                    // replace them with wrappers that prefer static_* implementations.
                    (function(){
                        let attempts = 0;
                        const maxAttempts = 100; // ~5 seconds at 50ms interval
                        const iv = setInterval(()=>{
                            attempts++;
                            const hasFetch = typeof window.fetchPath === 'function';
                            const hasRender = typeof window.renderDir === 'function';
                            if(hasFetch){
                                try{
                                    const origFetchPath = window.fetchPath;
                                    const origFetchPathWithHash = window.fetchPathWithHash;
                                    window.fetchPath = async function(p){
                                        try{
                                            return await static_fetchPath(p);
                                        }catch(e){
                                            try{ return await origFetchPath(p); }catch(e2){ throw e; }
                                        }
                                    };
                                    window.fetchPathWithHash = async function(p){
                                        try{
                                            return await static_fetchPathWithHash(p);
                                        }catch(e){
                                            try{ return await origFetchPathWithHash(p); }catch(e2){ throw e; }
                                        }
                                    };
                                }catch(e){/*ignore*/}
                            }
                            if(hasRender){
                                try{
                                    // If renderDir exists, call it once to ensure the UI
                                    // initializes using our patched fetchPath.
                                    try{ window.renderDir(''); }catch(e){}
                                    clearInterval(iv);
                                    return;
                                }catch(e){}
                            }
                            if(attempts>maxAttempts){
                                clearInterval(iv);
                            }
                        }, 50);
                    })();

                    // Replace runtime functions after the original script has loaded.
                    window.addEventListener('DOMContentLoaded', ()=>{
                        try{
                            window.fetchPath = static_fetchPath;
                            window.fetchPathWithHash = static_fetchPathWithHash;
                            window.resolveHtmlUrl = static_resolveHtmlUrl;
                        }catch(e){console.warn('Failed to override fetchPath for static view', e)}

                        // Disable editing controls by id to make them visible but greyed out
                        const disabledIds = ['save-btn','delete-btn','graphs-btn','pin-btn','up-btn','fullscreen-btn','open-raw','refresh-btn'];
                        for(const id of disabledIds){
                            const el = document.getElementById(id);
                            if(el) el.disabled = true;
                        }

                        try{ if(typeof renderDir === 'function') renderDir(''); }catch(e){}
                        try{ if(typeof removeCreateControls === 'function') removeCreateControls(); }catch(e){}
                    });

                    // Also patch the global fetch() so that calls to backend
                    // endpoints like /player_root/... succeed when opened via
                    // file:///. We only intercept the specific backend paths
                    // used by the frontend and fall back to the original fetch.
                    (function(){
                        const _origFetch = window.fetch.bind(window);
                        window.fetch = async function(input, init){
                            try{
                                const url = (typeof input === 'string') ? input : (input && input.url) || '';
                                // handle player_root API calls
                                const m = url.match(/[\/]player_root\/?(.*)$/);
                                if(m){
                                    const seg = decodeURIComponent((m[1]||'').replace(/^\/+/, ''));
                                    // renderDir and other callers use endpoints like /player_root/<seg>
                                    // Build a JSON response object similar to server's API
                                    const rel = seg || '';
                                    const data = await static_fetchPath(rel);
                                    return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
                                }
                                // some calls use /player_root/search or other endpoints; handle basic ones
                                if(url.indexOf('/player_root/search') !== -1){
                                    return new Response(JSON.stringify({ results: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
                                }
                                // otherwise fall back to original fetch (which may fail under file://)
                                return _origFetch(input, init);
                            }catch(e){
                                return new Response(JSON.stringify({ error: String(e) }), { status: 500, headers: { 'Content-Type': 'application/json' } });
                            }
                        };
                    })();
                    </script>
                    """)

                    # Substitute escaped manifest JSON into the injection template
                    injection = injection.replace('__MANIFEST_JSON__', manifest_json)

                    # Insert the injection into the <head> so it runs before the
                    # frontend's main script. This allows us to intercept global
                    # fetch() calls that the original script makes during
                    # initialization (renderDir calls fetchPath -> fetch).
                    head_tag = '<head>'
                    if head_tag in frontend_html:
                        static_browser_html = frontend_html.replace(head_tag, head_tag + '\n' + injection, 1)
                    else:
                        # fallback: append at the start
                        static_browser_html = injection + '\n' + frontend_html
                else:
                    # fallback to previous minimal template if reading fails
                    static_browser_html = '<!doctype html><html><body><pre>Failed to load frontend template.</pre></body></html>'

                # Only write/update disconnected_mycelium.html. Do not create a repo-root index.html
                # (the user requested no landing page). By default we won't overwrite an
                # existing disconnected_mycelium.html to preserve manual edits; set
                # FORCE_STATIC_UPDATE=1 in the environment to force an overwrite.
                try:
                    static_path = REPO_ROOT.joinpath(STATIC_SNAPSHOT_FILENAME)
                    # Always overwrite the static snapshot so the file matches the
                    # output of the current run_frontend_api generation logic.
                    static_path.write_text(static_browser_html, encoding='utf-8')
                    print(f"Wrote static snapshot: {static_path}", flush=True)
                except Exception as e:
                    print(f"Failed to write static snapshot file: {e}", flush=True)
        except Exception as e:
                print(f"Unexpected error while ensuring static index: {e}", flush=True)

@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def serve_frontend(path):
    # Build a prioritized list of candidate paths to try for this request.
    # Start by URL-decoding and normalizing the incoming path, then include
    # variants (original, double-decoded, %20->space, basename fallbacks).
    decoded = unquote(path or "")
    decoded = decoded.lstrip('/')
    original = (path or "").lstrip('/')
    candidates = []
    def add_once(p):
        if not p:
            return
        pp = Path(p).as_posix()
        if pp not in candidates:
            candidates.append(pp)

    add_once(decoded)
    add_once(original)
    try:
        double_decoded = unquote(decoded)
        add_once(double_decoded)
    except Exception:
        double_decoded = None
    if "%20" in (path or ""):
        add_once(original.replace('%20', ' '))
    # basename fallbacks (try under Mycelium/ and at repo root)
    bn = Path(decoded).name
    if bn:
        add_once(Path('Mycelium', bn).as_posix())
        add_once(bn)

    # Debug: print attempts
    try:
        my_dir = REPO_ROOT.joinpath('Mycelium')
        my_listing = []
        if my_dir.exists() and my_dir.is_dir():
            my_listing = [p.name for p in sorted(my_dir.iterdir())]
        print(f"serve_frontend: REPO_ROOT='{REPO_ROOT}' candidates={candidates} Mycelium_listing={my_listing}", flush=True)
    except Exception:
        print(f"serve_frontend: REPO_ROOT='{REPO_ROOT}' candidates={candidates}", flush=True)

    # Try each candidate: prefer FRONTEND_DIR, then REPO_ROOT. Use send_file for
    # absolute filesystem paths when possible to avoid send_from_directory quirks.
    for cand in candidates:
        # check frontend dir
        fe_path = FRONTEND_DIR.joinpath(cand)
        if fe_path.exists():
            try:
                # If candidate contains directory parts, serve from that folder
                parts = Path(cand).parts
                if len(parts) > 1:
                    folder = FRONTEND_DIR.joinpath(*parts[:-1])
                    return send_from_directory(str(folder), parts[-1])
                return send_from_directory(str(FRONTEND_DIR), cand)
            except Exception:
                try:
                    return send_file(str(fe_path))
                except Exception:
                    pass

        # check repo root
        repo_path = REPO_ROOT.joinpath(cand)
        if repo_path.exists():
            try:
                return send_file(str(repo_path))
            except Exception:
                try:
                    # fallback: serve using send_from_directory with folder/filename split
                    parts = Path(cand).parts
                    if len(parts) > 1:
                        folder = REPO_ROOT.joinpath(*parts[:-1])
                        return send_from_directory(str(folder), parts[-1])
                    return send_from_directory(str(REPO_ROOT), cand)
                except Exception:
                    pass

    # No candidate matched; raise a NotFound (will become 404)
    from werkzeug.exceptions import NotFound
    raise NotFound()


# Dedicated, robust handler for files under /Mycelium/
@app.route('/Mycelium/<path:subpath>')
def serve_mycelium(subpath):
    # subpath may be percent-encoded; decode and try to serve the file from
    # the repository's Mycelium directory.
    try:
        decoded = unquote(subpath or '')
        decoded = decoded.lstrip('/')
        # candidate under REPO_ROOT/Mycelium/<decoded>
        cand = REPO_ROOT.joinpath('Mycelium', decoded)
        if cand.exists() and cand.is_file():
            return send_file(str(cand))
        # fallback: try using the raw subpath directly
        cand2 = REPO_ROOT.joinpath('Mycelium', subpath)
        if cand2.exists() and cand2.is_file():
            return send_file(str(cand2))
        # fallback: try basename lookup in Mycelium/
        bn = Path(decoded).name
        if bn:
            cand3 = REPO_ROOT.joinpath('Mycelium', bn)
            if cand3.exists() and cand3.is_file():
                return send_file(str(cand3))
    except Exception:
        pass
    from werkzeug.exceptions import NotFound
    raise NotFound()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9002"))

    # Only perform the pre-start port detection in the initial parent process.
    # The Flask/werkzeug reloader spawns a child process (with
    # WERKZEUG_RUN_MAIN='true') which should not repeat the detection logic
    # or prompt the user. Skip the detection there to avoid kill/respawn loops.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # we're in the reloader child; skip pre-start checks
        # respect NO_RELOAD flag (child shouldn't run when NO_RELOAD set)
        no_reload = os.environ.get('NO_RELOAD', '0') == '1'
        if no_reload:
            # Parent intended no-reload; child should not proceed
            raise SystemExit(0)
        # Ensure static frontend index is available in repo root for convenience
        try:
            _ensure_static_index_at_repo_root()
        except Exception:
            pass
        app.run(host="0.0.0.0", port=port, debug=True)
        raise SystemExit(0)

    # Before starting, detect any processes listening on this port and offer to kill them.
    # On macOS, `lsof -i :<port> -sTCP:LISTEN` works well; fall back to netstat if needed.
    # Respect explicit FORCE_KILL, but also auto-enable in CI/non-interactive runs
    env_force_kill = os.environ.get("FORCE_KILL", "0") == "1"
    # Auto-enable force_kill when running in CI or headless/non-interactive shells.
    auto_enable = os.environ.get("HEADLESS", "0") == "1" or os.environ.get("CI", "0") == "1" or os.environ.get("NO_PROMPT", "0") == "1"
    force_kill = env_force_kill or auto_enable or (not __import__('sys').stdin.isatty())

    def find_listeners(p: int):
        import subprocess
        try:
            out = subprocess.check_output(["lsof", "-i", f":{p}", "-sTCP:LISTEN"], stderr=subprocess.DEVNULL, text=True)
            lines = [l for l in out.splitlines() if l.strip()]
            # first line is header; parse subsequent lines to extract PID and COMMAND
            listeners = []
            for ln in lines[1:]:
                parts = ln.split()
                if len(parts) >= 2:
                    cmd = parts[0]
                    pid = parts[1]
                    listeners.append((cmd, int(pid), ln))
            return listeners
        except Exception:
            return []

    listeners = find_listeners(port)
    if listeners:
        print(f"Detected {len(listeners)} process(es) listening on port {port}:")
        for cmd, pid, raw in listeners:
            print(f"  PID={pid} CMD={cmd}  -> {raw}")

        should_kill = False
        if force_kill:
            should_kill = True
        else:
            try:
                # only prompt if running in interactive terminal
                import sys
                if sys.stdin.isatty():
                    ans = input("Kill these processes and continue? [y/N]: ")
                    should_kill = ans.strip().lower() in ("y", "yes")
                else:
                    print("Non-interactive shell; set FORCE_KILL=1 to auto-kill.")
            except Exception:
                pass

        if should_kill:
            import os as _os, signal, time as _time
            # First attempt graceful termination
            for _cmd, _pid, _ in listeners:
                try:
                    print(f"Sending SIGTERM to PID {_pid}...")
                    _os.kill(_pid, signal.SIGTERM)
                except Exception as e:
                    print(f"Failed to SIGTERM PID {_pid}: {e}")

            # wait for the port to free up, with retries
            def still_listening():
                return bool(find_listeners(port))

            wait_seconds = 5
            interval = 0.25
            waited = 0.0
            while waited < wait_seconds and still_listening():
                _time.sleep(interval)
                waited += interval

            # escalate to SIGKILL if something still listens
            if still_listening():
                print("Some processes are still listening after SIGTERM; escalating to SIGKILL")
                for _cmd, _pid, _ in find_listeners(port):
                    try:
                        print(f"Sending SIGKILL to PID {_pid}...")
                        _os.kill(_pid, signal.SIGKILL)
                    except Exception as e:
                        print(f"Failed to SIGKILL PID {_pid}: {e}")

                # final short wait
                _time.sleep(0.5)

            if still_listening():
                print("Port still in use after attempted kills; aborting server start.")
                raise SystemExit(1)
        else:
            print("Not killing existing listeners; aborting server start.")
            raise SystemExit(1)

    # Allow starting without the werkzeug reloader for stable single-process runs
    no_reload = os.environ.get('NO_RELOAD', '0') == '1'
    debug_mode = not no_reload
    # Ensure static frontend index is available in repo root for convenience
    try:
        _ensure_static_index_at_repo_root()
    except Exception:
        pass
    # Optionally run the Wikigraphs generator in the background on startup.
    # Controlled by RUN_WIKIGRAPHS_ON_STARTUP=1 environment variable to avoid
    # surprising behavior in test or CI runs.
    try:
        run_wikigraphs = os.environ.get('RUN_WIKIGRAPHS_ON_STARTUP', '0') == '1'
        if run_wikigraphs:
            import subprocess, time
            script = Path(__file__).resolve().parents[1].joinpath('Python', 'Wikigraphs.py')
            if script.exists():
                cmd = [sys.executable, str(script), '--root', '.']
                # spawn as background process (detached)
                proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                pid_file = REPO_ROOT.joinpath('server_pid.txt')
                try:
                    pid_file.write_text(str(proc.pid) + '\n', encoding='utf-8')
                except Exception:
                    pass
                print(f"Spawned Wikigraphs background process, PID={proc.pid}")
                # small delay to allow process to start
                time.sleep(0.1)
    except Exception as e:
        print(f"Failed to spawn Wikigraphs on startup: {e}")

    app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=debug_mode)
