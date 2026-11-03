"""Procedural military silhouettes, built from the existing compact MDX emitter."""
from tools.emberfield import models as base
import struct
import math

def soldier(gun=26):
    return [
        (-8,0,0,6,9,24,7),         # left leg
        (8,0,0,6,9,24,7),          # right leg
        (-8,0,0,3,5,6,5),          # left boot
        (8,0,0,3,5,6,5),           # right boot
        (-9,0,18,3,4,4,5),         # left knee pad
        (9,0,18,3,4,4,5),          # right knee pad
        (0,0,24,17,10,25,7),       # torso
        (0,5,30,14,5,8,7),         # backpack
        (0,8,36,6,3,4,3),          # bedroll on pack
        (0,8,26,6,5,5,3),          # ammo pouch
        (-14,4,26,4,4,6,3),        # left hip pouch
        (14,-4,26,4,4,6,5),        # right hip holster
        (0,0,49,9,9,12,4),         # head (sand/skin)
        (0,0,61,13,12,5,7),        # helmet
        (0,-2,64,9,8,3,7),         # helmet rim
        (0,-8,62,2,3,2,7),         # helmet chin strap
        (-19,0,28,5,6,20,7),       # left arm
        (19,-7,28,5,6,20,7),       # right arm (holds weapon)
        (16,-12,33,3,gun,5,5),     # weapon barrel/stock
        (16,-4,36,4,6,3,3),        # weapon body (wood)
        (16,2,34,2,4,2,1),         # weapon receiver (metal)
        (16,-gun+12,34,2,2,2,5),   # weapon front sight
        (0,11,28,11,4,17,8),       # chest rig (team colour)
        (0,-6,42,5,3,5,8),         # shoulder patch (team)
    ]
def vehicle(gun=42):
    return [
        (-30,0,0,9,44,23,5),           # left track assembly
        (30,0,0,9,44,23,5),            # right track assembly
        (-30,-28,0,2,8,5,1),           # left front road wheel
        (-30,-14,0,2,8,5,1),           # left mid-front wheel
        (-30,0,0,2,8,5,1),             # left mid road wheel
        (-30,14,0,2,8,5,1),            # left mid-rear wheel
        (-30,28,0,2,8,5,1),            # left rear road wheel
        (30,-28,0,2,8,5,1),            # right front road wheel
        (30,-14,0,2,8,5,1),            # right mid-front wheel
        (30,0,0,2,8,5,1),              # right mid road wheel
        (30,14,0,2,8,5,1),             # right mid-rear wheel
        (30,28,0,2,8,5,1),             # right rear road wheel
        (-30,-36,12,4,7,6,1),          # left drive sprocket
        (30,-36,12,4,7,6,1),           # right drive sprocket
        (-30,38,10,4,6,5,1),           # left idler
        (30,38,10,4,6,5,1),            # right idler
        (-30,0,18,2,38,4,1),           # left track guard
        (30,0,18,2,38,4,1),            # right track guard
        (0,0,16,28,39,22,7),           # hull body
        (0,-32,16,18,7,8,7),           # glacis plate (sloped)
        (0,-36,20,12,3,4,7),           # lower glacis
        (0,32,10,14,8,12,7),           # engine deck
        (0,28,22,12,6,2,1),            # engine deck grille
        (0,36,22,8,5,6,5),             # exhaust pipe
        (0,38,26,4,3,3,5),             # exhaust tip
        (-24,20,24,5,8,3,3),           # left stowage box
        (24,20,24,5,8,3,3),            # right stowage box
        (0,0,38,20,22,17,7),           # turret
        (0,-6,55,3,8,3,7),             # mantlet (gun shield)
        (0,-gun/2,49,4,gun/2+15,5,1),  # main gun barrel
        (0,-gun-2,50,5,3,4,1),         # muzzle brake
        (12,-8,42,3,3,3,1),            # coaxial MG
        (0,0,56,10,12,4,8),            # commander's hatch (team colour)
        (-8,8,55,4,4,3,8),             # loader's hatch (team)
        (-14,5,55,2,2,8,1),            # antenna
        (14,-10,55,2,4,2,1),           # periscope
    ]
def ship(length=120,turrets=2,deck=False):
    if deck:
        # Carrier / transport: flight deck or open deck with island superstructure.
        b=[(0,0,-8,36,length,18,5),            # hull below waterline
           (0,0,10,44,length-4,9,3),            # deck (sand/brown for flight deck)
           (31,5,19,10,30,32,1),                # island superstructure
           (31,5,51,4,8,18,5),                  # island mast
           (31,5,69,11,3,3,1),                  # radar platform
           (31,-2,19,3,6,6,5),                  # island bridge windows
           (0,0,20,2,length-15,1,4),            # centreline deck marking
           (0,-90,21,18,7,2,8),                 # bow marking (team colour)
           (-30,-50,21,5,8,5,1),                # port AA gallery
           (30,-50,21,5,8,5,1),                 # starboard AA gallery
           (-30,40,21,5,8,5,1),                 # aft port AA
           (30,40,21,5,8,5,1),                  # aft starboard AA
           (-30,-20,21,3,6,3,1),                # port amidships AA
           (30,-20,21,3,6,3,1),                 # starboard amidships AA
           (0,length-12,10,20,6,6,1)]           # stern gallery
        return b
    # Warship: hull, superstructure, turrets, masts, secondary weapons.
    b=[
        (0,0,-8,29,length,17,5),                # hull below waterline
        (0,-length+10,0,21,27,14,1),            # bow sheer
        (0,-length-2,2,6,4,8,1),                # stem/cutwater
        (0,0,9,30,length-12,10,1),              # main deck
        # Superstructure block (bridge/conning tower).
        (0,0,19,14,34,20,1),                    # main superstructure body
        (0,-8,39,10,18,12,1),                   # bridge level
        (0,-14,39,11,4,8,5),                    # bridge windows (dark)
        (0,-8,51,6,10,8,5),                     # director tower
        (0,-8,59,3,4,18,1),                     # foremast
        (0,-8,77,12,3,3,1),                     # radar/yardarm
        (0,-8,75,4,1,4,1),                      # radar dish
        # Funnel(s).
        (0,20,22,8,10,28,5),                    # main funnel
        (0,20,50,6,8,5,5),                      # funnel cap
        (0,20,42,4,6,2,1),                      # funnel platform
        # Aft superstructure and mainmast.
        (0,45,19,10,18,14,1),                   # aft deckhouse
        (0,55,33,3,3,22,1),                     # mainmast
        (0,55,55,8,2,3,1),                      # mainmast yardarm
        # Team colour: stern ensign flag area.
        (0,-35,22,15,12,5,8),                   # bow turret platform (team colour)
        (0,length-8,10,8,3,5,8),                # stern ensign (team)
        # Secondary weapons and boat cranes.
        (-25,15,22,3,6,5,1),                    # port boat davit
        (25,15,22,3,6,5,1),                     # starboard boat davit
        (-20,-50,22,4,8,4,1),                   # port secondary
        (20,-50,22,4,8,4,1),                    # starboard secondary
        (-20,50,22,4,8,4,1),                    # port aft secondary
        (20,50,22,4,8,4,1),                     # starboard aft secondary
        # Depth charge racks (stern)
        (-12,length-10,10,3,6,3,1),             # port depth charges
        (12,length-10,10,3,6,3,1),              # starboard depth charges
    ]
    # Main turrets with barrels.
    for y in ([-70,65] if turrets>=2 else [-75]):
        b += [
            (0,y,20,19,18,14,1),                # turret barbette/house
            (0,y,34,13,10,4,1),                  # turret roof
            (0,y,38,4,4,2,1),                    # turret rangefinder
            (-6,y-21,27,3,30,4,1),              # port barrel
            (6,y-21,27,3,30,4,1),               # starboard barrel
            (-6,y-52,28,4,3,3,1),               # port muzzle
            (6,y-52,28,4,3,3,1),                # starboard muzzle
        ]
    # Cruiser third turret.
    if turrets>=3:
        b += [(0,85,20,17,16,13,1),(0,85,33,11,9,4,1),(0,85,37,4,4,2,1),(-5,85-18,27,3,26,3,1),(5,85-18,27,3,26,3,1)]
    return b

