"""Animated land units, aircraft, projectiles and impact effects (rich_mdx).

The ordinary unit table keeps eight sequences (Stand, Walk, Attack, Death, Birth,
Work, Stand Work, Decay); Death and Decay are longer so explosions can linger and
corpses keep their final pose instead of popping back up.
  infantry  walk sway and bob, recoil + muzzle flash, falls backwards and stays down
  vehicles  recoil + muzzle flash + gun smoke; Death: fireball, shockwave, flying
            debris and a burning wreck that smokes through Decay
  aircraft  banking weave, spinning propeller with a blur disc, smoking death dive
  shells    bigger impact: fireball, shockwave ring, debris, lingering smoke
  splash    near miss on water: column, spray and ring;  crater: near miss on land
"""
import math
import random

from tools.frontline import gltf_import as gi
from tools.frontline import rich_mdx as rm

UNIT_SEQ=[('Stand',0,999,0,False),('Walk',1000,1999,270,False),('Attack',2000,2999,0,False),
          ('Death',3000,5999,0,True),('Birth',6000,6999,0,True),('Work',7000,7999,0,False),
          ('Stand Work',8000,8999,0,False),('Decay',9000,12999,0,True)]
def span(name):return next((a,b) for n,a,b,_,_ in UNIT_SEQ if n==name)
STAND,WALK,ATTACK,DEATH,BIRTH,WORK,STANDWORK,DECAY=(span(n) for n,*_ in UNIT_SEQ)
END=UNIT_SEQ[-1][2]

def puff(x,y,z,r,colour,detail=1):
    from tools.frontline.imported import puff as p
    return p(x,y,z,r,colour,detail)

def split_team(tris,bone=0,alpha=None):
    return [rm.Layer([t for t in tris if t[1]!=gi.TEAM],rm.OPAQUE,bone,alpha),
            rm.Layer([t for t in tris if t[1]==gi.TEAM],rm.TEAMCOL,bone,alpha)]

def only(windows,value=1.0):
    return rm.visible_in(windows,END,value)

def gun_tip(tris,min_z_fraction=.35):
    lo,hi=gi.bounds(tris)
    pts=[p for t in tris for p in t[0] if p[2]>=lo[2]+(hi[2]-lo[2])*min_z_fraction]
    tip=max(pts,key=lambda p:p[0])
    return (tip[0],tip[1],tip[2])

def flash_layers(bones,tip,size,attack=ATTACK,smoke=True):
    """Muzzle flash for the first 80 ms of Attack and a gun-smoke puff drifting off."""
    bones.append(rm.Bone('Flash',0,tip));fid=len(bones)-1
    a,b=attack
    bones[fid].scale+=[(a,.5,.5,.5),(a+30,1.6,1.3,1.3),(a+80,.3,.3,.3),(b,.3,.3,.3)]
    layers=[rm.Layer(puff(size*.8,0,0,size,(255,214,120))+puff(size*1.8,0,0,size*.6,(255,244,190)),rm.ADD,fid,
                     [(0,0.0),(a-1,0.0),(a,1.0),(a+80,1.0),(a+81,0.0),(END,0.0)])]
    if smoke:
        bones.append(rm.Bone('GunSmoke',0,tip));sid=len(bones)-1
        bones[sid].translation+=[(a,0,0,0),(a+80,size,0,size*.3),(b,size*3,0,size*2)]
        bones[sid].scale+=[(a,.3,.3,.3),(a+80,1,1,1),(b,2.6,2.6,2.6)]
        layers.append(rm.Layer(puff(0,0,0,size*1.1,(160,158,150)),rm.BLEND,sid,[(0,0.0),(a+59,0.0),(a+60,.55),(b,0.0),(END,0.0)]))
    return layers

