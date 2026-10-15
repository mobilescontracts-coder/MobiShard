"""Safety tests for new repository scaffolding, separate from the 19 study tests."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from repository_common import ROOT,create_fresh_run,safe_generated_dir


class RepositorySafetyTests(unittest.TestCase):
    def test_generated_output_allowed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            self.assertEqual(safe_generated_dir('build/analysis',root),root/'build/analysis')

    def test_retained_results_protected(self):
        with tempfile.TemporaryDirectory() as t:
            for target in ('results/deployment','results/paper','model','provenance','build','runs'):
                with self.assertRaises(ValueError):safe_generated_dir(target,Path(t))

    def test_no_path_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            for label in ('../deployment','/tmp/run','a/b','','..','x y'):
                with self.assertRaises(ValueError):create_fresh_run(label,Path(t))

    def test_no_existing_run_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);created=create_fresh_run('example',root)
            (created/'sentinel').write_text('keep')
            with self.assertRaises(FileExistsError):create_fresh_run('example',root)
            self.assertEqual((created/'sentinel').read_text(),'keep')

    def test_symlink_output_parent_rejected(self):
        with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as u:
            root=Path(t)
            try:(root/'runs').symlink_to(Path(u),target_is_directory=True)
            except (NotImplementedError,OSError):self.skipTest('No symlink capability')
            with self.assertRaises(ValueError):create_fresh_run('escape',root)

    def test_optimized_python_rejected(self):
        result=subprocess.run([sys.executable,'-O',str(ROOT/'scripts/validate_repository.py')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Do not use Python -O',result.stderr)

if __name__=='__main__':unittest.main()
