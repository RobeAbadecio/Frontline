"""WWII naval base / repair yard: graving dock, piers, cranes, shops and fuel farm.

Original MIT procedural geometry in the smooth ship style (ships.bevel_box,
ships.cylinder), no downloaded mesh. Two yard sizes, each in two navies' styles:

  capital  drydock_usn, drydock_ijn       Capital Shipyard: 316-long graving dock,
           260-long pier; battleships and fleet carriers
  escort   escortdock_usn, escortdock_ijn Shipyard / Escort Shipyard: 256-long
           dock, 210-long pier; cruisers, destroyers, landing ships

  usn  Pearl Harbor style: concrete quays, hammerhead crane, portal crane on the
       dock wall, corrugated steel shops, silver fuel tanks
  ijn  Kure / Yokosuka style: red-brick shops with dark tile roofs, a luffing tower
       crane, a gantry spanning the dock, timber pier deck

ALIASES maps existing catalog model names onto a variant ('shipyard' is used by
fdoc, fesc, fhvy and flnd and draws the capital USN yard).

Model frame: +X is seaward (the WC3 building front, so the default -90 degree
placement shows the waterfront toward the camera), origin at the building
centre, z=0 the ground at the centre. Only the land body inside the 5x5-cell
(160x160) shipyard footprint is solid; quays, the dock and piers overhang the
water. Ground at a legal coastal site is ~10 above the sea (generate.terrain_files
caps land at +10), so the sea surface sits at WATER_Z in model space.

BERTHS = {model_name: [(x, y, heading_degrees, max_length, radius), ...]} in model
space, for every name in MODELS (variants and aliases):
  x, y         hull centre of a berthed ship
  heading      bow direction; 0 = +X (seaward, ready to sortie), 180 = bow-in (dock)
  max_length   longest hull that fits without touching the quay or the caisson gate
  radius       passive-repair radius (beam/2 + 30): a ship whose centre is within it
               is berthed; neighbouring radii overlap
BERTH_BEAM = {model_name: [widest hull beam per berth]}. Rotate (x, y) and add the
building angle to heading for world space (default angle -90: world = centre + (y, -x)).

Animation (rich_mdx): the quay crane slews in Stand and Stand Work, the travelling
crane / gantry trolley moves, and welding arcs flicker along the berths in Work
and Stand Work (repair while berthed). Death sinks the whole yard.
"""
import math

from tools.frontline import gltf_import as gi
from tools.frontline import rich_mdx as rm
from tools.frontline.ships import bevel_box, cylinder, quad

TEAM=gi.TEAM
FOOTPRINT_CELLS=5                 # models.FOOTPRINT_CELLS['shipyard']: 5 x 32 = 160 square
LAND_HALF=FOOTPRINT_CELLS*32/2    # solid land body: |x|,|y| <= 80
QUAY_X=86                         # seaward face of the quay wall
DECK_Z=1.5                        # quay, pier and dock-wall deck level
WATER_Z=-10                       # sea surface (world z=0) at a +10 coastal site
DOCK_Y,DOCK_WALL,PIER_HALF=-50,9,9
DOCK_X0=QUAY_X                    # graving dock head at the quay; caisson gate at DOCK_X1
CLEAR=4                           # hull clearance to walls / pier faces
REPAIR_SLACK=30                   # berth radius = beam/2 + this
# Per-size layout: dock gate x, dock inner half-width, pier end x, pier centre y,
# outboard berth (max length, beam), travelling-crane x, IJN gantry x.
LAYOUTS={'capital':dict(dock_x1=412,dock_half=30,pier_x1=346,pier_y=58,outboard=(345,82),travel_x=196,gantry_x=176),
         'escort': dict(dock_x1=352,dock_half=24,pier_x1=296,pier_y=52,outboard=(270,60),travel_x=170,gantry_x=160)}
VARIANTS={'drydock_usn':('usn','capital'),'drydock_ijn':('ijn','capital'),
          'escortdock_usn':('usn','escort'),'escortdock_ijn':('ijn','escort')}
ALIASES={'shipyard':'drydock_usn'}   # drop to restore the old boathouse shipyard art
MODELS={**VARIANTS,**{a:VARIANTS[v] for a,v in ALIASES.items()}}
TRIANGLE_BUDGET=10000

def _use(size):
    """Select a size's layout (module globals read by the part builders)."""
    global DOCK_X1,DOCK_HALF,PIER_X1,PIER_Y,TRAVEL_AT,GANTRY_X
    L=LAYOUTS[size]
    DOCK_X1,DOCK_HALF,PIER_X1,PIER_Y=L['dock_x1'],L['dock_half'],L['pier_x1'],L['pier_y']
    TRAVEL_AT=(L['travel_x'],DOCK_Y+DOCK_HALF+DOCK_WALL/2);GANTRY_X=L['gantry_x']
    return L

