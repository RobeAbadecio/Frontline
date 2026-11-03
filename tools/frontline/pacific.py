"""Pacific theatre geography for Frontline: Island Command.

World x grows east, y grows north. Longitude/latitude map linearly onto the
playable square (x = (lon-165)*LON, y = (lat-15)*LAT), so Japan sits in the
north-west, Hawaii in the east and the Solomons in the south. Coasts are
stylized: islands are capsule chains with a gentle wobble, and the Hawaiian
chain is spread out so the US base has room and every channel stays navigable.

Sites are keyed by navy ('USN', 'IJN'), never by player slot: in the USN start
map Player(0) commands the USN at Hawaii; in the IJN map Player(0) commands the
IJN in Japan. scenario.py places headquarters, home ore and outposts from here.
"""
import math

HALF = 24576                         # playable half-size in world units
LON, LAT = HALF / 50.0, HALF / 35.0  # 115E..215E, 20S..50N


def at(lon, lat):
    return (round((lon - 165) * LON), round((lat - 15) * LAT))


def chain(points, width):
    return [at(*p) for p in points], width


# Each island: name -> (polyline in world units, half-width). A single point is a round island.
ISLANDS = {
    # Japan home islands. Honshu is wide enough for a full base at Tokyo/Yokosuka.
    'Kyushu': chain([(130.3, 31.3), (130.8, 33.0), (131.5, 33.6)], 1300),
    'Shikoku': chain([(132.6, 33.5), (134.3, 34.0)], 700),
    'Honshu': chain([(131.0, 34.3), (133.5, 34.8), (135.5, 34.9), (137.0, 35.0), (139.4, 35.6),
                     (140.5, 37.5), (141.0, 39.5), (141.0, 41.0)], 1900),
    'Hokkaido': chain([(140.5, 42.4), (142.5, 43.3), (144.5, 43.5)], 1500),
    'Korea': chain([(126.6, 34.6), (127.0, 37.5), (127.6, 40.0)], 1400),
    'Taiwan': chain([(120.9, 22.2), (121.6, 25.1)], 600),
    'Okinawa': chain([(127.6, 26.1), (128.3, 26.8)], 520),
    'Iwo Jima': chain([(141.3, 24.8)], 480),
    # Saipan and Tinian as one island, long enough for an outpost HQ 600+ from its stockpile.
    'Saipan': chain([(145.5, 15.0), (145.95, 15.9)], 600),
    'Guam': chain([(144.5, 12.6)], 550),
    'Luzon': chain([(120.6, 18.4), (121.3, 16.5), (121.0, 14.6), (123.5, 13.5)], 1500),
    'Visayas': chain([(122.5, 11.0), (124.8, 11.5)], 800),
    'Mindanao': chain([(122.2, 7.5), (125.5, 8.5), (126.2, 7.0)], 1300),
    'Truk': chain([(151.8, 7.4)], 650),
    'Wake': chain([(166.6, 19.3)], 420),
    'Kwajalein': chain([(167.7, 9.0)], 420),
    'Tarawa': chain([(173.0, 1.4)], 420),
    'Midway': chain([(182.0, 28.0), (183.0, 28.5)], 600),
    'New Guinea': chain([(131.5, -1.5), (135.0, -3.2), (141.0, -2.8), (145.0, -4.8), (147.5, -6.5), (150.0, -10.4)], 2200),
    'New Britain': chain([(148.5, -5.6), (152.0, -4.5)], 600),
    'Bougainville': chain([(154.8, -5.6), (155.8, -6.6)], 700),
    'New Georgia': chain([(157.3, -8.2)], 500),
    'Guadalcanal': chain([(159.6, -9.4), (160.6, -9.8)], 650),
    # Hawaii, spread out for play: Oahu carries the US base; channels stay >= 700 wide.
    'Oahu': ([(17000, 4500)], 1750),
    'Kauai': ([(13600, 6000)], 650),
    'Maui': ([(20300, 3300)], 800),
    'Hawaii': ([(22600, 700)], 1500),
}

# Mainland Asia west of a coast that bends from the South China coast to Manchuria.
def asia(x, y):
    lat = y / LAT + 15
    lon = x / LON + 165
    if lat < 21.5:
        coast = 118.3 - (21.5 - lat) * 0.6          # south China coast bends away toward Vietnam
    elif lat < 38:
        coast = 118.3 + (lat - 21.5) * 0.3
    else:
        coast = 123.2 + (lat - 38) * 1.4
    return lon < coast + 0.35 * math.sin(lat * 1.7)


def _segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = 0.0 if not (dx or dy) else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _bounds(points, width):
    pad = width * 1.2
    return (min(p[0] for p in points) - pad, min(p[1] for p in points) - pad,
            max(p[0] for p in points) + pad, max(p[1] for p in points) + pad)


_SHAPES = [(name, points, width, _bounds(points, width)) for name, (points, width) in ISLANDS.items()]


def island_at(x, y):
    """Name of the island covering (x, y), or None."""
    for name, points, width, (x0, y0, x1, y1) in _SHAPES:
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        d = min(_segment_distance(x, y, *points[i], *points[min(i + 1, len(points) - 1)]) for i in range(len(points)))
        wobble = 0.08 * width * math.sin(x / 530 + y / 410) + 0.05 * width * math.sin(x / 190 - y / 230)
        if d < width + wobble:
            return name
    return None


