# Playwright smoke test for Mycelium frontend (Python)
# Requires: pip install playwright requests
# Then: playwright install

import asyncio
import json
import os
import time
from playwright.async_api import async_playwright
import requests
"""Playwright smoke test (synchronous) for Mycelium frontend.

Requirements:
  python -m pip install playwright requests
  playwright install

This script uses the synchronous Playwright API for simplicity and clearer output.
It performs:
  - a server precheck
  - creates a markdown file via the API
  - calls /api/wikigraphs and prints the JSON response
  - performs a move (delete) and undo via /player_root/move

Run with the project's venv python so Playwright + browsers are available.
"""

import os
import time
import json
import requests
from playwright.sync_api import sync_playwright


BASE = os.environ.get('MYCELIUM_BASE', 'http://127.0.0.1:9002')


def precheck_server():
    print('TEST: BASE =', BASE, flush=True)
    try:
        r = requests.get(f"{BASE}/", timeout=5)
        print('TEST: server GET', r.status_code, flush=True)
    except Exception as e:
        print('TEST: server GET failed:', e, flush=True)


def run_smoke_test():
    precheck_server()

    # create a test markdown file via API
    print('Creating MD via API...', flush=True)
    r = requests.post(f"{BASE}/api/create-md-file", json={"folderPath": "", "filename": "smoke_test_by_playwright.md"}, timeout=10)
    print('Create response:', r.status_code, r.text[:400], flush=True)
    if r.status_code == 200:
        j = r.json()
        assert j.get('success')
    else:
        # If file already exists, that's fine for idempotent test runs
        try:
            j = r.json()
            if r.status_code == 400 and j.get('error', '').lower().find('already exists') != -1:
                print('Note: test file already existed; continuing', flush=True)
            else:
                raise AssertionError(f'create-md-file failed: {r.status_code} {r.text}')
        except ValueError:
            raise AssertionError(f'create-md-file failed: {r.status_code} {r.text}')

    # run Playwright to open the frontend and exercise the graphs button
    print('Launching Playwright browser...', flush=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context()
            page = ctx.new_page()
            # msg.text is a string property (not callable) in this playwright version
            page.on('console', lambda msg: print('BROWSER-CONSOLE:', msg.text, flush=True))
            print('Opening frontend page...', flush=True)
            page.goto(f"{BASE}/", timeout=15000)
            time.sleep(0.5)
            print('PAGE TITLE:', page.title(), flush=True)
            # click graphs button if present (best-effort)
            try:
                page.wait_for_selector('#graphs-btn', timeout=3000)
                page.click('#graphs-btn')
            except Exception:
                print('graphs button not present or not clickable, continuing', flush=True)
            browser.close()
    except Exception as e:
        print('Playwright error:', e, flush=True)

    # call the wikigraphs API directly and show returned JSON
    print('Calling /api/wikigraphs...', flush=True)
    resp = requests.post(f"{BASE}/api/wikigraphs", json={"root": ""}, timeout=60)
    print('/api/wikigraphs status:', resp.status_code, flush=True)
    try:
        wikij = resp.json()
        print('wikigraphs JSON:', json.dumps(wikij, indent=2)[:1000], flush=True)
    except Exception:
        print('wikigraphs raw:', resp.text[:1000], flush=True)
        wikij = {}

    # If the API returned a list of written files, HEAD each to ensure they're accessible
    written = wikij.get('written') if isinstance(wikij, dict) else None
    if written:
        from urllib.parse import unquote
        print('Performing HTTP HEAD for generated files...', flush=True)
        for w in written:
            url = BASE + w
            try:
                h = requests.head(url, timeout=5)
                print('HEAD', url, '->', h.status_code, flush=True)
                if not (200 <= h.status_code < 400):
                    # attempt to check filesystem presence as a fallback diagnostic
                    path = unquote(w.lstrip('/'))
                    exists = os.path.exists(path)
                    print('  File exists on disk?', exists, ' path=', path, flush=True)
            except Exception as e:
                print('HEAD failed for', url, e, flush=True)
                path = unquote(w.lstrip('/'))
                print('  Checking local path:', path, 'exists=', os.path.exists(path), flush=True)

    # test move (delete) + undo
    print('Testing move (delete) + undo...', flush=True)
    src = 'Player Root/smoke_test_by_playwright.md'
    dst = 'Player Root/deleted/deleted_smoke_test_by_playwright.md'
    r = requests.post(f"{BASE}/player_root/move", json={"src": src, "dst": dst}, timeout=10)
    print('Move to deleted:', r.status_code, flush=True)
    assert r.status_code == 200
    r2 = requests.post(f"{BASE}/player_root/move", json={"src": dst, "dst": src}, timeout=10)
    print('Restore move:', r2.status_code, flush=True)
    assert r2.status_code == 200


if __name__ == '__main__':
    run_smoke_test()
