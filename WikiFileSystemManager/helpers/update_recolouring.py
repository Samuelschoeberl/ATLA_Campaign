#!/usr/bin/env python3
"""Top-level CLI shim for update_recolouring relocated into the
`WikiFileSystemManager.helpers` package.

This file intentionally contains no implementation. It only delegates to the
packaged helper to avoid duplication and static-import/type errors that
occur when the full implementation exists twice in the repo.
"""
from __future__ import annotations
import sys

try:
    from WikiFileSystemManager.helpers.update_recolouring import main
except Exception as e:
    print('Error: packaged helper WikiFileSystemManager.helpers.update_recolouring is not importable:', e)
    print('You can run the tool directly with: python -m WikiFileSystemManager.helpers.update_recolouring')
    raise SystemExit(2)


if __name__ == '__main__':
    raise SystemExit(main())

    if pc_header_key is None:
        # append header and block for PCs
        lines.append('\n')
        lines.append('# Per PC pastel overrides (generated)\n')
        lines.append('\n')
        lines.extend(gen_lines_pc)
    else:
        # find start of mappings after pc header
        j = pc_header_key + 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        k = j
        while k < len(lines) and MAPPING_RE.match(lines[k]):
            k += 1
        new_block = ['\n', '# Per PC pastel overrides (generated)\n', '\n'] + gen_lines_pc
        lines = lines[:pc_header_key] + new_block + lines[k:]

    new_lines = process_lines(lines)

    # If user asked for a dry-run, print the resulting sorted output.
    if args.dry_run:
        print(''.join(new_lines), end='')

    # If user asked to apply sorting, write backup and file.
    if args.sort:
        bak = path.with_suffix(path.suffix + '.bak')
        try:
            shutil.copy2(path, bak)
            print(f'Backup written to: {bak}')
        except Exception as e:
            print(f'Warning: could not write backup: {e}')

        path.write_text(''.join(new_lines), encoding='utf-8')
        print(f'Wrote sorted mappings to: {path}')
        return 0

    # If neither dry-run nor sort was requested, inform the user and exit.
    print('No action requested. Use --dry-run to preview changes or --sort to apply them.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
