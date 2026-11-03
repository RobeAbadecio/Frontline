"""Original dimensioned April 1945 Yamato reconstruction, authored in metres.

Axes: +X bow, +Y port, +Z up; z=0 design waterline. Documented historical
dimensions are exact; station/fitting geometry is a reference-based reconstruction,
not a shipyard CAD survey. See docs/games/warcraft-3/yamato-model.md.
"""
import math
from functools import lru_cache

from tools.frontline import gltf_import as gi

LENGTH = 263.0
BEAM = 38.9
DRAFT = 10.4
WORLD_SCALE = 344.0 / LENGTH  # retain capital-ship length, uniformly on all axes
# Plan-derived stations relative to LOA midpoint, not the old stylized layout.
BATTERIES_M = ((50.5, 0, 8.9), (26.5, 0, 12.5), (-63.5, 0, 8.9))
BATTERIES = tuple(tuple(v * WORLD_SCALE for v in p) for p in BATTERIES_M)
MUZZLE_M = (25.4, 0, 4.25)
TURRET_MODEL = 'yamato_turret'
TURRET_AA_MODEL = 'yamato_turret_aa'

GREY = (102, 109, 112)
LIGHT = (124, 130, 130)
DARK = (60, 67, 70)
STEEL = (79, 87, 91)
BLACK = (28, 32, 33)
RED = (117, 43, 39)
BRASS = (152, 129, 69)
GLASS = (31, 45, 49)
CANVAS = (181, 175, 151)
WOOD = (170, 156, 120)


class Mesh:
    def __init__(self):
        self.tris = []

    def face(self, points, colour=GREY, tag='fitting'):
        for i in range(1, len(points)-1):
            tri = (points[0], points[i], points[i+1])
            n = gi._cross(gi._sub(tri[1], tri[0]), gi._sub(tri[2], tri[0]))
            if gi._dot(n, n) > 1e-18:
                self.tris.append((tri, colour, tag))

    def box(self, x, y, z, w, d, h, colour=GREY, tag='fitting'):
        self.tris.extend((p, c, tag) for p, c, _ in gi.boxes([(x,y,z,w/2,d/2,h,colour)]))

    def loft(self, rings, colour=GREY, tag='fitting', caps=True):
        # Rings counter-clockwise as seen from the top, progressing upward.
        for a, b in zip(rings, rings[1:]):
            for i in range(len(a)):
                j = (i+1) % len(a)
                self.face((a[i],a[j],b[j],b[i]),colour,tag)
        if caps:
            self.face(tuple(reversed(rings[0])),colour,tag)
            self.face(rings[-1],colour,tag)

    def ellipse(self, x, y, z, rx, ry, h, colour=GREY, n=20, taper=1, tag='fitting', shift=0):
        rings = [[(x+rx*sc*math.cos(i*math.tau/n),y+dy+ry*sc*math.sin(i*math.tau/n),zz)
                  for i in range(n)] for zz,sc,dy in ((z,1,0),(z+h,taper,shift))]
        self.loft(rings,colour,tag)

    def rod(self, a, b, radius, colour=GREY, n=6, end_radius=None, tag='fitting'):
        delta = gi._sub(b,a)
        length = math.sqrt(gi._dot(delta,delta))
        if length < 1e-8:return
        direction = tuple(v/length for v in delta)
        u = gi._cross(direction,(0,0,1) if abs(direction[2])<.9 else (0,1,0))
        ul = math.sqrt(gi._dot(u,u)); u = tuple(v/ul for v in u)
        v = gi._cross(direction,u)
        rings = [[tuple(p[j]+r*(u[j]*math.cos(i*math.tau/n)+v[j]*math.sin(i*math.tau/n)) for j in range(3))
                  for i in range(n)] for p,r in ((a,radius),(b,radius if end_radius is None else end_radius))]
        self.loft(rings,colour,tag)

    def house(self, x, y, z, w, d, h, colour=GREY, taper=.92, tag='fitting'):
        # Chamfered octagonal house with a visibly sloping upper wall.
        def ring(zz,sc):
            a,b=w*sc/2,d*sc/2; c=min(a,b)*.22
            return [(x+px,y+py,zz) for px,py in ((a,-b+c),(a,b-c),(a-c,b),(-a+c,b),
                    (-a,b-c),(-a,-b+c),(-a+c,-b),(a-c,-b))]
        self.loft((ring(z,1),ring(z+h*.65,1),ring(z+h,taper)),colour,tag)

    def rail(self, points, height=1.05, colour=LIGHT, tag='railing'):
        for a,b in zip(points,points[1:]):
            for z in (.48,height):
                self.rod((a[0],a[1],a[2]+z),(b[0],b[1],b[2]+z),.025,colour,4,tag=tag)
        for p in points:
            self.rod(p,(p[0],p[1],p[2]+height),.034,colour,5,tag=tag)

    def transformed(self, x=0,y=0,z=0,yaw=0):
        c,s=math.cos(yaw),math.sin(yaw)
        return [(tuple((x+c*a-s*b,y+s*a+c*b,z+d) for a,b,d in pts),col,tag) for pts,col,tag in self.tris]


