#!/usr/bin/env bash
# Simple reboot helper for the env sync backend and static frontend.
# Stops any running instances, starts fresh processes, writes PID and log files
# and prints a short status + tail of the backend log.

set -eu

# Simple arg parsing: support -f/--follow to tail backend log after restart
FOLLOW=0
for arg in "$@"; do
  case "$arg" in
    -f|--follow)
      FOLLOW=1
      ;;
    -h|--help)
      echo "Usage: $(basename "$0") [-f|--follow]" >&2
      echo "  -f, --follow   follow backend log after restart and colorize important lines" >&2
      exit 0
      ;;
  esac
done

# Resolve paths relative to this script (handles spaces)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Derive project root by locating the ancestor directory named 'Mycelium'
# and using its parent directory as the project root. This is robust to
# different invocation casings (e.g. 'Python' vs 'python') and symlinked
# paths. If the 'Mycelium' ancestor cannot be found, fall back to a
# conservative 3-level traversal.
P="$HERE"
while [ "$P" != "/" ] && [ "$(basename "$P")" != "Mycelium" ]; do
  P=$(dirname "$P")
done
if [ "$(basename "$P")" = "Mycelium" ]; then
  ROOT=$(dirname "$P")
else
  ROOT="$(cd "$HERE/../../.." && pwd)"
fi

BACKEND_SCRIPT="$HERE/env_sync_server.py"
BACKEND_PID="$HERE/env_sync_server.pid"
BACKEND_LOG="$HERE/env_sync_server.log"

FRONTEND_DIR="$ROOT/Mycelium/scripts/frontend"
FRONTEND_PID="$FRONTEND_DIR/frontend.pid"
FRONTEND_LOG="$FRONTEND_DIR/frontend.log"

echo "Rebooting Mycelium env sync (backend + static frontend)"
echo "Project root: $ROOT"

# stop backend if pid file exists
if [ -f "$BACKEND_PID" ]; then
  echo "Killing backend pid $(cat "$BACKEND_PID")"
  kill "$(cat "$BACKEND_PID")" 2>/dev/null || true
  rm -f "$BACKEND_PID"
fi

# best-effort: kill any stray processes by name
pkill -f env_sync_server.py 2>/dev/null || true

sleep 0.05

echo "Starting backend: $BACKEND_SCRIPT (binding to all interfaces)"
nohup python3 "$BACKEND_SCRIPT" --bind-all --port 9001 > "$BACKEND_LOG" 2>&1 &
echo $! > "$BACKEND_PID"

sleep 0.2

# stop frontend static server if pid file exists
if [ -f "$FRONTEND_PID" ]; then
  echo "Killing frontend pid $(cat "$FRONTEND_PID")"
  kill "$(cat "$FRONTEND_PID")" 2>/dev/null || true
  rm -f "$FRONTEND_PID"
fi

pkill -f "http.server" 2>/dev/null || true

sleep 0.05

echo "Starting static frontend serving $FRONTEND_DIR on port 8000 (binding to all interfaces)"
nohup python3 -m http.server 8000 --bind 0.0.0.0 --directory "$FRONTEND_DIR" > "$FRONTEND_LOG" 2>&1 &
echo $! > "$FRONTEND_PID"

# Create a convenient symlink inside the frontend directory so clients can
# browse the whole project (including generated .html files) via the web UI.
# The link will be available at http://<host>:8000/vault/
SYMLINK="$FRONTEND_DIR/vault"
if [ -e "$FRONTEND_DIR" ]; then
  if [ -L "$SYMLINK" ] || [ -e "$SYMLINK" ]; then
    rm -rf "$SYMLINK" || true
  fi
  ln -s "$ROOT" "$SYMLINK" 2>/dev/null || echo "Warning: could not create symlink $SYMLINK -> $ROOT"
  echo "Exposed project root at /vault (http://<host>:8000/vault/)"
else
  echo "Warning: frontend dir $FRONTEND_DIR does not exist; cannot create vault symlink"
fi

sleep 0.15

