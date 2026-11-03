"""Pacific place-name labels (war3mapLabels.txt) against the theatre geography."""
import re
import unittest
from tools.frontline import pacific, place_names

LINE = re.compile(r'^(sea|region|group|island|base) (-?\d+) (-?\d+) (\S.{0,46})$')


class PlaceNames(unittest.TestCase):
    def setUp(self):
        self.rows = place_names.labels()
        self.names = {name: (kind, x, y) for kind, x, y, name in self.rows}

    def test_every_island_shape_is_labelled_on_its_land(self):
        for key, (points, _) in pacific.ISLANDS.items():
            name = place_names.ISLAND_NAMES.get(key, key)
            self.assertIn(name, self.names, key)
            _, x, y = self.names[name]
            self.assertTrue(pacific.land(x, y), name)

    def test_required_places_are_present(self):
        for name in ('Hawaii', 'Pearl Harbor', 'Midway', 'Wake', 'Guam', 'Saipan', 'Tinian', 'Iwo Jima', 'Okinawa',
                     'Philippines', 'Leyte', 'Guadalcanal', 'Solomon Islands', 'New Guinea', 'Rabaul', 'Truk',
                     'Marshall Islands', 'Kwajalein', 'Tarawa', 'Gilbert Islands', 'Aleutian Islands', 'Japan',
                     'Honshu', 'Kyushu', 'Formosa', 'Coral Sea', 'Philippine Sea'):
            self.assertIn(name, self.names)

    def test_seas_lie_on_water_and_labels_inside_the_playable_square(self):
        for kind, x, y, name in self.rows:
            self.assertLessEqual(max(abs(x), abs(y)), pacific.HALF, name)
            if kind == 'sea':
                self.assertFalse(pacific.land(x, y), name)

    def test_bases_sit_on_or_beside_land(self):
        near = lambda x, y: any(pacific.land(x + dx, y + dy) for dx in (-400, 0, 400) for dy in (-400, 0, 400))
        for kind, x, y, name in self.rows:
            if kind == 'base':
                self.assertTrue(near(x, y), name)

    def test_file_lines_match_the_client_parser_contract(self):
        lines = place_names.text().splitlines()
        self.assertTrue(lines[0].startswith('#'))
        self.assertEqual(len(lines) - 1, len(self.rows))
        for line in lines[1:]:
            self.assertRegex(line, LINE)
            self.assertLess(len(line.encode()), 160)
        self.assertLessEqual(len(self.rows), 256)
        self.assertEqual(len(self.names), len(self.rows), 'duplicate label names')

    def test_large_kinds_come_first(self):
        order = [place_names.KINDS.index(kind) for kind, *_ in self.rows]
        self.assertEqual(order, sorted(order))


if __name__ == '__main__':
    unittest.main()