def house(w=75,d=65,h=60):
    return [
        (0,0,0,w+8,d+8,8,0),           # foundation slab
        (0,0,8,w,d,h,0),               # walls
        # Peaked roof: eave, mid slope, ridge
        (0,0,h+8,w+5,d+5,4,3),         # eave overhang (dark brown)
        (0,0,h+12,w-8,d-8,4,3),        # mid slope
        (0,0,h+16,w-20,d-20,3,3),      # ridge beam
        # Corner posts
        (-w+3,-d+3,8,3,3,h+2,5),       # front-left
        (w-3,-d+3,8,3,3,h+2,5),        # front-right
        (-w+3,d-3,8,3,3,h+2,5),        # rear-left
        (w-3,d-3,8,3,3,h+2,5),         # rear-right
        # Door and windows
        (0,-d-1,10,17,2,35,5),         # doorway (near-black)
        (-w+2,0,h*0.55,2,11,9,6),      # left window (blue-grey)
        (w-2,0,h*0.55,2,11,9,6),       # right window
        (0,d-1,h*0.55,14,2,9,6),       # rear window
        # Team flag/sign
        (-w/2,-d-2,35,10,2,12,8),
    ]
def plane(bomber=False):
    if bomber:
        return [
            (0,0,9,8,42,12,7),         # fuselage
            (0,-8,20,4,12,3,6),         # cockpit glass
            (0,-41,13,7,13,9,1),        # engine cowling
            (0,-48,15,4,4,2,1),         # engine intake
            (0,-52,16,3,5,3,5),         # propeller hub
            (0,-54,16,1,1,8,5),         # propeller disc
            (-38,-5,15,32,13,4,7),      # left wing
            (38,-5,15,32,13,4,7),       # right wing
            (-52,-5,14,8,5,2,8),        # left wing tip (team)
            (52,-5,14,8,5,2,8),         # right wing tip (team)
            (-20,-12,12,3,4,2,5),       # left wing gun bay
            (20,-12,12,3,4,2,5),        # right wing gun bay
            (0,32,15,28,8,3,7),         # tail plane
            (0,34,19,3,11,15,8),        # vertical stabilizer (team)
            (0,40,24,2,4,8,8),          # rudder marking (team)
            (-35,-12,12,6,18,7,5),      # left engine nacelle
            (35,-12,12,6,18,7,5),       # right engine nacelle
            (-35,-28,14,3,4,3,5),       # left propeller hub
            (35,-28,14,3,4,3,5),        # right propeller hub
            (0,5,22,4,8,4,1),           # dorsal turret
            (0,5,26,3,4,3,6),           # turret glass dome
            (0,-20,6,4,8,3,5),          # bomb bay doors
        ]
    return [
        (0,0,9,7,34,11,7),             # fuselage
        (0,-6,20,3,8,3,6),             # cockpit canopy glass
        (0,-35,12,5,9,8,1),            # engine cowling
        (0,-38,14,3,4,2,1),            # engine intake
        (0,-42,14,3,4,3,5),            # propeller hub
        (0,-44,14,1,1,7,5),            # propeller disc
        (-25,-6,15,22,10,3,7),         # left wing
        (25,-6,15,15,10,3,8),          # right wing (team colour)
        (-34,-6,14,6,4,2,8),           # left wing marking (team)
        (-14,-14,12,2,6,2,5),          # left wing gun barrels
        (14,-14,12,2,6,2,5),           # right wing gun barrels
        (0,26,15,20,7,3,7),            # tail plane
        (0,28,18,3,8,14,7),            # vertical stabilizer
        (0,32,24,2,4,8,8),             # rudder marking (team)
        (0,-45,13,24,2,3,5),           # nose gun barrels
        (0,0,21,3,6,3,1),              # cockpit frame
        (0,-2,8,3,6,2,5),              # belly radiator
    ]
