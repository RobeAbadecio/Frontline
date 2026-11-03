"""Generated archive/asset contracts, using native tools rather than retail data."""
from pathlib import Path
import math,struct
import subprocess
import tempfile
import unittest
from tools.frontline import generate as front, catalog, models, pacific
from tools.emberfield import generate as base

REPO=Path(__file__).resolve().parents[2]

class FrontlinePack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.out=Path(cls.tmp.name)
        base.generate(cls.out,REPO,front)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_both_faction_choices_have_visible_menu_ancestors(self):
        import re
        fdf=(self.out/'content/UI/FrameDef/Glue/MainMenu.fdf').read_text()
        for parent in ('ControlLayer','SinglePlayerBackdrop','BattleNetBackdrop','LocalAreaNetworkBackdrop','ExitBackdrop'):
            match=re.search(r'Frame "FRAME" "'+parent+r'" \{ Width ([0-9.]+), Height ([0-9.]+), Anchor TOPLEFT,(-?[0-9.]+),(-?[0-9.]+)',fdf)
            self.assertIsNotNone(match,parent)
            width,height,x,y=map(float,match.groups())
            self.assertGreater(width,0,parent);self.assertGreater(height,0,parent)
            self.assertGreater(x+width,0,parent);self.assertLess(x,.8,parent)

    def test_every_packaged_sound_is_plain_pcm(self):
        # The engine loader rejects WAVE_FORMAT_EXTENSIBLE; Kenney sources are converted.
        sounds=list((self.out/'content/Emberfield/Sounds').glob('*.wav'))
        self.assertGreater(len(sounds),10)
        for wav in sounds:
            self.assertEqual(struct.unpack('<H',wav.read_bytes()[20:22])[0],1,wav.name)

    def test_lan_screens_are_packaged_with_direct_join(self):
        glue=self.out/'content/UI/FrameDef/Glue'
        for name in ('LocalMultiplayerJoin','LocalMultiplayerCreate','GameChatroom','PlayerSlot','MapListBox','MapInfoPane','StandardTemplates'):
            text=(glue/(name+'.fdf')).read_text()
            self.assertNotIn('UI\\Widgets',text,name)  # every retail texture reference is re-skinned
        self.assertIn('DirectAddressEditBox',(glue/'LocalMultiplayerJoin.fdf').read_text())

    def test_placement_cursor_is_original_and_packaged(self):
        root=self.out/'content'
        skin=(root/'UI/war3skins.txt').read_text()
        self.assertIn('PlacementCursor=Emberfield\\Textures\\placement.blp',skin)
        data=(root/'Emberfield/Textures/placement.blp').read_bytes()
        self.assertEqual(data[:4],b'BLP2')
        self.assertTrue((root/'Emberfield/Models/critical.mdx').is_file())
        self.assertIn('cl_same_type_select "1"',(self.out/'autoexec.cfg').read_text())

    def test_roster_uses_no_housing(self):
        for code,u in catalog.UNITS.items():
            self.assertEqual(u.get('food',0),0,code)
            self.assertEqual(u.get('supply',0),0,code)

    def test_mobile_art_faces_engine_positive_x(self):
        for name in models.SHIPS+models.VEHICLES:
            boxes=models.GEOMETRY[name]
            x=max(b[0]+b[3] for b in boxes)-min(b[0]-b[3] for b in boxes)
            y=max(b[1]+b[4] for b in boxes)-min(b[1]-b[4] for b in boxes)
            self.assertGreater(x,y,name)

    def test_ship_air_and_land_models_load(self):
        for name in models.GEOMETRY:
            with self.subTest(name=name):
                result=subprocess.run([str(REPO/'build/bin/mdxtool'),'-mpq',str(self.out/'War3.mpq'),'-model',f'Emberfield/Models/{name}.mdx','--info'],capture_output=True,text=True,check=True)
                # Ships and their turrets carry one sequence per condition (ship_states.py).
                ship=name in models.SHIPS or name in ('naval_triple','naval_twin','yamato_turret','yamato_turret_aa') or name in [n+'_broken' for n in models.turret_damage.TURRETS]
                # Dry docks add 'Stand Alternate' (caisson open, drydock.py).
                expected=len(models.ship_states.SEQUENCES) if ship else len(models.drydock.SEQUENCES) if name in models.drydock.MODELS else len(models.unit_anim.AIR_SEQ) if name in models.AIRCRAFT else 8
                self.assertIn(f'SEQS: count={expected}',result.stderr)
                self.assertIn('CAMS: count=1',result.stderr)
        death=models.ship_states.seq('Death')
        for name in ['battleship','carrier','landingcraft']:
            data=(self.out/f'content/Emberfield/Models/{name}.mdx').read_bytes()
            for tag in (b'KGTR',b'KGRT',b'GEOA',b'KGAO',b'Stand List2 Fire',b'Walk List3 Inferno'):self.assertIn(tag,data,name)
            # The hull is under water by the end of Death (bow-first plunge or capsize).
            self.assertTrue(struct.pack('<I3f',death[2],0,0,-130) in data or struct.pack('<I3f',death[2],0,0,-110) in data,name)

    def test_water_and_land_are_separate_navigable_domains(self):
        path=(self.out/'map/war3map.wpm').read_bytes()
        self.assertEqual(path[:4],b'MP3W')
        def cell(x,y):return path[16+int((y+front.TERRAIN_HALF)/32)*front.CELLS+int((x+front.TERRAIN_HALF)/32)]
        self.assertEqual(cell(0,0)&2,2)
        self.assertEqual(cell(0,0)&64,0)
        self.assertEqual(cell(-3000,3000)&2,0)
        self.assertEqual(cell(-3000,3000)&64,64)
        self.assertEqual(cell(0,0)&8,8) # No building construction at sea.
        # Naval layout: a 2800-radius open ocean at the centre, buildable resource islands.
        for r in range(0,2800,100):
            for a in range(0,360,15):
                x,y=r*math.cos(math.radians(a)),r*math.sin(math.radians(a))
                self.assertEqual(cell(x,y)&64,0,(x,y))
        for x,y in [(2550,3300),(3400,1150),(-2550,-3300),(-3400,-1150)]:
            self.assertEqual(cell(x,y)&(2|8),0,(x,y))

    def test_map_size_is_configurable_and_forests_are_natural_and_clear(self):
        # The playable half-size is a parameter; the pathing grid and terrain follow it.
        self.assertEqual((front.TILES-1)*4,front.CELLS)
        self.assertEqual(front.TERRAIN_HALF,front.MAP_HALF+1792)
        pts=front.forest_points()
        self.assertGreater(len(pts),700)
        for x,y,_,_ in pts:
            self.assertFalse(front.water(x,y),(x,y))                       # every tree stands on land
            self.assertGreater(math.hypot(x+front.HQ,y-front.HQ),500)      # HQ building clearing
            self.assertGreater(math.hypot(x-front.HQ,y+front.HQ),500)
        # Natural: clumped (many neighbours within 150) with open ground between clumps, not a uniform scatter.
        near=sum(1 for x,y,_,_ in pts if sum(1 for u,v,_,_ in pts if 0<math.hypot(x-u,y-v)<250)>=3)
        self.assertGreater(near/len(pts),.4)
        # The layout is point-symmetric: both sides get the same forest.
        self.assertAlmostEqual(sum(1 for x,y,_,_ in pts if y-x>0)/len(pts),.5,delta=.06)
        script=(self.out/'map/war3map.j').read_text()
        self.assertGreater(script.count("CreateDestructable('epin'"),700)
        self.assertIn('FrontlineRimMines',script)

    def test_pacific_theatre_is_navigable_with_named_islands_and_dry_sites(self):
        from collections import deque
        from tools.frontline import pacific
        path=(self.out/'map-pacific/war3map.wpm').read_bytes()
        self.assertEqual(path[:4],b'MP3W')
        n=front.PACIFIC_CELLS
        def index(x,y):return int((y+front.PACIFIC_TERRAIN_HALF)/32)*n+int((x+front.PACIFIC_TERRAIN_HALF)/32)
        def cell(x,y):return path[16+index(x,y)]
        self.assertEqual(cell(0,0)&(2|8|64),2|8)                  # open Pacific: floats only, no building
        # The named theatre: Japan, the Marianas, the Philippines, the Solomons, Midway and Hawaii.
        for name in ['Honshu','Saipan','Guam','Luzon','Mindanao','Guadalcanal','Midway','Oahu','Iwo Jima','Okinawa']:
            x,y=pacific.ISLANDS[name][0][0]
            self.assertEqual(cell(x,y)&(2|8),0,name)
        # Every scenario and island stockpile site is dry, buildable ground.
        sites=list(pacific.HQ.values())+list(pacific.HOME_ORE.values())+list(pacific.OUTPOST.values())+[(x,y) for _,x,y in pacific.ORE]
        for x,y in sites:self.assertEqual(cell(x,y)&(2|8),0,(x,y))
        # Each yard stands on dry ground within 300 of the sea; each staging point is open water.
        for x,y in pacific.SHIPYARD.values():
            self.assertEqual(cell(x,y)&(2|8),0,(x,y))
            self.assertTrue(any(not cell(x+r*math.cos(a/6*math.pi),y+r*math.sin(a/6*math.pi))&64 for r in range(50,301,25) for a in range(12)))
        for x,y in pacific.STAGING.values():
            self.assertTrue(all(not cell(x+r*math.cos(a/6*math.pi),y+r*math.sin(a/6*math.pi))&64 for r in (0,300,600) for a in range(12)))
        # Each outpost HQ fits on its island at least 600 from that island's stockpile
        # (the engine refuses a headquarters closer than 512 to a mine).
        ore={name:(x,y) for name,x,y in pacific.ORE}
        for navy,(x,y) in pacific.OUTPOST.items():
            mx,my=ore[pacific.OUTPOST_ISLAND[navy]]
            self.assertGreaterEqual(math.hypot(x-mx,y-my),600,navy)
            self.assertTrue(pacific.coast_clear(x,y,300),navy)
        for navy,(x,y) in pacific.LANDING.items():
            self.assertTrue(cell(x,y)&2,navy)                                # afloat
            self.assertLess(math.hypot(x-pacific.OUTPOST[navy][0],y-pacific.OUTPOST[navy][1]),2000)
            self.assertTrue(any(not cell(x+r*math.cos(a/6*math.pi),y+r*math.sin(a/6*math.pi))&2 for r in (350,450) for a in range(12)))
        # Both fleets share one ocean: the harbour water off Yokosuka reaches Pearl Harbor.
        def harbour(x,y):
            return next(index(x+r*math.cos(a/8*math.pi),y+r*math.sin(a/8*math.pi)) for r in range(100,4000,64)
                        for a in range(16) if not path[16+index(x+r*math.cos(a/8*math.pi),y+r*math.sin(a/8*math.pi))]&64)
        start,goal=harbour(*pacific.HQ['IJN']),harbour(*pacific.HQ['USN'])
        seen=bytearray(n*n);seen[start]=1;queue=deque([start])
        while queue and not seen[goal]:
            i=queue.popleft()
            for j in (i-1,i+1,i-n,i+n):
                if 0<=j<n*n and not seen[j] and not path[16+j]&64:seen[j]=1;queue.append(j)
        self.assertTrue(seen[goal])

    def test_pacific_is_three_times_wider_with_natural_clear_forests(self):
        from tools.frontline import pacific
        self.assertEqual(pacific.HALF,3*front.MAP_HALF)              # Pacific scale: 3x Island Command
        self.assertEqual(front.PACIFIC_CELLS,(2*front.PACIFIC_TERRAIN_HALF//128)*4)
        self.assertEqual(front.PACIFIC_CELLS//4%32,0)                # terrain chunks: multiples of 32 tiles
        pts=front.pacific_forest_points()
        self.assertGreater(len(pts),2000)
        self.assertLessEqual(len(pts),4000)                         # the map editor's tree limit
        buckets={}
        for x,y,_,_ in pts:
            self.assertTrue(pacific.land(x,y),(x,y))                # every tree stands on land
            for hx,hy in pacific.HQ.values():self.assertGreater(math.hypot(x-hx,y-hy),500)
            buckets.setdefault((int(x//250),int(y//250)),[]).append((x,y))
        # Natural: clumped (many neighbours within 250) with open ground between clumps, not a uniform scatter.
        def neighbours(x,y):
            return sum(1 for dx in (-1,0,1) for dy in (-1,0,1) for u,v in buckets.get((int(x//250)+dx,int(y//250)+dy),())
                       if 0<math.hypot(x-u,y-v)<250)
        self.assertGreater(sum(1 for x,y,_,_ in pts if neighbours(x,y)>=3)/len(pts),.4)
        script=(self.out/'map-pacific/war3map.j').read_text()
        self.assertGreater(script.count("CreateDestructable('epin'"),2000)
        self.assertIn('FrontlineRimMines',script)
        sites=(self.out/'map-pacific/war3mapSites.txt').read_text().split()
        self.assertEqual(sites[:3],['hq0',*map(str,pacific.HQ['USN'])])

    def test_island_command_maps_keep_their_paths_and_pacific_maps_ship_beside_them(self):
        names=set(p.relative_to(self.out/'content').as_posix() for p in (self.out/'content/Maps/Frontline').iterdir())
        for path in [front.MAP_PATH,front.IJN_MAP_PATH,front.SANDBOX_MAP_PATH,front.PACIFIC_MAP_PATH,front.PACIFIC_IJN_MAP_PATH,front.PACIFIC_SANDBOX_MAP_PATH]:
            self.assertIn(path,names)
        # The IJN Pacific start puts Player(0) in Japan.
        self.assertTrue((self.out/'map-pacific-ijn/war3mapSites.txt').read_text().startswith('hq0 %d %d'%pacific.HQ['IJN']))

    def test_ship_bounds_and_portrait_cover_the_hull(self):
        for name in ['carrier','battleship','destroyer','transport']:
            data=models.mesh(name)
            radius,xmin,ymin,zmin,xmax,ymax,zmax=struct.unpack_from('<7f',data,data.index(b'MODL')+8+340)
            # The drawn hull is the smooth class model (ships.GENERIC), not the legacy box layout.
            lo,hi=models.gltf_import.bounds(models.ships.generic(name))
            depth=max(abs(lo[1]),hi[1])
            with self.subTest(name=name):
                self.assertGreaterEqual(radius,depth)
                self.assertLessEqual(ymin,lo[1]+.01)
                self.assertGreaterEqual(ymax,hi[1]-.01)
                self.assertLessEqual(zmin,lo[2]+.01)
                camera=struct.unpack_from('<3f',data,data.index(b'CAMS')+8+84)
                self.assertGreaterEqual(camera[0],depth*2.8-0.01)

    def test_every_produced_unit_has_original_art_and_command_metadata(self):
        root=self.out/'content'
        for code,unit in catalog.UNITS.items():
            self.assertTrue((root/f'Emberfield/Models/{unit["model"]}.mdx').is_file(),code)
            self.assertTrue((root/f'Emberfield/Icons/{unit["model"]}.blp').is_file(),code)
            for product in unit.get('trains','').split(','):
                if product:self.assertIn(product,catalog.UNITS)
        self.assertTrue((root/front.IJN_MAP_PATH).is_file())
        self.assertIn('OfflineAlternateSkirmishMap='+front.PACIFIC_IJN_MAP_PATH,(root/'UI/war3skins.txt').read_text())
        self.assertIn("'uiow'",(root/'Scripts/usn.ai').read_text())
        for code,label,key,symbol,x,y in catalog.SPELL_UI:
            self.assertTrue((root/f'Emberfield/Icons/{symbol}.blp').is_file(),code)
        self.assertIn('Maps/Frontline/IslandCommand.w3m',(self.out/'autoexec.cfg').read_text())
        self.assertTrue((self.out/'War3.mpq').stat().st_size>0)
        self.assertTrue((root/'Emberfield/Fonts/LICENSE_DEJAVU.txt').is_file())

    def test_water_animation_and_icon_mips(self):
        root=self.out/'content/Emberfield'
        for path in [root/f'Textures/water{i:02}.blp' for i in range(8)]+[root/'Icons/airstrike.blp',root/'Icons/Disabled/DISreturn.blp']:
            data=path.read_bytes()
            self.assertEqual(data[:4],b'BLP2')
            self.assertEqual(data[11],1)
            offsets=struct.unpack_from('<16I',data,20)
            lengths=struct.unpack_from('<16I',data,84)
            self.assertGreater(sum(bool(n) for n in offsets),1)
            for offset,length in zip(offsets,lengths):
                if offset:self.assertLessEqual(offset+length,len(data))
        self.assertNotEqual((root/'Textures/water00.blp').read_bytes(),(root/'Textures/water01.blp').read_bytes())

if __name__=='__main__':unittest.main()