def explosion(bones,centre,size,start,rng,debris_colour=(70,66,58),smoke_until=None,ground=True):
    """Fireball, shockwave ring, debris arcs and a rising smoke column from `start`."""
    layers=[];cx,cy,cz=centre
    # Fireball: two additive puffs that pop and fade.
    bones.append(rm.Bone('Fireball',0 if not ground else -1,centre));fb=len(bones)-1
    bones[fb].scale+=[(0,0,0,0),(start,.2,.2,.2),(start+120,2.4,2.4,2.0),(start+420,3.0,3.0,2.6),(start+700,0,0,0)]
    layers.append(rm.Layer(puff(0,0,size*.4,size,(255,150,50))+puff(size*.4,size*.2,size*.9,size*.7,(255,226,120)),rm.ADD,fb,
                           [(0,0.0),(start-1,0.0),(start,1.0),(start+700,1.0),(start+701,0.0),(END,0.0)]))
    # Shockwave: a flat ring racing outward along the ground or water.
    bones.append(rm.Bone('Shock',-1,(cx,cy,1)));sw=len(bones)-1
    bones[sw].scale+=[(0,.1,.1,1),(start,.1,.1,1),(start+350,4.5,4.5,1),(start+351,.1,.1,1)]
    ring=[];r0,r1=size*.85,size
    for k in range(20):
        a0,a1=k*math.tau/20,(k+1)*math.tau/20
        q=[(math.cos(a0)*r0,math.sin(a0)*r0,.5),(math.cos(a0)*r1,math.sin(a0)*r1,.5),(math.cos(a1)*r1,math.sin(a1)*r1,.5),(math.cos(a1)*r0,math.sin(a0)*0+math.sin(a1)*r0,.5)]
        ring+=[((q[0],q[1],q[2]),(232,224,200),'ring'),((q[0],q[2],q[3]),(232,224,200),'ring')]
    layers.append(rm.Layer(ring,rm.BLEND,sw,[(0,0.0),(start-1,0.0),(start,.8),(start+350,0.0),(END,0.0)]))
    # Debris: chunks thrown out on ballistic arcs.
    for i in range(5):
        bones.append(rm.Bone(f'Debris{i}',-1,centre));db=len(bones)-1
        ang=rng.uniform(0,math.tau);dist=size*rng.uniform(2,4.5);up=size*rng.uniform(2,4)
        for k in range(9):
            f=k/8;t=start+int(900*f)
            bones[db].translation.append((t,math.cos(ang)*dist*f,math.sin(ang)*dist*f,up*4*f*(1-f)))
        bones[db].rotation+=[(start,*rm.euler(0,0)),(start+450,*rm.euler(170,90)),(start+900,*rm.euler(340,180))]
        layers.append(rm.Layer(gi.boxes([(0,0,0,size*.18,size*.12,size*.14,debris_colour)]),rm.OPAQUE,db,
                               [(0,0.0),(start-1,0.0),(start,1.0),(start+900,1.0),(start+901,0.0),(END,0.0)]))
    # Smoke column (two staggered puffs) until smoke_until.
    until=smoke_until or start+1500
    for phase in (0,.5):
        bones.append(rm.Bone(f'Smoke{int(phase*2)}',-1,(cx,cy,cz+size*.6)));sb=len(bones)-1
        tr={0:0.0};sc={0:.5};al={0:0.0,start-1:0.0,until+1:0.0,END:0.0}
        t=start+150;period=1200
        while t<until:
            wrap=min(until,t+int(period*(1-phase)))
            for when,f in ((t,phase),(wrap,1.0),(min(until,wrap+1),0.0),(min(until,t+period),phase)):
                tr[when]=size*5*f;sc[when]=1+2.2*f;al[when]=.65*(1-f)
            t+=period
        bones[sb].translation=[(k,0,0,v) for k,v in sorted(tr.items())]
        bones[sb].scale=[(k,v,v,v) for k,v in sorted(sc.items())]
        layers.append(rm.Layer(puff(0,0,0,size*.9,(58,56,54)),rm.BLEND,sb,sorted(al.items())))
    return layers

