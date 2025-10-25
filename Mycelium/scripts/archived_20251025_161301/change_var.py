from __future__ import annotations

"""Minimal compatibility copy of change_var.py used by tests.
This smaller variant focuses on reliably locating the vault variable folder,
writing a single named variable file, and invoking the updater script.
It's intentionally compact to avoid duplication issues in tests.
"""
from pathlib import Path
import importlib.util
import argparse
import subprocess
import sys
from .common import get_variable_root, write_var_file

ROOT = Path('.').resolve()


def main() -> None:
    # diagnostic info for test debugging
    try:
        print('change_var: __file__=', __file__, file=sys.stderr)
        try:
            text = Path(__file__).read_text(encoding='utf-8')
            for i, ln in enumerate(text.splitlines()[:20], start=1):
                print(f'{i:02d}: {ln}', file=sys.stderr)
        except Exception:
            pass
    except Exception:
        pass
    print('change_var: main() starting', file=sys.stderr)
    print('change_var: ROOT=', ROOT, file=sys.stderr)
    p = argparse.ArgumentParser()
    p.add_argument('--name', '-n', required=True)
    p.add_argument('--value', '-v', required=True)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    var_root = get_variable_root()
    if var_root is None:
        print('ERROR: could not locate variable root')
        return
    matches = list(var_root.rglob(f"{args.name}.md"))
    if matches:
        target = matches[0]
        if args.dry_run:
            print('Would update', target)
        else:
            write_var_file(target, args.value)
            print('Wrote', target)
    else:
        target = var_root.joinpath(f"{args.name}.md")
        if args.dry_run:
            print('Would create', target)
        else:
            write_var_file(target, args.value)
            print('Created', target)

    # try to invoke updater in the typical location
    if not args.dry_run:
        # primary expected location
        upd = ROOT.joinpath('Mycelium', 'scripts', 'python', 'update_sheets_for_var.py')
        # debug: list files under Mycelium/scripts/python to help tests diagnose path issues
        try:
            dbg_dir = ROOT.joinpath('Mycelium', 'scripts', 'python')
            print('Debug: listing', dbg_dir, file=sys.stderr)
            if dbg_dir.exists():
                for c in sorted(dbg_dir.iterdir()):
                    print('  contains:', c.name, file=sys.stderr)
            else:
                print('  (dir missing)', file=sys.stderr)
        except Exception:
            pass
        print('Updater path check:', upd, 'exists=', upd.exists())
        if not upd.exists():
            # fallback: search for any updater script under the repo root
            found = None
            for p in ROOT.rglob('update_sheets_for_var.py'):
                found = p
                break
            if found:
                print('Found updater via rglob fallback:', found)
                upd = found
        if upd.exists():
            # Try to import and call main() from the updater script in-process. This
            # works better for test stubs placed in temp workspaces.
            try:
                spec = importlib.util.spec_from_file_location('update_sheets_for_var_tmp', str(upd))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    # run the module with cwd changed to ROOT so stubs that use Path('.').resolve()
                    # will write into the temporary test workspace.
                    import os
                    old_cwd = Path.cwd()
                    try:
                        os.chdir(str(ROOT))
                        spec.loader.exec_module(mod)
                        mod_main = getattr(mod, 'main', None)
                        if mod_main:
                            try:
                                print('Calling updater.main() in-process')
                                # ensure the updater sees argv similar to CLI invocation
                                old_argv = sys.argv[:]
                                sys.argv = [str(upd), '--name', args.name]
                                try:
                                    mod_main()
                                finally:
                                    sys.argv = old_argv
                                print('Updater.main() completed')
                            except SystemExit:
                                # some stubs may call sys.exit(); ignore
                                print('Updater.main() exited via SystemExit')
                            except Exception as e:
                                print('Updater.main() raised exception:', e)
                    finally:
                        os.chdir(str(old_cwd))
                    # done
                    return
            except Exception as e:
                print('Import-and-run updater failed:', e)
            # fallback to subprocess if import-run didn't work
            try:
                print('Falling back to subprocess invocation of updater:', upd)
                subprocess.run([sys.executable, str(upd), '--name', args.name], check=False, cwd=str(ROOT))
                print('Subprocess updater completed (return ignored)')
            except Exception as e:
                print('Updater subprocess invocation failed:', e)


if __name__ == '__main__':
    main()
