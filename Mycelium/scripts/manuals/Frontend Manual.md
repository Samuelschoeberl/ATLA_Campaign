Frontend Manual — Mycelium

Last updated: 2025-09-28

## Purpose

This manual documents the frontend behavior, UI flows, and server APIs that the Mycelium single-file frontend (`Mycelium/scripts/frontend/index.html`) relies on. It also records the recent changes made to improve pins, the Up button, the "Create/Update graphs" flow, and robustness for opening generated HTML artifacts.

## Highlights (what changed)

- Up button semantics: the frontend normalizes the folder stack so repository root is represented as the empty string `""`. The Up button is disabled only when the current normalized path is the empty string.
- Pinned items: pins are stored in `localStorage.mycelium_pins` as an array of objects `{path, label}`. Paths are canonicalized with a `Player Root/` prefix to deduplicate and compare reliably.
- Create MD: A `createMdFile(folder, filename)` helper exists and POSTs `{folderPath, filename}` to `/api/create-md-file`.
- Create/Update graphs: The frontend will POST `{root}` to `/api/wikigraphs`. The server runs `Wikigraphs.py` using the Python executable and returns JSON with `success`, `stdout`, `stderr`, and `code`.
- HTML file linking: The frontend uses `resolveHtmlUrl(seg)` to try a direct repo-relative URL and the `/graphs/...` alias (served by the backend) by performing HEAD requests and selecting the first working URL. Legacy `/vault/...` proxy fallbacks have been removed.
- Sidebar: Pinned list moved into a fixed left sidebar for easier access and drag-reorder enabled.

## Key frontend helpers

- `encodeSegments(p)` — returns URL-encoded path segments (no `Player Root/` prefix) for use in URLs.
- `ensurePlayerRoot(p)` — returns a canonical `Player Root/...` string for any path input.
- `resolveHtmlUrl(seg)` — given encoded path segments (e.g., `Mycelium/scripts/manuals/.../name.html`), it HEADs the direct path and then the `/graphs/...` alias before returning a final URL.
- `createMdFile(folder, filename)` — POSTs to `/api/create-md-file` to create an empty markdown file in the given folder (folder may be `""` for root or a relative folder string).
- `renderDir(p)` — main folder renderer. Accepts `p` as a relative path (no `Player Root/` prefix). Root is `""`.

## Server endpoints used by the frontend

- GET /player_root[/<encoded path>] — returns directory listing or file content JSON. (Existing backend route.)
- POST /api/create-md-file — create a new markdown file. Accepts JSON `{folderPath, filename}` and returns `{success: true, path: "Player Root/..."}` on success.
- POST /api/wikigraphs — run Wikigraphs on the server. Accepts `{root}` where `root` is a relative path (empty or `"PCs/..."`). Returns JSON `{ success, stdout, stderr, code }`.
- POST /player_root/move — atomic server-side move used for Delete/Restore flows.

## How "Create/Update graphs" works (notes for ops)

- The frontend collects the current folder (relative to `Player Root/`), strips file suffixes if needed, and POSTs `{ root: <rel> }` to `/api/wikigraphs`.
- The server locates `Wikigraphs.py` and runs it with `sys.executable` in the repository root; the script writes HTML files (sunburst/treemap) to `Mycelium/scripts/manuals/...` (and possibly nested cluster subfolders).
- The frontend probes the direct repo-relative path first and then `/graphs/Mycelium/scripts/manuals/...` (served by the backend alias) using `resolveHtmlUrl()` and opens the first working URL. The legacy `/vault` proxy is no longer used.

## Troubleshooting

- If the graphs button reports an error or no files appear, try these steps:
  1. Open the server logs and confirm `/api/wikigraphs` returned HTTP 200 and `stdout` showing `Wrote:` entries.
  2. From a shell, HEAD the candidate path(s) reported in stdout via the `vault` proxy, e.g. `HEAD /vault/Mycelium/scripts/manuals/ATLA_Campaignclusters/ATLA_Campaign_wikigraph_sunburst.html`.
  3. If HEAD returns 200, the frontend resolver should find the file; if it returns 404, consider adding a server alias (see next section).

## Recommended follow-ups

- Canonical served path: For predictable links consider either (A) modifying `Wikigraphs.py` to write directly into a canonical served directory (e.g., `Player Root/graphs/`) or (B) adding a small Flask alias route to serve `Mycelium/scripts/manuals/graphs` at `/graphs/`. The latter is low-risk and preserves the generator's current behavior.
- Add small automated smoke tests that programmatically exercise `create-md`, `api/wikigraphs`, and a HEAD check for the generated HTML; these are already part of the manual's smoke-check instructions below.

## Quick smoke-test steps (automated)

Run these from the repository root (where the dev server is running on http://127.0.0.1:9002):

1. Create a test markdown file via the API

curl -v -X POST 'http://127.0.0.1:9002/api/create-md-file' \
 -H 'Content-Type: application/json' \
 -d '{"folderPath":"","filename":"smoke_test_created_by_agent.md"}'

Expect: JSON `{success:true, path: "Player Root/smoke_test_created_by_agent.md"}`

2. Run Wikigraphs for the repository root

curl -v -X POST 'http://127.0.0.1:9002/api/wikigraphs' \
 -H 'Content-Type: application/json' \
 -d '{"root":""}'

Expect: JSON with `success: true` and stdout listing `Wrote:` entries for generated HTML files.

3. HEAD-check a known candidate generated HTML (adjust path if your stdout shows a different cluster)

Use the `/graphs/` alias which maps to `Mycelium/scripts/manuals/` on the server. Example:

curl -I 'http://127.0.0.1:9002/graphs/Mycelium/scripts/manuals/ATLA_Campaignclusters/ATLA_Campaign_wikigraph_sunburst.html' -v

Expect: HTTP/1.1 200 OK

If any step fails, follow the Troubleshooting section above.

## Notes for contributors

- When editing `index.html`, preserve the encoded path helpers `encodeSegments` and `ensurePlayerRoot` — they are relied on by multiple places.
- If you add new backend endpoints, avoid nesting them under `/player_root` because the existing catch-all route may intercept and treat POSTs as file operations.

## Contact

If anything here is unclear, reply in the repository with the exact failing command and server logs; I'll continue with fixes or an optional server alias implementation.

## Playwright smoke test (Python)

Quick setup:

- Install Python packages: pip install playwright requests
- Install browser binaries for Playwright: playwright install

Run the test (ensure the backend server is running and reachable via MYCELIUM_BASE or default http://localhost:5000):

python3 Mycelium/scripts/tests/playwright_smoke_test.py

The test will open the frontend in a headless Chromium, create a file via API, pin the current folder, trigger graph generation, and exercise delete/restore via the atomic move API. Check stdout for progress and any failures.