# Width fractions sampled against the public 1945 plan/profile. Smooth cosine
# interpolation avoids the straight triangular bow / rectangular stern of boxes.
STATIONS = ((-131.5,.015),(-128,.20),(-122,.37),(-112,.48),(-101,.57),
            (-91,.65),(-82,.83),(-75,.94),(-65,.985),(-45,1),(-15,1),
            (15,.995),(35,.955),(55,.85),(75,.67),(95,.45),(113,.26),
            (125,.16),(130,.08),(131.5,0))


def width(x):
    for (a,wa),(b,wb) in zip(STATIONS,STATIONS[1:]):
        if a <= x <= b:
            t=(x-a)/(b-a); t=(1-math.cos(math.pi*t))/2
            return (wa+(wb-wa)*t)*BEAM/2
    return 0


def deck_z(x):
    # The forward dip and raised bow are characteristic, with a low aircraft deck.
    if x < -78:return 6.1
    if x < -68:return 6.1+(x+78)/10*1.9
    if x < 50:return 8.0
    return 7.4+2.7*((x-50)/81.5)**1.5


def hull_mesh():
    m=Mesh(); stations=160; sections=[]
    for i in range(stations+1):
        x=-LENGTH/2+LENGTH*i/stations
        w=width(x); top=deck_z(x)
        # Separate black boot-topping, red bilge and a flat-bottomed full hull.
        bow=max(0,(x-111)/20.5); stern=max(0,(-x-104)/27.5)
        section=[]
        for factor,z in ((1,top),(.985,2),(.975,.3),(.97,-.6),(.94,-3.2),(.84,-7.6),(.56,-DRAFT),(0,-DRAFT)):
            below=max(0,-z)/DRAFT
            px=x-bow*((top-z)*.19+max(0,-z)*.45)+stern*20*below
            zz=z+stern**2*5.5*below
            section.append((px,w*factor,zz))
        sections.append(section)
    colours=(GREY,GREY,BLACK,RED,RED,RED,RED)
    for a,b in zip(sections,sections[1:]):
        for j,col in enumerate(colours):
            for s in (-1,1):
                pts=[(p[0],s*p[1],p[2]) for p in (a[j],a[j+1],b[j+1],b[j])]
                m.face(pts[::-1] if s==1 else pts,col,'hull')
    # Close stern/bow profiles; bow bulb is part of the designed LOA envelope.
    for sec,rev in ((sections[0],False),(sections[-1],True)):
        pts=sec+[ (x,-y,z) for x,y,z in reversed(sec[:-1]) ]
        m.face(pts[::-1] if rev else pts,GREY,'hull_end')
    bulb=[]
    for x,ry,rz,cz in ((116,1.9,2.5,-6.8),(124,2.4,3.1,-6.6),(129.5,1.6,2.4,-6.4),(131,.05,.1,-6.2)):
        bulb.append([(x,ry*math.cos(i*math.tau/24),cz+rz*math.sin(i*math.tau/24)) for i in range(24)])
    # Elliptic rings here progress along X, normals still wind outwards.
    m.loft(bulb,RED,'bulbous_bow')
    # Bilge keels, exposed shaft brackets and four 5m propellers.
    for side in (-1,1):
        m.rod((-48,side*15,-8),(62,side*14,-8),.14,RED,6,tag='bilge_keel')
        for yy,xx in ((5.0,-112),(9.0,-103)):
            y=side*yy
            m.rod((xx+24,y,-7.7),(xx,y,-8.1),.26,STEEL,10,tag='propeller_shaft')
            m.rod((xx+8,y,-7.9),(xx+12,side*12,-6),.18,RED,8,tag='shaft_bracket')
            m.rod((xx-.5,y,-8.1),(xx+1,y,-8.1),.65,BRASS,12,tag='propeller_hub')
            for k in range(3):
                ang=k*math.tau/3
                p=[]
                for r,da,dx in ((.5,-.3,0),(2.5,-.15,.25),(2.35,.34,.12),(.6,.55,-.1)):
                    p.append((xx+dx,y+r*math.cos(ang+da),-8.1+r*math.sin(ang+da)))
                m.face(p,BRASS,'propeller');m.face(p[::-1],BRASS,'propeller')
    for x,z,w,h in ((-121,-10.35,3.6,5.9),(-108,-10.35,2.8,4.5)):
        m.house(x,0,z,w,.55,h,RED,tag='rudder')
    return m