def _berths(size):
    L=_use(size);out_len,out_beam=L['outboard']
    inner=PIER_Y-PIER_HALF-(DOCK_Y+DOCK_HALF+DOCK_WALL)
    between=min(PIER_X1-QUAY_X+40,out_len-45)
    rows=[((DOCK_X0+DOCK_X1)/2,DOCK_Y,180,DOCK_X1-DOCK_X0-2*CLEAR-2,2*(DOCK_HALF-CLEAR)),            # graving dock
          (QUAY_X+CLEAR+between/2,(DOCK_Y+DOCK_HALF+DOCK_WALL+PIER_Y-PIER_HALF)/2,0,between,inner-2*CLEAR), # dock/pier slip
          (QUAY_X+CLEAR+out_len/2,PIER_Y+PIER_HALF+CLEAR+out_beam/2,0,out_len,out_beam)]                  # outboard of pier
    # Repair radius: half the widest beam plus 30 slack for ships nudged by collision; radii of
    # neighbouring berths may overlap (repair is passive, any berth counts).
    return [(x,y,h,l,round(b/2+REPAIR_SLACK)) for x,y,h,l,b in rows],[b for *_,b in rows]

def _silhouette(size):
    """Box silhouette for models.GEOMETRY (bounds, icon framing); atlas cells as in models.py."""
    _use(size);mid,half=(DOCK_X0+DOCK_X1+12)/2,(DOCK_X1+12-DOCK_X0)/2
    return [(0,-3,0,84,91,8,0),(mid,DOCK_Y+DOCK_HALF+DOCK_WALL/2,0,half,DOCK_WALL/2,8,0),
            (mid,DOCK_Y-DOCK_HALF-DOCK_WALL/2,0,half,DOCK_WALL/2,8,0),
            ((QUAY_X+PIER_X1)/2,PIER_Y,0,(PIER_X1-QUAY_X)/2,PIER_HALF,8,3),(11,56,8,41,28,26,1),(QUAY_X-17,19,8,6,6,64,1)]

BERTHS={};BERTH_BEAM={};SILHOUETTE={}
for _name,(_variant,_size) in MODELS.items():
    BERTHS[_name],BERTH_BEAM[_name]=_berths(_size);SILHOUETTE[_name]=_silhouette(_size)

PALETTES={
 'usn':dict(concrete=(170,168,158),edge=(196,192,176),dark=(122,121,114),asphalt=(66,68,68),water=(30,66,80),
            wall=(146,154,144),wall2=(126,136,128),roof=(86,92,92),glass=(52,66,74),crane=(128,136,140),
            crane2=(96,104,108),tank=(196,198,192),berm=(122,112,84),timber=(92,70,46),iron=(40,42,44),
            rail=(150,150,146),sleeper=(76,62,48),brick=(150,96,74),pier=(160,158,148),car=(118,72,50),
            truck=(86,96,66),flash=(255,236,170),arc=(196,222,255)),
 'ijn':dict(concrete=(160,154,140),edge=(184,176,158),dark=(116,112,102),asphalt=(70,68,64),water=(30,62,72),
            wall=(150,76,58),wall2=(124,62,48),roof=(52,54,58),glass=(46,56,58),crane=(96,106,100),
            crane2=(70,78,74),tank=(92,96,88),berm=(118,106,80),timber=(96,72,48),iron=(38,38,38),
            rail=(146,144,140),sleeper=(74,58,44),brick=(150,76,58),pier=(120,94,64),car=(64,66,60),
            truck=(92,96,74),flash=(255,236,170),arc=(196,222,255)),
}

# ---------------------------------------------------------------- primitives
def box(x0,x1,y0,y1,z0,z1,colour,bevel=0):
    x,y,w,d,h=(x0+x1)/2,(y0+y1)/2,(x1-x0)/2,(y1-y0)/2,z1-z0
    return bevel_box(x,y,z0,w,d,h,colour,bevel) if bevel else gi.boxes([(x,y,z0,w,d,h,colour)])

def _orient(pts,colour,inside):
    """Polygon fan facing away from an interior point."""
    n=gi._normal(*pts[:3]);c=[sum(p[i] for p in pts)/len(pts) for i in range(3)]
    if gi._dot(n,gi._sub(c,inside))<0:pts=pts[::-1]
    return [((pts[0],pts[i],pts[i+1]),colour,'s') for i in range(1,len(pts)-1)]

def beam(p0,p1,r,colour):
    """Square strut between two points (truss chords, braces, legs)."""
    d=gi._sub(p1,p0);l=math.sqrt(gi._dot(d,d)) or 1;d=tuple(v/l for v in d)
    up=(0,0,1) if abs(d[2])<.9 else (1,0,0)
    u=gi._cross(d,up);lu=math.sqrt(gi._dot(u,u));u=tuple(v/lu*r for v in u)
    v=gi._cross(d,u);v=tuple(c for c in v)
    ring=lambda p:[tuple(p[i]+s*u[i]+t*v[i] for i in range(3)) for s,t in ((1,1),(-1,1),(-1,-1),(1,-1))]
    a,b=ring(p0),ring(p1);mid=tuple((p0[i]+p1[i])/2 for i in range(3))
    tris=[]
    for i in range(4):
        j=(i+1)%4;tris+=_orient([a[i],a[j],b[j],b[i]],colour,mid)
    return tris+_orient(a,colour,mid)+_orient(b,colour,mid)