GEOMETRY={
'engineer':soldier(12)+[
        (10,-8,0,6,6,8,3),             # toolbox
        (-12,-6,0,4,8,6,1),            # wire cutters/equipment
    ],
 'rifle':soldier()+[
        (14,6,26,2,3,2,3),             # bayonet scabbard
    ],
 'machinegun':soldier(36)+[
        (17,-35,0,2,2,33,5),           # bipod leg
        (17,-38,0,2,2,33,5),           # bipod leg 2
        (16,-22,38,5,4,2,1),           # ammo box on weapon
        (0,12,0,8,6,8,3),              # ammo crate (carried)
    ],
 'tank':vehicle(), 'scoutcar':vehicle(20),
 'artillery':[(0,0,8,24,28,10,7),                    # gun platform/trail
              (-29,0,0,6,12,25,5),(29,0,0,6,12,25,5),# wheels
              (-29,0,0,3,12,3,1),(29,0,0,3,12,3,1),  # wheel hubs
              (-29,0,12,2,12,2,1),(29,0,12,2,12,2,1), # wheel spokes
              (0,28,0,6,6,8,7),                       # trail spade
              (0,32,0,8,4,6,1),                       # spade blade
              (0,0,18,12,14,23,7),                    # gun shield
              (0,0,18,14,2,20,1),                     # shield face plate
              (0,-10,22,8,6,4,1),                     # breech block
              (0,-6,26,4,4,3,1),                      # recoil cylinder
              (0,-33,32,4,44,7,1),                    # barrel
              (0,-62,33,6,5,4,1),                     # muzzle brake
              (0,-64,34,3,3,3,1),                     # muzzle slots
              (0,32,0,4,27,8,7),                      # trail leg
              (0,20,0,3,16,6,7),                      # trail brace
              (0,0,43,6,7,2,8),                       # sight (team colour)
              (-8,4,42,3,3,3,1),                      # elevation hand wheel
              (8,-8,0,6,6,8,3)],                      # ammo ready rack
 'antiair':vehicle(25)+[(-8,-12,58,3,30,7,1),(8,-12,58,3,30,7,1)],
 'heavytank':[(-34,0,0,11,50,26,5),(34,0,0,11,50,26,5),  # tracks
              (-34,-32,0,2,9,5,1),(-34,-16,0,2,9,5,1),(-34,0,0,2,9,5,1),(-34,16,0,2,9,5,1),(-34,32,0,2,9,5,1),  # left road wheels (5)
              (34,-32,0,2,9,5,1),(34,-16,0,2,9,5,1),(34,0,0,2,9,5,1),(34,16,0,2,9,5,1),(34,32,0,2,9,5,1),        # right road wheels (5)
              (-34,-42,14,4,8,6,1),(34,-42,14,4,8,6,1),                   # drive sprockets
              (-34,44,12,4,7,5,1),(34,44,12,4,7,5,1),                     # idlers
              (-34,0,20,2,44,4,1),(34,0,20,2,44,4,1),                     # track guards
              (0,0,18,32,44,24,7),                   # hull body
              (0,-36,18,22,8,10,7),                  # upper glacis (sloped)
              (0,-40,14,18,4,6,7),                   # lower glacis
              (0,36,12,16,10,14,7),                  # engine deck
              (0,32,26,14,6,2,1),                    # engine deck grille
              (0,40,26,10,6,8,5),                    # exhaust muffler
              (0,42,30,4,3,3,5),                     # exhaust tip
              (-28,30,28,6,12,4,1),                  # side skirt left
              (28,30,28,6,12,4,1),                   # side skirt right
              (-28,0,28,3,30,4,7),                   # left hull sponson
              (28,0,28,3,30,4,7),                    # right hull sponson
              (0,0,42,24,28,20,7),                   # turret
              (0,-10,62,4,12,4,7),                   # mantlet (gun shield)
              (0,-52,54,5,52,6,1),                   # main gun
              (0,-82,56,8,6,5,1),                    # muzzle brake
              (0,-84,57,4,3,4,1),                    # muzzle brake slots
              (14,-14,48,3,4,3,1),                   # coaxial MG
              (0,0,63,12,14,5,8),                    # commander's cupola (team)
              (-10,8,62,4,4,3,8),                    # loader's hatch (team)
              (-16,5,62,2,2,9,1),                    # antenna
              (16,-8,62,3,4,2,1),                    # periscope
              (0,22,20,4,22,10,1),                   # rear stowage rack
              (-20,-30,28,4,6,3,3),                  # spare track links left
              (20,-30,28,4,6,3,3)],                  # spare track links right
 'rocketart':[(-28,0,0,8,42,22,5),(28,0,0,8,42,22,5),(0,0,16,24,34,18,7),(0,0,34,14,18,16,7),(-12,-18,42,6,22,8,1),(0,-18,42,6,22,8,1),(12,-18,42,6,22,8,1),(0,0,52,8,8,3,8)],
 'mortar':soldier(10)+[
        (0,12,28,8,8,6,5),             # mortar baseplate
        (0,14,34,4,4,20,1),            # mortar tube
        (0,4,52,3,3,2,8),              # mortar sight (team)
        (0,16,34,6,6,3,1),             # bipod mount
        (-4,18,34,2,2,12,1),           # bipod leg left
        (4,18,34,2,2,12,1),            # bipod leg right
        (8,6,0,6,6,10,3),              # mortar shell rack
    ],
 'commando':soldier(30)+[
        (0,-8,0,5,5,4,5),              # equipment bag
        (0,0,62,8,8,2,8),              # beret (team)
        (-16,6,26,3,6,4,5),            # suppressor on sidearm
        (12,10,0,3,8,4,5),             # demo charge pack
        (0,-4,48,3,4,3,5),             # face paint/scarf
    ],
 'fighter':plane(), 'bomber':plane(True), 'recon':plane(),
 'battleship':ship(145), 'destroyer':ship(95,1), 'cruiser':ship(115,3), 'carrier':ship(160,0,True),
 'landingcraft':[(0,0,-6,30,64,12,5),              # hull
                 (0,0,6,24,56,6,3),                # deck
                 (-28,0,6,4,60,21,1),              # port gunwale
                 (28,0,6,4,60,21,1),               # starboard gunwale
                 (-28,0,22,2,40,4,1),              # port railing
                 (28,0,22,2,40,4,1),               # starboard railing
                 (0,52,6,25,6,25,7),               # wheelhouse
                 (0,52,31,6,5,12,1),               # wheelhouse mast
                 (0,46,10,20,2,18,5),              # wheelhouse front windows
                 (0,52,43,10,2,3,1),               # yardarm
                 (-22,52,27,3,3,6,5),              # port ventilator
                 (22,52,27,3,3,6,5),               # starboard ventilator
                 (-24,40,27,3,3,5,1),              # port MG mount
                 (24,40,27,3,3,5,1),               # starboard MG mount
                 (0,-60,6,25,4,7,8),               # bow ramp (team colour)
                 (0,-58,12,20,2,3,1)],             # ramp hinge
 'transport':ship(110,0,True),
 'headquarters':[
        # L-shaped compound: main wing + side wing
        (0,0,0,103,86,8,0),                # foundation slab
        (0,0,8,95,78,65,0),                # main block walls
        (0,0,73,97,80,4,1),                # flat military roof (metal)
        (0,0,77,90,74,2,7),                # roof edge trim
        # Command tower (rises above main block)
        (30,-20,73,30,28,35,0),            # tower walls
        (30,-20,108,32,30,4,1),            # tower roof
        (30,-20,112,26,24,2,7),            # tower parapet
        (30,-20,90,28,26,3,6),             # tower window band (blue-grey glass)
        # Side wing (L-shape extension)
        (-72,25,0,35,55,50,0),             # wing walls
        (-72,25,50,37,57,3,1),             # wing roof
        (-72,-28,8,3,3,42,5),              # wing corner post
        # Covered entrance portico
        (0,-82,8,35,12,50,0),              # portico walls
        (0,-82,58,40,16,4,1),              # portico roof
        (0,-82,62,36,12,2,7),              # portico fascia
        (-18,-92,8,3,3,50,5),              # portico left column
        (18,-92,8,3,3,50,5),               # portico right column
        (0,-94,30,14,2,22,5),              # entrance door (dark)
        # Windows
        (-95,0,40,2,14,10,6),              # left window 1
        (-95,35,40,2,14,10,6),             # left window 2
        (95,0,40,2,14,10,6),               # right window 1
        (95,35,40,2,14,10,6),              # right window 2
        # Flagpole on tower
        (30,-20,112,2,2,50,1),             # flagpole
        (30,-20,148,27,2,22,8),            # flag (team colour)
        # Radio antenna array
        (-72,60,53,2,2,55,1),              # antenna mast
        (-72,60,108,8,8,3,1),              # antenna crossbar
        (-72,60,100,3,3,2,5),              # antenna insulator
        # Sandbag perimeter
        (-95,-90,0,6,30,18,4),             # front-left sandbags
        (95,-90,0,6,30,18,4),              # front-right sandbags
        (-95,90,0,6,30,18,4),              # rear-left sandbags
        (95,90,0,6,30,18,4),               # rear-right sandbags
        (0,-100,0,50,6,14,4),              # front sandbag wall
        # Map table under portico
        (0,-80,28,18,10,2,3),              # table surface
        (0,-80,8,14,8,20,5),               # table legs
        # Guard booth
        (80,-60,0,12,12,35,7),             # booth walls
        (80,-60,35,14,14,3,3),             # booth roof
        (80,-60,15,3,12,14,5),             # booth opening
        # Vehicle parking area
        (-70,-55,0,18,22,2,1),             # parking pad
    ],
 'barracks':[
        # Long, low Nissen/Quonset-style barracks hut
        (0,0,0,83,73,8,0),                 # foundation slab
        (0,0,8,75,65,40,0),                # main walls (low and wide)
        # Arched roof approximation (stacked layers)
        (0,0,48,77,67,5,1),                # roof base (metal)
        (0,0,53,70,62,5,1),                # roof mid
        (0,0,58,58,54,4,1),                # roof upper
        (0,0,62,42,42,3,1),                # roof peak
        # End walls (semicircular approximation)
        (0,-66,8,60,3,40,0),               # front end wall
        (0,-66,48,50,3,5,1),               # front end cap lower
        (0,-66,53,38,3,4,1),               # front end cap upper
        (0,66,8,60,3,40,0),                # rear end wall
        # Doors (two entrances)
        (-25,-68,10,14,2,28,5),            # front-left door
        (25,-68,10,14,2,28,5),             # front-right door
        # Window row (evenly spaced along sides)
        (-76,-40,28,2,10,8,6),             # left window 1
        (-76,-10,28,2,10,8,6),             # left window 2
        (-76,20,28,2,10,8,6),              # left window 3
        (-76,50,28,2,10,8,6),              # left window 4
        (76,-40,28,2,10,8,6),              # right window 1
        (76,-10,28,2,10,8,6),              # right window 2
        (76,20,28,2,10,8,6),               # right window 3
        (76,50,28,2,10,8,6),               # right window 4
        # Stovepipe chimney
        (30,30,65,4,4,18,5),               # chimney pipe
        (30,30,83,6,6,3,5),                # chimney cap
        # Sandbag fortification (front)
        (0,-80,0,45,6,16,4),               # front sandbag wall
        (-50,-80,0,6,6,20,4),              # front-left corner
        (50,-80,0,6,6,20,4),               # front-right corner
        # Drill/parade ground
        (-50,-50,0,22,18,2,1),             # parade pad
        # Flagpole
        (-70,55,0,2,2,80,1),               # pole
        (-70,55,70,18,2,14,8),             # flag (team colour)
        # Crate stacks
        (35,-60,0,8,8,12,3),               # supply crate 1
        (35,-60,12,7,7,10,3),              # crate 2 stacked
        # Clothesline
        (-60,30,0,2,2,40,5),               # line post 1
        (-60,60,0,2,2,40,5),               # line post 2
        (-60,45,40,2,16,1,4),              # line
    ],
    'depot':[
        # Open-sided lean-to warehouse with loading dock
        (0,0,0,48,43,6,0),                 # concrete pad
        # Back wall and two side walls (front open)
        (0,38,6,40,5,38,0),                # back wall
        (-43,0,6,5,38,38,0),               # left wall
        (43,0,6,5,38,38,0),                # right wall
        # Sloped lean-to roof (higher at back, lower at front)
        (0,0,44,48,45,3,1),                # main roof (metal)
        (0,0,47,44,40,2,1),                # roof upper layer
        (0,-43,38,46,3,3,1),               # front roof edge (lower overhang)
        # Support posts (front face, holding up roof)
        (-35,-38,6,4,4,32,5),              # front-left post
        (0,-38,6,4,4,32,5),                # front-centre post
        (35,-38,6,4,4,32,5),               # front-right post
        # Loading dock (raised platform at front)
        (0,-46,0,38,8,10,1),               # dock platform
        (0,-52,0,34,6,5,1),                # dock ramp
        # Stacked supply crates (inside)
        (25,15,6,14,18,22,3),              # large crate stack
        (25,15,28,12,14,14,3),             # upper crate
        (-25,10,6,10,14,16,3),             # side crate 1
        (-25,-8,6,10,14,20,7),             # side crate 2 (olive)
        # Fuel drums (outside, along wall)
        (50,20,0,6,6,14,5),               # drum 1
        (50,8,0,6,6,14,5),                # drum 2
        (50,-5,0,6,6,14,1),               # drum 3
        # Tarp cover over crates
        (-25,0,36,16,22,2,7),             # tarp
        # Team sign
        (0,39,28,10,2,8,8),               # sign on back wall (team colour)
    ],
 'factory':[
        # Wide industrial shed with saw-tooth roof
        (0,0,0,98,78,8,0),                 # foundation slab
        (0,0,8,90,70,73,0),                # main walls (wide industrial)
        # Saw-tooth roof: three ridges running left-right
        # Ridge 1 (front)
        (0,-35,81,92,20,8,1),              # front bay roof slope
        (0,-35,89,86,16,4,1),              # front ridge
        (0,-50,81,88,4,12,6),              # front clerestory window (blue-grey)
        # Ridge 2 (center)
        (0,0,81,92,20,8,1),               # center bay roof slope
        (0,0,89,86,16,4,1),               # center ridge
        (0,-15,81,88,4,12,6),             # center clerestory window
        # Ridge 3 (rear)
        (0,35,81,92,20,8,1),              # rear bay roof slope
        (0,35,89,86,16,4,1),              # rear ridge
        (0,20,81,88,4,12,6),              # rear clerestory window
        # Assembly bay doors (front, wide)
        (-30,-72,10,28,3,60,1),            # bay door left
        (30,-72,10,28,3,60,1),             # bay door right
        (0,-72,70,60,3,6,1),               # bay door lintel
        # Side loading door
        (91,20,10,3,22,45,1),              # side door
        # Main smokestack
        (65,45,93,12,12,70,5),             # stack body
        (65,45,163,16,16,6,5),             # stack cap
        (65,45,169,10,10,3,1),             # smoke rim
        # Second smaller stack
        (60,-30,93,8,8,50,5),              # secondary stack
        (60,-30,143,12,12,5,5),            # secondary cap
        # Interior crane rail (visible through clerestories)
        (0,0,75,4,60,4,1),                # crane rail
        (-35,0,70,3,3,7,1),               # rail support left
        (35,0,70,3,3,7,1),                # rail support right
        # Metal scrap/material yard
        (-85,35,0,18,22,8,1),             # scrap pile base
        (-85,35,8,14,18,6,1),             # scrap pile mid
        (-85,35,14,8,10,4,1),             # scrap pile top
        # Vehicle exit ramp
        (0,-85,0,26,10,8,1),              # ramp
        # Team-colour sign
        (-92,-72,40,3,2,20,8),            # factory sign
    ],
 'airfield':[
        # Large arched hangar (Quonset/Blister style)
        (0,0,0,118,88,6,0),                # foundation slab
        # Arch approximation: stacked progressively narrower boxes
        (0,0,6,110,80,30,0),               # base walls
        (0,0,36,108,78,10,1),              # lower arch (metal)
        (0,0,46,100,72,10,1),              # mid arch
        (0,0,56,88,64,8,1),                # upper arch
        (0,0,64,70,54,6,1),                # arch shoulder
        (0,0,70,48,40,5,1),                # arch peak
        # Open front bay (hangar doors)
        (0,-82,8,90,3,28,1),               # hangar door frame
        (-55,-82,8,3,3,28,5),              # left door jamb
        (55,-82,8,3,3,28,5),               # right door jamb
        # Rear wall
        (0,82,8,90,3,28,0),                # rear wall
        # Runway
        (0,-115,0,100,22,3,1),             # runway surface
        (0,-75,3,4,60,1,4),                # centre line marking
        (-40,-135,3,3,3,1,4),              # left threshold marker
        (40,-135,3,3,3,1,4),               # right threshold marker
        # Control tower (separate structure)
        (-95,65,0,18,18,70,0),             # tower base
        (-95,65,70,22,22,25,6),            # tower cab (blue-grey glass)
        (-95,65,95,24,24,4,1),             # tower roof
        (-95,65,99,3,3,18,1),              # tower antenna
        (-95,65,117,6,2,3,8),              # tower beacon (team)
        # Windsock
        (75,75,0,2,2,50,1),               # windsock pole
        (75,75,50,3,10,5,4),              # windsock fabric
        # Fuel storage tanks (cylindrical approximation)
        (105,30,0,10,22,16,7),             # fuel tank 1
        (105,-10,0,10,22,16,7),            # fuel tank 2
        (105,10,16,4,4,8,5),              # fuel pipe connector
        # Revetment walls (sandbag blast shields)
        (-95,-55,0,6,25,20,4),             # left revetment
        (95,-55,0,6,25,20,4),              # right revetment
        # Parked vehicle/tractor
        (-65,-50,0,8,12,10,7),             # tractor body
    ],
 'shipyard':[
        # Open boathouse with gabled waterfront
        (0,20,0,70,73,8,0),                # foundation (offset from water)
        # Boathouse frame: open at water side, gabled
        (0,20,8,62,65,50,0),               # main walls
        (0,20,58,64,67,4,3),               # roof eave
        (0,20,62,52,58,4,3),               # roof mid slope
        (0,20,66,36,44,3,3),               # roof ridge
        # Large open bay facing water (no front wall)
        (-63,-46,8,3,3,50,5),              # left door jamb
        (63,-46,8,3,3,50,5),               # right door jamb
        (0,-46,58,64,3,4,1),               # door lintel
        # Workshop windows (sides)
        (-63,10,30,2,12,10,6),             # left window 1
        (-63,40,30,2,12,10,6),             # left window 2
        (63,10,30,2,12,10,6),              # right window 1
        (63,40,30,2,12,10,6),              # right window 2
        # Pier / dry dock rails
        (-90,0,0,18,125,12,3),             # port pier
        (90,0,0,18,125,12,3),              # starboard pier
        # Crane gantry
        (0,60,70,100,5,8,1),               # crane beam
        (-95,60,12,5,5,58,1),              # crane left leg
        (95,60,12,5,5,58,1),               # crane right leg
        (0,60,78,3,3,30,1),               # crane mast
        (0,60,108,6,2,3,8),               # crane top (team)
        (30,60,78,4,4,8,5),               # crane hoist block
        (30,60,70,2,2,8,1),               # hoist cable
        # Slipway (water-side ramp)
        (0,-90,0,60,30,5,1),              # slipway surface
        (0,-120,0,50,8,3,5),              # slipway lip
        # Fuel/supply storage
        (-55,85,0,10,18,14,7),            # storage tank
        (55,85,0,10,18,14,7),             # storage tank 2
        (-55,85,14,6,14,4,5),             # tank cap
        (55,85,14,6,14,4,5),              # tank cap 2
        # Repair scaffolding
        (-50,-30,0,3,3,40,3),             # scaffold post 1
        (-50,-50,0,3,3,40,3),             # scaffold post 2
        (-50,-40,20,4,14,2,3),            # scaffold platform
        (-50,-40,38,4,14,2,3),            # scaffold upper platform
        # Bollards along piers
        (-90,-80,12,4,4,6,1),             # bollard 1
        (-90,80,12,4,4,6,1),              # bollard 2
        (90,-80,12,4,4,6,1),              # bollard 3
        (90,80,12,4,4,6,1),               # bollard 4
    ],
 'bunker':[
        # Low-profile concrete pillbox — squat and angular
        (0,0,0,58,53,6,0),                 # foundation slab
        # Main bunker body: thick concrete, sloped front
        (0,5,6,50,45,30,0),                # main walls (low and thick)
        (0,-20,6,46,10,26,0),              # front glacis (sloped armor)
        # Thick reinforced roof slab
        (0,5,36,54,50,6,1),                # roof slab (metal/concrete)
        (0,5,42,50,46,3,1),                # roof upper cap
        # Firing embrasure (wide horizontal slit)
        (0,-46,22,34,3,6,5),               # main firing slit (dark)
        # Side observation slits
        (-51,0,22,3,12,5,5),               # left slit
        (51,0,22,3,12,5,5),                # right slit
        # Gun barrel protruding from slit
        (0,-62,26,4,30,6,1),               # main gun
        (0,-88,28,6,5,4,1),                # muzzle brake
        # Rear entrance (recessed)
        (0,48,8,14,3,22,5),                # rear door
        # Sandbag ring
        (-58,-50,0,8,20,20,4),             # front-left sandbags
        (58,-50,0,8,20,20,4),              # front-right sandbags
        (-58,35,0,8,20,20,4),              # rear-left sandbags
        (58,35,0,8,20,20,4),               # rear-right sandbags
        (0,-64,0,30,8,16,4),               # front sandbag wall
        # Ventilation pipes
        (-25,30,45,4,4,14,1),              # vent pipe 1
        (25,30,45,4,4,14,1),               # vent pipe 2
        (-25,30,59,6,6,3,1),               # vent cap 1
        (25,30,59,6,6,3,1),                # vent cap 2
        # Ammo crate near rear entrance
        (30,50,0,8,8,10,3),                # ammo crate
        # Camouflage/concealment
        (-38,35,0,2,2,30,7),               # camo pole 1
        (38,35,0,2,2,30,7),                # camo pole 2
        (-38,35,30,3,3,2,7),               # camo net hook 1
        (38,35,30,3,3,2,7),                # camo net hook 2
        # Team marker on roof
        (0,5,45,8,8,2,8),                  # team colour marker
    ],
 'coastalgun':[
        (0,0,0,56,52,12,0),                # concrete emplacement base
        (0,0,12,30,27,32,7),               # gun shield
        (-8,-45,35,4,48,7,1),(8,-45,35,4,48,7,1),  # twin barrels
        (-12,-80,38,5,5,4,1),(12,-80,38,5,5,4,1),  # muzzle brakes
        (0,0,45,10,12,3,8),                # sight housing (team)
        # Rangefinder
        (0,10,48,18,3,3,1),               # rangefinder bar
        (-18,10,48,3,5,5,1),              # rangefinder left optic
        (18,10,48,3,5,5,1),               # rangefinder right optic
        # Sandbag perimeter
        (-52,-55,0,8,18,16,4),            # front-left sandbags
        (52,-55,0,8,18,16,4),             # front-right sandbags
        (-52,40,0,8,18,16,4),             # rear-left sandbags
        (52,40,0,8,18,16,4),              # rear-right sandbags
        # Ammo storage bunker
        (45,35,0,16,14,18,0),             # ammo bunker walls
        (45,35,18,18,16,3,1),             # ammo bunker roof
        (45,22,5,8,2,12,5),               # ammo bunker door
        # Crew shelter
        (-45,35,0,14,16,22,0),            # shelter walls
        (-45,35,22,16,18,3,1),            # shelter roof
    ],
 'watchtower':[
        (0,0,0,30,30,8,0),                 # foundation
        # Four legs (braced)
        (-20,-18,8,4,4,110,3),             # front-left leg
        (20,-18,8,4,4,110,3),              # front-right leg
        (-20,18,8,4,4,110,3),              # rear-left leg
        (20,18,8,4,4,110,3),               # rear-right leg
        # Cross braces
        (-20,0,40,4,14,3,3),              # left brace lower
        (20,0,40,4,14,3,3),               # right brace lower
        (0,-18,65,16,4,3,3),              # front brace upper
        (0,18,65,16,4,3,3),               # rear brace upper
        # Observation platform
        (0,0,110,36,32,4,7),              # platform floor
        (0,0,114,34,30,21,7),             # platform walls
        (0,0,135,38,34,4,3),              # platform roof
        # Railing details
        (-34,0,114,2,28,18,5),            # left railing
        (34,0,114,2,28,18,5),             # right railing
        # Team flag
        (0,-33,115,15,2,12,8),            # flag (team colour)
        # Searchlight
        (18,0,135,6,8,4,1),               # light housing
        (18,-8,137,4,4,2,6),              # light lens
        # Radio antenna
        (-12,0,135,2,2,18,1),             # antenna mast
        (-12,0,153,5,2,2,1),              # antenna crossbar
        # Ladder (front face)
        (0,-22,8,5,2,102,5),              # ladder rail
    ],
 'stockpile':[
        (0,0,0,60,50,35,3),                # main pile base
        (-35,0,35,20,23,27,7),             # left stack (olive)
        (25,0,35,25,24,17,1),              # right stack (steel)
        # Additional crate variety
        (-30,-35,0,14,12,20,3),            # front crate stack
        (-30,-35,20,12,10,14,3),           # front crate upper
        (30,-30,0,16,14,26,7),             # front-right stack (olive)
        # Fuel drums along back
        (-40,40,0,6,6,14,5),              # drum 1
        (-26,40,0,6,6,14,5),              # drum 2
        (-12,40,0,6,6,14,1),              # drum 3
        (2,40,0,6,6,14,5),               # drum 4
        # Tarp covers
        (-35,0,62,24,28,2,7),             # tarp over left stack
        (25,0,52,28,28,2,7),              # tarp over right stack
        # Ammo boxes (small, dark)
        (40,30,0,8,8,10,5),               # ammo box 1
        (50,30,0,8,8,10,5),               # ammo box 2
        (45,30,10,6,6,8,5),               # ammo box stacked
        # Inventory sign
        (55,-45,0,3,3,30,5),              # sign post
        (55,-45,25,10,2,8,8),             # sign board (team)
    ],
 # Engineer field constructions.
 'road':[
        (0,0,0,42,42,2,1),                 # gravel base (steel)
        (0,0,2,38,38,1,4),                 # dirt surface (light sand)
        (-14,0,3,3,32,0.5,5),              # left wheel track
        (14,0,3,3,32,0.5,5),               # right wheel track
        (0,0,3,3,36,0.5,5),                # centre worn line
        (-38,0,0,4,4,4,1),                 # left road marker
        (38,0,0,4,4,4,1),                  # right road marker
        (0,-38,3,8,4,1,8),                 # direction marker (team)
    ],
 'sandbag':[
        (0,0,0,36,16,16,4),                # sandbag stack base (light sand)
        (0,0,16,30,12,10,4),               # sandbag stack upper
        (0,0,26,24,8,6,4),                 # sandbag stack top
        (-28,0,0,8,14,12,4),               # left wing
        (28,0,0,8,14,12,4),                # right wing
        (0,0,0,40,18,3,0),                 # ground pad (olive)
        (0,-14,10,6,4,6,5),                # firing port gap (dark)
        (0,18,0,4,4,18,5),                 # rear brace post
        (0,18,18,8,2,4,8),                 # team marker
    ],
 'barbedwire':[
        (-28,0,0,3,3,30,5),                # left post (near-black)
        (28,0,0,3,3,30,5),                 # right post
        (0,0,0,3,3,30,5),                  # centre post
        (-14,0,10,14,2,1,1),               # lower wire strand left
        (14,0,10,14,2,1,1),                # lower wire strand right
        (-14,0,20,14,2,1,1),               # upper wire strand left
        (14,0,20,14,2,1,1),                # upper wire strand right
        (0,0,15,28,3,1,1),                 # diagonal cross wire
        (0,0,25,28,3,1,1),                 # top cross wire
        (-14,0,30,4,2,2,1),                # left barb cluster
        (14,0,30,4,2,2,1),                 # right barb cluster
        (0,0,28,3,3,4,8),                  # warning marker (team)
    ],
 # Projectiles: Death plays at the hit point as a smoke/dust burst.
 'tracer':[
        (0,0,0,1.5,18,1.5,4),              # bullet core
        (0,-6,0,2.5,8,2.5,4),              # hot trail glow
    ],
 'shell':[
        (0,0,0,3,12,3,5),                  # shell body
        (0,-6,0,2,4,2,1),                  # driving band
        (0,-12,1,4,4,3,4),                 # nose fuse (light)
        (0,8,0,5,6,5,5),                   # smoke trail base
    ],
 'bomb':[
        (0,0,0,5,16,5,5),                  # bomb body
        (0,16,0,8,3,8,1),                  # tail fins
        (0,18,0,3,3,3,1),                  # tail ring
        (0,-8,0,3,3,3,5),                  # nose fuse
        (0,0,0,7,10,7,5),                  # shadow/smoke
    ],
}
INFANTRY=('engineer','rifle','machinegun','mortar','commando')
VEHICLES=('tank','scoutcar','artillery','antiair','heavytank','rocketart')
AIRCRAFT=('fighter','bomber','recon')
SHIPS=('battleship','destroyer','cruiser','carrier','transport','landingcraft')
PROJECTILES={'tracer':(6,.8,6),'shell':(7,5,7),'bomb':(10,8,10)}
# Muzzle flash: Stand opens oversized and settles within 70 ms (bombs drop unlit).
FLASH={'tracer':3.5,'shell':3,'bomb':1}
# Sequences: Stand 0, Walk 1000, Attack 2000, Death 3000, Birth 4000 (ms). Every
# track pins each sequence's ends so keys never interpolate across sequences.
def anim(name):
    if name in PROJECTILES:
        sx,sy,sz=PROJECTILES[name]
        return None,[(0,FLASH[name]),(70,1),(2999,1),(3000,1,1,1),(3100,sx*.6,sy*.6,sz*.6),(3250,sx,sy,sz),(3500,sx*1.4,sy*1.4,sz*1.4),(3750,sx*1.8,sy*1.8,sz*1.8),(3999,0),(4000,1)]
    bob=4 if name in INFANTRY else 1.5 if name in VEHICLES else 0
    recoil=3 if name in INFANTRY else 9 if name in VEHICLES else 5 if name in SHIPS+('naval_triple','naval_twin') else 0
    sink=-190 if name in SHIPS+('naval_triple','naval_twin') else -230 if name in AIRCRAFT else -28 if name in INFANTRY+VEHICLES else -60
    keys=[(0,0,0,0)]
    if name in AIRCRAFT:keys+=[(500,0,0,6),(999,0,0,0),(1000,0,0,0),(1500,0,0,6),(1999,0,0,0)]
    else:keys+=[(999,0,0,0),(1000,0,0,0),(1250,0,0,bob),(1500,0,0,0),(1750,0,0,bob),(1999,0,0,0)]
    keys+=[(2000,0,0,0),(2070,0,recoil,0),(2400,0,0,0),(2999,0,0,0),(3000,0,0,0),(3999,0,0,sink),(4000,0,0,0),(7999,0,0,0)]
    return [(t,-y,x,z) for t,x,y,z in keys],None

