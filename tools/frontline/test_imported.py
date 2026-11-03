"""Contracts for the CC0 mesh importer and third-party credits."""
from pathlib import Path
import struct
import unittest

from tools.frontline import gltf_import as gi, imported, models

REPO=Path(__file__).resolve().parents[2]
MOBILE_BUDGET=1500
INFANTRY_BUDGET=2500      # realistic body + per-role kit
BUILDING_BUDGET=4000      # also the procedural tanks (armor.py)

def geosets(data):
    """(material id, triangle count) per GEOS entry of an emitted MDX."""
    offset=4;out=[]
    while offset<len(data):
        tag,size=data[offset:offset+4],struct.unpack_from('<I',data,offset+4)[0]
        if tag==b'GEOS':
            body=data[offset+8:offset+8+size];g=0
            while g<len(body):
                n=struct.unpack_from('<I',body,g)[0];geo=body[g+4:g+n]
                pcnt=geo.index(b'PCNT');mats=geo.index(b'MATS')
                out.append((struct.unpack_from('<I',geo,mats+12)[0],struct.unpack_from('<I',geo,pcnt+8)[0]))
                g+=n
        offset+=8+size
    return out

class Importer(unittest.TestCase):
    def test_triangle_budgets(self):
        for name in imported.RECIPES:
            limit=(BUILDING_BUDGET if imported.RECIPES[name] is imported.building or imported.RECIPES[name] is imported.tank
                   else INFANTRY_BUDGET if name in imported.INFANTRY+imported.INFANTRY_IJN else MOBILE_BUDGET)
            self.assertLessEqual(len(imported.triangles(name)),limit,name)
        self.assertLessEqual(len(imported.triangles('pine')),600)   # hundreds of palms per map

    def test_team_colour_survives_import(self):
        for name in imported.RECIPES:
            mats={m for m,_ in geosets(models.mesh(name))}
            # Historical USN/IJN aircraft wear fixed national insignia; each navy is one side.
            national=imported.AIRCRAFT.get(name,(0,)*6)[5] in ('usn','ijn')
            # 0 lit palette, 1 team colour; animated units add 2 (blend) and 3 (additive) effects.
            self.assertIn(0,mats,name);self.assertLessEqual(mats,{0,1,2,3},name)
            self.assertEqual(1 in mats,not national,name)

    def test_meshes_fit_existing_footprints(self):
        # Imported art replaces the drawn model only; footprints still come from the box silhouette.
        for name in imported.RECIPES:
            lo,hi=gi.bounds(imported.triangles(name))
            box=models.GEOMETRY[name]
            ref=max(max(abs(b[0])+b[3],abs(b[1])+b[4]) for b in box)
            self.assertLess(max(abs(v) for v in lo[:2]+hi[:2]),ref*1.6+20,name)
            self.assertGreaterEqual(lo[2],-1,name)

    def test_decimation_respects_target(self):
        tris=gi.load('swat',0,('Swat_Body',))
        self.assertLessEqual(len(gi.decimate(tris,500)),500)

    def test_palette_has_room(self):
        for name in list(imported.RECIPES)+list(imported.SCENERY):gi.mdx(name,imported.triangles(name))
        self.assertLess(len(gi._palette),gi.GRID*gi.GRID)

    def test_every_third_party_file_is_credited(self):
        credits=(REPO/'third_party/CREDITS.md').read_text()
        for path in (REPO/'third_party/source').rglob('*'):
            if path.suffix in ('.glb','.jpg'):self.assertIn(path.name,credits,path)

if __name__=='__main__':unittest.main()

class Factions(unittest.TestCase):
    def test_japanese_land_units_mirror_us_stats_with_own_art(self):
        from tools.frontline import catalog,scenario
        for us,(ijn,name,model) in catalog.LAND_IJN.items():
            a,b=catalog.UNITS[us],catalog.UNITS[ijn]
            self.assertEqual({k:v for k,v in a.items() if k not in ('name','model','faction')},
                             {k:v for k,v in b.items() if k not in ('name','model','faction')},ijn)
            self.assertNotEqual(a['model'],b['model'])
            self.assertEqual((a['faction'],b['faction']),('USN','IJN'))
            self.assertIn(f"SetPlayerTechMaxAllowed(Player(1), '{us}', 0)",scenario.faction_init)
            self.assertIn(f"SetPlayerTechMaxAllowed(Player(0), '{ijn}', 0)",scenario.faction_init)
            self.assertIn(f"SetProduce(1, '{ijn}'",scenario.AI_SCRIPT)
            self.assertNotIn(f"SetProduce(1, '{us}'",scenario.AI_SCRIPT)
            self.assertIn(f"SetProduce(1, '{us}'",scenario.AI_SCRIPT_USN)