def gable(x0,x1,y0,y1,eave,ridge,colour,end_colour,over=2):
    """Pitched roof with its ridge along x; gable ends filled in the wall colour."""
    ym=(y0+y1)/2;inside=((x0+x1)/2,ym,eave+.1)
    a,b,c,d=(x0-over,y0-over,eave-1),(x1+over,y0-over,eave-1),(x1+over,ym,ridge),(x0-over,ym,ridge)
    e,f=(x1+over,y1+over,eave-1),(x0-over,y1+over,eave-1)
    tris=_orient([a,b,c,d],colour,inside)+_orient([f,e,c,d][::-1],colour,inside)
    tris+=_orient([(x0,y0,eave),(x0,ym,ridge-.5),(x0,y1,eave)],end_colour,inside)
    tris+=_orient([(x1,y0,eave),(x1,ym,ridge-.5),(x1,y1,eave)],end_colour,inside)
    return tris

def sawtooth(x0,x1,y0,y1,eave,rise,teeth,colour,glass):
    """North-light roof: teeth along y, each a slope plus a vertical glazed face."""
    tris=[];step=(y1-y0)/teeth
    for i in range(teeth):
        a,b=y0+i*step,y0+(i+1)*step;inside=((x0+x1)/2,a+step*.6,eave+.1)
        tris+=_orient([(x0,a,eave),(x1,a,eave),(x1,b,eave+rise),(x0,b,eave+rise)],colour,inside)
        tris+=_orient([(x0,b,eave),(x1,b,eave),(x1,b,eave+rise),(x0,b,eave+rise)],glass,inside)
        tris+=_orient([(x0,a,eave),(x0,b,eave),(x0,b,eave+rise)],colour,inside)
        tris+=_orient([(x1,a,eave),(x1,b,eave),(x1,b,eave+rise)],colour,inside)
    return tris

def flat(x0,x1,y0,y1,z,colour):
    return quad((x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z),colour)

def bollard(x,y,pal):
    return cylinder(x,y,DECK_Z,1.5,1.5,2.6,pal['iron'],6,taper=1.3)

def fender(x,y,face,pal,along='x'):
    """Vertical timber fender on a wall face; `face` is the outward normal sign."""
    if along=='x':return box(x-1.4,x+1.4,y,y+face*1.6,WATER_Z-2,DECK_Z-.5,pal['timber']) if face>0 else box(x-1.4,x+1.4,y-1.6,y,WATER_Z-2,DECK_Z-.5,pal['timber'])
    return box(x,x+1.6,y-1.4,y+1.4,WATER_Z-2,DECK_Z-.5,pal['timber'])

def flag(x,y,z,height,width):
    """Pole with a team-colour flag (two-sided)."""
    tris=cylinder(x,y,z,.7,.7,height,(200,200,196),6)
    top=z+height-1;cloth=[(x,y,top),(x+width,y+1.5,top-1),(x+width,y+1.5,top-width*.62),(x,y,top-width*.6)]
    return tris+[((cloth[0],cloth[1],cloth[2]),TEAM,'s'),((cloth[0],cloth[2],cloth[3]),TEAM,'s'),
                 ((cloth[0],cloth[2],cloth[1]),TEAM,'s'),((cloth[0],cloth[3],cloth[2]),TEAM,'s')]

# ---------------------------------------------------------------- yard parts
def caisson(pal):
    """Caisson gate (own bone, pivot at its centre): a floating steel box across the dock
    entrance with a deck walkway, capstans and a team band. Opens in 'Stand Alternate'."""
    t=[];g0=DOCK_X1
    t+=box(g0,g0+10,DOCK_Y-DOCK_HALF-1,DOCK_Y+DOCK_HALF+1,WATER_Z-12,DECK_Z-1,pal['crane2'],1.5)
    t+=box(g0+1,g0+9,DOCK_Y-DOCK_HALF,DOCK_Y+DOCK_HALF,DECK_Z-1,DECK_Z,pal['dark'])
    t+=box(g0+10,g0+10.6,DOCK_Y-DOCK_HALF+2,DOCK_Y+DOCK_HALF-2,WATER_Z+.5,WATER_Z+4,TEAM)
    t+=box(g0+4.5,g0+5.5,DOCK_Y-DOCK_HALF,DOCK_Y+DOCK_HALF,DECK_Z+1.8,DECK_Z+2.3,pal['rail'])   # walkway handrail
    for s in (-1,1):t+=cylinder(g0+5,DOCK_Y+s*(DOCK_HALF-3),DECK_Z,2.2,2.2,4,pal['iron'],6)   # capstans
    pivot=(g0+5,DOCK_Y,0)
    return gi.transform(t,1,(-pivot[0],-pivot[1],0)),pivot

def gate_slide():
    """Where the open caisson rests, relative to its closed pivot: floated seaward, then warped
    aside along the quay, away from the pier."""
    away=-1 if PIER_Y>DOCK_Y else 1
    return (16,away*(2*DOCK_HALF+8),-1)