# Small shared details preserve the two-material batching of each silhouette.
for _name in SHIPS:
    if _name=='landingcraft':continue
    GEOMETRY[_name]+=[(-17,y,30,4,9,4,3) for y in (-34,30)]
    GEOMETRY[_name]+=[(17,y,30,4,9,4,3) for y in (-34,30)]
    GEOMETRY[_name]+=[(x,-33,42,3,1,5,5) for x in (-8,0,8)]
    GEOMETRY[_name]+=[(x,25,57,2,2,15,1) for x in (-9,9)]
for _name in VEHICLES:
    GEOMETRY[_name]+=[(x,y,2,10,5,12,1) for x in (-30,30) for y in (-26,-9,9,26)]
# Per-building front details (unique shapes replaced house() shutters)
GEOMETRY['headquarters']+=[(x,-73,30,6,2,14,5) for x in (-40,0,40)]   # HQ glacis shutters
GEOMETRY['factory']+=[(x,-70,35,8,2,12,5) for x in (-50,0,50)]        # factory bay shutters

# Historical hulls are original geometry, sharing only true sister-class models.
from tools.frontline import historical_models as historical
GEOMETRY.update(historical.GEOMETRY)
from tools.frontline import yamato
BATTERIES=dict(historical.BATTERIES)
BATTERIES['yamato']=list(yamato.BATTERIES)
SHIPS+=historical.SHIPS
# Single-engine carrier aircraft, distinct spans/cockpits and radial noses.
for name,span,length,canopy in [('wildcat',26,34,10),('dauntless',34,39,20),('avenger',39,45,23),('zero',31,36,12),('val',33,40,22),('kate',37,44,23)]:
    GEOMETRY[name]=[(0,0,9,6,length,11,1),(0,-length+3,11,8,8,10,5),
        (0,-length-6,15,18,1,2,5),(0,-4,20,4,canopy,6,5),
        (-span/2-3,-5,14,span/2,9,3,1),(span/2+3,-5,14,span/2,9,3,1),
        (0,length-5,15,16,6,3,1),(0,length-5,17,2,8,12,1),(0,length-4,28,2,3,2,8)]
    if name in ('zero','val','kate'):GEOMETRY[name]+=[(-span*.75,-5,17,4,4,1,4),(span*.75,-5,17,4,4,1,4)]
    if name=='val':GEOMETRY[name]+=[(-10,-2,2,2,3,10,5),(10,-2,2,2,3,10,5)]