# ------------------------------------------------------------------ infantry
def soldier_mdx(name,tris):
    rng=random.Random(name)
    lo,hi=gi.bounds(tris);h=hi[2]-lo[2]
    bones=[rm.Bone('Root')];root=bones[0]
    for (a,b),kind in ((STAND,'stand'),(WALK,'walk'),(ATTACK,'attack'),(WORK,'work'),(STANDWORK,'work'),(BIRTH,'stand')):
        for i in range(9):
            t=a+(b-a)*i//8;ph=2*math.pi*i/8
            if kind=='walk':
                root.translation.append((t,0,0,abs(math.sin(ph))*h*.05));root.rotation.append((t,*rm.euler(3*math.sin(ph),1.5,0)))
            elif kind=='work':
                root.translation.append((t,0,0,0));root.rotation.append((t,*rm.euler(0,12*abs(math.sin(ph)),0)))
            elif kind=='attack':
                root.translation.append((t,-h*.04 if i==1 else 0,0,0));root.rotation.append((t,*rm.euler(0,-2 if i==1 else 0,0)))
            else:
                root.translation.append((t,0,0,h*.006*math.sin(ph)));root.rotation.append((t,*rm.euler(0,0,0)))
    # Death: knocked back, knees give, falls flat on the back and stays down through Decay.
    a,b=DEATH;side=rng.choice((-1,1))
    for f,pitch,roll,x in ((0,0,0,0),(.06,-12,4*side,-h*.05),(.14,-55,8*side,-h*.15),(.2,-88,10*side,-h*.2),(.23,-82,10*side,-h*.2),(.26,-90,10*side,-h*.21),(1,-90,10*side,-h*.21)):
        t=a+int((b-a)*f);root.rotation.append((t,*rm.euler(roll,pitch,0)));root.translation.append((t,x,0,h*.02 if 0<f<.2 else 0))
    for t in DECAY:root.rotation.append((t,*rm.euler(10*side,-90,0)));root.translation.append((t,-h*.21,0,-h*.02 if t==DECAY[1] else -h*.12))
    layers=split_team(tris,0,[(0,1.0),(END-400,1.0),(END,0.0)])
    layers+=flash_layers(bones,gun_tip(tris,.5),h*.06)
    return rm.emit(name,layers,bones,UNIT_SEQ)

# ------------------------------------------------------------------ vehicles
def vehicle_mdx(name,tris):
    rng=random.Random(name)
    lo,hi=gi.bounds(tris);h=hi[2]-lo[2];length=hi[0]-lo[0]
    bones=[rm.Bone('Root')];root=bones[0]
    for (a,b),kind in ((STAND,'stand'),(WALK,'walk'),(ATTACK,'attack'),(BIRTH,'stand'),(WORK,'stand'),(STANDWORK,'stand')):
        for i in range(9):
            t=a+(b-a)*i//8;ph=2*math.pi*i/8
            if kind=='walk':   # suspension pitching over rough ground
                root.translation.append((t,0,0,h*.02*abs(math.sin(ph*2))));root.rotation.append((t,*rm.euler(.8*math.sin(ph*1.5),1.2*math.sin(ph),0)))
            elif kind=='attack':  # recoil rocks the hull back, then it settles
                root.translation.append((t,(-length*.05,-length*.02,0,0,0,0,0,0,0)[i],0,0))
                root.rotation.append((t,*rm.euler(0,(-3,-1.5,.5,0,0,0,0,0,0)[i],0)))
            else:
                root.translation.append((t,0,0,0));root.rotation.append((t,*rm.euler(0,0,0)))
    a,b=DEATH   # explosion lifts the hull, it slams down and settles as a wreck
    for f,z,pitch,roll in ((0,0,0,0),(.04,h*.25,-6,4),(.1,h*.05,2,-3),(.14,-h*.05,0,-2),(1,-h*.08,1,-4)):
        t=a+int((b-a)*f);root.translation.append((t,0,0,z));root.rotation.append((t,*rm.euler(roll,pitch,0)))
    for t in DECAY:root.translation.append((t,0,0,-h*.08 if t==DECAY[0] else -h*.4));root.rotation.append((t,*rm.euler(-4,1,0)))
    # The hull chars: a dark copy fades in over the paint as it burns.
    burnt=[(p,tuple(int(c*.25) for c in (col if col!=gi.TEAM else (90,90,90))),tag) for p,col,tag in tris]
    burnt=[(tuple((x*1.01,y*1.01,z*1.01+.05) for x,y,z in p),c,tag) for p,c,tag in burnt]
    layers=split_team(tris)
    layers.append(rm.Layer(burnt,rm.BLEND,0,[(0,0.0),(DEATH[0]+150,0.0),(DEATH[0]+900,.8),(DECAY[1],.8),(END,.8)]))
    layers+=flash_layers(bones,gun_tip(tris),max(4.0,h*.12))
    layers+=explosion(bones,(0,0,h*.6),max(10.0,length*.18),DEATH[0]+80,rng,smoke_until=DECAY[1]+3000)
    return rm.emit(name,layers,bones,UNIT_SEQ)