def waterfront(pal,variant):
    t=[]
    # Land apron (the solid footprint) and the quay wall running along the waterline.
    t+=box(-84,QUAY_X,-94,88,-14,DECK_Z,pal['concrete'],2)
    t+=box(QUAY_X-6,QUAY_X,-94,88,DECK_Z,DECK_Z+.6,pal['edge'])
    # Graving dock: two long walls, stepped altars inside, a flooded basin and the caisson.
    wall_n0,wall_s1=DOCK_Y+DOCK_HALF,DOCK_Y-DOCK_HALF
    for y0,y1 in ((wall_n0,wall_n0+DOCK_WALL),(wall_s1-DOCK_WALL,wall_s1)):
        t+=box(DOCK_X0-4,DOCK_X1+12,y0,y1,WATER_Z-12,DECK_Z,pal['concrete'],1.2)
        t+=box(DOCK_X0,DOCK_X1+12,y0+(1 if y0>DOCK_Y else 0),y1-(0 if y0>DOCK_Y else 1),DECK_Z,DECK_Z+.5,pal['edge'])
    for step in range(3):
        inset=DOCK_HALF-2-step*2.5;z=WATER_Z-4-step*3
        t+=box(DOCK_X0,DOCK_X1,DOCK_Y+inset,DOCK_Y+DOCK_HALF,WATER_Z-12,z,pal['dark'])
        t+=box(DOCK_X0,DOCK_X1,DOCK_Y-DOCK_HALF,DOCK_Y-inset,WATER_Z-12,z,pal['dark'])
    t+=flat(DOCK_X0,DOCK_X1,DOCK_Y-DOCK_HALF,DOCK_Y+DOCK_HALF,WATER_Z-.35,pal['water'])
    # Finger pier on piles, with a deck kerb, crane rails and a pier-head shed.
    deck=pal['pier']
    t+=box(QUAY_X-2,PIER_X1,PIER_Y-PIER_HALF,PIER_Y+PIER_HALF,DECK_Z-3,DECK_Z,deck,1)
    if variant=='ijn':   # planked timber deck reads as strakes
        for i in range(4):
            y0=PIER_Y-PIER_HALF+i*PIER_HALF/2
            t+=box(QUAY_X,PIER_X1-1,y0+.3,y0+PIER_HALF/2-.3,DECK_Z,DECK_Z+.15,tuple(int(c*(1.08 if i%2 else .93)) for c in deck))
    for x in range(int(QUAY_X)+14,PIER_X1,26):
        for s in (-1,1):t+=cylinder(x,PIER_Y+s*(PIER_HALF-2),WATER_Z-8,1.6,1.6,8+DECK_Z-3,pal['timber'] if variant=='ijn' else pal['dark'],6)
    for y in (PIER_Y-3,PIER_Y+3):t+=box(QUAY_X,PIER_X1-4,y-.4,y+.4,DECK_Z,DECK_Z+.5,pal['rail'])
    t+=box(PIER_X1-26,PIER_X1-8,PIER_Y-5,PIER_Y+5,DECK_Z,DECK_Z+9,pal['wall2'],.8)+gable(PIER_X1-26,PIER_X1-8,PIER_Y-5,PIER_Y+5,DECK_Z+9,DECK_Z+13,pal['roof'],pal['wall2'],1)
    # Bollards and fenders along every berth face.
    for x in range(int(QUAY_X)+10,PIER_X1-4,24):
        t+=bollard(x,PIER_Y-PIER_HALF+2,pal)+bollard(x,PIER_Y+PIER_HALF-2,pal)
        t+=fender(x+12,PIER_Y-PIER_HALF,-1,pal)+fender(x+12,PIER_Y+PIER_HALF,1,pal)
    for x in range(int(DOCK_X0)+12,DOCK_X1,30):
        t+=bollard(x,wall_n0+DOCK_WALL-2,pal)+bollard(x,wall_s1+2.5,pal)
        t+=fender(x+15,wall_n0+DOCK_WALL,1,pal)
    for y in (-4,22,40):t+=fender(QUAY_X,y,1,pal,along='y')+bollard(QUAY_X-3,y+6,pal)
    for y in (66,80):t+=bollard(QUAY_X-3,y,pal)
    # Crane rails along the dock's north wall (travelling crane) and the quay.
    for y in (wall_n0+2,wall_n0+DOCK_WALL-4):t+=box(DOCK_X0,DOCK_X1,y-.4,y+.4,DECK_Z+.5,DECK_Z+1,pal['rail'])
    for x in (QUAY_X-24,QUAY_X-10):t+=box(x-.4,x+.4,-94,88,DECK_Z,DECK_Z+.5,pal['rail'])
    return t

def railway(pal):
    """Standard-gauge spur along the yard with a few wagons, and the yard road."""
    t=box(-84,QUAY_X-4,-6,4,DECK_Z,DECK_Z+.2,pal['asphalt'])
    t+=box(-84,QUAY_X-4,9,17,DECK_Z,DECK_Z+.3,(96,90,80))
    for x in range(-80,int(QUAY_X)-6,9):t+=box(x-1,x+1,9.6,16.4,DECK_Z+.3,DECK_Z+.7,pal['sleeper'])
    for y in (11.3,14.7):t+=box(-84,QUAY_X-4,y-.35,y+.35,DECK_Z+.7,DECK_Z+1.3,pal['rail'])
    for x,colour,h in ((-30,pal['car'],7),(-8,pal['car'],7),(30,pal['dark'],4)):
        t+=box(x-9,x+9,10.2,15.8,DECK_Z+2.4,DECK_Z+2.4+h,colour,.8)
        for wx in (x-6,x+6):t+=box(wx-2,wx+2,10.6,15.4,DECK_Z+1.2,DECK_Z+2.4,pal['iron'])
    for x,y in ((-56,-1),(44,-1)):   # trucks on the road
        t+=box(x-6,x+3,y-2.6,y+2.6,DECK_Z+1,DECK_Z+5,pal['truck'],.8)+box(x+3,x+7,y-2.4,y+2.4,DECK_Z+1,DECK_Z+6,pal['truck'],.8)
        t+=box(x+6.8,x+7.2,y-2,y+2,DECK_Z+3.5,DECK_Z+5.5,pal['glass'])
    return t