AIRCRAFT+=('wildcat','dauntless','avenger','zero','val','kate')

# Imported authoring forward is -Y; the engine heading is +X. Bake the
# quarter-turn once into geometry, keeping movement/turret state independent.
for _name in INFANTRY+VEHICLES+AIRCRAFT+SHIPS+tuple(PROJECTILES)+('naval_triple','naval_twin'):
    GEOMETRY[_name]=[(-y,x,z,d,w,h,c) for x,y,z,w,d,h,c in GEOMETRY[_name]]

# Accurate hull and separate game-owned main-battery envelopes.
GEOMETRY['yamato']=[(0,0,-yamato.DRAFT*yamato.WORLD_SCALE,172,yamato.BEAM*yamato.WORLD_SCALE/2,57*yamato.WORLD_SCALE,4)]
GEOMETRY['yamato_turret']=[(12,0,0,22,10,8,11)]
GEOMETRY['yamato_turret_aa']=list(GEOMETRY['yamato_turret'])
# Knocked-out main-battery turrets (tools/frontline/turret_damage.py): '<turret>_broken'.
from tools.frontline import turret_damage
for _name in turret_damage.TURRETS:GEOMETRY[turret_damage.broken(_name)]=list(GEOMETRY[_name])

# Japanese land variants share their US counterpart's box layout (bounds, selection, tests);
# their drawn art comes from imported.py (Type 98 infantry kit, Chi-Ha / Chi-Nu).
LAND_IJN={'rifle':'rifle_ijn','machinegun':'machinegun_ijn','commando':'commando_ijn','mortar':'mortar_ijn',
          'tank':'tank_ijn','heavytank':'heavytank_ijn'}
