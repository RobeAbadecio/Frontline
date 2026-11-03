"""Original MIT WWII warship models, authored bow toward -Y, +X toward port.

Each hull is built from a faired station profile with sheer, boot topping and a
planked deck, then fitted with class-specific superstructure, funnels, masts,
directors, secondary and anti-aircraft mounts, boats, catapults and (carriers)
flight-deck markings, elevators, gallery sponsons and parked aircraft. Colours
come from the 4x4 naval atlas (USN Measure 21 vs IJN grey and wooden decks).
No downloaded mesh or retail content is used.
"""
import math

# Naval atlas cells (tools/frontline/generate.py: naval_atlas). 8 is team colour.
USN=dict(hull=1,lower=0,sup=1,deck=2,fdeck=3,plane=11)  # Measure 22: navy blue band, haze grey above
IJN=dict(hull=4,sup=5,deck=6,fdeck=6,plane=5)
M21=dict(USN,hull=0,lower=0,sup=0)    # Measure 21: navy blue overall (1942-43)
IJN_DD=dict(IJN,deck=7)                # destroyers: brown linoleum decks
TEAM,BOOT,RED,GUN,WHITE,MARK,DARK,BLACK=8,9,10,11,12,13,14,15
PORT,STARBOARD=1,-1
# Shape codes added to a cell for the smooth ship emitter (tools/frontline/ships.py);
# cell = code % 100. Box consumers (footprints, wakes, bounds) only read geometry.
CYL,ROUND,BARREL=100,200,300
HULL_LOG=[]   # (length, beam, pal, sheer, deck, shape, box count) per hull() call, in GEOMETRY order

def hull_width(t,beam,bow=.32,stern=.14,stern_min=.55):
    """Half-beam at t (0 bow .. 1 stern): fine entry, parallel body, rounded stern."""
    if t<bow:return beam*max(.08,(t/bow)**.62)
    if t>1-stern:return beam*(stern_min+(1-stern_min)*((1-t)/stern)**.5)
    return beam

def hull(length,beam,pal,sheer=6,deck=12,stations=24,**shape):
    """Lower hull, boot topping, planked deck and a raked stem."""
    b=[];seg=length/stations
    for i in range(stations):
        t=(i+.5)/stations;y=-length+2*length*t;w=hull_width(t,beam,**shape)
        z=deck+sheer*max(0,(.4-t)/.4)**1.6
        if 'lower' in pal:                                 # dark lower band to the main-deck line
            b+=[(0,y,-7,w,seg+.4,11,pal['lower']),(0,y,4,w,seg+.4,max(.5,z-6),pal['hull'])]
        else:b+=[(0,y,-7,w,seg+.4,z-7-2,pal['hull'])]     # side plating to the deck edge
        b+=[(0,y,-1.5,w+.35,seg+.4,2.6,BOOT)]              # boot topping at the waterline
        b+=[
            (0,y,z-2,max(.5,w-.7),seg+.4,2.2,pal['deck'])] # planked weather deck
    b+=[(0,-length-2,-6,.9,3,deck+sheer+4,pal['hull'])]   # stem
    HULL_LOG.append((length,beam,pal,sheer,deck,shape,len(b)))
    return b

def deck_z(y,length,sheer=6,deck=12):
    t=(y+length)/(2*length)
    return deck+sheer*max(0,(.4-t)/.4)**1.6

def mount(x,y,z,barrels,size,pal,cell=None):
    """Static gun house with barrels toward the bow."""
    c=(pal['sup'] if cell is None else cell)%100
    b=[(x,y,z,size,size,size*.75,c+ROUND),(x,y-size*.35,z+size*.75,size*.85,size*.6,size*.15,c+ROUND)]
    for i in range(barrels):
        b+=[(x+(i-(barrels-1)/2)*size*.55,y-size*1.9,z+size*.45,size*.13,size*1.2,size*.16,GUN+BARREL)]
    return b

def aa(x,y,z,barrels,pal,tub=2.8):
    """Light AA mount in a tub: quad/twin 40 mm or triple 25 mm."""
    b=[(x,y,z,tub,tub,1.4,pal['sup']+CYL)]
    for i in range(barrels):
        b+=[(x+(i-(barrels-1)/2)*1.1,y-tub-1.5,z+1.4,.28,2.6,.4,GUN+BARREL)]
    return b

def funnel(x,y,z,w,d,h,rake,pal,cap=True):
    """Raked funnel from stacked sections; black cap."""
    b=[];n=4
    for i in range(n):
        b+=[(x,y+rake*i/n,z+h*i/n,w,d,h/n+.2,pal['sup']+CYL)]
    if cap:b+=[(x,y+rake,z+h,w*1.03,d*1.03,2,BLACK+CYL)]
    return b

def mast(x,y,z,h,yard,pal,radar=True):
    b=[(x,y,z,.6,.6,h,pal['sup']+CYL),(x,y,z+h*.8,yard,.4,.4,pal['sup'])]
    if radar:b+=[(x,y+.6,z+h+.2,yard*.55,.3,2.4,DARK)]
    return b

def director(x,y,z,pal,rangefinder=9):
    return [(x,y,z,3.4,3.8,3.2,pal['sup']+ROUND),(x,y,z+3.2,rangefinder,.9,1.2,GUN+ROUND),(x,y-3.9,z+1.2,3,.2,1,DARK)]

def boat(x,y,z,pal):
    return [(x,y,z,2.2,6,1.6,pal['sup']),(x,y,z+1.6,1.4,3,1,DARK)]

def floatplane(x,y,z,pal):
    return [(x,y,z+2,1,4.5,1.2,pal['sup']),(x,y-.5,z+2.6,6,1.1,.3,pal['sup']),(x,y+3.6,z+2.4,2.2,.6,.3,pal['sup']),
            (x,y-1,z,.5,3.5,.6,GUN)]

def parked(x,y,z,pal):
    """Deck-parked aircraft: fuselage, wing, tailplane; team-coloured tail."""
    c=pal['plane']
    return [(x,y,z,1.2,5,1.6,c),(x,y-1.2,z+.7,6.4,1.4,.45,c),(x,y+4.4,z+.7,2.5,.7,.35,c),(x,y+4.6,z+1.6,.25,.6,1.6,TEAM)]

def mount_aft(x,y,z,barrels,size,pal,cell=None):
    """Gun house trained aft (stern-facing mounts behind the superstructure)."""
    return [(bx,2*y-by,bz,bw,bd,bh,c) for bx,by,bz,bw,bd,bh,c in mount(x,y,z,barrels,size,pal,cell)]

