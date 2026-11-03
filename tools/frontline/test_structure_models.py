"""Defence structures, AA guns, the aa_mount upgrade and the airfield (tools/frontline/structures.py)."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.frontline import models, structures as st
from tools.frontline import gltf_import as gi

REPO=Path(__file__).resolve().parents[2]
TOOLS=REPO/'build/bin'
BUDGET=4000            # triangles per structure, effects included
OWNED=[n for n in st.MODELS if n!='airfield_neutral']

class Structures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data={name:st.mdx(name) for name in st.MODELS}

    def test_final_roster_names_are_registered(self):
        for name in ('pillbox_usn','pillbox_ijn','aa_oerlikon','aa_type98','aa_bofors','aa_type96','aa_m1_90mm',
                     'aa_type88','coastal_usn','coastal_ijn','radar_usn','radar_ijn','aa_mount','airfield'):
            self.assertIn(name,st.MODELS)
            self.assertIn(name,models.GEOMETRY)
        self.assertFalse([n for n in models.GEOMETRY if n.startswith('def_')])

    def test_models_load_in_mdxtool(self):
        if not (TOOLS/'mdxtool').is_file() or not (TOOLS/'mpqtool').is_file():
            self.skipTest('make mdxtool mpqtool first')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'content';args=[str(TOOLS/'mpqtool'),'-mpq',str(Path(tmp)/'test.mpq'),'pack']
            for name,data in self.data.items():
                path=root/f'Emberfield/Models/{name}.mdx';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                args+=[str(path),f'Emberfield/Models/{name}.mdx']
            subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
            for name in self.data:
                with self.subTest(name=name):
                    result=subprocess.run([str(TOOLS/'mdxtool'),'-mpq',str(Path(tmp)/'test.mpq'),'-model',f'Emberfield/Models/{name}.mdx','--info'],
                                          capture_output=True,text=True,check=True)
                    self.assertIn('SEQS: count=8',result.stderr)
                    self.assertIn('CAMS: count=1',result.stderr)

    def test_triangle_budgets(self):
        for name in st.STRUCTURES:
            with self.subTest(name=name):self.assertLess(st.triangle_count(self.data[name]),BUDGET)
        # The airfield only adds its flag and roof bands to the imported art.
        self.assertLess(st.triangle_count(self.data['airfield']),len(st.base_triangles('airfield'))+600)

    def test_every_structure_has_a_team_marker(self):
        for name in OWNED:
            with self.subTest(name=name):self.assertTrue(any(c==gi.TEAM for _,c,_ in st.triangles(name)))

    def test_neutral_airfield_has_no_team_colour(self):
        tris=st.triangles('airfield_neutral')
        self.assertFalse(any(c==gi.TEAM for _,c,_ in tris))
        self.assertTrue(all(max(c)-min(c)<40 for _,c,_ in tris))       # weathered grey
        self.assertEqual(models.footprint_cells('airfield_neutral'),models.footprint_cells('airfield'))
        # The owned airfield's flag and roof bands are team colour, so Player(15) shows them grey.
        team=[t for t in st.triangles('airfield') if t[1]==gi.TEAM]
        self.assertGreater(len(team),40)
        self.assertGreater(max(p[2] for t in team for p in t[0]),100)    # the flag flies above the hangar

    def test_guns_flash_and_recoil_in_attack(self):
        for name in st.GUNS:
            s=st.spec(name)
            with self.subTest(name=name):
                self.assertTrue(s.guns and all(g.muzzles for g in s.guns))
                for tag in (b'Flash',b'Recoil0',b'KGAO'):self.assertIn(tag,self.data[name])

    def test_aa_mount_contract(self):
        tris=st.triangles('aa_mount');lo,hi=gi.bounds(tris)
        self.assertAlmostEqual(lo[2],0,delta=.01)                         # origin at the base of the sandbags
        self.assertLess(max(lo[0],lo[1]),0);self.assertGreater(min(hi[0],hi[1]),0)
        guns=st.spec('aa_mount').guns
        self.assertEqual(len(guns),2)                                       # twin Bofors
        self.assertTrue(all(d[1]<0 and d[2]>0 for g in guns for _,d,_ in g.muzzles))   # front -Y, elevated
        for model,(y,z) in st.aa_mount_table().items():
            with self.subTest(model=model):
                self.assertIn(model,models.GEOMETRY)
                # The mount fits the footprint and rests within reach of the roof at (0, Y).
                self.assertLessEqual(abs(y)+st.MOUNT_RADIUS,models.footprint_cells(model)[0]*models.FOOTPRINT_CELL)
                if model in st.MODELS:self.assertLess(abs(st.surface(model,y)-z),15)

if __name__=='__main__':unittest.main()