# Generate sunburst / treemap graphs for each top-level subfolder in the project.
# This runs the Wikigraphs.py generator for every first-level directory under $ROOT
# and places the generated HTML files into that directory (uses --out <dir>).
# Runs in the background and writes per-folder logs into the scripts/python folder.
WIKIGRAPHS_SCRIPT="$ROOT/Mycelium/scripts/manuals/Wikigraphs.py"
if [ -f "$WIKIGRAPHS_SCRIPT" ]; then
  echo "Generating sunburst/treemap graphs for top-level subfolders (background)..."
  for d in "$ROOT"/*/; do
    # skip non-directories and hidden dirs
    [ -d "$d" ] || continue
    base=$(basename "$d")
    case "$base" in
      .git|Mycelium|node_modules|venv|.venv|__pycache__)
        # skip internal or large directories
        continue
        ;;
    esac
    # run generator: output placed into the folder itself
    outdir="$d"
    logfile="$HERE/wikigraphs_${base}.log"
    echo "  Launching graph generation for '$base' -> logs: $logfile"
    # Remove any previously-generated wikigraph HTML files in the target
    # directory so old files don't persist alongside newly-generated ones.
    find "$d" -maxdepth 1 -type f -name '*_wikigraph_*.html' -print -delete || true
  # Call the generator by importing its make_graphs function so we control
  # the root and outdir behavior (the script's main() intentionally
  # writes cluster files into its own folder; importing make_graphs lets
  # us write files directly into each target directory).
  nohup python3 - <<PY > "$logfile" 2>&1 &
import sys, pathlib
sys.path.insert(0, "$ROOT")
try:
  from Mycelium.scripts.manuals.Wikigraphs import make_graphs
except Exception:
  # Fallback: try absolute path import if package import fails
  import runpy
  runpy.run_path("$WIKIGRAPHS_SCRIPT", run_name='__main__')
else:
  make_graphs(pathlib.Path(r"$d"), pathlib.Path(r"$d"), embed_js=True)
PY
  done
  # Also generate graphs for each character folder under Player Root/PCs
  SCHEDULED=""
  PCS_DIR="$ROOT/Player Root/PCs"
  if [ -d "$PCS_DIR" ]; then
    for cd in "$PCS_DIR"/*/; do
      [ -d "$cd" ] || continue
      # avoid duplicates
      case "${SCHEDULED}" in
        *";$cd;"*) continue ;;
      esac
      SCHEDULED+=";$cd;"
      base=$(basename "$cd")
      logfile="$HERE/wikigraphs_PC_${base}.log"
      echo "  Launching graph generation for PC '$base' -> logs: $logfile"
  # Remove previous PC wikigraph HTML files in the PC folder
  find "$cd" -maxdepth 1 -type f -name '*_wikigraph_*.html' -print -delete || true
      nohup python3 - <<PY > "$logfile" 2>&1 &
import sys, pathlib
sys.path.insert(0, "$ROOT")
try:
  from Mycelium.scripts.manuals.Wikigraphs import make_graphs
except Exception:
  import runpy
  runpy.run_path("$WIKIGRAPHS_SCRIPT", run_name='__main__')
else:
  make_graphs(pathlib.Path(r"$cd"), pathlib.Path(r"$cd"), embed_js=True)