def team_band(funnel_boxes):
    """Team-colour band round a funnel: a ring a little below its cap."""
    x,y,z,w,d,h,_=funnel_boxes[-2]
    return [(x,y,z+h*.1,w*1.06,d*1.06,1.6,TEAM+CYL)]

def bridge_windows(y,z,w):
    return [(0,y,z,w,.4,1.5,DARK)]

def torpedoes(x,y,z,tubes,pal,length=5):
    """Centreline or wing torpedo mount: shielded house and tubes trained forward."""
    return [(x,y,z,3,length*.9,1.8,pal['sup']+ROUND)]+[(x+(k-(tubes-1)/2)*.8,y-length*.8,z+1.6,.35,length,.45,GUN)
                                                       for k in range(tubes)]

def edge_guns(length,beam,y_from,y_to,step,z,sheer,deck):
    """Single 20 mm guns along both deck edges."""
    b=[]
    y=y_from
    while y<=y_to:
        w=hull_width((y+length)/(2*length),beam)-1.6
        b+=[(s*w,y,deck_z(y,length,sheer,deck),.6,.6,1.8,GUN+CYL) for s in (-1,1)]
        y+=step
    return b

# ---------------------------------------------------------------- battleships
STATIONS={
 'iowa':[(-106,17),(-75,27),(94,17)],
 'yamato':[(-104,17),(-70,28),(98,17)],
 'nagato':[(-92,17),(-62,27),(59,27),(91,17)],
 'northcarolina':[(-96,17),(-66,27),(82,17)],
 'southdakota':[(-88,17),(-60,27),(74,17)],
 'kongo':[(-94,17),(-68,25),(52,17),(86,17)],
}

def barbettes(stations,pal):
    return [(0,y,z-6,11.5,11.5,6,pal['sup']+CYL) for y,z in stations]

def iowa():
    L,B,p=166,24,USN
    b=hull(L,B,p,sheer=7,deck=12,bow=.36)+barbettes(STATIONS['iowa'],p)
    b+=[(0,-8,12,13,42,7,p['sup']),(0,-20,19,10,22,7,p['sup']),          # deckhouses
        (0,-52,19,5,5,11,p['sup']),                                       # conning tower
        (0,-44,26,8.5,8,6,p['sup']),(0,-42,32,7,6.5,5,p['sup']),            # bridge levels
        (0,-48.6,33.5,6.6,.4,1.5,DARK),(0,-50.6,27.5,8,.4,1.5,DARK),
        (0,-38,37,3,3,16,p['sup'])]                                        # forward tower
    b+=director(0,-38,53,p,10)+mast(0,-35,57,8,7,p)
    b+=funnel(0,-6,19,5.5,7,20,4,p)+funnel(0,20,19,5.5,7,18,4,p)
    b+=mast(0,34,19,24,8,p)+director(0,46,19,p,8)
    for s in (-1,1):                                                       # ten 5"/38 twins
        for y in (-46,-28,-10,8,26):b+=mount(s*11.5,y,19,2,3.2,p)
    for y in (-130,122):b+=aa(0,y,deck_z(y,L,7)+1,4,p)
    for s in (-1,1):                                                       # quad 40 mm galleries
        for y in (-62,-30,36,70,108):b+=aa(s*(B-4.5),y,12.5,4,p)
        b+=aa(s*7,-2,26,4,p)+aa(s*7,30,26,4,p)
        b+=boat(s*9,42,19,p)
    b+=edge_guns(L,B,-120,140,12,0,7,12)
    b+=[(s*9,146,12,.8,10,1.4,GUN) for s in (-1,1)]+[(0,154,12,.8,.8,12,p['sup']),(0,149,24,.6,6,.6,p['sup'])]
    b+=floatplane(9,140,13,p)+floatplane(-9,140,13,p)
    b+=[(0,28,41,2,2,2,TEAM),(0,156,12.5,6,4,.3,TEAM)]                    # identity flag, stern square
    return b