for _us,_ijn in LAND_IJN.items():GEOMETRY[_ijn]=list(GEOMETRY[_us])
INFANTRY+=tuple(v for k,v in LAND_IJN.items() if k in INFANTRY)
VEHICLES+=tuple(v for k,v in LAND_IJN.items() if k in VEHICLES)

NAVAL_TEXTURE='Emberfield\\Textures\\naval.blp'
def atlas(name):
    """Historical warships and their turrets use the 4x4 naval atlas."""
    return dict(texture=NAVAL_TEXTURE,grid=(4,4)) if name in historical.GEOMETRY else {}

FOOTPRINT_CELL=32
# A shipyard's piers reach into the water; only its land-side body is solid and must sit on shore.
FOOTPRINT_CELLS={'shipyard':5}
# Naval base / repair yard art (tools/frontline/drydock.py): capital/escort x USN/IJN, berths as data.
# drydock.ALIASES also redraws 'shipyard' as the capital USN yard (same footprint).
from tools.frontline import drydock
for _name in drydock.VARIANTS:GEOMETRY[_name]=list(drydock.SILHOUETTE[_name]);FOOTPRINT_CELLS[_name]=drydock.FOOTPRINT_CELLS
def footprint_cells(name):
    """Building footprint in 32-unit pathing cells: the ground-level extent of the
    model, so the blocked area equals what is drawn (taller parts overhang it)."""
    if name in FOOTPRINT_CELLS:return [FOOTPRINT_CELLS[name]]*2
    ground=[b for b in GEOMETRY[name] if b[2]<30]
    # Square, so a building can still be rotated in place like every other Warcraft structure.
    side=max(1,math.ceil(2*max(abs(b[axis])+b[axis+3] for b in ground for axis in (0,1))/FOOTPRINT_CELL))
    return [side,side]