def shops(pal,variant):
    t=[]
    # Machine shop: long gabled hall with a clerestory monitor and window bands.
    x0,x1,y0,y1=-30,52,28,84;eave=24
    t+=box(x0,x1,y0,y1,DECK_Z,eave,pal['wall'],.6)
    for z in (8,17):
        t+=box(x0+3,x1-3,y0-.4,y0,z,z+5,pal['glass'])+box(x0+3,x1-3,y1,y1+.4,z,z+5,pal['glass'])
    for x in range(x0+5,x1-3,9):t+=box(x,x+1,y0-.8,y0,DECK_Z,eave,pal['wall2'])   # pilasters
    t+=box(x1,x1+.5,y0+14,y1-14,DECK_Z,DECK_Z+16,pal['dark'])                     # seaward bay door
    t+=gable(x0,x1,y0,y1,eave,eave+10,pal['roof'],pal['wall'])
    t+=box(x0+6,x1-6,(y0+y1)/2-5,(y0+y1)/2+5,eave+9,eave+13,pal['glass'])+gable(x0+6,x1-6,(y0+y1)/2-5,(y0+y1)/2+5,eave+13,eave+16,pal['roof'],pal['wall2'],1)
    t+=box(x0+8,x0+20,y0+3,y0+5.5,eave+5.2,eave+5.8,TEAM)                            # painted roof identifier
    # Foundry / plate shop with a sawtooth north-light roof and a stack.
    x0,x1,y0,y1=-82,-38,30,84;eave=18
    t+=box(x0,x1,y0,y1,DECK_Z,eave,pal['wall2'] if variant=='usn' else pal['wall'],.6)
    t+=sawtooth(x0,x1,y0,y1,eave,7,4,pal['roof'],pal['glass'])
    t+=box(x0+4,x1-4,y0-.4,y0,6,12,pal['glass'])
    t+=cylinder(-46,76,eave,2.6,2.6,22,pal['dark'],8,taper=.85)
    # Power house with a tall chimney beside the dock head; pump house at the dock.
    x0,x1,y0,y1=4,50,-90,-60;eave=20
    t+=box(x0,x1,y0,y1,DECK_Z,eave,pal['brick'],.6)+box(x0+2,x1-2,y1,y1+.4,10,15,pal['glass'])
    t+=gable(x0,x1,y0,y1,eave,eave+7,pal['roof'],pal['brick']) if variant=='ijn' else box(x0-1,x1+1,y0-1,y1+1,eave,eave+1.4,pal['dark'])
    t+=cylinder(42,-84,DECK_Z,4.2,4.2,62,pal['brick'] if variant=='ijn' else pal['dark'],10,taper=.7)
    t+=cylinder(42,-84,DECK_Z+58,3.2,3.2,4,pal['iron'],10)
    t+=box(58,74,-72,-58,DECK_Z,DECK_Z+10,pal['wall2'],.6)+box(57,75,-73,-57,DECK_Z+10,DECK_Z+11.2,pal['roof'])
    # Yard office / signal station with the base's flag.
    t+=box(-30,-6,-44,-18,DECK_Z,DECK_Z+14,pal['wall'] if variant=='usn' else (176,168,146),.6)
    t+=box(-29,-7,-43.6,-44.2,6,10,pal['glass'])
    t+=gable(-30,-6,-44,-18,DECK_Z+14,DECK_Z+21,pal['roof'],pal['wall'] if variant=='usn' else (176,168,146),1.5)
    t+=flag(-2,-30,DECK_Z,48,13)
    for x,y in ((-36,6),(28,22),(QUAY_X-16,-14),(QUAY_X-16,46)):    # lamp standards
        t+=cylinder(x,y,DECK_Z,.6,.6,16,pal['iron'],5)+box(x-1.6,x+1.6,y-1,y+1,DECK_Z+16,DECK_Z+17.4,pal['edge'])
    for i,(x,y) in enumerate(((QUAY_X-18,28),(QUAY_X-14,32),(QUAY_X-18,36),(66,-30))):     # crates, drums
        t+=box(x-2.6,x+2.6,y-2.6,y+2.6,DECK_Z,DECK_Z+5,pal['timber'],.4) if i%2==0 else cylinder(x,y,DECK_Z,1.8,1.8,4,(80,90,70),7)
    return t