def yamato():
    L,B,p=172,36,dict(IJN,lower=RED)  # April 1945; red anti-fouling hull below waterline
    b=hull(L,B,p,sheer=11,deck=13,bow=.40,stern_min=.58)+barbettes(STATIONS['yamato'],p)
    # Yamato's distinctive bulbous bow extension
    b+=[(0,-L-4,-6,6,6,8,p['hull']),(0,-L-1,-3,4,3,6,p['hull'])]
    # Amidships deckhouse — long, lower than bridge
    b+=[(0,-6,13,18,42,7,p['sup']),(0,-14,20,14,28,8,p['sup'])]
    # 15.5 cm secondary triples — April 1945: wing turrets removed, only 2 centreline remain
    b+=mount(0,-44,21,3,6.5,p)+mount(0,56,14,3,6.5,p)
    # Where the wing turrets stood: replaced by triple 25mm AA platforms
    for s in (-1,1):
        b+=aa(s*16,-36,21,3,p,3.0)+aa(s*16,-28,21,3,p,3.0)+aa(s*16,-44,21,3,p,3.0)
    # Tower bridge — Yamato's distinctive stepped pyramid shape
    # Base level (armoured conning tower)
    b+=[(0,-28,28,9,10,10,p['sup'])]
    # Navigation bridge (wider, with bridge wings)
    b+=[(0,-28,38,8,9,8,p['sup'])]
    b+=[(s*8.5,-28,40,2.5,4,4,p['sup']) for s in (-1,1)]  # bridge wings
    # Upper bridge / air defence director level
    b+=[(0,-29,46,7,7.5,7,p['sup'])]
    # Top platform with 15m rangefinder
    b+=[(0,-29,53,6,6,5,p['sup'])]
    b+=[(0,-29,58,18,1.6,2,GUN)]                           # main rangefinder (wide)
    # Optical director on top
    b+=[(0,-29,60,4,4,4,p['sup']),(0,-29,64,1.2,1.2,9,p['sup'])]
    # Bridge window slits
    b+=[(0,-35.6,42,7,.4,1.8,DARK),(0,-35.2,32,8.5,.4,1.8,DARK)]
    b+=[(s*7,-29,56,2.5,.3,3.5,DARK) for s in (-1,1)]
    # Single large raked funnel (Yamato's distinctive capped funnel)
    b+=funnel(0,8,21,9,13,22,8,p)+[(0,16,43,9.5,13.5,3,BLACK)]  # heavy cap
    # Aft superstructure and mainmast
    b+=[(0,30,20,10,20,7,p['sup'])]                           # aft deckhouse
    b+=mast(0,34,27,20,10,p)
    b+=director(0,40,20,p,9)
    # Aft deck structures (boat storage, catapult area, stern gallery)
    b+=[(0,60,13,14,16,6,p['sup'])]                            # aft boat deck platform
    b+=[(0,80,13,12,20,5,p['sup'])]                            # catapult platform base
    b+=[(0,100,13,10,16,4,p['sup'])]                           # stern working deck
    b+=[(0,120,13,8,14,4,p['sup'])]                            # stern gallery deck
    b+=[(0,140,13,6,10,3,p['sup'])]                            # fantail deck
    # 12.7 cm twin DP mounts (6 per side, spread along the hull)
    for s in (-1,1):
        for y in (-26,-10,6,16,50,68):b+=mount(s*16,y,21,2,3.4,p)
        # Massive 25mm AA batteries — April 1945 config (~150 barrels)
        for y in (-52,-38,-24,28,42,56,70,84,100,116,130):b+=aa(s*(B-6),y,13.5,3,p,2.4)  # hull-edge AA
        for y in (-60,-46,-32,36,48,60,74,88,106,122):b+=aa(s*(B-9),y,13.5,3,p,2.2)       # inner ring
        for y in (-16,0,14):b+=aa(s*11,y,28,3,p,2.4)           # bridge-level AA
        for y in (-8,6):b+=aa(s*14,y,21,3,p,2.0)               # deckhouse-level AA
        for y in (62,78,96,112):b+=aa(s*12,y,19,3,p,2.2)       # aft deck AA
        b+=boat(s*14,44,20,p)
        b+=boat(s*10,66,19,p)
    b+=edge_guns(L,B,-130,156,10,0,11,13)
    # Stern catapult and floatplanes
    b+=[(s*14,130,14,.8,14,1.4,GUN) for s in (-1,1)]           # catapult rails
    b+=[(0,122,14,.8,.8,14,p['sup']),(0,116,28,.6,8,.6,p['sup'])]  # catapult crane/derrick
    b+=floatplane(14,142,15,p)+floatplane(-14,142,15,p)+floatplane(0,148,15,p)
    # Stern flagstaff and team markings
    b+=[(0,162,13,.4,.4,8,p['sup'])]                            # stern flagstaff
    b+=[(0,8,44,9,13,1.2,TEAM),(0,162,17,4,2,.3,TEAM),(0,158,13.5,8,4,.3,TEAM)]
    return b

def nagato():
    L,B,p=143,27,IJN
    b=hull(L,B,p,sheer=8,deck=12,bow=.34)+barbettes(STATIONS['nagato'],p)
    b+=[(0,-10,12,13,30,7,p['sup'])]
    z=19
    for w,d,h,dy in [(9,9,7,0),(8,7,6,1),(7.5,8,5,0),(6,6,5,2),(7,5,4,1),(5,4,4,2),(8,2,2,2)]:  # pagoda levels
        b+=[(0,-36+dy,z,w,d,h,p['sup'])];z+=h
    b+=[(0,-44.6,32,6.6,.4,1.5,DARK),(0,-42,44,4.5,.4,1.4,DARK)]+director(0,-34,52,p,9)
    b+=funnel(0,-8,19,6.5,8,15,2,p,cap=False)+[(0,-6,34,6.8,9,3,p['sup']),(0,-1,35,6.8,4,3,BLACK)]  # trunked cap
    b+=mast(0,24,19,22,9,p)+director(0,32,19,p,7)
    for s in (-1,1):
        for y in (-58,-46,-34,-22,-10,2,14,26,38):                         # 14 cm casemates
            w=hull_width((y+L)/(2*L),B)
            b+=[(s*(w+.2),y,6,.6,1.8,2,p['sup']),(s*(w+1.4),y-.5,7,1.4,.3,.5,GUN)]
        for y in (-20,0,18):b+=mount(s*10,y,19,2,3,p)
        for y in (-70,46,74):b+=aa(s*(B-5),y,12.5,3,p,2.3)
        b+=boat(s*10,30,19,p)
    b+=edge_guns(L,B,-108,128,13,0,8,12)
    b+=[(0,128,12,.8,.8,11,p['sup']),(0,124,23,.6,5,.6,p['sup'])]+floatplane(0,132,13,p)
    b+=[(0,-8,34.5,6,1,.3,TEAM),(0,136,12.5,6,4,.3,TEAM)]
    return b

# ------------------------------------------------- cruisers and destroyers
def cleveland():
    L,B,p=126,20,USN
    st=[(-80,17),(-52,25),(53,25),(82,17)]
    b=hull(L,B,p,sheer=6,deck=12,bow=.34)+barbettes(st,p)
    for y,z in st:b+=mount(0,y,z,3,6,p,GUN if False else None)
    b+=[(0,-12,12,10,30,7,p['sup']),(0,-24,19,8,10,7,p['sup']),(0,-26,26,6.5,6,5,p['sup']),
        (0,-31.8,27.5,6.2,.4,1.4,DARK)]+director(0,-25,31,p,7)+mast(0,-18,26,18,6,p)
    b+=funnel(0,-2,19,4.4,5.5,15,3,p)+funnel(0,16,19,4.4,5.5,14,3,p)+mast(0,26,19,16,6,p,False)+director(0,34,19,p,6)
    for s in (-1,1):
        for y in (-28,-8,12):b+=mount(s*9,y,19,2,2.8,p)
        for y in (-60,36,68):b+=aa(s*(B-4),y,12.5,4,p,2.4)
        b+=boat(s*8,30,19,p)
    b+=edge_guns(L,B,-100,110,12,0,6,12)+[(s*6,110,12,.7,8,1.2,GUN) for s in (-1,1)]+[(0,118,12,.7,.7,9,p['sup'])]
    b+=[(0,24,35,1.6,1.6,1.6,TEAM)]
    return b

