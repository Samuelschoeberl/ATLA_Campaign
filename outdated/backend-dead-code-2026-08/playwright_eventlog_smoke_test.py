# Playwright smoke test for event log UI
# Requires: playwright (pip install playwright) and playwright browsers installed
# Usage: python3 -m pytest Mycelium/scripts/tests/playwright_eventlog_smoke_test.py

from playwright.sync_api import sync_playwright
import time
import sys
import os
import subprocess
import signal

# Base URL can be provided via MYCELIUM_BASE_URL env var. If not provided,
# the test will start the local frontend server using run_frontend_api.py and
# target http://127.0.0.1:9002
BASE_URL = os.environ.get('MYCELIUM_BASE_URL', None)

LAUNCHED_SERVER = None

def start_local_server():
    """Start the run_frontend_api.py server as a subprocess and return (proc, url).
    The script listens on port 9002 by default. We return the base URL used.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    runner = os.path.join(repo_root, 'Mycelium', 'scripts', 'Python', 'run_frontend_api.py')
    if not os.path.exists(runner):
        raise RuntimeError(f"run_frontend_api.py not found at expected path: {runner}")
    # start in its repo root so it can resolve paths
    cmd = [sys.executable, runner]
    env = os.environ.copy()
    # run in non-reloader single-process mode for stability
    env['NO_RELOAD'] = '1'
    proc = subprocess.Popen(cmd, cwd=repo_root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # wait for server to be responsive
    base = 'http://127.0.0.1:9002'
    for i in range(60):
        try:
            import urllib.request
            with urllib.request.urlopen(base, timeout=1) as r:
                if r.status == 200:
                    return proc, base
        except Exception:
            time.sleep(0.25)
    # timed out
    # attempt to kill proc and raise
    try:
        proc.kill()
    except Exception:
        pass
    raise RuntimeError('Failed to start local server in time')

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print('Opening frontend...')
        page.goto(BASE_URL)

        # wait for the app to load and for appendEventLog to be available
        for i in range(30):
            try:
                has_func = page.evaluate('typeof appendEventLog === "function"')
                if has_func:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            print('appendEventLog not found on page; aborting')
            sys.exit(2)

        # clear any existing logs
        page.evaluate("(function(){ try{ const body=document.getElementById('event-log-body'); if(body) body.innerHTML=''; const i0=document.getElementById('event-log-compact-item-0'); const i1=document.getElementById('event-log-compact-item-1'); if(i0) i0.textContent='No events'; if(i1) i1.textContent='\u00A0'; localStorage.removeItem('mycelium_event_log_v1'); } catch(e){} })();")

        print('Injecting a general message (A)')
        page.evaluate("appendEventLog('A','First general message','info',[], 'general')")
        time.sleep(0.2)
        print('Injecting a general message (B)')
        page.evaluate("appendEventLog('B','Second general message','info',[], 'general')")
        time.sleep(0.2)
        print('Injecting a debug message (d1)')
        page.evaluate("appendEventLog('d1','debug message 1','info',[], 'debug')")
        time.sleep(0.2)

        # Check compact items: should show two most recent GENERAL messages (B then A), not debug
        item0 = page.locator('#event-log-compact-item-0').inner_text()
        item1 = page.locator('#event-log-compact-item-1').inner_text()
        print('Compact items:', repr(item0), repr(item1))
        assert 'B:' in item0 or 'B' in item0, 'Most recent compact item should show B'

        # Expand the log
        page.locator('#toggle-log').click()
        time.sleep(0.2)

        # Debug message should not be visible until filter toggled
        visible_debug = page.is_visible('.channel-debug:has-text("debug message 1")')
        assert visible_debug is False, 'Debug entry should be hidden by default'

        # Enable debug filter
        page.locator('#filter-debug').check()
        time.sleep(0.2)
        visible_debug_after = page.is_visible('.channel-debug:has-text("debug message 1")')
        assert visible_debug_after is True, 'Debug entry should become visible when filter enabled'

        # Reload page to test persistence
        page.reload()
        time.sleep(0.5)
        # wait for restore
        for i in range(20):
            try:
                ok = page.evaluate('localStorage.getItem("mycelium_event_log_v1") !== null')
                if ok:
                    break
            except Exception:
                pass
            time.sleep(0.2)

        raw = page.evaluate('localStorage.getItem("mycelium_event_log_v1")')
        print('Persisted raw:', raw)
        assert raw is not None and ('d1' in raw or 'B' in raw), 'Persistence should include our entries'

        print('Smoke test passed')
        browser.close()

if __name__ == '__main__':
    try:
        if not BASE_URL:
            print('No MYCELIUM_BASE_URL provided; starting local run_frontend_api.py server...')
            proc, url = start_local_server()
            LAUNCHED_SERVER = proc
            BASE_URL = url
            print('Started local server at', BASE_URL)
        run_test()
    finally:
        if LAUNCHED_SERVER:
            try:
                print('Shutting down local server...')
                LAUNCHED_SERVER.terminate()
                try:
                    LAUNCHED_SERVER.wait(timeout=2)
                except Exception:
                    LAUNCHED_SERVER.kill()
            except Exception:
                pass
