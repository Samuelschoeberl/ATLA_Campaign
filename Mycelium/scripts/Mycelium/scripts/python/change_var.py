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

ROOT = Path('.').resolve()


def discover_variable_root() -> Path:
	# Best-effort discovery: prefer Root.md helper, otherwise Player Root/variable
	try:
		helper_path = ROOT.joinpath('Mycelium', 'scripts', 'Python', 'mycelium_grow_mushroom.py')
		if helper_path.exists():
			spec = importlib.util.spec_from_file_location('mycelium_grow_mushroom', str(helper_path))
			if spec and spec.loader:
				mod = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(mod)
				if hasattr(mod, 'find_root_md'):
					rm = mod.find_root_md()
					if rm:
						try:
							txt = Path(rm).read_text(encoding='utf-8')
							for ln in txt.splitlines():
								s = ln.strip()
								if not s or s.startswith('#'):
									continue
								vault = ROOT.joinpath(s)
								var_dir = vault.joinpath('variable')
								var_dir.mkdir(parents=True, exist_ok=True)
								return var_dir
						except Exception:
							pass
	except Exception:
		pass
	cand = ROOT.joinpath('Player Root', 'variable')
	cand.mkdir(parents=True, exist_ok=True)
	return cand


def write_variable_file(path: Path, value: str, raw: bool = False) -> None:
	if raw:
		path.write_text(str(value) + '\n', encoding='utf-8')
		return
	content = '```markdown\n' + str(value) + '\n\n#variable\n\n```\n'
	path.write_text(content, encoding='utf-8')


def main() -> None:
	p = argparse.ArgumentParser()
	p.add_argument('--name', '-n', required=True)
	p.add_argument('--value', '-v', required=True)
	p.add_argument('--dry-run', action='store_true')
	args = p.parse_args()

	var_root = discover_variable_root()
	matches = list(var_root.rglob(f"{args.name}.md"))
	if matches:
		target = matches[0]
		if args.dry_run:
			print('Would update', target)
		else:
			write_variable_file(target, args.value)
			print('Wrote', target)
	else:
		target = var_root.joinpath(f"{args.name}.md")
		if args.dry_run:
			print('Would create', target)
		else:
			write_variable_file(target, args.value)
			print('Created', target)

	# try to invoke updater in the typical location
	if not args.dry_run:
		upd = ROOT.joinpath('Mycelium', 'scripts', 'python', 'update_sheets_for_var.py')
		if upd.exists():
			try:
				subprocess.run([sys.executable, str(upd), '--name', args.name], check=False)
			except Exception:
				pass


if __name__ == '__main__':
	main()