def mogami():
    L,B,p=132,21,IJN
    st=[(-88,17),(-63,24),(-38,17),(63,24),(88,17)]
    b=hull(L,B,p,sheer=8,deck=12,bow=.36)+barbettes(st,p)
    for y,z in st:b+=mount(0,y,z,2,6,p)
    b+=[(0,-14,12,9,14,7,p['sup']),(0,-17,19,7.5,9,8,p['sup']),(0,-18,27,6,6.5,6,p['sup']),(0,-19,33,5,4.5,5,p['sup']),
        (0,-23.8,28,5.8,.4,1.4,DARK)]+director(0,-18,38,p,8)+mast(0,-10,27,16,6,p)
    b+=funnel(0,6,12,5,9,19,6,p)+mast(0,26,12,22,7,p,False)
    for s in (-1,1):
        for y in (14,28):b+=[(s*12,y,12.5,3.2,4.5,1.8,p['sup'])]+[(s*12+k,y-5,14,.4,4,.5,GUN) for k in (-1.2,0,1.2)]  # torpedo triples
        for y in (-4,12):b+=mount(s*8.5,y,19,2,2.6,p)
        for y in (-52,40,54):b+=aa(s*(B-4),y,12.5,3,p,2.2)
    b+=edge_guns(L,B,-104,120,13,0,8,12)+[(s*7,112,12,.7,9,1.2,GUN) for s in (-1,1)]+[(0,104,12,.7,.7,10,p['sup'])]
    b+=floatplane(7,118,13,p)+floatplane(-7,118,13,p)+[(0,6,32,5.2,9.2,1,TEAM)]
    return b

def fletcher():
    L,B,p=92,14,USN
    st=[(-66,17),(-44,24),(36,17),(55,24),(73,17)]
    b=hull(L,B,p,sheer=5,deck=11,bow=.38)
    for y,z in st:b+=mount(0,y,z-5,1,4.5,p)
    b+=[(0,-24,11,6.5,12,8,p['sup']),(0,-26,19,5,6,5,p['sup']),(0,-30.8,20,4.8,.4,1.3,DARK)]+director(0,-25,24,p,5)+mast(0,-18,19,16,5,p)
    b+=funnel(0,-6,11,3.2,4,14,2,p)+funnel(0,12,11,3.2,4,13,2,p)
    b+=[(0,2,11.5,3,6,1.8,p['sup']),(0,22,11.5,3,6,1.8,p['sup'])]+[(k,y-6,13.3,.35,5,.45,GUN) for y in (2,22) for k in (-1.6,-.8,0,.8,1.6)]  # quintuple tubes
    for s in (-1,1):b+=aa(s*(B-3.5),-10,12,2,p,2)+aa(s*(B-3.5),30,12,2,p,2)
    b+=edge_guns(L,B,-70,80,11,0,5,11)+[(0,12,27.5,3.3,1.2,.8,TEAM)]
    return b

def fubuki():
    L,B,p=93,15,IJN
    st=[(-64,17),(48,24),(73,17)]
    b=hull(L,B,p,sheer=7,deck=11,bow=.38)
    for y,z in st:b+=mount(0,y,z-4,2,5,p)
    b+=[(0,-40,11,6,9,8,p['sup']),(0,-42,19,5,6,6,p['sup']),(0,-46.8,20,4.6,.4,1.3,DARK)]+director(0,-41,25,p,5)+mast(0,-34,19,16,5,p)
    b+=funnel(0,-22,11,3.6,5.5,15,3,p)+funnel(0,2,11,3,4,13,3,p)
    for y in (-8,16,32):b+=[(0,y,11.5,3,5,1.8,p['sup'])]+[(k,y-5,13.3,.4,4.5,.5,GUN) for k in (-1.2,0,1.2)]  # triple tubes
    for s in (-1,1):b+=aa(s*(B-3.5),-14,12,2,p,2)
    b+=edge_guns(L,B,-70,80,11,0,7,11)+[(0,-22,30.5,3.7,1.2,.8,TEAM)]
    return b

# -------------------------------------------------------------- carriers
def carrier(length,beam,pal,side=STARBOARD,island_y=-8,island='usn',elevators=(),edge_elevator=None,
            five_inch=(),parked_rows=4,ijn_marks=False,overhang=1.0):
    L,B,p=length,beam,pal
    hb=B-7
    b=hull(L-8,hb,p,sheer=4,deck=12,bow=.36)
    # Hangar walls with open bays (USN) or enclosed sides (IJN) under the flight deck.
    b+=[(0,0,12,hb-.5,L-22,12,p['sup'])]
    if island in ('usn','cvl'):
        b+=[(s*(hb-.2),y,15,.3,5,6,DARK) for s in (-1,1) for y in range(-int(L)+40,int(L)-30,18)]
    else:
        b+=[(s*(hb-.2),y,17,.3,1.2,1.2,DARK) for s in (-1,1) for y in range(-int(L)+40,int(L)-30,9)]
    # Flight deck, overhanging bow and stern on open supports.
    fz=24
    b+=[(0,4,fz,B,L*overhang-6,2,p['fdeck'])]
    b+=[(s*B*.5,y,10,.8,.8,fz-10,GUN) for s in (-1,1) for y in (-(L-10),L-6)]
    top=fz+2
    if ijn_marks:
        b+=[(s*(B-1.2),4,top,.5,L-10,.08,WHITE) for s in (-1,1)]
        b+=[(0,L-14+k*2.4,top,B-1,1.1,.09,RED if k%2==0 else WHITE) for k in range(4)]   # stern stripes
        b+=[(0,-L+34,top,6.5,6.5,.06,WHITE),(0,-L+34,top+.02,5,3,.06,RED),(0,-L+34,top+.02,3,5,.06,RED),(0,-L+34,top+.02,4.3,4.3,.06,RED)]
    else:
        b+=[(0,y,top,.5,3,.08,WHITE) for y in range(-int(L)+20,int(L)-10,12)]            # centreline dashes
        b+=[(s*(B-1.2),4,top,.4,L-10,.08,WHITE) for s in (-1,1)]
        b+=[(0,L-12,top,B-1,.6,.08,WHITE),(0,-L+18,top,B-1,.6,.08,WHITE)]
    for y in elevators:b+=[(0,y,top,9.5,8.5,.05,WHITE if not ijn_marks else DARK),(0,y,top+.03,8.8,7.8,.05,p['fdeck'])]
    if edge_elevator is not None:b+=[(-side*(B+4),edge_elevator,fz-1,4,8,1.5,p['sup'])]
    # Island
    ix=side*(B-5) if island!='cvl' else side*(B-1.5)
    if island=='cvl':
        # Independence class: a small open bridge forward and four short funnels angled outboard.
        b+=[(ix,island_y,top,2.4,6,4.5,p['sup']),(ix,island_y-.5,top+4.5,2,3.6,2.5,p['sup']),
            (ix-side*.1,island_y-3.2,top+5,1.8,.4,1.2,DARK)]+mast(ix,island_y+2,top+4.5,10,4,p)
        funnels=[]
        for k,y in enumerate((-18,-6,6,18)):
            f=funnel(side*(B+2.5),y,fz-9,1.7,2.2,12,0,p)
            funnels+=f
            if k==0:b+=team_band(f)
        b+=funnels+[(side*(B+1.2),y,fz-6,2,2.6,3,p['sup']) for y in (-18,-6,6,18)]
    elif island=='usn':
        b+=[(ix,island_y,top,4,17,7,p['sup']),(ix,island_y-6,top+7,3.6,9,5,p['sup']),
            (ix-side*.1,island_y-15.2,top+8,3.3,.4,1.6,DARK),(ix,island_y-4,top+12,2.8,5,3,p['sup'])]
        b+=funnel(ix,island_y+8,top+7,3.4,6,10,2,p)
        b+=mast(ix,island_y-3,top+15,14,6,p)+director(ix,island_y-11,top+12,p,6)
        b+=[(ix,island_y+2,top+12.5,2,2,2,TEAM)]
    else:
        b+=[(ix,island_y,top,3,7,6,p['sup']),(ix,island_y-1,top+6,2.6,4.5,3,p['sup']),
            (ix-side*.1,island_y-5.3,top+6.6,2.3,.4,1.2,DARK),(ix,island_y,top+9,.5,.5,11,p['sup']),(ix,island_y,top+17,4,.4,.4,p['sup'])]
        b+=[(ix,island_y+1,top+9.4,1.5,1.5,1.5,TEAM)]
    # Gallery sponsons with AA, plus 5-inch twins (USN on deck, IJN on sponsons).
    for s in (-1,1):
        for y in (-L*.72,-L*.42,L*.28,L*.62):
            if s==side and abs(y-island_y)<26:continue
            if island=='cvl' and s==side and abs(y)<30:continue    # the funnels stand here
            b+=[(s*(B+3),y,fz-2.5,3.6,5,1,p['sup'])]+aa(s*(B+3),y,fz-1.5,4 if island in ('usn','cvl') else 3,p,2.4)
    for x,y in five_inch:
        b+=mount(x,y,top if island=='usn' else fz-2,2,3,p)
        if island!='usn':b+=[(x,y,fz-3,3.8,3.8,1,p['sup'])]
    b+=edge_guns(L-8,hb,-L+30,L-20,14,0,4,12)
    # Spotted deck: aircraft ranged aft for launch.
    for r in range(parked_rows):
        y=L*.42+r*12
        if y>L-14:break
        for x in (-B*.55,0,B*.55):
            if abs(x-ix)<6 and abs(y-island_y)<26:continue
            b+=parked(x,y,top,p)
    return b