def deck_mesh():
    m=Mesh()
    # Match the hull's station tessellation exactly. The fine plank strips are
    # an overlay: clipping them alone dropped tapered edge wedges at the stern.
    for i in range(160):
        a=-LENGTH/2+LENGTH*i/160;b=-LENGTH/2+LENGTH*(i+1)/160
        m.face(((a,-width(a),deck_z(a)-.006),(b,-width(b),deck_z(b)-.006),
                (b,width(b),deck_z(b)-.006),(a,width(a),deck_z(a)-.006)),
               STEEL if a<-70 or a>86 else WOOD,'deck_surface')
    # Individual longitudinal planks: 280mm wide, staggered joints, no texture
    # dependency. Grey forepeak and steel aircraft deck remain unplanked.
    plank=.28
    for i in range(140):
        y0=-BEAM/2+i*plank; y1=min(y0+plank,BEAM/2)
        tone=(.94,.98,1.02,1.045,1.0)[i%5]
        col=tuple(int(c*tone) for c in WOOD)
        for j in range(100):
            x0=-131.5+j*LENGTH/100;x1=x0+LENGTH/100
            w0,w1=width(x0),width(x1)
            a,b=max(y0,-w0),min(y1,w0);c,d=max(y0,-w1),min(y1,w1)
            if b<=a or d<=c:continue
            colour=STEEL if (x0 < -70 or x0 > 86) else col
            m.face(((x0,a,deck_z(x0)),(x1,c,deck_z(x1)),(x1,d,deck_z(x1)),(x0,b,deck_z(x0))),colour,'deck_plank')
        for j in range(16):
            x=-68+j*9.2+(i%3)*3.05
            if x>86 or abs(y0)>width(x)-.5:continue
            m.box(x,y0+plank/2,deck_z(x)+.012,.018,plank*.9,.008,(125,116,94),'plank_joint')
    # Main barbettes remain on the hull; rotating houses are separate edicts.
    for index,(x,y,z) in enumerate(BATTERIES_M):
        m.ellipse(x,y,deck_z(x),6.65,6.65,z-deck_z(x)+.3,GREY,40,tag='barbette_'+str(index))
        m.ellipse(x,y,z-.15,6.85,6.85,.22,DARK,40,tag='turret_race')
    # The aircraft deck is a continuous steel surface. Do not paint black
    # rectangles on the hull to fake the side handling recesses.
    return m


def secondary(m,x,z,aft=False):
    part=Mesh()
    part.ellipse(0,0,0,3.5,3.5,.7,GREY,24,tag='155mm_barbette')
    part.house(0,0,.7,7.9,6.8,3.1,GREY,.82,'155mm_turret')
    part.box(-.4,0,3.8,.7,8.8,.55,LIGHT,'155mm_rangefinder')
    for y in (-1.75,0,1.75):
        part.rod((3,y,2.3),(11.3,y,2.65),.15,STEEL,8,.09,'155mm_barrel')
        part.rod((2.7,y,2.3),(4,y,2.35),.34,CANVAS,8,tag='155mm_blastbag')
    m.tris.extend(part.transformed(x,0,z,math.pi if aft else 0))


def aa25(m,x,y,z,index,single=False,yaw=0,enclosed=False):
    p=Mesh();tag=('25mm_single_' if single else '25mm_triple_')+str(index)
    if not single:
        # Tub has an open interior, rather than a solid cylinder obscuring guns.
        r=1.8
        p.ellipse(0,0,0,r,r,.12,STEEL,16,tag=tag)
        if enclosed:p.house(0,-.1,.1,3.3,3.1,1.6,GREY,.8,tag)
        else:
            for i in range(16):
                a,b=i*math.tau/16,(i+1)*math.tau/16
                p.face(((r*math.cos(a),r*math.sin(a),.1),(r*math.cos(b),r*math.sin(b),.1),
                        (r*math.cos(b),r*math.sin(b),.75),(r*math.cos(a),r*math.sin(a),.75)),GREY,tag)
    p.ellipse(0,0,.15,.23,.23,.85,STEEL,8,tag=tag)
    p.box(0,0,.9,1.2 if not single else .45,.7,.35,STEEL,tag)
    for yy in ((-.32,0,.32) if not single else (0,)):
        p.rod((.2,yy,1.05),(1.9,yy,1.7),.034,BLACK,6,tag=tag+'_barrel')
        p.box(-.1,yy,1.18,.42,.15,.26,DARK,tag)
    if not single:
        for yy in (-.65,.65):p.box(-.55,yy,.45,.45,.4,.1,DARK,tag)
    m.tris.extend(p.transformed(x,y,z,yaw))


def armament_mesh():
    m=Mesh();secondary(m,11.5,12);secondary(m,-48.5,11.5,True)
    # Six original enclosed 127mm twins, six added open twins in the outer row.
    for s in (-1,1):
        for j,x in enumerate((-3.5,-14,-25)):
            for outer in (False,True):
                y=s*(11.2 if not outer else 17.7);z=12.4 if not outer else 10.2
                p=Mesh();tag='127mm_twin_'+str((s+1)*3+j*2+int(outer))
                p.ellipse(0,0,-1.8,2.75,2.75,1.8,GREY,20,tag=tag)
                if not outer:p.house(0,0,0,5.5,5,3.0,GREY,.83,tag)
                else:
                    p.box(-1,0,.2,.3,4.3,2.3,GREY,tag)
                    p.box(0,0,.2,2.3,3.2,.65,STEEL,tag)
                for yy in (-.65,.65):
                    p.rod((.6,yy,1.7),(5.4,yy,2.65),.14,STEEL,10,.09,tag+'_barrel')
                    p.rod((0,yy,1.6),(1.6,yy,1.9),.28,GREY,10,tag=tag)
                m.tris.extend(p.transformed(x,y,z,s*math.pi/2))
    positions=[]
    for s in (-1,1):
        positions += [(x,s*11.5,deck_z(x)+.12,s*1.15,False) for x in (37,17)]
        positions += [(x,s*(width(x)-1.6),deck_z(x)+.18,s*1.8,False) for x in (-44,-53,-60,-78,-94,-101,-108)]
        positions += [(x,s*18.4,10.3,s*math.pi/2,True) for x in (2.5,-9,-19.5,-30.5,-36.5)]
        positions += [(x,s*12,16.1,s*math.pi/2,False) for x in (-7,-17,-29,-37)]
        positions += [(x,s*5.3,zz,s*math.pi/2,True) for x,zz in ((-43,14.5),(-35,18.9),(-19,20.5),(-27,19.2))]
        positions += [(-121,s*5.5,6.2,math.pi,False)]
    # Four remaining triples ride the roofs of turrets II/III, and must rotate
    # with those child models rather than remaining fixed in the hull geometry.
    assert len(positions)==46
    for i,(x,y,z,yaw,enclosed) in enumerate(positions):
        if abs(y)>8 and z>10:
            m.ellipse(x,y,z-.35,1.85,1.85,.35,STEEL,16,tag='aa_sponson')
            m.rod((x,y,deck_z(x)),(x,y,z-.35),.32,GREY,10,tag='aa_platform_support')
        aa25(m,x,y,z,i,yaw=yaw,enclosed=enclosed)
    for i,(x,s) in enumerate(( (x,s) for x in (70,82,-115) for s in (-1,1) )):
        aa25(m,x,s*(width(x)-1.0),deck_z(x)+.1,i,True,s*math.pi/2)
    return m