def footprint_tga(name):
    """Uncompressed 32-bit TGA, BGRA bytes: red = blocks walking, blue = unbuildable, no air block."""
    width,height=footprint_cells(name)
    header=struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,width,height,32,8)
    return header+bytes([255,0,255,255])*(width*height)

def ship_wake(data,name):
    """Walk-only foam uses native geoset alpha tracks; no runtime emitters.
    A stern wake trails the hull and a bow wave curls off both sides of the stem."""
    def chunks(blob):
        offset=4
        while offset<len(blob):
            size=struct.unpack_from('<I',blob,offset+4)[0]
            yield blob[offset:offset+4],blob[offset+8:offset+8+size]
            offset+=8+size
    length=max(abs(b[0])+b[3] for b in GEOMETRY[name])
    beam=max(abs(b[1])+b[4] for b in GEOMETRY[name] if abs(b[0])<length*.3)
    white=12 if name in historical.GEOMETRY else 6
    foam=[(-length-12-i*13,sign*(beam*.6+i*3),2,12,2.5,1,white) for i in range(5) for sign in (-1,1)]
    foam+=[(length-8-i*9,sign*(beam*.35+i*4),1.5,6,1.6,1.4,white) for i in range(4) for sign in (-1,1)]
    extra=dict(chunks(base.mesh('wake',foam,**atlas(name))))[b'GEOS']
    pieces=[];count=0
    for tag,payload in chunks(data):
        if tag==b'GEOS':
            offset=0
            while offset<len(payload):
                count+=1;offset+=struct.unpack_from('<I',payload,offset)[0]
            payload+=extra
        if tag==b'MODL':
            radius,x0,y0,z0,x1,y1,z1=struct.unpack_from('<7f',payload,340)
            x0=min(x0,-length-80)
            radius=math.sqrt(max(abs(x0),abs(x1))**2+max(abs(y0),abs(y1))**2+max(abs(z0),abs(z1))**2)
            payload=payload[:340]+base.P('7f',radius,x0,y0,z0,x1,y1,z1)+payload[368:]
        pieces.append(base.CH(tag.decode(),payload))
    keys=[(0,0),(999,0),(1000,.6),(1999,.6),(2000,0),(7999,0)]
    track=b'KGAO'+base.P('3I',len(keys),0,0xffffffff)+b''.join(base.P('If',*k) for k in keys)
    alpha=base.P('IfI3fI',28+len(track),1,0,1,1,1,count)+track
    return b'MDLX'+b''.join(pieces)+base.CH('GEOA',alpha)