def kaga_extras():
    p=IJN
    return [(-34,30+k*9,8,2.6,4,10,BLACK) for k in range(4)]+[(-37,72,6,4,6,12,BLACK)]+\
           [(s*30,y,8,1.4,2.8,2.6,p['sup']) for s in (-1,1) for y in (95,110,125)]+[(s*31.6,y-3,9,.5,3,.6,GUN) for s in (-1,1) for y in (95,110,125)]
def akagi_extras():
    p=IJN
    return [(-31,18,4,4.5,7,14,BLACK),(-33,16,17,3,4,4,BLACK),(-29,34,14,2.4,3,10,p['sup']),(-29,34,24,2.5,3.1,1.5,BLACK)]

# ------------------------------------------------- 1941-45 classes (round 12)
def northcarolina():
    """North Carolina class, 1944 Measure 22: single tower forward, two funnels close together."""
    L,B,p=150,24,USN
    b=hull(L,B,p,sheer=7,deck=12,bow=.36)+barbettes(STATIONS['northcarolina'],p)
    b+=[(0,-6,12,12,40,7,p['sup']),(0,-14,19,9.5,20,7,p['sup']),
        (0,-48,19,4.5,4.5,10,p['sup']),                                  # conning tower
        (0,-40,26,8,7.5,6,p['sup']),(0,-38,32,6.5,6,5,p['sup']),(0,-36,37,3,3,14,p['sup'])]
    b+=bridge_windows(-47.6,27.5,7.6)+bridge_windows(-44.1,33.5,6.2)
    b+=director(0,-36,51,p,9)+mast(0,-33,55,7,6,p)
    f1=funnel(0,-4,19,5,6.5,17,3,p);f2=funnel(0,9,19,5,6.5,16,3,p)
    b+=f1+f2+team_band(f1)
    b+=[(0,30,19,6,8,8,p['sup'])]+director(0,30,27,p,8)+mast(0,24,19,22,7,p)
    for s in (-1,1):                                                     # ten 5"/38 twins
        for y in (-38,-22,-6,10,26):b+=mount(s*10.5,y,19,2,3.1,p)
        for y in (-58,-30,44,64,100):b+=aa(s*(B-4.5),y,12.5,4,p)
        b+=aa(s*6.5,-26,26,4,p)+boat(s*9,40,19,p)
    for y in (-118,112):b+=aa(0,y,deck_z(y,L,7)+1,4,p)
    b+=edge_guns(L,B,-110,130,12,0,7,12)
    b+=[(s*8,132,12,.8,9,1.4,GUN) for s in (-1,1)]+[(0,140,12,.8,.8,11,p['sup']),(0,135,23,.6,5,.6,p['sup'])]
    b+=floatplane(8,126,13,p)+floatplane(-8,126,13,p)+[(0,144,12.5,6,4,.3,TEAM)]
    return b