def superstructure_mesh():
    m=Mesh()
    # The 1945 bridge has rounded continuous walls and irregular shoulders;
    # a stack of chamfered rectangular houses does not reproduce its outline.
    for x,y,z,w,d,h in ((-18,0,8,58,17,3.3),(-21,0,11.3,44,12.5,3),
                         (-26,0,14.3,23,10,4.3)):
        m.house(x,y,z,w,d,h,GREY,.96,'deckhouse')

    def tower_ring(z,x,rx,ry):
        # Full rounded foreface, clipped aft services wall. Thirty-two facets
        # preserve the cylindrical corners through all levels of the tower.
        return [(x+rx*max(-.88,math.cos(i*math.tau/32)),ry*math.sin(i*math.tau/32),z)
                for i in range(32)]
    def shell(rows,tag,colour=GREY):
        m.loft([tower_ring(*r) for r in rows],colour,tag)
    shell(((11.3,-3.7,6.7,6.3),(16.8,-3.7,6.65,6.3),(18.2,-3.8,6.45,6.15)),
          'lower_command_block')
    shell(((18.2,-4.1,6.0,5.85),(21.5,-4.1,6.0,5.85)), 'lower_navigation_bridge')
    shell(((21.5,-4.1,6.5,6.25),(21.75,-4.1,6.5,6.25)), 'lower_observation_deck',LIGHT)
    shell(((21.75,-5.0,4.5,4.7),(25,-5.15,4.4,4.55),
           (29.8,-5.45,4.15,4.25),(32.2,-5.55,4.1,4.15)), 'bridge_tower')

    # Continuous narrow lower navigation glazing, separated by individual
    # pillars, follows the curved front and shoulders under the deck lip.
    for i in range(25):
        a=-math.pi*.72+i*math.pi*1.44/24;da=.065
        pts=[(-4.1+6.025*math.cos(q),5.875*math.sin(q),z)
             for q,z in ((a-da,20.85),(a+da,20.85),(a+da,21.30),(a-da,21.30))]
        m.face(pts,GLASS,'lower_navigation_window')
    for s in (-1,1):
        m.rail([(-7.6,s*6.1,21.75),(-4.2,s*6.1,21.75),(-1.7,s*5.8,21.75)],.78)

    def instrument_sponson(x,y,z,rx,ry,screen=True):
        # Rounded projecting floor with a downward tapered bearing support.
        m.ellipse(x,y,z-1.1,rx*.55,ry*.55,1.1,GREY,24,taper=1/.55,tag='bridge_sponson_support')
        m.ellipse(x,y,z,rx,ry,.17,LIGHT,24,tag='bridge_sponson_deck')
        if screen:
            for i in range(24):
                a,b=i*math.tau/24,(i+1)*math.tau/24
                pts=[(x+rx*math.cos(q),y+ry*math.sin(q),h)
                     for q,h in ((a,z+.17),(b,z+.17),(b,z+.85),(a,z+.85))]
                m.face(pts,GREY,'bridge_sponson_screen');m.face(pts[::-1],GREY,'bridge_sponson_screen')

    # One pronounced upper navigation/air-defence platform, with a solid
    # splinter screen. A low open gallery runs around its perimeter.
    m.house(-5.3,0,32.15,10.1,11.3,.24,LIGHT,1,'upper_bridge_platform')
    m.house(-5.35,0,31.25,8.9,10.4,.85,GREY,.98,'navigation_bridge')
    outline=[(-.35,-3.95),(-.35,3.95),(-1.25,5.35),(-8.7,5.35),
             (-10.15,3.8),(-10.15,-3.8),(-8.7,-5.35),(-1.25,-5.35)]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        pts=[(*a,32.39),(*b,32.39),(*b,33.25),(*a,33.25)]
        m.face(pts,GREY,'upper_bridge_screen');m.face(pts[::-1],GREY,'upper_bridge_screen')
        m.rod((*a,33.25),(*b,33.25),.045,LIGHT,5,tag='screen_cap')
    # Glazing is confined to the actual observation bands, not every storey.
    for yy in (-3.3,-2.2,-1.1,0,1.1,2.2,3.3):
        m.box(-.87,yy,31.43,.07,.72,.45,GLASS,'navigation_window')
    for s in (-1,1):
        for xx in (-2,-3.25,-4.5,-5.75,-7):
            m.box(xx,s*5.13,31.43,.77,.06,.45,GLASS,'navigation_window')
        # Front optical/control stations and aft ventilator shoulders have
        # curved underbodies, not square floating AA turrets.
        for x,y,z,rx,ry in ((-.7,s*5.1,21.75,1.8,1.65),(-7.9,s*4.7,24.0,1.65,1.7),
                            (-5.8,s*5.55,18.3,2.15,1.5)):
            instrument_sponson(x,y,z,rx,ry)
        m.ellipse(-.7,s*5.1,21.95,.85,.8,1.35,GREY,20,tag='bridge_control_station')
        m.rod((-.7,s*5.1-.95,22.85),(-.7,s*5.1+.95,22.85),.1,DARK,8,tag='bridge_control_optics')
        # Curved ventilation hoods on the aft shoulders, with recessed louvres.
        for x,z in ((-7.9,24.15),(-5.8,18.5)):
            m.house(x,s*5.0,z,1.35,1.45,1.85,GREY,.85,'bridge_vent_hood')
            for j in range(7):
                m.box(x+.69,s*5.0,z+.35+j*.18,.035,1.03,.045,DARK,'bridge_vent_louvre')
        for xx in (-5.7,-4.4,-3.1):
            m.box(xx,s*6.1,16.15,.85,.045,.42,GLASS,'lower_command_window')
        # Type 22 horns have their own small curved shoulder and brackets.
        instrument_sponson(-3.8,s*4.35,27.0,1.7,1.15,False)
        # Portholes placed along the curved upper forward face.
        for a in (-.78,-.32,.32,.78):
            x=-5.3+4.29*math.cos(a);yy=4.4*math.sin(a)
            if yy*s<0:continue
            for z in (25.9,29.4):
                m.rod((x,yy,z),(x+.08*math.cos(a),yy+.08*math.sin(a),z),.145,LIGHT,12,tag='bridge_scuttle_rim')
                m.rod((x+.085*math.cos(a),yy+.085*math.sin(a),z),(x+.10*math.cos(a),yy+.10*math.sin(a),z),.105,GLASS,12,tag='bridge_scuttle')
        for xx in (-7.7,-8.35):m.rod((xx,s*4.6,21.8),(xx,s*4.35,31.1),.04,LIGHT,5,tag='ladder')
        for i in range(23):
            z=21.8+i*.4; yy=s*(4.6-(z-21.8)/9.3*.25)
            m.rod((-7.7,yy,z),(-8.35,yy,z),.024,LIGHT,4,tag='ladder_rung')
        m.rod((-8.8,s*2.5,19),(-9.1,s*2.5,31),.19,STEEL,10,tag='bridge_service_trunk')
    # Narrow eyebrow walkway and visible vertical gussets under the upper
    # observation platform, prominent in the close Tamiya bridge reference.
    for i in range(13):
        a=-1.15+i*2.3/12
        x=-5.55+4.12*math.cos(a);yy=4.22*math.sin(a)
        outer=(-5.3+5.0*math.cos(a),5.35*math.sin(a),31.25)
        m.rod((x,yy,30.5),outer,.055,STEEL,5,tag='upper_bridge_bracket')
    shell(((30.95,-5.55,4.65,4.7),(31.12,-5.55,4.65,4.7)), 'upper_bridge_eyebrow',LIGHT)
    # Armoured conning position at the forward foot of the tower.
    m.ellipse(1.2,0,11.5,2.9,3.0,4.2,GREY,28,tag='conning_tower')
    m.ellipse(1.2,0,15.7,3.15,3.25,.23,LIGHT,28,tag='conning_roof')
    # Type 94 director and 15 m optical rangefinder form the characteristic crown.
    m.ellipse(-5.55,0,32.4,2.65,2.65,3.05,GREY,32,tag='main_director')
    m.ellipse(-5.55,0,35.45,2.9,2.9,.24,LIGHT,32,tag='director_walkway')
    m.rod((-5.55,-7.5,35.05),(-5.55,7.5,35.05),.62,GREY,16,tag='15m_rangefinder')
    for s in (-1,1):
        m.house(-5.55,s*7.0,34.35,1.6,1.3,1.35,GREY,.95,'rangefinder_end')
        for zz in (34.8,35.2):
            m.rod((-4.73,s*7.0,zz),(-4.69,s*7.0,zz),.13,BLACK,8,tag='rangefinder_optics')
    m.ellipse(-5.55,0,35.7,1.85,1.85,2.5,GREY,28,tag='director_roof')
    m.ellipse(-5.55,0,38.2,2.02,2.02,.18,LIGHT,28,tag='director_roof_lip')
    # Optical apertures and railing distinguish the director crown from a
    # featureless cylinder. Positions follow the cylindrical wall normals.
    for z,rx,zz in ((34.05,2.655,.65),(37.25,1.855,.40)):
        for i in range(11):
            a=-math.pi*.78+i*math.pi*1.56/10
            da=.12
            pts=[(-5.55+rx*math.cos(q),rx*math.sin(q),h)
                 for q,h in ((a-da,z),(a+da,z),(a+da,z+zz),(a-da,z+zz))]
            m.face(pts,GLASS,'director_window')
    m.rail([(-5.55+2.84*math.cos(i*math.tau/20),2.84*math.sin(i*math.tau/20),35.69)
            for i in range(21)],.75,tag='director_railing')
    # Paired Type 21 antenna frames sit over the two rangefinder arms.
    for s in (-1,1):
        for yy in (s*3.5,s*6.4):m.rod((-5.7,yy,35.5),(-5.7,yy,36.6),.055,GREY,6,tag='radar_support')
        for j in range(9):
            yy=s*(3.1+j*.45)
            m.rod((-5.7,yy,36.6),(-5.7,yy,38.5),.028,DARK,5,tag='type21_radar')
        for j in range(6):
            z=36.6+j*.38
            m.rod((-5.7,s*3.1,z),(-5.7,s*6.7,z),.028,DARK,5,tag='type21_radar')
        # Paired Type 22 horns point forward beside the upper tower.
        for z in (27.5,28.35):
            m.rod((-4.2,s*4.65,z),(-2.5,s*4.65,z),.21,GREY,12,.40,'type22_horn')
        # Binoculars around the open top platform.
        for x in (-1.8,-3.7,-7.5):
            m.rod((x,s*4.65,32.4),(x,s*4.65,33.4),.07,GREY,6,tag='binocular_stand')
            for yy in (-.12,.12):m.rod((x,s*4.65+yy,33.4),(x+.45,s*4.65+yy,33.5),.09,DARK,8,tag='binocular')
    m.rod((-6.4,0,38.4),(-6.8,0,40.3),.06,GREY,8,tag='foretop_aerial')
    m.rod((-6.8,0,40.3),(-7.25,0,42.0),.045,GREY,8,tag='foretop_aerial')
    # Profile comparison: the upper observation platform is about 5 m above
    # the funnel rim. Lift it to 34.35 m, extending only the exposed tower core;
    # the lower bridge and all deck/battery stations stay fixed.
    def bridge_height(z):
        return z+2.2*max(0,min(1,(z-21.75)/(32.2-21.75)))
    m.tris=[(tuple((x,y,bridge_height(z)) for x,y,z in pts),colour,tag)
            for pts,colour,tag in m.tris]
    # Single aft-raked trunk: ring offsets form one continuous funnel surface.
    rings=[]
    for z,xc,rx,ry in ((14,-22,5.9,3.7),(20,-24,5.3,3.6),(26,-27,4.9,3.5),(29,-28.5,4.9,3.5)):
        rings.append([(xc+rx*math.cos(i*math.tau/32),ry*math.sin(i*math.tau/32),z) for i in range(32)])
    m.loft(rings,GREY,'funnel',False)
    m.ellipse(-28.7,0,29,4.95,3.55,1.3,BLACK,32,tag='funnel_cap')
    m.ellipse(-28.8,0,30.31,4.25,2.9,.025,(17,20,21),32,tag='funnel_mouth')
    for y in (-2,-1,0,1,2):m.rod((-32.6,y,30.4),(-25,y,30.4),.055,DARK,5,tag='funnel_grille')
    for s in (-1,1):
        for x in (-19,-24):m.rod((x,s*3.3,15),(x-3,s*3.7,28),.17,STEEL,8,tag='steam_pipe')
        m.rod((-19,s*3.8,16),(-30,s*3.8,28.5),.07,LIGHT,6,tag='funnel_stay')
    # Aft director on a narrow pedestal, with local wing platforms rather than
    # the previous tall rectangular chimney-like block.
    m.house(-42,0,11.3,6.9,6.7,4.0,GREY,.9,'aft_bridge_base')
    m.ellipse(-42,0,15.3,2.2,2.5,4.9,GREY,24,taper=.82,tag='aft_director_support')
    m.house(-42,0,19.9,6.4,8.2,.3,LIGHT,1,'aft_gallery')
    m.ellipse(-42,0,20.2,2.1,2.1,3.5,GREY,24,tag='aft_director')
    m.ellipse(-42,0,23.7,2.3,2.3,.22,LIGHT,24,tag='aft_director_roof')
    m.rod((-42,-5,22.8),(-42,5,22.8),.35,GREY,12,tag='10m_rangefinder')
    return m


