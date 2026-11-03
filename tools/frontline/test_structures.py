"""Engineer build folders, faction fortifications, AA mounts and neutral airfields (catalog data)."""
import unittest
from tools.frontline import catalog, models, pacific, scenario


class EngineerFolders(unittest.TestCase):
    def test_engineer_lists_folders_then_every_structure_once(self):
        builds = catalog.UNITS['fwkr']['builds'].split(',')
        folders = [f[0] for f in catalog.BUILD_FOLDERS]
        self.assertEqual(builds[:len(folders)], folders)
        children = [c for f in catalog.BUILD_FOLDERS for c, _, _ in f[6]]
        self.assertEqual(builds[len(folders):], children)
        self.assertEqual(len(children), len(set(children)))

    def test_generic_structures_left_the_card_but_stay_defined(self):
        builds = catalog.UNITS['fwkr']['builds'].split(',')
        for code in ('fbnk', 'fbn2', 'fcst', 'fdoc', 'faa0'):
            self.assertNotIn(code, builds)
            self.assertIn(code, catalog.UNITS)  # old maps and saves still create them

    def test_folder_codes_are_not_units(self):
        for code, *_ in catalog.BUILD_FOLDERS + [catalog.BUILD_BACK]:
            self.assertNotIn(code, catalog.UNITS)
            self.assertFalse(any(s['alias'] == code for s in catalog.SPELLS))

    def test_folder_slots_and_hotkeys_do_not_collide_within_a_faction(self):
        for folder in catalog.BUILD_FOLDERS:
            for faction in ('USN', 'IJN'):
                seen = {}
                for code, slot, key in folder[6]:
                    if catalog.UNITS[code].get('faction', faction) != faction:
                        continue
                    self.assertNotIn(slot, seen, (folder[0], code, seen.get(slot)))
                    seen[slot] = code
                    self.assertNotEqual(slot, catalog.BUILD_BACK[4])
                keys = [k for c, _, k in folder[6] if catalog.UNITS[c].get('faction', faction) == faction]
                self.assertEqual(len(keys), len(set(keys)), folder[0])

    def test_folders_cover_the_requested_kinds(self):
        by_name = {f[1]: [c for c, _, _ in f[6]] for f in catalog.BUILD_FOLDERS}
        self.assertEqual(set(by_name), {'Base', 'Defences', 'Anti-Aircraft', 'Naval', 'Air'})
        self.assertIn('fair', by_name['Air'])
        self.assertTrue({'uaa2', 'uaa4', 'uaa9', 'jaa2', 'jaa4', 'jaa8'} <= set(by_name['Anti-Aircraft']))


class Fortifications(unittest.TestCase):
    def test_every_fortification_has_a_faction_twin_in_the_same_slot(self):
        pairs = [('upbx', 'jpbx'), ('uaa2', 'jaa2'), ('uaa4', 'jaa4'), ('uaa9', 'jaa8'), ('ucst', 'jcst'), ('urad', 'jrad')]
        for us, ijn in pairs:
            self.assertEqual(catalog.UNITS[us]['faction'], 'USN')
            self.assertEqual(catalog.UNITS[ijn]['faction'], 'IJN')
            self.assertEqual(catalog.UNITS[us]['slot'], catalog.UNITS[ijn]['slot'])

    def test_anti_aircraft_guns_fire_at_aircraft_only_and_scale_by_tier(self):
        for code in ('uaa2', 'jaa2', 'uaa4', 'jaa4', 'uaa9', 'jaa8'):
            self.assertEqual(catalog.UNITS[code]['targets'], 'air')
            self.assertGreater(catalog.UNITS[code]['damage'], 0)
        for light, medium, heavy in (('uaa2', 'uaa4', 'uaa9'), ('jaa2', 'jaa4', 'jaa8')):
            self.assertLess(catalog.UNITS[light]['range'], catalog.UNITS[medium]['range'])
            self.assertLess(catalog.UNITS[medium]['range'], catalog.UNITS[heavy]['range'])
            self.assertLess(catalog.UNITS[light]['cost'], catalog.UNITS[heavy]['cost'])

    def test_every_new_structure_has_its_own_model_with_a_footprint(self):
        for code, u in catalog.FORTIFICATIONS.items():
            self.assertIn(u['model'], models.GEOMETRY, code)
            self.assertGreaterEqual(models.footprint_cells(u['model'])[0], 2, code)
        self.assertIn(catalog.AA_MOUNT_MODEL, models.GEOMETRY)

    def test_the_other_navy_cannot_build_them(self):
        for code, u in catalog.FORTIFICATIONS.items():
            hidden = 0 if u['faction'] == 'IJN' else 1
            self.assertIn(f"SetPlayerTechMaxAllowed(Player({hidden}), '{code}', 0)", scenario.faction_init)

    def test_bots_build_their_own_pillbox_and_count_the_start_bunker(self):
        self.assertNotIn("SetProduce(1, 'fbnk'", scenario.AI_SCRIPT)
        self.assertIn("SetProduce(1, 'jpbx', 0)", scenario.AI_SCRIPT)
        self.assertIn("GetUnitCount('fbnk') + GetUnitCount('jpbx')", scenario.AI_SCRIPT)
        self.assertIn("SetProduce(1, 'upbx', 0)", scenario.AI_SCRIPT_USN)


class AAMount(unittest.TestCase):
    def test_every_crewed_structure_offers_exactly_one_mount(self):
        aliases = {s['alias']: s for s in catalog.SPELLS if s['code'] == 'Fmnt'}
        for code, u in catalog.UNITS.items():
            if u['speed'] != 0:
                continue
            mounts = [a for a in u['ability'].split(',') if a in aliases]
            if code in catalog.AA_MOUNT_EXCLUDED or 'air' in u.get('targets', '').split(','):
                self.assertEqual(mounts, [], code)
            else:
                self.assertEqual(len(mounts), 1, code)
                spell = aliases[mounts[0]]
                self.assertEqual((spell['DataH1'], spell['DataI1']), catalog.AA_MOUNT[u['model']])
                self.assertEqual((spell['DataF1'], spell['DataG1']), catalog.AA_MOUNT_COST)

    def test_mount_buttons_fit_the_card_and_tooltip(self):
        ui = {e[0]: e for e in catalog.SPELL_UI}
        for alias in catalog.AA_MOUNT_ALIAS.values():
            self.assertEqual(ui[alias][4:6], (3, 2))
            self.assertIn('materiel', ui[alias][1])


class NeutralAirfields(unittest.TestCase):
    def test_island_and_pacific_maps_place_neutral_airfields(self):
        script = scenario.MAP_SCRIPT
        self.assertIn("call FrontlineNeutralAirfields()", script)
        self.assertEqual(script.count("CreateUnit(Player(15), 'fair'"), 2)
        pacific_script = scenario.theater_script(script, 'USN')
        self.assertEqual(pacific_script.count("CreateUnit(Player(15), 'fair'"), len(pacific.AIRFIELD_ISLANDS))

    def test_pacific_airfields_stand_on_land(self):
        for x, y in pacific.airfield_sites():
            self.assertTrue(pacific.coast_clear(x, y, 205), (x, y))

    def test_airfields_capture_and_can_still_be_built(self):
        self.assertIn('Fcpt', catalog.UNITS['fair']['ability'].split(','))
        self.assertIn('fair', catalog.UNITS['fwkr']['builds'].split(','))


if __name__ == '__main__':
    unittest.main()