def southdakota():
    """South Dakota class, 1942 Measure 21: short beamy hull, one funnel faired into the tower."""
    L,B,p=138,25,M21
    b=hull(L,B,p,sheer=7,deck=12,bow=.34,stern_min=.6)+barbettes(STATIONS['southdakota'],p)
    b+=[(0,-2,12,13,34,7,p['sup']),
        (0,-30,19,9,15,8,p['sup']),(0,-32,27,8,11,6,p['sup']),(0,-33,33,6.5,8,5,p['sup']),
        (0,-30,38,3,3,12,p['sup'])]
    b+=bridge_windows(-41.1,28.5,7.6)+bridge_windows(-41.1,34.5,6.2)
    b+=director(0,-30,50,p,9)+mast(0,-27,54,7,6,p)
    f=funnel(0,-14,19,6,8.5,18,4,p)
    b+=[(0,-19,19,6.4,6,15,p['sup'])]+f+team_band(f)                    # funnel faired into the tower
    b+=[(0,24,19,6,7,7,p['sup'])]+director(0,24,26,p,8)+mast(0,30,19,16,6,p,False)
    for s in (-1,1):                                                     # eight 5"/38 twins in two tiers
        for y in (-36,-20,-4):b+=mount(s*11,y,19,2,3.1,p)
        b+=mount(s*8,-6,26,2,3.1,p)
        for y in (-52,-28,36,56,88):b+=aa(s*(B-4.5),y,12.5,4,p)
        b+=boat(s*9,34,19,p)
    for y in (-108,104):b+=aa(0,y,deck_z(y,L,7)+1,4,p)
    b+=edge_guns(L,B,-100,120,12,0,7,12)
    b+=[(s*8,120,12,.8,9,1.4,GUN) for s in (-1,1)]+[(0,128,12,.8,.8,11,p['sup'])]
    b+=floatplane(8,116,13,p)+floatplane(-8,116,13,p)+[(0,132,12.5,6,4,.3,TEAM)]
    return b

def kongo():
    """Kongo after her 1930s rebuild: pagoda bridge, two funnels, four twin 14-inch turrets."""
    L,B,p=148,23,IJN
    b=hull(L,B,p,sheer=9,deck=12,bow=.36)+barbettes(STATIONS['kongo'],p)
    b+=[(0,-2,12,11,34,7,p['sup'])]
    z=19
    for w,d,h,dy in [(8,8,7,0),(7,6.5,6,1),(6.5,7.5,6,0),(5.5,5.5,5,2),(6.5,4.5,5,1),(4.5,4,4,2),(7,2,2,2)]:  # pagoda
        b+=[(0,-42+dy,z,w,d,h,p['sup'])];z+=h
    b+=bridge_windows(-49.6,32,6)+bridge_windows(-46.4,44,4.2)+director(0,-40,54,p,9)
    f1=funnel(0,-16,19,5.5,7,17,3,p);f2=funnel(0,10,19,4.8,6,14,3,p)
    b+=f1+f2+team_band(f1)
    b+=mast(0,30,19,22,8,p)+director(0,36,19,p,7)
    for s in (-1,1):
        for y in (-58,-46,-34,-22,-10,20,32):                           # 15 cm casemates
            w=hull_width((y+L)/(2*L),B)
            b+=[(s*(w+.2),y,6,.6,1.8,2,p['sup']),(s*(w+1.4),y-.5,7,1.4,.3,.5,GUN)]
        for y in (-28,0):b+=mount(s*9.5,y,19,2,2.8,p)                    # 12.7 cm twin HA
        for y in (-64,-4,40,104):b+=aa(s*(B-4.5),y,12.5,3,p,2.3)
        b+=boat(s*9,22,19,p)
    b+=edge_guns(L,B,-118,130,13,0,9,12)
    b+=[(0,70,12,.8,9,1.4,GUN),(0,66,12,.8,.8,10,p['sup'])]+floatplane(0,72,13,p)
    b+=[(0,140,12.5,6,4,.3,TEAM)]
    return b

def baltimore():
    """Baltimore-class heavy cruiser, Measure 22: three triple 8-inch, two funnels."""
    L,B,p=134,19,USN
    st=[(-86,17),(-62,24),(76,17)]
    b=hull(L,B,p,sheer=6,deck=12,bow=.34)+barbettes(st,p)
    b+=mount(0,-86,17,3,6.5,p)+mount(0,-62,24,3,6.5,p)+mount_aft(0,76,17,3,6.5,p)
    b+=[(0,-6,12,9.5,40,7,p['sup']),(0,-32,19,8,10,7,p['sup']),(0,-34,26,6.5,7,5,p['sup'])]
    b+=bridge_windows(-41.6,27.5,6.2)+director(0,-32,31,p,7)+mast(0,-26,31,18,6,p)
    f1=funnel(0,-4,19,4.6,6,15,3,p);f2=funnel(0,18,19,4.6,6,14,3,p)
    b+=f1+f2+team_band(f1)
    b+=[(0,38,19,5,7,5,p['sup'])]+director(0,38,24,p,7)+mast(0,30,19,14,6,p,False)
    b+=mount(0,-44,26,2,3.2,p)+mount_aft(0,54,24,2,3.2,p)                 # centreline 5"/38 twins
    for s in (-1,1):
        for y in (-18,8):b+=mount(s*9,y,19,2,3,p)
        for y in (-54,28,46,64):b+=aa(s*(B-4),y,12.5,4,p,2.4)
        b+=boat(s*8,30,19,p)
    b+=edge_guns(L,B,-104,118,12,0,6,12)
    b+=[(s*6,112,12,.7,8,1.2,GUN) for s in (-1,1)]+[(0,120,12,.7,.7,9,p['sup'])]+floatplane(6,108,13,p)
    b+=[(0,126,12.5,5,3.5,.3,TEAM)]
    return b

def atlanta():
    """Atlanta-class AA cruiser, 1942 Measure 21: 5-inch twins stepped fore and aft, two wing mounts."""
    L,B,p=112,15,M21
    b=hull(L,B,p,sheer=6,deck=11,bow=.38)
    for y,z in ((-74,12),(-62,18),(-50,24)):                            # stepped pyramid forward
        if z>12:b+=[(0,y,11,3.6,3.6,z-11,p['sup']+CYL)]
        b+=mount(0,y,z,2,3.6,p)
    for y,z in ((46,24),(58,18),(70,12)):                               # and aft, trained aft
        if z>12:b+=[(0,y,11,3.6,3.6,z-11,p['sup']+CYL)]
        b+=mount_aft(0,y,z,2,3.6,p)
    b+=[(0,-30,11,6,9,8,p['sup']),(0,-31,19,5,6,6,p['sup'])]+bridge_windows(-37.2,20,4.8)
    b+=director(0,-31,25,p,6)+mast(0,-24,19,16,5,p)
    b+=[(0,-2,11,5.5,20,6,p['sup'])]
    f1=funnel(0,-10,17,3,4,13,2,p);f2=funnel(0,8,17,3,4,12,2,p)
    b+=f1+f2+team_band(f1)
    b+=[(0,32,11,5,7,7,p['sup'])]+director(0,32,18,p,6)+mast(0,26,11,18,5,p,False)
    for s in (-1,1):
        b+=mount(s*8.5,22,12,2,3.2,p)                                   # wing 5-inch twins
        b+=torpedoes(s*6.5,6,11.5,4,p)
        for y in (-42,-16,38):b+=aa(s*(B-3.5),y,12,4,p,2.2)
    b+=edge_guns(L,B,-86,96,11,0,6,11)+[(0,100,11.5,5,3,.3,TEAM)]
    return b

