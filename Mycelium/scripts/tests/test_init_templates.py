import tempfile
from pathlib import Path
import sys
import shutil


def run_test():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # prepare a pcs_input.md with one PC named TestPC
        pcs = root / 'pcs_input.md'
        pcs.write_text('| name | STR |\n| --- | ---: |\n| TestPC | 12 |\n')

        # copy templates directory into temp repo (source: repository Mycelium/template)
        repo_root = Path(__file__).resolve().parents[2]
        template_src = repo_root.joinpath('Mycelium').joinpath('template')
        template_dst = root.joinpath('Mycelium').joinpath('template')
        template_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(template_src, template_dst)

        # Ensure Python can import the Mycelium package from the repo and the temp root
        sys.path.insert(0, str(repo_root))
        sys.path.insert(0, str(root))

        # Import and run the pipeline helper
        from Mycelium import update_variables_and_rebuild as uv
        rv = uv.main(['--pcs-input', str(pcs), '--root', str(root), '--init-templates', '--create-sheets', '--apply'])

        # Check that Primary_variable file and Character Sheet were created
        pv = root.joinpath('Players Part/PCs/TestPC/TestPC Variable.md')
        cs = root.joinpath('Players Part/PCs/TestPC/Character Sheet.md')
        assert pv.exists() or (root / 'TestPC Variable.md').exists(), 'Primary variable file not created'
        assert cs.exists() or (root / 'TestPC Character Sheet.md').exists(), 'Character Sheet not created'

    print('TEST_INIT_TEMPLATES_OK')


if __name__ == '__main__':
    run_test()