# ------------------------------------------------------------------ aircraft
# Extra airframe sequences selected by animation tags the server publishes
# (games/warcraft-3/game/skills/s_air_effects.c, S_AircraftCritEffect kinds 1-4 and
# S_AircraftEvadeEffect):
#   fire    1 engine fire with a black smoke trail     vapour 4 fuel leak: white vapour trail
#   wobble  2 pilot hit: erratic wobble, nose sagging; Death Wobble glides gently into the surface
#   spin    3 control loss: a rolling spin; Death Spin tumbles down
#   jink    evade: a sharp snap roll and reversal
# Order matters: with several tags the server's best-overlap tie goes to the first
# sequence, so an evasive jink shows over a fire, and control loss over a pilot hit.
AIR_TAGS=('Jink','Spin','Wobble','Fire','Vapour')
AIR_EXTRA=[];_t=13000
for _tag in AIR_TAGS:
    for _primary,_speed in (('Stand',0),('Walk',270),('Attack',0)):
        AIR_EXTRA.append((f'{_primary} {_tag}',_t,_t+999,_speed,False));_t+=1000
for _tag in ('Spin','Wobble'):
    AIR_EXTRA.append((f'Death {_tag}',_t,_t+2999,0,True));_t+=3000
AIR_SEQ=UNIT_SEQ+AIR_EXTRA
AIR_END=AIR_SEQ[-1][2]
def air_span(name):return next((a,b) for n,a,b,_,_ in AIR_SEQ if n==name)
def tag_windows(tag,death=False):
    return [air_span(f'{p} {tag}') for p in ('Stand','Walk','Attack')+(('Death',) if death else ())]
FIRE_WINDOWS=tag_windows('Fire')
VAPOUR_WINDOWS=tag_windows('Vapour')
JINK_WINDOWS=tag_windows('Jink')
WOBBLE_WINDOWS=tag_windows('Wobble')
SPIN_WINDOWS=tag_windows('Spin')
# The tumbling fatal dive burns and smokes all the way down.
SMOKE_WINDOWS=FIRE_WINDOWS+[air_span('Death Spin')]

def _windowed_alpha(windows,inside):
    windows=list(windows)
    """Alpha keys: `inside(t)` samples (every 50 ms) in each window, 0 at both ends of every other sequence."""
    keys={0:0.0,AIR_END:0.0}
    for _,a,b,_,_ in AIR_SEQ:
        if (a,b) not in windows:keys[a]=0.0;keys[b]=0.0
    for a,b in windows:
        for t in list(range(a,b,50))+[b]:keys[t]=inside(t-a)
    return sorted(keys.items())

def smoke_trail(bones,engine,length,windows,colour=(30,29,28),fire=True,puffs=7,period=1100,peak=.78,name='Trail'):
    """A trail streaming aft (-x) in every window: black smoke behind an engine fire, or
    (fire=False, pale colour) a fuel-vapour stream."""
    layers=[]
    if fire:
        bones.append(rm.Bone('EngineFire',0,engine));fid=len(bones)-1
        for a,b in windows:
            for k,t in enumerate(range(a,b,70)):s=(1.0,1.5,.8,1.3,1.1)[k%5];bones[fid].scale.append((t,s,s*.8,s))
            bones[fid].scale.append((b,1,1,1))
        layers.append(rm.Layer(puff(0,0,1,4.2,(255,128,36))+puff(-3,0,3,3,(255,214,110))+puff(-6,0,2,2.4,(255,150,50)),rm.ADD,fid,
                               _windowed_alpha(windows,lambda t:.95)))
    for k in range(puffs):
        bones.append(rm.Bone(f'{name}{k}',0,engine));tid=len(bones)-1;phase=k/puffs   # rides the airframe, dives included
        f=lambda t:((t/period)+phase)%1.0
        for a,b in windows:
            times=set(range(a,b,50))|{b}
            w=a+int(period*(1-phase))
            while w<b:times|={w-1,w};w+=period
            for t in sorted(times):
                v=f(t-a)
                bones[tid].translation.append((t,-length*3.2*v,0,length*.25*v))
                sc=.5+2.6*v;bones[tid].scale.append((t,sc,sc,sc))
        layers.append(rm.Layer(puff(0,0,0,3.5 if fire else 2.6,colour),rm.BLEND,tid,_windowed_alpha(windows,lambda t:peak*(1-f(t))**.7)))
    return layers