def sumner():
    """Allen M. Sumner destroyer, Measure 22: three twin 5-inch (two forward), twin funnels."""
    L,B,p=94,14.5,USN
    b=hull(L,B,p,sheer=5,deck=11,bow=.38)
    b+=mount(0,-64,12,2,4.4,p)+[(0,-46,11,3.6,3.6,6,p['sup']+CYL)]+mount(0,-46,17,2,4.4,p)+mount_aft(0,64,12,2,4.4,p)
    b+=[(0,-26,11,6.5,10,8,p['sup']),(0,-28,19,5,6,5,p['sup'])]+bridge_windows(-34.2,20,4.8)
    b+=director(0,-27,24,p,5)+mast(0,-20,19,16,5,p)
    f1=funnel(0,-10,11,3.2,4,13,2,p);f2=funnel(0,8,11,3.2,4,12,2,p)
    b+=f1+f2+team_band(f1)
    b+=torpedoes(0,0,11.5,5,p,6)+torpedoes(0,24,11.5,5,p,6)
    b+=[(0,44,11,5,7,4,p['sup'])]+aa(0,44,15,4,p,2.4)
    for s in (-1,1):b+=aa(s*(B-3.5),-12,12,2,p,2)+aa(s*(B-3.5),34,12,4,p,2.2)
    b+=edge_guns(L,B,-72,82,11,0,5,11)+[(0,84,11.5,4,2.5,.3,TEAM)]
    return b

def _ijn_cruiser(st,pal):
    """Myoko/Takao hull: five twin 8-inch (three forward in a pyramid, two aft trained aft)."""
    L,B,p=134,20,pal
    b=hull(L,B,p,sheer=9,deck=12,bow=.38)+barbettes(st,p)
    for y,z in st:b+=(mount(0,y,z,2,6,p) if y<0 else mount_aft(0,y,z,2,6,p))
    for s in (-1,1):
        for y in (20,34):b+=torpedoes(s*12,y,12.5,4,p,4.5)               # quad Long Lance mounts
        for y in (-52,46,58):b+=aa(s*(B-4),y,12.5,3,p,2.2)
    b+=edge_guns(L,B,-106,122,13,0,9,12)
    b+=[(s*7,42,19,.7,9,1.2,GUN) for s in (-1,1)]+floatplane(7,40,20,p)+floatplane(-7,40,20,p)
    return b

def takao():
    """Takao: the massive block bridge and a raked, trunked fore funnel."""
    st=[(-92,17),(-72,24),(-52,17),(70,24),(92,17)]
    p=IJN;b=_ijn_cruiser(st,p)
    b+=[(0,-6,12,9,26,7,p['sup']),
        (0,-26,19,9.5,14,8,p['sup']),(0,-27,27,9,12,7,p['sup']),(0,-28,34,8,10,6,p['sup']),(0,-28,40,6,7,5,p['sup'])]
    b+=bridge_windows(-39.2,28.5,8.6)+bridge_windows(-38.2,35.5,7.6)+bridge_windows(-35.2,41.5,5.6)
    b+=director(0,-28,45,p,8)+mast(0,-16,27,18,6,p)
    f1=funnel(0,-6,19,5.5,10,18,8,p,cap=False)+[(0,2,37,5.6,6,2,BLACK)]   # two uptakes trunked aft
    f2=funnel(0,16,19,3.8,5,14,4,p)
    b+=f1+f2+team_band(f2)
    for s in (-1,1):
        for y in (6,24):b+=mount(s*9,y,19,2,2.6,p)                       # 12.7 cm twin HA
    b+=mast(0,30,19,20,7,p,False)+[(0,126,12.5,5,3.5,.3,TEAM)]
    return b

def myoko():
    """Myoko: a smaller bridge than Takao and two raked funnels."""
    st=[(-92,17),(-72,24),(-52,17),(70,24),(92,17)]
    p=dict(IJN,sup=4);b=_ijn_cruiser(st,p)
    b+=[(0,-6,12,9,26,7,p['sup']),(0,-28,19,7.5,10,8,p['sup']),(0,-29,27,6.5,7,6,p['sup'])]
    b+=bridge_windows(-36.2,28.5,6.6)+director(0,-29,33,p,7)+mast(0,-20,27,18,6,p)
    f1=funnel(0,-8,19,4.8,8,17,6,p);f2=funnel(0,14,19,3.8,5.5,15,5,p)
    b+=f1+f2+team_band(f1)
    for s in (-1,1):
        for y in (2,22):b+=mount(s*9,y,19,2,2.6,p)
    b+=mast(0,32,19,18,7,p,False)+[(0,126,12.5,5,3.5,.3,TEAM)]
    return b

def kagero():
    """Kagero fleet destroyer: three twin 5-inch (one forward, two aft), two quad torpedo mounts."""
    L,B,p=94,13.5,IJN_DD
    b=hull(L,B,p,sheer=7,deck=11,bow=.38)
    b+=mount(0,-62,12,2,4.4,p)+[(0,44,11,3.6,3.6,6,p['sup']+CYL)]+mount_aft(0,44,17,2,4.4,p)+mount_aft(0,62,12,2,4.4,p)
    b+=[(0,-40,11,5.5,8,8,p['sup']),(0,-41,19,4.6,5,5,p['sup'])]+bridge_windows(-46.2,20,4.4)
    b+=director(0,-40,24,p,5)+mast(0,-33,19,15,5,p)
    f1=funnel(0,-24,11,3.6,5,14,3,p);f2=funnel(0,4,11,3.2,4.5,13,3,p)
    b+=f1+f2+team_band(f1)
    b+=torpedoes(0,-10,11.5,4,p,5.5)+torpedoes(0,22,11.5,4,p,5.5)
    b+=[(s*3.8,y,11.5,1.4,3,1.6,p['sup']) for s in (-1,1) for y in (-10,22)]   # reload lockers
    for s in (-1,1):b+=aa(s*(B-3.5),-14,12,2,p,2)
    b+=aa(0,32,12,3,p,2.2)+edge_guns(L,B,-70,80,11,0,7,11)+[(0,84,11.5,4,2.5,.3,TEAM)]
    return b