def fittings_mesh():
    m=Mesh()
    # Anchor deck: two chain runs with raised alternate links, windlasses,
    # bollards, fairleads, hatches, vents and a small chrysanthemum bow crest.
    for s in (-1,1):
        for x in (96,104):
            m.ellipse(x,s*3.3,deck_z(x),.7,.7,.95,GREY,14,tag='capstan')
            m.ellipse(x,s*3.3,deck_z(x)+.95,.95,.95,.17,DARK,14,tag='capstan_head')
        for i in range(59):
            x=96+i*.49;y=s*(3.3+(x-96)*.04);z=deck_z(x)+.12
            m.rod((x,y-.13,z),(x+.32,y+.13,z+.09),.055,DARK,5,tag='anchor_chain')
        for x in (-119,-110,-84,-58,8,48,79,119):
            y=s*(width(x)-.75);z=deck_z(x)
            m.box(x,y,z,1.7,.65,.16,STEEL,'bollard_base')
            for dx in (-.48,.48):m.ellipse(x+dx,y,z+.16,.16,.16,.52,DARK,8,tag='bollard')
        # Side scuttles and degaussing cable follow the faired hull.
        cable=[]
        for i in range(89):
            x=-117+i*2.65; y=s*(width(x)*.998+.035)
            cable.append((x,y,deck_z(x)-1.0))
            if x>-80:
                m.rod((x,y,3.7),(x,y+s*.035,3.7),.115,BLACK,8,tag='scuttle')
        for a,b in zip(cable,cable[1:]):m.rod(a,b,.045,STEEL,5,tag='degaussing_cable')
        m.rod((125,s*2.4,3),(124,s*3.5,1),.22,DARK,8,tag='anchor')
        m.rod((124,s*3.5,1),(122.5,s*4.3,2.4),.2,DARK,8,tag='anchor_fluke')
        m.rod((124,s*3.5,1),(125.5,s*2.7,2.4),.2,DARK,8,tag='anchor_fluke')
    m.rod((131.1,0,8.4),(131.25,0,8.4),.48,BRASS,16,tag='bow_crest')
    for x in (-115,-88,-59,0,57,86,110):
        m.house(x,0,deck_z(x)+.05,1.7,1.2,.25,GREY,tag='hatch')
    for s in (-1,1):
        for x in (-60,-45,-30,-12,14,53):
            y=s*(width(x)-3);z=deck_z(x)
            m.box(x,y,z,1.4,.9,.5,GREY,'ammunition_locker')
            m.box(x+.71,y,z+.13,.03,.65,.18,DARK,'locker_vent')
        for x in (-34,-17,-1):
            m.ellipse(x,s*7,11.3,.55,.55,1.9,GREY,12,tag='ventilator')
            m.rod((x,s*7,13.2),(x+.7,s*7,13.2),.65,DARK,12,tag='ventilator_cowl')
        # Searchlights on the superstructure with a distinct lens face.
        for x in (-14,-32):
            m.rod((x,s*6.8,16.5),(x,s*6.8,18),.12,GREY,8,tag='searchlight_stand')
            m.rod((x,s*6.5,18),(x,s*7.4,18),.75,GREY,16,tag='searchlight')
            m.rod((x,s*7.41,18),(x,s*7.44,18),.61,(171,177,165),16,tag='searchlight_lens')
    # Stern catapults, tracks and turntables. Aircraft were removed before Ten-Go;
    # the reconstruction deliberately leaves the aircraft handling deck clear.
    for s in (-1,1):
        x,y=-117.455,s*9.0;z=6.3
        m.ellipse(x,y,z,1.25,1.25,.4,STEEL,16,tag='catapult_turntable')
        for yy in (-.5,.5):
            m.rod((-127,y+yy-s*2,z+1),(-107.91,y+yy+s*2,z+1),.10,STEEL,6,tag='catapult_rail')
            m.rod((-127,y+yy-s*2,z+.1),(-107.91,y+yy+s*2,z+.1),.10,STEEL,6,tag='catapult_frame')
        for i in range(14):
            xx=-127+i*1.36; yy=y-s*2+(xx+127)/19.09*s*4
            m.rod((xx,yy-.5,z+.1),(xx+1.3,yy+.5,z+1),.055,LIGHT,5,tag='catapult_brace')
            m.rod((xx,yy-.5,z+1),(xx,yy+.5,z+1),.06,LIGHT,5,tag='catapult_sleeper')
        for i in range(13):
            xx=-124+i*2.4;yy=s*(2+(xx+124)*.19)
            m.box(xx,yy,6.15,2.5,.10,.08,(122,91,75),'aircraft_deck_track')
    # Stowed lattice crane rests low over the aircraft deck; the former raised
    # 8.7 m tip made an enormous triangular framework above the stern.
    m.ellipse(-111.5,0,6.1,1.15,1.15,2.1,GREY,18,tag='crane_base')
    for yy in (-.45,.45):
        m.rod((-111.5,yy,8.1),(-131.0,yy,9.3),.09,STEEL,6,tag='crane_jib')
        m.rod((-111.5,yy,9.15),(-131.0,yy,9.3),.09,STEEL,6,tag='crane_jib')
    for i in range(15):
        x=-111.5-i*1.3;z=8.1+i*.08
        m.rod((x,-.45,z),(x-1.3,-.45,9.3),.045,LIGHT,5,tag='crane_lattice')
        m.rod((x,.45,z),(x-1.3,.45,9.3),.045,LIGHT,5,tag='crane_lattice')
        m.rod((x,-.45,z),(x,.45,z),.04,LIGHT,5,tag='crane_crossbar')
    m.rod((-130.7,0,9.3),(-130.7,0,6.9),.025,DARK,5,tag='crane_cable')
    m.rod((-130.7,0,6.9),(-130.3,0,6.6),.08,STEEL,6,tag='crane_hook')
    return m