from tools.frontline import imported, gltf_import, ships, ship_states, unit_anim
# Defence structures, AA guns, the aa_mount upgrade and the airfield (tools/frontline/structures.py).
from tools.frontline import structures
GEOMETRY.update(structures.geometry(GEOMETRY))
CARRIERS=('carrier','yorktown','essex','akagi','kaga','soryu','hiryu','shokaku','independence')
def mesh(name):
    if name.endswith('_broken') and name[:-len('_broken')] in turret_damage.TURRETS:return turret_damage.mdx(name)
    if name in drydock.MODELS:return drydock.mdx(name)
    # All vertices bind to root 0: walk bob, firing recoil, Death sink/crash/collapse.
    if name in structures.MODELS:return structures.mdx(name)
    translation,scale=anim(name)
    if name=='yamato':
        tris=yamato.triangles()
        return ship_states.ship_mdx(name,tris,ships.wake(tris))
    if name in ('yamato_turret','yamato_turret_aa'):
        return ship_states.turret_mdx(name,ships.triangles(name))
    if name in imported.RECIPES:
        # Animated units (tools/frontline/unit_anim.py); buildings keep the static emitter.
        if name in INFANTRY:return unit_anim.soldier_mdx(name,imported.triangles(name))
        if name in VEHICLES:return unit_anim.vehicle_mdx(name,imported.triangles(name))
        if name in AIRCRAFT:return unit_anim.aircraft_mdx(name,imported.triangles(name))
        return gltf_import.mdx(name,imported.triangles(name),translation=translation,scale=scale)
    if name in imported.PROJECTILE_BURST:
        body,_=imported.projectile(name)
        return unit_anim.projectile_mdx(name,body,imported.PROJECTILE_BURST[name][0]*1.05,FLASH[name])
    if name in historical.GEOMETRY or name in ships.GENERIC:
        # Smooth lofted hulls and rounded fittings (tools/frontline/ships.py); walk-only foam wake.
        # Every condition (healthy, smoke, fire, inferno x list levels, sinking) is its own
        # sequence (tools/frontline/ship_states.py); turrets share the table and recoil.
        tris=ships.generic(name) if name in ships.GENERIC else ships.triangles(name)
        if name not in SHIPS:return ship_states.turret_mdx(name,tris)
        return ship_states.ship_mdx(name,tris,ships.wake(tris),capsize=name in CARRIERS)
    data=base.mesh(name,GEOMETRY[name],translation=translation,scale=scale,**atlas(name))
    return ship_wake(data,name) if name in SHIPS else data

# Faction fortifications (catalog.FORTIFICATIONS) and the roof AA mount (catalog.AA_MOUNT).
# Provisional box art under the final model names; the graphics pass replaces them in place.
# Structures keep model space: front is -Y, up is +Z (no quarter-turn).
def _sandbag_ring(r,h=14):
    return [(-r,0,0,4,r,h,4),(r,0,0,4,r,h,4),(0,r,0,r,4,h,4),(0,-r,0,r,4,h,4)]
def _light_aa(barrels):
    return _sandbag_ring(26)+[(0,0,0,24,24,3,0),(0,0,3,6,6,24,1),(0,-3,26,11,5,10,7)]+\
        [(x,-24,32,2,22,2,1) for x in barrels]+[(0,0,38,5,5,2,8)]
GEOMETRY.update({
 'pillbox_usn':[(0,0,0,48,48,6,0),(0,0,6,40,40,28,0),(0,0,34,44,44,5,1),(0,-41,18,26,3,6,5),
                (0,-52,22,3,16,4,1),(0,40,6,10,3,20,5),(-50,-30,0,8,18,16,4),(50,-30,0,8,18,16,4),(0,0,39,7,7,2,8)],
 'pillbox_ijn':[(0,0,0,52,50,6,0),(0,0,6,46,44,24,3),(0,0,30,50,48,8,3),(0,0,38,40,38,6,4),
                (0,-45,16,30,3,6,5),(0,-56,19,3,14,4,1),(0,0,44,7,7,2,8)],
 'aa_oerlikon':_light_aa((0,)),
 'aa_type98':_light_aa((-3,3)),
 'aa_bofors':_sandbag_ring(40,16)+[(0,0,0,38,38,5,0),(0,0,5,18,14,14,7),(0,0,19,14,10,12,7),
                (0,-8,20,16,2,14,7),(0,-34,30,3,30,3,1),(0,-66,31,4,4,3,1),(0,0,31,5,5,2,8)],
 'aa_type96':_sandbag_ring(38,16)+[(0,0,0,36,36,5,0),(0,0,5,16,14,14,7),(0,0,19,18,10,10,7)]+
                [(x,-30,30,2,28,2,1) for x in (-7,0,7)]+[(0,0,29,5,5,2,8)],
 'aa_m1_90mm':[(0,0,0,52,8,6,1),(0,0,0,8,52,6,1),(0,0,6,22,22,16,7),(0,0,22,16,22,14,7),
                (0,-52,40,4,50,4,1),(0,-104,41,5,4,3,1),(0,0,36,6,6,4,8)]+_sandbag_ring(56,12),
 'aa_type88':[(0,0,0,48,8,6,1),(0,0,0,8,48,6,1),(0,0,6,20,20,16,7),(0,0,22,15,20,12,7),
                (0,-48,36,4,46,4,1),(0,0,34,6,6,4,8)]+_sandbag_ring(52,12),
 'coastal_usn':[(0,0,0,56,52,12,0),(0,0,12,26,24,26,7),(0,-55,30,5,58,7,1),(0,-114,32,6,6,5,1),
                (0,0,38,10,12,3,8),(-52,40,0,8,18,16,4),(52,40,0,8,18,16,4),(45,35,0,16,14,18,0)],
 'coastal_ijn':[(0,0,0,58,54,14,0),(0,0,14,32,28,30,0),(0,0,44,34,30,4,1),(-9,-56,30,5,52,7,1),
                (9,-56,30,5,52,7,1),(0,0,48,10,12,3,8),(-48,40,0,14,16,22,0)],
 'radar_usn':[(0,0,0,30,30,6,0),(0,0,6,4,4,90,3),(0,0,96,42,3,26,1),(0,-4,100,38,1,18,5),
              (30,30,0,14,10,16,7),(0,0,6,7,7,2,8)],
 'radar_ijn':[(0,0,0,28,28,6,0),(0,0,6,5,5,80,3),(0,0,86,30,4,20,1),(0,0,106,4,30,3,1),
              (-28,28,0,12,12,18,0),(0,0,6,7,7,2,8)],
 'aa_mount':[(0,0,0,10,10,4,4),(0,0,4,3,3,8,1),(0,0,12,6,5,5,7),(-2,-14,15,1.5,12,1.5,1),(2,-14,15,1.5,12,1.5,1)],
})