def akizuki():
    """Akizuki AA destroyer: four twin 10 cm turrets, one large trunked funnel, HA director."""
    L,B,p=100,14,IJN_DD
    b=hull(L,B,p,sheer=7,deck=11,bow=.38)
    b+=mount(0,-70,12,2,4.2,p)+[(0,-54,11,3.6,3.6,6,p['sup']+CYL)]+mount(0,-54,17,2,4.2,p)
    b+=[(0,56,11,3.6,3.6,6,p['sup']+CYL)]+mount_aft(0,56,17,2,4.2,p)+mount_aft(0,72,12,2,4.2,p)
    b+=[(0,-34,11,6,9,8,p['sup']),(0,-35,19,5,6,6,p['sup'])]+bridge_windows(-41.2,20,4.8)
    b+=director(0,-34,25,p,7)+mast(0,-26,19,16,5,p)
    f=funnel(0,-6,11,4.2,7.5,15,4,p,cap=False)+[(0,-2,26,4.3,5,2,BLACK)]   # uptakes trunked into one
    b+=f+team_band(f)+torpedoes(0,16,11.5,4,p,5.5)
    b+=[(0,36,11,4.5,6,5,p['sup'])]+mast(0,36,16,12,4,p,False)
    for s in (-1,1):b+=aa(s*(B-3.5),-14,12,3,p,2.2)+aa(s*(B-3.5),28,12,3,p,2.2)
    b+=edge_guns(L,B,-76,86,11,0,7,11)+[(0,90,11.5,4,2.5,.3,TEAM)]
    return b

# ------------------------------------------------------------ landing craft
def landing(length,beam,wheelhouse,pal,gun_mounts=2):
    p=pal
    b=hull(length,beam,p,sheer=2,deck=5,stations=10,bow=.12,stern=.1,stern_min=.85)
    b+=[(0,0,5,beam-3,length-10,1,DARK),                              # open cargo well
        (beam-1.4,0,5,1.4,length-3,9,p['hull']),(-beam+1.4,0,5,1.4,length-3,9,p['hull']),
        (beam-1.4,0,14,1.6,length-3,.6,p['sup']),(-beam+1.4,0,14,1.6,length-3,.6,p['sup']),  # gunwales
        (0,-length+1.5,4,beam,1.5,11,p['sup']),(0,-length+.6,13,beam-1,.4,1,DARK),        # bow ramp + hinge
        (beam-6,length-9,6,5,7,wheelhouse,p['sup']),(beam-6,length-15.5,6+wheelhouse-3,4.6,.4,1.4,DARK),
        (0,length-3,6,beam-3,3,6,p['hull']),(0,length-3,12,4,2,1.5,TEAM)]
    for i in range(gun_mounts):
        b+=[((-1)**i*(beam-1.5),length-14,15,.8,.8,2,GUN),((-1)**i*(beam-1.5),length-15.5,17,.25,2.5,.3,GUN)]
    return b

LCVP=dict(USN,lower=1)  # Higgins boats ran in light ocean grey

GEOMETRY={
 'iowa':iowa(),'yamato':yamato(),'nagato':nagato(),
 'cleveland':cleveland(),'mogami':mogami(),'fletcher':fletcher(),'fubuki':fubuki(),
 'yorktown':carrier(151,27,USN,STARBOARD,-8,'usn',elevators=(-80,-6,56),five_inch=((-22,-32),(-22,20),(22,-110),(22,110))),
 'essex':carrier(170,32,USN,STARBOARD,-10,'usn',elevators=(-92,40),edge_elevator=-6,
                 five_inch=((-27,-42),(-27,-30),(-27,14),(-27,26)),parked_rows=5),
 'akagi':carrier(164,28,IJN,PORT,12,'ijn',elevators=(-92,-12,60),five_inch=((-32,110),(32,110)),ijn_marks=True)+akagi_extras(),
 'kaga':carrier(153,34,IJN,STARBOARD,-30,'ijn',elevators=(-86,-10,50),five_inch=((38,-90),(38,60)),ijn_marks=True,parked_rows=5)+kaga_extras(),
 'soryu':carrier(138,24,IJN,STARBOARD,-32,'ijn',elevators=(-78,-8,48),five_inch=((28,-70),(-28,-70),(28,60),(-28,60)),ijn_marks=True),
 'hiryu':carrier(141,25,IJN,PORT,8,'ijn',elevators=(-80,-8,50),five_inch=((29,-70),(-29,-70),(29,60),(-29,60)),ijn_marks=True),
 'shokaku':carrier(163,29,IJN,STARBOARD,-25,'ijn',elevators=(-92,-14,58),five_inch=((33,-80),(-33,-80),(33,70),(-33,70)),ijn_marks=True,parked_rows=5),
 'lcvp':landing(43,16,9,LCVP,1),'lcm':landing(61,25,17,USN,2),'daihatsu':landing(55,21,13,IJN,1),
 # 1941-45 classes (catalog NEW_SHIP_ART resolves each unit to its own model by name).
 'northcarolina':northcarolina(),'southdakota':southdakota(),'kongo':kongo(),
 'baltimore':baltimore(),'atlanta':atlanta(),'sumner':sumner(),
 'takao':takao(),'myoko':myoko(),'kagero':kagero(),'akizuki':akizuki(),
 'independence':carrier(128,19,M21,STARBOARD,-62,'cvl',elevators=(-66,34),parked_rows=3),
}
SHIPS=tuple(GEOMETRY)
BATTERIES={name:[(-y,0,z) for y,z in stations] for name,stations in STATIONS.items()}

def turret(barrels):
    """Main-battery house: sloped face, roof, rangefinder ears, blast bags and barrels."""
    b=[(0,0,0,12.5,12.5,3,DARK+CYL),(0,2,3,11.5,10,8,GUN+ROUND),(0,-7.5,3,10.5,2.5,6,GUN+ROUND),(0,1,11,10.5,9.5,1,GUN+ROUND),
       (0,4,12,4,3,.4,TEAM)]
    b+=[(s*11.8,6,6,1.8,2.2,2.2,GUN) for s in (-1,1)]+[(0,7,12,3,2,1.6,GUN)]
    for i in range(barrels):
        x=(i-(barrels-1)/2)*7
        b+=[(x,-10.5,6,1.8,2.5,2.4,DARK+ROUND),(x,-25,6.6,1.05,12.5,1.3,GUN+BARREL),(x,-38,6.5,1.3,.8,1.5,GUN+BARREL)]
    return b
GEOMETRY['naval_triple']=turret(3)
GEOMETRY['naval_twin']=turret(2)