PY
    done
  fi

  # Parse variable definition files and attempt to generate graphs in folders
  # mentioned there. We treat non-empty, non-comment lines as candidate folder
  # names and try a few likely locations (root, Player Root, or a shallow
  # search). This makes the generation robust to variable-driven folder names.
  VAR_DIR="$ROOT/Mycelium/data/variable"
  if [ -d "$VAR_DIR" ]; then
    for vf in "$VAR_DIR"/*.md; do
      [ -f "$vf" ] || continue
      # extract non-empty, non-# lines
      while IFS= read -r line; do
        name=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$name" ] && continue
        case "$name" in
          \#* ) continue ;;
        esac
        # try common candidate locations
        candidates=""
        if [ -d "$ROOT/$name" ]; then
          candidates+="$ROOT/$name/;"
        fi
        if [ -d "$ROOT/Player Root/$name" ]; then
          candidates+="$ROOT/Player Root/$name/;"
        fi
        if [ -z "$candidates" ]; then
          # shallow search up to depth 3 for a directory with this basename
          found=$(find "$ROOT" -maxdepth 3 -type d -iname "$name" 2>/dev/null | head -n 1 || true)
          [ -n "$found" ] && candidates+="$found;"
        fi

        IFS=';' read -r -a arr <<< "$candidates"
        for cd in "${arr[@]}"; do
          [ -z "$cd" ] && continue
          case "${SCHEDULED}" in
            *";$cd;"*) continue ;;
          esac
          SCHEDULED+=";$cd;"
          base=$(basename "$cd")
          logfile="$HERE/wikigraphs_var_${base}.log"
          echo "  Launching graph generation for var '$name' -> logs: $logfile"
          # Remove previous wikigraph HTML files referenced by this variable-driven folder
          find "$cd" -maxdepth 1 -type f -name '*_wikigraph_*.html' -print -delete || true
          nohup python3 - <<PY > "$logfile" 2>&1 &
import sys, pathlib
sys.path.insert(0, "$ROOT")
try:
  from Mycelium.scripts.manuals.Wikigraphs import make_graphs
except Exception:
  import runpy
  runpy.run_path("$WIKIGRAPHS_SCRIPT", run_name='__main__')
else:
  make_graphs(pathlib.Path(r"$cd"), pathlib.Path(r"$cd"), embed_js=True)
PY
        done
      done < <(awk 'NF && $1 !~ /^#/{print $0}' "$vf")
    done
  fi
else
  echo "Wikigraphs generator not found at $WIKIGRAPHS_SCRIPT; skipping graph generation"
fi

echo "RESTARTED"
echo "Backend PID: $(cat "$BACKEND_PID" 2>/dev/null || echo 'n/a')"
echo "Frontend PID: $(cat "$FRONTEND_PID" 2>/dev/null || echo 'n/a')"
echo "--- backend log (parsed, last 200 lines) ---"
# Pretty-print recent log lines: parse python http.server request lines and color them.
tail -n 200 "$BACKEND_LOG" 2>/dev/null | awk '
  BEGIN {
    METHOD_GET = "\033[1;34m";  # blue
    METHOD_POST = "\033[1;32m"; # green
    METHOD_OTHER = "\033[1;35m"; # magenta
    STATUS_OK = "\033[1;32m";   # green
    STATUS_REDIRECT = "\033[1;33m"; # yellow
    STATUS_ERROR = "\033[1;31m"; # red
    HILITE = "\033[1;33m";
    ENV_HILITE = "\033[1;32m";
    RESET = "\033[0m";
  }
  {
    line = $0;
    l = tolower(line);
    # extract timestamp in brackets (POSIX-compatible)
    ts = "";
    if (match(line, /\[[^]]+\]/)) {
      ts = substr(line, RSTART+1, RLENGTH-2);
    }
    # extract quoted request like "GET /path HTTP/1.1"
    method = ""; path = ""; status = "";
    if (match(line, /"[^"]+"/)) {
      req = substr(line, RSTART+1, RLENGTH-2);
      n = split(req, parts, " ");
      if (n >= 2) {
        method = parts[1]; path = parts[2];
      }
      # find 3-digit status after the quoted request
      rest = substr(line, RSTART+RLENGTH+1);
      m = split(rest, rparts, " ");
      for (i = 1; i <= m; i++) {
        if (rparts[i] ~ /^[0-9]{3}$/) { status = rparts[i]; break }
      }
    }

    if (method != "") {
      if (method == "GET") mcol = METHOD_GET; else if (method == "POST") mcol = METHOD_POST; else mcol = METHOD_OTHER;
      if (status ~ /^2/) scol = STATUS_OK; else if (status ~ /^3/) scol = STATUS_REDIRECT; else if (status != "") scol = STATUS_ERROR; else scol = "";
      printf "%s %s%-4s%s %s %s%s%s\n", (ts?"["ts"]":""), mcol, method, RESET, path, (scol? (scol status RESET) : ""), "", "";
    }
    else if (l ~ /propagated|updated environmental variable|canonical file/) {
      print HILITE line RESET;
    }
    else if (l ~ /environmental/) {
      print ENV_HILITE line RESET;
    }
    else {
      print line;
    }
  }'

echo "--- recent propagation events (tail + grep context) ---"
# show last 120 lines filtered for propagation markers with a few context lines for readability
grep -E -n "Updated environmental variable|Updated environmental variable files|Propagated|Canonical file|propagated \(|propagated\(" "$BACKEND_LOG" | tail -n 80 || true

echo "--- recent lines mentioning 'environmental' ---"
grep -i -n "environmental" "$BACKEND_LOG" | tail -n 80 || true

echo "Logs:"
echo "  Backend: $BACKEND_LOG"
echo "  Frontend: $FRONTEND_LOG"

echo "Done. Open http://127.0.0.1:8000/index.html for the frontend."

if [ "$FOLLOW" -eq 1 ]; then
  echo "Following backend log (press Ctrl-C to stop). Parsed requests and important lines will be highlighted."
  # Follow in realtime and pretty-print lines similar to the static dump above
  tail -n 0 -F "$BACKEND_LOG" 2>/dev/null | awk '
    BEGIN {
      METHOD_GET = "\033[1;34m";  # blue
      METHOD_POST = "\033[1;32m"; # green
      METHOD_OTHER = "\033[1;35m"; # magenta
      STATUS_OK = "\033[1;32m";   # green
      STATUS_REDIRECT = "\033[1;33m"; # yellow
      STATUS_ERROR = "\033[1;31m"; # red
      HILITE = "\033[1;33m";
      ENV_HILITE = "\033[1;32m";
      RESET = "\033[0m";
    }
      {
        line = $0;
        l = tolower(line);
        ts = "";
        if (match(line, /\[[^]]+\]/)) {
          ts = substr(line, RSTART+1, RLENGTH-2);
        }
        method = ""; path = ""; status = "";
        if (match(line, /"[^"]+"/)) {
          req = substr(line, RSTART+1, RLENGTH-2);
          n = split(req, parts, " ");
          if (n >= 2) { method = parts[1]; path = parts[2]; }
          rest = substr(line, RSTART+RLENGTH+1);
          m = split(rest, rparts, " ");
          for (i = 1; i <= m; i++) { if (rparts[i] ~ /^[0-9]{3}$/) { status = rparts[i]; break } }
        }

        if (method != "") {
          if (method == "GET") mcol = METHOD_GET; else if (method == "POST") mcol = METHOD_POST; else mcol = METHOD_OTHER;
          if (status ~ /^2/) scol = STATUS_OK; else if (status ~ /^3/) scol = STATUS_REDIRECT; else if (status != "") scol = STATUS_ERROR; else scol = "";
          printf "%s %s%-4s%s %s %s%s%s\n", (ts?"["ts"]":""), mcol, method, RESET, path, (scol? (scol status RESET) : ""), "", "";
        }
        else if (l ~ /propagated|updated environmental variable|canonical file/) {
          print HILITE line RESET;
        }
        else if (l ~ /environmental/) {
          print ENV_HILITE line RESET;
        }
        else {
          print line;
        }
      }'
fi