def aircraft_mdx(name,tris):
    rng=random.Random(name)
    lo,hi=gi.bounds(tris);span_=hi[1]-lo[1];length=hi[0]-lo[0]
    prop=[t for t in tris if t[2]=='prop'];body=[t for t in tris if t[2]!='prop']
    hub=(hi[0]-1,0,sum(p[2] for t in prop for p in t[0])/max(1,3*len(prop))) if prop else (hi[0],0,(lo[2]+hi[2])/2)
    bones=[rm.Bone('Root'),rm.Bone('Prop',0,hub)];root=bones[0]
    cruise=[(STAND,6),(WALK,16),(ATTACK,10),(BIRTH,0),(WORK,6),(STANDWORK,6)]
    cruise+=list(zip(FIRE_WINDOWS,(9,20,12)))+list(zip(VAPOUR_WINDOWS,(6,16,10)))
    for (a,b),bank in cruise:
        for i in range(9):
            t=a+(b-a)*i//8;ph=2*math.pi*i/8
            root.rotation.append((t,*rm.euler(bank*math.sin(ph),2*math.sin(ph*2),0)))
            root.translation.append((t,0,span_*.04*math.sin(ph),3*math.sin(ph*2)))
    # Jink: a snap roll one way, a hard reversal and recovery, with a sideslip.
    for a,b in JINK_WINDOWS:
        for f,roll,yaw,y in ((0,0,0,0),(.15,78,8,.15),(.35,82,10,.3),(.55,-64,-9,.05),(.75,-70,-8,-.2),(1,0,0,0)):
            t=a+int((b-a)*f);root.rotation.append((t,*rm.euler(roll,-4*abs(math.sin(f*math.pi)),yaw)));root.translation.append((t,0,span_*y,0))
    # Pilot hit: irregular wobble, the nose sagging and the aircraft sinking a little.
    for a,b in WOBBLE_WINDOWS:
        for f,roll,pitch,z in ((0,0,4,-6),(.12,-18,6,-8),(.3,14,9,-12),(.45,-9,5,-10),(.62,22,10,-14),(.8,-12,7,-9),(1,0,4,-6)):
            t=a+int((b-a)*f);root.rotation.append((t,*rm.euler(roll,pitch,6*math.sin(f*math.tau))));root.translation.append((t,0,0,z))
    # Control loss: a continuous rolling spin with the nose dropping.
    for a,b in SPIN_WINDOWS:
        for k in range(9):
            f=k/8;t=a+int((b-a)*f)
            root.rotation.append((t,*rm.euler(360*f,14+6*math.sin(f*math.tau),20*math.sin(f*math.tau))));root.translation.append((t,0,0,-10*math.sin(f*math.pi)))
    # Death Wobble: a gentle, shallow glide that meets the surface at ~90% of the clip.
    a,b=air_span('Death Wobble')
    for k in range(13):
        f=k/12;t=a+int((b-a)*f)
        root.rotation.append((t,*rm.euler(10*math.sin(f*9),8+10*f,0)))
        root.translation.append((t,length*2.2*f,0,-270*min(1.0,f/.9)**1.3))
    a,b=DEATH   # spinning, smoking dive into the sea/ground
    for k in range(13):
        f=k/12;t=a+int((b-a)*f)
        root.rotation.append((t,*rm.euler(360*2*f,35*f,0)))
        root.translation.append((t,0,0,-230*f*f))
    # Death Spin (control loss or a fatal hit): a burning, tumbling dive that reaches the surface
    # at ~90% of the clip, where the server's crash splash/explosion blooms.
    a,b=air_span('Death Spin')
    for k in range(25):
        f=k/24;t=a+int((b-a)*f)
        root.rotation.append((t,*rm.euler(360*4.5*f,25+45*f,140*f*f)))
        root.translation.append((t,length*.6*f,0,-270*min(1.0,f/.9)**1.7))
    for t in DECAY:root.rotation.append((t,*rm.euler(0,35,0)));root.translation.append((t,0,0,-260))
    # Propeller: blades spin ~12 rev/s; a translucent disc reads as motion blur.
    for s0,e0 in [STAND,WALK,ATTACK,WORK,STANDWORK,DEATH,BIRTH]+[(a,b) for n,a,b,_,_ in AIR_EXTRA]:
        t=s0;angle=0
        while t<e0:
            bones[1].rotation.append((t,*rm.euler(angle,0,0)));t+=21;angle+=90
        bones[1].rotation.append((e0,*rm.euler(angle,0,0)))
    radius=max([math.hypot(p[1],p[2]-hub[2]) for t in prop for p in t[0]] or [6])
    disc=[]
    for k in range(16):
        a0,a1=k*math.tau/16,(k+1)*math.tau/16
        disc.append((((0,0,0),(0,math.cos(a0)*radius,math.sin(a0)*radius),(0,math.cos(a1)*radius,math.sin(a1)*radius)),(70,70,74),'blur'))
        disc.append((((0,0,0),(0,math.cos(a1)*radius,math.sin(a1)*radius),(0,math.cos(a0)*radius,math.sin(a0)*radius)),(70,70,74),'blur'))
    local_prop=gi.transform(prop,1,(-hub[0],-hub[1],-hub[2]))
    layers=split_team(body)+[rm.Layer(local_prop,rm.OPAQUE,1),rm.Layer(disc,rm.BLEND,1,[(0,.35),(AIR_END,.35)])]
    for attack in [ATTACK]+[air_span(f'Attack {tag}') for tag in AIR_TAGS]:
        layers+=flash_layers(bones,(hi[0],span_*.3,(lo[2]+hi[2])/2),3,attack=attack,smoke=False)
    layers+=explosion(bones,(0,0,(lo[2]+hi[2])/2),12,DEATH[0]+60,rng,smoke_until=DEATH[1],ground=False)
    # Engine fire sits just behind the cowling; the trail streams back past the tail.
    top=max(p[2] for t in body for p in t[0] if p[0]>hi[0]-length*.4)
    layers+=smoke_trail(bones,(hi[0]-length*.3,0,top),length,SMOKE_WINDOWS)
    # Fuel leak: a thin white vapour stream from the wing root.
    layers+=smoke_trail(bones,(-length*.1,span_*.22,(lo[2]+hi[2])/2),length,VAPOUR_WINDOWS,colour=(238,240,242),fire=False,peak=.6,name='Vapour')
    return rm.emit(name,layers,bones,AIR_SEQ)