def fuel_farm(pal):
    t=box(-84,-36,-92,-24,DECK_Z,DECK_Z+3,pal['berm'],1.5)      # containment berm
    t+=box(-80,-40,-88,-28,DECK_Z+3,DECK_Z+3.2,pal['dark'])
    for x,y,r,h in ((-64,-70,13,20),(-64,-41,11,18),(-46,-56,6,14)):
        t+=cylinder(x,y,DECK_Z+3,r,r,h,pal['tank'],14)
        t+=cylinder(x,y,DECK_Z+3+h,r,r,r*.22,pal['tank'],14,taper=.45)
        t+=beam((x+r*.7,y-r*.7,DECK_Z+3),(x+r*.7,y-r*.7,DECK_Z+3+h),.5,pal['iron'])   # ladder
    t+=beam((-40,-56,DECK_Z+4),(QUAY_X-6,-56,DECK_Z+4),.9,pal['iron'])                    # fuel line to the dock
    return t

# ---------------------------------------------------------------- cranes
CRANE_AT=(QUAY_X-17,19)          # quay crane slewing axis
def lattice(x,y,half,z0,z1,colour,levels=4,brace=.5,leg=1.1):
    t=[];corners=[(x+sx*half,y+sy*half) for sx,sy in ((1,1),(-1,1),(-1,-1),(1,-1))]
    for cx,cy in corners:t+=beam((cx,cy,z0),(cx,cy,z1),leg,colour)
    zs=[z0+(z1-z0)*i/levels for i in range(levels+1)]
    for k in range(4):
        (ax,ay),(bx,by)=corners[k],corners[(k+1)%4]
        for i,z in enumerate(zs[1:]):
            t+=beam((ax,ay,z),(bx,by,z),brace,colour)
            za=zs[i];t+=beam((ax,ay,za),(bx,by,z),brace,colour) if (i+k)%2 else beam((bx,by,za),(ax,ay,z),brace,colour)
    return t

def quay_crane(pal,variant):
    """Static tower and the slewing head (returned separately, relative to the head pivot)."""
    x,y=CRANE_AT
    if variant=='usn':
        top=72
        tower=box(x-8,x+8,y-8,y+8,DECK_Z,DECK_Z+3,pal['concrete'],1)+lattice(x,y,6,DECK_Z+3,top,pal['crane'],5)
        tower+=box(x-7,x+7,y-7,y+7,top,top+2.5,pal['crane2'])
        # Hammerhead jib: rectangular truss, long arm seaward, machinery house and counterweight aft.
        head=[];z0,z1=2.5,11;arm=78;tail=-30
        for sy in (-3.2,3.2):
            for z in (z0,z1):head+=beam((tail,sy,z),(arm,sy,z),.8,pal['crane'])
            n=9
            for i in range(n):
                xa,xb=tail+(arm-tail)*i/n,tail+(arm-tail)*(i+1)/n
                head+=beam((xa,sy,z0),(xb,sy,z1),.45,pal['crane']) if i%2 else beam((xa,sy,z1),(xb,sy,z0),.45,pal['crane'])
        head+=box(tail-2,tail+14,-4.4,4.4,z0-1,z1+3,pal['crane2'],.8)               # machinery house
        head+=box(tail-4,tail+1,-4,4,z0-6,z0+2,pal['dark'],.6)                       # counterweight
        head+=box(tail+3,tail+11,-4.5,-4.4,z0+6,z0+9,TEAM)+box(tail+3,tail+11,4.4,4.5,z0+6,z0+9,TEAM)
        head+=box(-4,4,-5,5,z0-4,z0+1,pal['crane2'],.6)                               # slewing ring
        head+=box(-6,2,-6.2,-4,z0-1,z0+5,pal['glass'])                                # cab glazing
        trolley=arm-16
        head+=box(trolley-3,trolley+3,-3,3,z0-2,z0,pal['crane2'])
        head+=beam((trolley,0,z0-2),(trolley,0,z0-30),.25,pal['iron'])+box(trolley-1.5,trolley+1.5,-1.5,1.5,z0-33,z0-30,pal['iron'])
        head+=flag(arm-1,0,z1,9,5)
        return tower,head,(x,y,top)
    # IJN luffing tower crane: tapered portal tower, raised jib, A-frame and hanging block.
    top=58
    tower=box(x-9,x+9,y-9,y+9,DECK_Z,DECK_Z+3,pal['concrete'],1)+lattice(x,y,6.5,DECK_Z+3,top,pal['crane'],4)
    head=box(-7,7,-6,6,0,9,pal['crane2'],.8)+box(-9,-4,-5,5,-1,6,pal['dark'],.6)+box(5,7.2,-4,4,3,7,pal['glass'])
    head+=box(-8,-6.5,-6.1,6.1,9,10.5,TEAM)
    jib0,jib1=(4,0,5),(66,0,42)
    for sy in (-2.4,2.4):
        head+=beam((jib0[0],sy,jib0[2]),(jib1[0],sy*.5,jib1[2]),.8,pal['crane'])
        n=7
        for i in range(n):
            a=[jib0[k]+(jib1[k]-jib0[k])*i/n for k in range(3)];b=[jib0[k]+(jib1[k]-jib0[k])*(i+1)/n for k in range(3)]
            w=sy*(1-.5*(i+1)/n)
            head+=beam((a[0],sy*(1-.5*i/n),a[2]),(b[0],w,b[2]+2.2),.35,pal['crane'])
    head+=beam((-2,0,9),(0,0,24),.7,pal['crane'])+beam((0,0,24),(jib1[0],0,jib1[2]),.3,pal['iron'])
    head+=beam((jib1[0],0,jib1[2]),(jib1[0],0,-24),.25,pal['iron'])+box(jib1[0]-1.6,jib1[0]+1.6,-1.6,1.6,-28,-24,pal['iron'])
    head+=flag(jib1[0],0,jib1[2],7,5)
    return tower,head,(x,y,top)

