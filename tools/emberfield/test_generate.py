import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('emberfield_generate',Path(__file__).with_name('generate.py'))
gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
from tools.emberfield.catalog import UNITS
REPO=Path(__file__).resolve().parents[2]

class OriginalAssets(unittest.TestCase):
    def test_original_models_survive_engine_parser(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);gen.generate(out,REPO)
            for name in sorted({unit['model'] for unit in UNITS.values()} | {'pine','bolt'}):
                with self.subTest(name=name):
                    r=subprocess.run([str(REPO/'build/bin/mdxtool'),'-mpq',str(out/'War3.mpq'),'-model',f'Emberfield/Models/{name}.mdx','--info'],capture_output=True,text=True,check=True)
                    self.assertIn('TEXS: count=2',r.stderr)
                    self.assertIn('SEQS: count=8',r.stderr)
                    self.assertIn('CAMS: count=1',r.stderr)
            archive=subprocess.check_output([str(REPO/'build/bin/mpqtool'),'-mpq',str(out/'War3.mpq'),'cat','Maps/Emberfield/FirstLight.w3m'])
            self.assertTrue(archive.startswith(b'MPQ'))
            self.assertNotIn('TestUI/',(out/'manifest.json').read_text())

if __name__=='__main__': unittest.main()