# ------------------------------------------------------------------ projectiles and impacts
def projectile_mdx(name,body,size,flash=3.0):
    """Body in flight (with an oversized first frame as before); a big burst on Death."""
    rng=random.Random(name)
    bones=[rm.Bone('Root')]
    bones[0].scale+=[(0,flash,flash,flash),(70,1,1,1),(DEATH[0]-1,1,1,1),(DEATH[0],1,1,1),(END,1,1,1)]
    layers=[rm.Layer(body,rm.OPAQUE,0,[(0,1.0),(DEATH[0]-1,1.0),(DEATH[0],0.0),(DEATH[1],0.0),(DEATH[1]+1,1.0),(END,1.0)])]
    if name=='tracer':   # bullets: a short spark, no debris (machine guns fire constantly)
        bones.append(rm.Bone('Spark',-1,(0,0,0)));sp=len(bones)-1
        bones[sp].scale+=[(0,0,0,0),(DEATH[0],.4,.4,.4),(DEATH[0]+60,1.3,1.3,1.3),(DEATH[0]+200,0,0,0)]
        layers.append(rm.Layer(puff(0,0,0,size*.45,(255,220,140)),rm.ADD,sp,[(0,0.0),(DEATH[0]-1,0.0),(DEATH[0],1.0),(DEATH[0]+200,0.0),(END,0.0)]))
    else:
        layers+=explosion(bones,(0,0,0),size,DEATH[0],rng,smoke_until=DEATH[0]+2400)
    return rm.emit(name,layers,bones,UNIT_SEQ)

EFFECT_SEQ=[('Stand',0,99,0,False),('Death',100,6099,0,True)]
def splash_mdx():
    """Near miss on water: a white column that rises and collapses, spray and a foam ring."""
    bones=[rm.Bone('Column'),rm.Bone('Ring',-1,(0,0,1))]
    bones[0].scale+=[(0,.1,.1,.1),(100,.3,.3,.2),(350,1,1,1.2),(900,1.2,1.2,.9),(1500,1.5,1.5,.2),(1600,.1,.1,.1),(6099,.1,.1,.1)]
    bones[1].scale+=[(0,.2,.2,1),(100,.2,.2,1),(1600,3.5,3.5,1),(6099,3.5,3.5,1)]
    column=puff(0,0,20,9,(240,246,248))+puff(0,0,42,7,(232,240,244))+puff(0,0,62,5,(226,236,240))
    spray=[t for i in range(6) for t in puff(math.cos(i)*10,math.sin(i)*10,12,4,(236,242,246))]
    ring=[]
    for k in range(18):
        a0,a1=k*math.tau/18,(k+1)*math.tau/18
        q=[(math.cos(a0)*10,math.sin(a0)*10,.4),(math.cos(a0)*14,math.sin(a0)*14,.4),(math.cos(a1)*14,math.sin(a1)*14,.4),(math.cos(a1)*10,math.sin(a1)*10,.4)]
        ring+=[((q[0],q[1],q[2]),(238,244,246),'ring'),((q[0],q[2],q[3]),(238,244,246),'ring')]
    layers=[rm.Layer(column+spray,rm.BLEND,0,[(0,0.0),(99,0.0),(100,.85),(1000,.7),(1600,0.0),(6099,0.0)]),
            rm.Layer(ring,rm.BLEND,1,[(0,0.0),(99,0.0),(100,.7),(3000,0.0),(6099,0.0)])]
    return rm.emit('splash',layers,bones,EFFECT_SEQ)