# TRAVEL_AT (USN portal crane on the dock's north wall) and GANTRY_X (IJN gantry) come from _use().
def travelling(pal,variant):
    """Rail-mounted portal crane (USN) or dock gantry (IJN): static frame + moving part
    relative to its bone pivot."""
    if variant=='usn':
        x,y=TRAVEL_AT;t=[]
        # The whole portal travels; the moving part is everything.
        part=[]
        for sx in (-5,5):
            for sy in (-3.5,3.5):part+=beam((sx,sy,DECK_Z+1),(sx*.6,sy*.6,DECK_Z+22),.8,pal['crane'])
            part+=box(sx-1.6,sx+1.6,-4.6,4.6,DECK_Z+.5,DECK_Z+2,pal['crane2'])
        part+=box(-5,5,-4.5,4.5,DECK_Z+22,DECK_Z+25,pal['crane2'],.6)
        part+=box(-4,4,-4,3,DECK_Z+25,DECK_Z+33,pal['crane'],.8)+box(3.9,4.4,-3,2,DECK_Z+28,DECK_Z+31,pal['glass'])
        part+=box(-4.1,-3.8,-3,2,DECK_Z+29,DECK_Z+32,TEAM)
        part+=beam((2,0,DECK_Z+28),(14,-34,DECK_Z+46),.7,pal['crane'])+beam((-3,0,DECK_Z+33),(14,-34,DECK_Z+46),.3,pal['iron'])
        part+=beam((14,-34,DECK_Z+46),(14,-34,DECK_Z+16),.2,pal['iron'])+box(12.6,15.4,-35.4,-32.6,DECK_Z+13,DECK_Z+16,pal['iron'])
        return t,part,(x,y,0)
    # Gantry: two portal legs standing on the dock walls, a box girder across, trolley moves on y.
    x=GANTRY_X;t=[];yn,ys=DOCK_Y+DOCK_HALF+DOCK_WALL/2,DOCK_Y-DOCK_HALF-DOCK_WALL/2;top=54
    for y in (yn,ys):
        for sx in (-7,7):t+=beam((x+sx,y,DECK_Z),(x+sx*.5,y,top),1.3,pal['crane'])
        t+=beam((x-6,y,DECK_Z+20),(x+6,y,DECK_Z+20),.7,pal['crane'])+box(x-9,x+9,y-2.5,y+2.5,DECK_Z,DECK_Z+2,pal['crane2'])
    for sx in (-3,3):t+=box(x+sx-1.8,x+sx+1.8,ys-3,yn+3,top,top+6,pal['crane'],.6)
    t+=box(x-5,x+5,yn-1,yn+4,top+6,top+7,pal['crane2'])+box(x-5.2,x+5.2,ys-3,ys+2,top-1,top+5,TEAM)
    part=box(-4.5,4.5,-4,4,top+6,top+11,pal['crane2'],.8)+box(-4,4,3.9,4.3,top+7,top+10,pal['glass'])
    part+=beam((0,0,top),(0,0,top-36),.3,pal['iron'])+box(-2,2,-2,2,top-40,top-36,pal['iron'])
    return t,part,(x,DOCK_Y,0)

def weld_points(name):
    """Arc-welding spots on the hulls' waterline beside each berth (model space)."""
    pts=[]
    berths=BERTHS[name];bx,by=berths[0][:2];pts+=[(bx-60,by+DOCK_HALF-5,WATER_Z+8),(bx+40,by-DOCK_HALF+5,WATER_Z+10),(bx+95,by+DOCK_HALF-6,WATER_Z+6)]
    bx,by=berths[1][:2];pts+=[(bx-30,PIER_Y-PIER_HALF-1.5,WATER_Z+7),(bx+70,PIER_Y-PIER_HALF-1.5,WATER_Z+9)]
    return pts

# ---------------------------------------------------------------- assembly
SEQUENCES=[('Stand',0,7999,0,False),('Walk',8000,8999,0,False),('Attack',9000,9999,0,False),
           ('Death',10000,11999,0,True),('Birth',12000,12999,0,True),('Work',13000,16999,0,False),
           ('Stand Work',17000,20999,0,False),('Decay',21000,21999,0,True),
           # S_DockGate(dock, true) adds 'alternate': the caisson floats out and holds open.
           ('Stand Alternate',22000,23999,0,True)]
GATE_OPEN_MS=1600
def _span(name):return next((a,b) for n,a,b,_,_ in SEQUENCES if n==name)
END=SEQUENCES[-1][2]

def parts(name):
    """{'static','jib','travel','weld'} triangle lists plus bone pivots for a variant."""
    variant,size=MODELS[name];pal=PALETTES[variant];_use(size)
    static=waterfront(pal,variant)+railway(pal)+shops(pal,variant)+fuel_farm(pal)
    tower,jib,jib_pivot=quay_crane(pal,variant)
    frame,travel,travel_pivot=travelling(pal,variant)
    gate,gate_pivot=caisson(pal)
    weld=[]
    for x,y,z in weld_points(name):
        weld+=box(x-1.2,x+1.2,y-1.2,y+1.2,z-1.2,z+1.2,pal['flash'])+box(x-.5,x+.5,y-.5,y+.5,z+1.2,z+2.8,pal['arc'])
    return dict(static=static+tower+frame,jib=jib,travel=travel,weld=weld,jib_pivot=jib_pivot,travel_pivot=travel_pivot,
                gate=gate,gate_pivot=gate_pivot,gate_slide=gate_slide())

