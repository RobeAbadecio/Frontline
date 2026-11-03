"""Historical roster acceptance: real archive tests live in test_generate and t_frontline."""
import unittest
from tools.frontline import catalog, models

REQUIRED = {
 'uiow':'USS Iowa (BB-61)', 'umss':'USS Missouri (BB-63)',
 'uent':'USS Enterprise (CV-6)', 'uykt':'USS Yorktown (CV-5)', 'uesx':'USS Essex (CV-9)',
 'uflt':'Fletcher-class', 'uclv':'Cleveland-class', 'ulcv':'LCVP Higgins Boat', 'ulcm':'LCM',
 'jyam':'Yamato', 'jmus':'Musashi', 'jnag':'Nagato', 'jakg':'Akagi', 'jkag':'Kaga',
 'jsor':'Soryu', 'jhir':'Hiryu', 'jsho':'Shokaku', 'jzui':'Zuikaku',
 'jmog':'Mogami-class', 'jfub':'Fubuki-class', 'jdai':'Daihatsu-class',
}
class HistoricalNavy(unittest.TestCase):
    def test_entire_roster_is_integrated(self):
        for code,name in REQUIRED.items():
            with self.subTest(ship=name):
                self.assertIn(code,catalog.UNITS)
                u=catalog.UNITS[code]
                self.assertEqual(u['name'],name)
                self.assertEqual(u['food'],0)
                self.assertEqual(u['movement'],'float')
                self.assertIn(u['model'],models.SHIPS)
                self.assertNotIn(u['model'],('battleship','carrier','cruiser','destroyer','landingcraft'))
                self.assertIn(code,catalog.UNITS[u['facility']]['trains'].split(','))
                self.assertIn(u['faction'],('USN','IJN'))
                self.assertTrue(u['description'])
    def test_faction_cards_fit_without_overlap(self):
        for facility in ('fhvy','fesc','flnd'):
            for faction in ('USN','IJN'):
                products=[catalog.UNITS[c] for c in catalog.UNITS[facility]['trains'].split(',') if catalog.UNITS[c]['faction']==faction]
                slots=[u['slot'] for u in products]
                self.assertEqual(len(slots),len(set(slots)))
                self.assertNotIn((3,2),slots) # Kidō Butai / cancel
                self.assertLessEqual(len(slots),10)  # 12 buttons less Rally and Kidō Butai
    def test_roles_and_historical_shapes(self):
        self.assertGreater(catalog.UNITS['uiow']['range'],catalog.UNITS['uflt']['range'])
        self.assertGreater(catalog.UNITS['uflt']['speed'],catalog.UNITS['uclv']['speed'])
        self.assertGreater(catalog.UNITS['uclv']['damage'],catalog.UNITS['uflt']['damage'])
        for model,count in [('iowa',3),('yamato',3),('nagato',4)]:
            self.assertEqual(len(models.BATTERIES[model]),count)
        self.assertNotEqual(models.GEOMETRY['akagi'],models.GEOMETRY['kaga'])
        self.assertNotEqual(models.GEOMETRY['soryu'],models.GEOMETRY['hiryu'])

    def test_new_classes_have_their_own_realistic_models(self):
        from tools.frontline import ships
        art={'unca':'northcarolina','usdk':'southdakota','uind':'independence','ubal':'baltimore','uatl':'atlanta',
             'usum':'sumner','jkon':'kongo','jtak':'takao','jmyo':'myoko','jkgr':'kagero','jaki':'akizuki'}
        self.assertEqual(catalog.NEW_SHIP_ART,art)
        for code,name in art.items():
            with self.subTest(name=name):
                self.assertEqual(catalog.UNITS[code]['model'],name)          # no stand-in hull left
                self.assertIn(name,models.SHIPS)
                self.assertLessEqual(len(ships.triangles(name)),8000)
                self.assertTrue(any(c==ships.TEAM for _,c,_ in ships.triangles(name)),name)   # team-colour band
        # Capital ships carry their own turret layout and AA battery data.
        for model,code,count,alias,aa in [('northcarolina','unca',3,'Gnca','Bnca'),('southdakota','usdk',3,'Gsdk','Bsdk'),
                                          ('kongo','jkon',4,'Gkon','Bkon')]:
            self.assertEqual(len(models.BATTERIES[model]),count)
            abilities=catalog.UNITS[code]['ability'].split(',')
            self.assertIn(alias,abilities);self.assertIn(aa,abilities)
            self.assertNotIn('Fgun',abilities);self.assertNotIn('Fbaa',abilities)
        self.assertIn('independence',models.CARRIERS)                       # carriers capsize
        self.assertEqual(ships.battery_model('kongo'),'naval_twin')

if __name__=='__main__':unittest.main()