def crater_mdx():
    """Near miss on land: dirt thrown up, a small flash, smoke, and a scorched crater that lingers."""
    rng=random.Random('crater')
    bones=[rm.Bone('Root')]
    layers=explosion(bones,(0,0,0),9,100,rng,debris_colour=(92,74,52),smoke_until=2600)
    dirt=[t for i in range(5) for t in puff(rng.uniform(-6,6),rng.uniform(-6,6),6+i*3,5,(110,92,68))]
    bones.append(rm.Bone('Dirt',-1,(0,0,0)));d=len(bones)-1
    bones[d].scale+=[(0,.1,.1,.1),(100,.3,.3,.3),(400,1.4,1.4,1.8),(1300,1.6,1.6,.4),(1400,.1,.1,.1),(6099,.1,.1,.1)]
    layers.append(rm.Layer(dirt,rm.BLEND,d,[(0,0.0),(99,0.0),(100,.9),(1300,0.0),(6099,0.0)]))
    crater=[]
    for k in range(14):
        a0,a1=k*math.tau/14,(k+1)*math.tau/14;r=14*(.85+.3*rng.random())
        crater.append((((0,0,.7),(math.cos(a0)*r,math.sin(a0)*r,.7),(math.cos(a1)*r,math.sin(a1)*r,.7)),(40,34,28),'crater'))
    layers.append(rm.Layer(crater,rm.BLEND,0,[(0,0.0),(99,0.0),(200,.85),(4500,.7),(6099,0.0)]))
    return rm.emit('crater',layers,bones,[(n,a,b,s,o) for n,a,b,s,o in EFFECT_SEQ])

# ------------------------------------------------------------------ flak and aircraft crashes
def flak_layers(heavy):
    """Anti-aircraft burst at altitude. Heavy (5"/38, 90 mm, Type 88, 12.7 cm): a big
    near-black cluster; light (40/25/20 mm): a small grey puff. Both open with a brief
    orange flash, then hang, swell, drift downwind (+x) and fade over the Death clip."""
    rng=random.Random('flak_heavy' if heavy else 'flak_light')
    a,b=EFFECT_SEQ[1][1:3]
    size=13.0 if heavy else 5.5
    shade=(34,32,30) if heavy else (132,130,126)
    count=6 if heavy else 3
    drift=(55,24) if heavy else (32,14)
    bones=[rm.Bone('Flash')]
    bones[0].scale+=[(0,.2,.2,.2),(a,.3,.3,.3),(a+50,1.3,1.3,1.3),(a+180,.6,.6,.6),(a+260,.1,.1,.1),(b,.1,.1,.1)]
    layers=[rm.Layer(puff(0,0,0,size*.7,(255,150,40))+puff(0,0,0,size*.4,(255,230,150)),rm.ADD,0,
                     [(0,0.0),(a-1,0.0),(a,1.0),(a+160,.9),(a+260,0.0),(b,0.0)])]
    for k in range(count):
        off=(0,0,0) if k==0 else (rng.uniform(-1,1)*size*.7,rng.uniform(-1,1)*size*.7,rng.uniform(-.5,.6)*size*.6)
        bones.append(rm.Bone(f'Puff{k}',-1,off));pid=len(bones)-1
        dx,dz=drift[0]*rng.uniform(.8,1.2),drift[1]*rng.uniform(.7,1.3)
        bones[pid].translation+=[(0,0,0,0),(a,0,0,0),(a+400,dx*.08,0,dz*.05),(b,dx,rng.uniform(-6,6),dz)]
        s0=rng.uniform(.25,.4);s1=rng.uniform(.9,1.1);s2=rng.uniform(1.8,2.3)
        bones[pid].scale+=[(0,s0,s0,s0),(a,s0,s0,s0),(a+250,s1,s1,s1),(a+1500,s1*1.3,s1*1.3,s1*1.2),(b,s2,s2,s2*.85)]
        r=size*rng.uniform(.65,.95) if k else size
        tone=tuple(max(0,min(255,c+rng.randint(-8,10))) for c in shade)
        peak=.92 if heavy else .8
        layers.append(rm.Layer(puff(0,0,0,r,tone),rm.BLEND,pid,
                               [(0,0.0),(a-1,0.0),(a+20,peak),(a+2600,peak*.75),(a+4800,peak*.25),(b-150,0.0),(b,0.0)]))
    return layers,bones