def triangles(name):
    """Every triangle at rest, in model space (icons, contact sheets, budgets)."""
    p=parts(name)
    return (p['static']+gi.transform(p['jib'],1,p['jib_pivot'])+gi.transform(p['travel'],1,p['travel_pivot'])+
            gi.transform(p['gate'],1,p['gate_pivot']))

def _split(tris,bone,alpha=None):
    return [rm.Layer([t for t in tris if t[1]!=TEAM],rm.OPAQUE,bone,alpha),rm.Layer([t for t in tris if t[1]==TEAM],rm.TEAMCOL,bone,alpha)]

def _flicker(phase):
    """Arc flashes in Work and Stand Work: short irregular bursts, dark otherwise."""
    keys={0:0.0,END:0.0}
    for a,b in (_span('Work'),_span('Stand Work')):
        keys[a]=0.0;t=a+phase
        while t+260<b:
            keys[t]=0.0;keys[t+1]=1.0;keys[t+90]=.35;keys[t+150]=1.0;keys[t+230]=0.0
            t+=520+(phase*7+t)%430
        keys[b]=0.0
    return sorted(keys.items())

def root_track():
    """Root translation keys: level in every sequence, sinking only in Death and held under in
    Decay. WC3 holds a track's interpolated value through sequences without keys, so a level key
    must close the gap before Decay (Work / Stand Work otherwise slid toward -60 while producing)."""
    d0,d1=_span('Death');k0,k1=_span('Decay')
    keys=[(0,0,0,0),(d0,0,0,0),(d0+400,0,0,-8),(d1,0,0,-60),(d1+1,0,0,0),(k0-1,0,0,0),(k0,0,0,-60),(k1,0,0,-60)]
    return keys+([(k1+1,0,0,0),(END,0,0,0)] if END>k1 else [])

def gate_track(slide):
    """Caisson keys: closed (rest) everywhere; in 'Stand Alternate' it floats seaward, then
    slides clear of the entrance and holds (the sequence does not loop)."""
    a,b=_span('Stand Alternate');dx,dy,dz=slide
    return [(0,0,0,0),(a,0,0,0),(a+GATE_OPEN_MS*2//5,dx,0,dz),(a+GATE_OPEN_MS,dx,dy,dz),(b,dx,dy,dz)]

def mdx(name):
    p=parts(name);variant=MODELS[name][0]
    bones=[rm.Bone('Root'),rm.Bone('Crane',0,p['jib_pivot']),rm.Bone('Travel',0,p['travel_pivot']),
           rm.Bone('Gate',0,p['gate_pivot'])]
    root,crane,travel,gate=bones
    gate.translation=gate_track(p['gate_slide'])
    d0,d1=_span('Death')
    root.translation=root_track()
    # Slew: a slow pick-and-place swing; faster cycles while repairing.
    def slew(a,b,angles):
        n=len(angles)-1;return [(int(a+(b-a)*i/n),*rm.quat_axis('z',ang)) for i,ang in enumerate(angles)]
    rest=rm.quat_axis('z',0)
    crane.rotation=(slew(*_span('Stand'),[0,0,32,32,0,0])+slew(*_span('Work'),[0,40,40,-20,-20,0])+
                    slew(*_span('Stand Work'),[0,-25,-25,30,30,0])+
                    [(t,*rest) for t in (8000,8999,9000,9999,d0,d1,12000,12999,21000,END)])
    if variant=='usn':   # portal crane travels along the dock wall
        move=lambda a,b,d:[(a,0,0,0),(a+(b-a)//3,d,0,0),(a+2*(b-a)//3,d,0,0),(b,0,0,0)]
    else:                # gantry trolley runs across the dock
        move=lambda a,b,d:[(a,0,0,0),(a+(b-a)//3,0,d*.5,0),(a+2*(b-a)//3,0,d*.5,0),(b,0,0,0)]
    travel.translation=(move(*_span('Stand'),-24)+move(*_span('Work'),40)+move(*_span('Stand Work'),-40)+
                        [(t,0,0,0) for t in (8000,8999,9000,9999,d0,d1,12000,12999,21000,END)])
    layers=_split(p['static'],0)+_split(p['jib'],1)+_split(p['travel'],2)+_split(p['gate'],3)
    welds=weld_points(name);per=len(p['weld'])//len(welds)
    for i in range(len(welds)):
        layers.append(rm.Layer(p['weld'][i*per:(i+1)*per],rm.ADD,0,_flicker(97*i+40)))
    return rm.emit(name,layers,bones,SEQUENCES,camera_scale=1.4)

def preview(name,size=512,background=(40,92,112,255)):
    """Front-three-quarter render (gltf_import.preview) over a sea-coloured background."""
    return gi.preview(gi.transform(triangles(name),yaw=180),size,background)