def rigging_mesh():
    m=Mesh()
    # Peripheral railings have actual metre-size stanchions and two wires.
    for side in (-1,1):
        points=[(x,side*(width(x)-.22),deck_z(x)+.08) for x in
                [-128+i*2.3 for i in range(113)] if -128<=x<=129.6]
        m.rail(points)
    # Tripod mainmast, braced lattice, signal yards and Type 13 ladder radar.
    top=(-35,0,41)
    for base in ((-39,-3.1,14.3),(-39,3.1,14.3),(-31,0,14.3)):
        m.rod(base,top,.18,GREY,8,tag='tripod_mainmast')
    for z in (20,25,30,35):
        t=(z-14.3)/(41-14.3); xx=-39+4*t;yy=3.1*(1-t)
        m.rod((xx,-yy,z),(xx,yy,z),.09,GREY,6,tag='mast_crossbrace')
        m.rod((xx,-yy,z),(xx+1.5,yy*.7,z+4),.07,GREY,5,tag='mast_diagonal')
        m.rod((xx,yy,z),(xx+1.5,-yy*.7,z+4),.07,GREY,5,tag='mast_diagonal')
    for z,w in ((32,12),(38,17)):
        m.rod((-35, -w/2,z),(-35,w/2,z),.1,GREY,8,tag='signal_yard')
        for s in (-1,1):
            m.rod((-35,s*w/2,z),(-35,0,z+2),.035,DARK,5,tag='yard_stay')
            m.rod((-35,s*w/2,z),(-28,s*4,15),.015,DARK,4,tag='signal_halyard')
    for z in (38.2,38.9,39.6,40.3,41,41.7):
        m.rod((-35,-.8,z),(-35,.8,z),.035,DARK,5,tag='type13_radar')
    m.rod((-35,0,38),(-35,0,42.5),.045,GREY,6,tag='type13_radar')
    # Fine standing aerials, bow and stern flagstaffs.
    for s in (-1,1):
        for a,b in (((-35,s*3,38),(-5,s*3,35)),((-35,s*3,38),(-119,0,10))):
            m.rod(a,b,.017,DARK,4,tag='wire_aerial')
    m.rod((129,0,deck_z(129)),(129,0,14),.055,GREY,8,tag='bow_staff')
    m.rod((-129,0,6.1),(-129,0,11.7),.055,GREY,8,tag='stern_staff')
    return m