def flak_mdx(heavy):
    layers,bones=flak_layers(heavy)
    return rm.emit('flak_heavy' if heavy else 'flak_light',layers,bones,EFFECT_SEQ)

# The crash effect is spawned as the aircraft dies (Death / Death Spin start) and holds
# invisible until the dive reaches the surface. Server copy: AIRCRAFT_CRASH_DELAY_MS.
CRASH_AT=EFFECT_SEQ[1][1]+2700
def crash_layers(water):
    """Aircraft hitting the sea (tall splash, burning fuel slick, smoke) or land (fireball, debris, scorch)."""
    rng=random.Random('crash_sea' if water else 'crash_land')
    a,b=EFFECT_SEQ[1][1:3];t0=CRASH_AT
    hide=lambda keys:[(0,0.0),(t0-1,0.0)]+keys+[(b,0.0)]
    bones=[rm.Bone('Root')]
    if water:
        bones.append(rm.Bone('Column',-1,(0,0,0)));c=len(bones)-1
        bones[c].scale+=[(0,.1,.1,.1),(t0,.2,.2,.2),(t0+250,1.3,1.3,1.6),(t0+800,1.5,1.5,1.1),(t0+1500,1.8,1.8,.2),(t0+1600,.1,.1,.1),(b,.1,.1,.1)]
        column=puff(0,0,26,12,(240,246,248))+puff(0,0,54,9,(232,240,244))+puff(0,0,80,6,(226,236,240))
        spray=[t for i in range(8) for t in puff(math.cos(i*.8)*16,math.sin(i*.8)*16,14,5,(236,242,246))]
        layers=[rm.Layer(column+spray,rm.BLEND,c,hide([(t0,.9),(t0+1000,.7),(t0+1600,0.0)]))]
        slick=[]
        for k in range(16):
            a0,a1=k*math.tau/16,(k+1)*math.tau/16;r=20*(.8+.4*rng.random())
            slick.append((((0,0,.6),(math.cos(a0)*r,math.sin(a0)*r,.6),(math.cos(a1)*r,math.sin(a1)*r,.6)),(26,24,22),'slick'))
        layers.append(rm.Layer(slick,rm.BLEND,0,hide([(t0+150,.75),(b-300,.5)])))
        bones.append(rm.Bone('Burn',-1,(0,0,3)));f=len(bones)-1
        for k,t in enumerate(range(t0,b,90)):s=(1,1.3,.9,1.2)[k%4];bones[f].scale.append((t,s,s,s*1.2))
        layers.append(rm.Layer(puff(0,0,0,5,(255,120,30))+puff(4,2,2,3.5,(255,200,90)),rm.ADD,f,hide([(t0+150,.9),(b-600,.6),(b-200,0.0)])))
        layers+=[l for l in explosion(bones,(0,0,0),10,t0+60,rng,smoke_until=b-200,ground=True) if l.material==rm.BLEND and l.tris[0][2]=='puff']
    else:
        layers=explosion(bones,(0,0,0),16,t0,rng,debris_colour=(60,62,56),smoke_until=b-100)
        scorch=[]
        for k in range(14):
            a0,a1=k*math.tau/14,(k+1)*math.tau/14;r=22*(.8+.4*rng.random())
            scorch.append((((0,0,.7),(math.cos(a0)*r,math.sin(a0)*r,.7),(math.cos(a1)*r,math.sin(a1)*r,.7)),(34,30,26),'scorch'))
        layers.append(rm.Layer(scorch,rm.BLEND,0,hide([(t0+100,.85),(b-400,.6)])))
    for l in layers:   # explosion() keys run to END; clip everything to before impact
        if l.alpha:l.alpha=[(t,v if t>=t0 else 0.0) for t,v in l.alpha]+[(t0-1,0.0)]
    return layers,bones

def crash_mdx(water):
    layers,bones=crash_layers(water)
    return rm.emit('crash_sea' if water else 'crash_land',layers,bones,EFFECT_SEQ)
