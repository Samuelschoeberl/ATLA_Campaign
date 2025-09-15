"""Site custom importer to help tests import Mycelium.helpers when temporary
test copies of the package don't include the helpers subpackage.

This module installs a simple meta_path finder that handles imports for
Mycelium.helpers and Mycelium.helpers.<submodule> by loading files from the
development repo's `Mycelium/scripts/helpers` directory.

This is safe and only active when the original helpers files exist on-disk.
"""
from importlib.abc import MetaPathFinder, Loader
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys


class _MyceliumHelpersFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        # handle only Mycelium.helpers and its submodules
        if not fullname.startswith('Mycelium.helpers'):
            return None
        repo_root = Path(__file__).resolve().parent
        src_helpers = repo_root.joinpath('Mycelium').joinpath('scripts').joinpath('helpers')
        if not src_helpers.exists():
            return None

        parts = fullname.split('.')
        # if requesting the package Mycelium.helpers
        if fullname == 'Mycelium.helpers':
            pkg_init = src_helpers.joinpath('__init__.py')
            if pkg_init.exists():
                return spec_from_file_location(fullname, str(pkg_init))
            # create a namespace package spec by pointing to the helpers dir
            spec = spec_from_file_location(fullname, str(pkg_init)) if pkg_init.exists() else None
            return spec

        # submodule e.g. Mycelium.helpers.update_char
        sub = parts[2:]
        file_candidate = src_helpers.joinpath(*sub).with_suffix('.py')
        if file_candidate.exists():
            return spec_from_file_location(fullname, str(file_candidate))
        return None


def _install():
    # avoid duplicate installation
    for f in sys.meta_path:
        if isinstance(f, _MyceliumHelpersFinder):
            return
    sys.meta_path.insert(0, _MyceliumHelpersFinder())


_install()