def land(x, y):
    return asia(x, y) or island_at(x, y) is not None


# Headquarters: Yokosuka on Tokyo Bay, and Pearl Harbor on Oahu.
HQ = {'IJN': at(139.6, 35.55), 'USN': (16700, 4300)}
# Home stockpiles (50,000) behind each HQ.
HOME_ORE = {'IJN': at(138.4, 35.35), 'USN': (17500, 5100)}
# Coastal yard spot near each HQ: dry ground with open water about 200 units away, so every
# shipyard footprint fits and its ships find a legal exit. The bot builds and rebuilds here.
SHIPYARD = {'IJN': (-11226, 13527), 'USN': (15400, 4300)}
# Open water at least 600 from any shore, offshore of each yard: fleets and landing craft muster here.
STAGING = {'IJN': (-9887, 13085), 'USN': (14090, 4813)}
# Offshore of each OUTPOST beach, on the home side: water about 300 from the shore, where
# landing craft stop to unload settlers.
LANDING = {'IJN': (-9583, 1453), 'USN': (9584, 8963)}
# Islands each bot settles first with an outpost HQ (the stockpile is in ORE).
OUTPOST = {'IJN': at(145.95, 15.9), 'USN': at(183.0, 28.5)}
# Contested and flank stockpiles (20,000 each), by island.
ORE = [
    ('Kyushu', *at(130.8, 32.6)), ('Okinawa', *at(127.9, 26.4)), ('Iwo Jima', *at(141.3, 24.8)),
    ('Taiwan', *at(121.2, 23.6)), ('Saipan', *at(145.5, 15.0)), ('Guam', *at(144.5, 12.6)),
    ('Luzon', *at(121.2, 16.0)), ('Mindanao', *at(125.0, 8.2)), ('Truk', *at(151.8, 7.4)),
    ('Wake', *at(166.6, 19.3)), ('Kwajalein', *at(167.7, 9.0)), ('Tarawa', *at(173.0, 1.4)),
    ('Midway', *at(182.0, 28.0)), ('New Britain', *at(151.4, -4.7)), ('Bougainville', *at(155.3, -6.1)),
    ('Guadalcanal', *at(160.1, -9.6)), ('New Guinea', *at(141.0, -3.3)), ('Kauai', 13600, 6000),
    ('Hawaii', 22600, 700),
]


def coast_clear(x, y, distance):
    """True when every point within `distance` (sampled on a ring) is land."""
    return land(x, y) and all(land(x + distance * math.cos(a * math.pi / 6), y + distance * math.sin(a * math.pi / 6))
                              for a in range(12))


# The bots raise an outpost on these islands; scenario.py creates their stockpiles itself.
OUTPOST_ISLAND = {'IJN': 'Saipan', 'USN': 'Midway'}


def land_mask(cells, origin, cell):
    """Rows (south to north) of bytearrays, 1 = land, for cell centres origin + (i + 0.5) * cell.
    Rasterized shape by shape inside each bounding box, so a 1648^2 grid stays quick."""
    rows = [bytearray(cells) for _ in range(cells)]
    centre = lambda i: origin + (i + 0.5) * cell
    index = lambda v: int((v - origin) / cell)
    for j in range(cells):
        y = centre(j)
        lat = y / LAT + 15
        coast = 118.3 - (21.5 - lat) * 0.6 if lat < 21.5 else 118.3 + (lat - 21.5) * 0.3 if lat < 38 else 123.2 + (lat - 38) * 1.4
        coast += 0.35 * math.sin(lat * 1.7)
        end = max(0, min(cells, index((coast - 165) * LON) + 1))
        row = rows[j]
        for i in range(end):
            if asia(centre(i), y):
                row[i] = 1
    for name, points, width, (x0, y0, x1, y1) in _SHAPES:
        for j in range(max(0, index(y0)), min(cells, index(y1) + 1)):
            row, y = rows[j], centre(j)
            for i in range(max(0, index(x0)), min(cells, index(x1) + 1)):
                if not row[i] and island_at(centre(i), y) == name:
                    row[i] = 1
    return rows


# Neutral airfields (scenario.FrontlineNeutralAirfields): historical island strips; the first side
# to hold one owns it. Each sits on solid ground beside its island's stockpile.
AIRFIELD_ISLANDS = ('Guadalcanal', 'Iwo Jima', 'Truk', 'Okinawa', 'Guam', 'New Britain')


def airfield_sites():
    sites = []
    for name in AIRFIELD_ISLANDS:
        ox, oy = next((x, y) for n, x, y in ORE if n == name)
        best = None
        for ring in (480, 400, 340, 300, 560):
            for a in range(16):
                x, y = ox + ring * math.cos(a * math.pi / 8), oy + ring * math.sin(a * math.pi / 8)
                # The 288-unit strip square stays on land and clear of the stockpile's footprint.
                if max(abs(x - ox), abs(y - oy)) >= 250 and coast_clear(x, y, 215):
                    best = (round(x), round(y))
                    break
            if best:
                break
        sites.append(best or (ox + 480, oy))
    return sites