@lru_cache(maxsize=1)
def body_parts():
    """Named sections bound MDX geoset sizes without losing fine detail."""
    return {name:tuple(fn().tris) for name,fn in (
        ('hull',hull_mesh),('deck',deck_mesh),('superstructure',superstructure_mesh),
        ('armament',armament_mesh),('fittings',fittings_mesh),('rigging',rigging_mesh))}


def turret_m(roof_aa=False):
    m=Mesh()
    m.ellipse(0,0,0,6.7,6.7,.35,DARK,40,tag='main_turret_race')
    # Broad, sloping 650mm armoured face; clipped rear corners and shallow roof.
    lower=[(7.6,-5.7,.35),(7.6,5.7,.35),(4.9,6.8,.35),(-5.5,6.8,.35),
           (-7.2,4.5,.35),(-7.2,-4.5,.35),(-5.5,-6.8,.35),(4.9,-6.8,.35)]
    upper=[(5.8,-5.6,4.95),(5.8,5.6,4.95),(4.3,6.3,5.1),(-5.6,6.3,5.1),
           (-6.6,4.4,5.1),(-6.6,-4.4,5.1),(-5.6,-6.3,5.1),(4.3,-6.3,5.1)]
    m.loft((lower,upper),GREY,'460mm_turret')
    m.rod((-3,-7.5,4.3),(-3,7.5,4.3),.38,LIGHT,12,tag='turret_rangefinder')
    for s in (-1,1):m.house(-3,s*7.1,3.7,1.6,1.1,1.3,GREY,tag='rangefinder_hood')
    for y in (-3.25,0,3.25):
        m.rod((5.4,y,3.75),(8.7,y,3.9),.66,CANVAS,16,.51,'main_blast_bag')
        # 460mm bore, stepped built-up barrel jackets, visible dark muzzle bore.
        for a,b,r0,r1 in ((8.3,12,.49,.45),(12,18,.40,.34),(18,25.4,.31,.29)):
            za=3.9+(a-8.3)*.0205;zb=3.9+(b-8.3)*.0205
            m.rod((a,y,za),(b,y,zb),r0,STEEL,16,r1,'460mm_barrel')
        m.rod((25.405,y,4.2505),(25.42,y,4.2508),.23,BLACK,16,tag='460mm_bore')
    for x in (-4,0,3):
        m.house(x,0,5.12,1.3,1.4,.25,LIGHT,tag='turret_roof_hatch')
        for y in (-5.5,5.5):m.box(x,y,5.11,.75,.35,.22,DARK,'turret_roof_vent')
    if roof_aa:
        for i,s in enumerate((-1,1)):aa25(m,-.5,s*4.4,5.15,46+i,yaw=s*math.pi/2)
    return m.tris


def world(tris):
    return gi.transform(tris,WORLD_SCALE)


def triangles(full=False, metres=False):
    tris=[t for part in body_parts().values() for t in part]
    if full:
        for i,offset in enumerate(BATTERIES_M):
            tris+=gi.transform(turret_m(roof_aa=i>0),1,offset,yaw=180 if i==2 else 0)
    return tris if metres else world(tris)
