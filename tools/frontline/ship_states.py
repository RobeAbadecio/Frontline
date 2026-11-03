"""Ship condition presentation: one MDX per hull with a sequence for every state.

The server (s_naval.c CAbilityShipDamage) sets two animation properties on a
ship: an effect tag (smoke | fire | inferno) and a list level (list1..list3,
stepped one level at a time so the hull settles gradually). Each Stand / Walk /
Attack sequence here is one combination of those tags:

  healthy   bow wave + wake (Walk), gentle pitch and roll
  smoke     light damage: scorch patches and rising smoke wisps
  fire      burning: flickering flames and a thick smoke column at the hit
  inferno   critical: several fires, secondary explosions
  listN     flooding/critical: progressive list to starboard, bow trim down,
            lower freeboard, a smaller wake
  Death     bow-first plunge (carriers capsize) with fires, steam, bubbles,
            spreading oil and debris; the hull fades under water
  Decay     the oil slick and debris drift and fade; no hull
  Stand*    dead in the water: no wake, the hull only rolls

Main-battery turrets are separate server mounts that copy the ship's frame, so
turret_mdx uses the same sequence table (recoil, muzzle flash and gun smoke in
Attack). POSES must match SHIP_POSE in games/warcraft-3/game/skills/s_naval.c.
"""
import math
import random

from tools.frontline import gltf_import as gi
from tools.frontline import rich_mdx as rm

# (roll degrees to starboard, bow-down trim degrees, freeboard drop) per list level.
POSES=[(0.0,0.0,0.0),(3.5,0.8,2.5),(7.0,1.6,5.0),(11.0,2.6,8.0)]
EFFECTS=('','smoke','fire','inferno')
# Death motion keys (fraction of Death, roll, trim, z). PLUNGE must match SHIP_PLUNGE in
# s_naval.c (turret mounts follow it); carriers carry no mounts and capsize instead.
PLUNGE=[(0,0,0,0),(.2,4,3,-6),(.5,7,14,-26),(.8,9,28,-70),(1,10,38,-130)]
CAPSIZE=[(0,0,0,0),(.25,25,1,-6),(.55,80,3,-20),(.8,120,6,-55),(1,140,8,-110)]
STAND_MS,ATTACK_MS,DEATH_MS,DECAY_MS=2000,1000,6000,4000

def sequences():
    """[(name, start, end, move speed, non-looping, primary, list level, effect)]"""
    out=[];t=0
    for primary,length in (('Stand',STAND_MS),('Walk',STAND_MS),('Attack',ATTACK_MS)):
        for level in range(len(POSES)):
            for fx in EFFECTS:
                name=' '.join(w for w in (primary,f'List{level}' if level else '',fx.capitalize() if fx else '') if w)
                out.append((name,t,t+length-1,270 if primary=='Walk' else 0,False,primary,level,fx));t+=length
    for name,length,once in (('Death',DEATH_MS,True),('Birth',1000,True),('Decay',DECAY_MS,True)):
        out.append((name,t,t+length-1,0,once,name,0,''));t+=length
    return out

SEQUENCES=sequences()
END=SEQUENCES[-1][2]
FIELD={'primary':5,'level':6,'fx':7}
def windows(**match):
    """Sequence (start, end) windows whose fields equal (or satisfy a predicate for) `match`."""
    ok=lambda v,want:want(v) if callable(want) else v==want
    return [(s[1],s[2]) for s in SEQUENCES if s[5] in ('Stand','Walk','Attack') and all(ok(s[FIELD[k]],w) for k,w in match.items())]
def seq(name):
    return next(s for s in SEQUENCES if s[0]==name)

def puff(x,y,z,r,colour,detail=1):
    from tools.frontline.imported import puff as p
    return p(x,y,z,r,colour,detail)

def _deck_points(tris,count,rng):
    """Spots on the upper deck (deck-tagged faces, else the top of the hull) for fires and scorch."""
    lo,hi=gi.bounds(tris)
    deck=[t for t in tris if t[2] in ('deck','deck_plank')] or [t for t in tris if min(p[2] for p in t[0])>hi[2]*.15]
    pts=[]
    for i in range(count):
        t=deck[rng.randrange(len(deck))][0]
        c=[sum(p[k] for p in t)/3 for k in range(3)]
        pts.append((c[0],c[1]*.5,c[2]+1))
    return sorted(pts)

def ship_mdx(name,tris,wake,capsize=False):
    """tris: engine-frame hull (bow +X); wake: walk-only foam triangles."""
    rng=random.Random(name)
    lo,hi=gi.bounds(tris);length=hi[0]-lo[0];beam=hi[1]-lo[1]
    scale=max(.6,length/250.0)                   # effect size follows hull size
    bones=[rm.Bone('Hull')];water=1;bones.append(rm.Bone('Water'))
    layers=[]
    hull=[t for t in tris if t[1]!=gi.TEAM];team=[t for t in tris if t[1]==gi.TEAM]
    death=seq('Death');decay=seq('Decay')
    # Hull visible until it slips under in Death; hidden through Decay.
    hull_alpha=[(0,1.0),(death[2]-1200,1.0),(death[2],0.0),(decay[1],0.0),(decay[2],0.0)]
    layers+=[rm.Layer(hull,rm.OPAQUE,0,hull_alpha),rm.Layer(team,rm.TEAMCOL,0,hull_alpha)]

    # ---- hull motion: bob per sequence on top of the list pose; Death plunge/capsize.
    root=bones[0]
    for s in SEQUENCES:
        a,b,primary,level=s[1],s[2],s[5],s[6]
        roll,trim,drop=POSES[level]
        if primary in ('Stand','Walk','Attack'):
            amp_r,amp_p,heave=(0.7,0.3,0.6) if primary!='Walk' else (0.45,0.7,0.9)
            steps=8
            for i in range(steps+1):
                t=a+(b-a)*i//steps;ph=2*math.pi*i/steps
                root.rotation.append((t,*rm.euler(roll+amp_r*math.sin(ph),trim+amp_p*math.sin(ph+1.3))))
                root.translation.append((t,0,0,-drop+heave*math.sin(ph+.6)))
    a,b=death[1],death[2]
    plan=CAPSIZE if capsize else PLUNGE
    for f,roll,trim,z in plan:
        t=a+int((b-a)*f)
        root.rotation.append((t,*rm.euler(roll,trim)));root.translation.append((t,0,0,z))
    for t in (decay[1],decay[2]):
        root.rotation.append((t,*rm.euler(10,38)));root.translation.append((t,0,0,-160))

    # ---- wakes (water bone: they stay on the surface); flooding hulls push a smaller wake.
    layers.append(rm.Layer(wake,rm.BLEND,water,rm.visible_in(windows(primary='Walk',level=lambda v:v<2),END,.6)))
    small=gi.transform(wake,(.6,.75,1.0))
    layers.append(rm.Layer(small,rm.BLEND,water,rm.visible_in(windows(primary='Walk',level=lambda v:v>=2),END,.45)))

    damaged=lambda fx:fx!=''
    burning=lambda fx:fx in ('fire','inferno')
    # ---- scorch patches on the deck (any damage, and the sinking hulk).
    spots=_deck_points(tris,6,rng)
    scorch=sum((gi.boxes([(x,y,z,4*scale+rng.random()*3*scale,3*scale+rng.random()*2*scale,.4,(34,32,30))]) for x,y,z in spots[:4]),[])
    layers.append(rm.Layer(scorch,rm.OPAQUE,0,rm.visible_in(windows(fx=damaged)+[(death[1],death[2])],END)))

    def rising(index,x,y,z,colour,size,height,material,match,alpha,period=1000,extra=()):
        """Two staggered puffs on their own bones (children of the hull) that rise, swell
        and fade, looping every `period` ms through each matching sequence window."""
        out=[]
        wins=windows(fx=match)+list(extra)
        for phase in (0.0,.5):
            bone=rm.Bone(f'Puff{index}_{int(phase*2)}',0,(x,y,z));bones.append(bone);bid=len(bones)-1
            tr,sc,al={0:0.0},{0:.5},{0:0.0,END:0.0}
            for a,b in wins:
                al.setdefault(a-1 if a else 0,0.0)
                t=a
                while t<b:
                    wrap=min(b,t+int(period*(1-phase)))
                    for when,frac in ((t,phase),(wrap,1.0),(min(b,wrap+1),0.0),(min(b,t+period),phase)):
                        tr[when]=height*frac;sc[when]=1+1.6*frac;al[when]=alpha*(1-frac)
                    t+=period
                al[b+1]=0.0
            bone.translation=[(k,0,0,v) for k,v in sorted(tr.items())]
            bone.scale=[(k,v,v,v) for k,v in sorted(sc.items())]
            out.append(rm.Layer(puff(0,0,0,size,colour),material,bid,sorted(al.items())))
        return out

    # ---- smoke wisps (light damage and worse), thick smoke and flames at the hit (burning).
    sx,sy,sz=spots[4];fx_,fy_,fz_=spots[1]
    layers+=rising(0,sx,sy,sz,(118,116,112),8*scale,40*scale,rm.BLEND,damaged,.6)
    layers+=rising(1,fx_,fy_,fz_,(52,50,48),13*scale,95*scale,rm.BLEND,burning,.8,extra=[(death[1],death[1]+4000)])
    flames=[]
    fire_points=[spots[1]]+[spots[2],spots[3]]
    for i,(x,y,z) in enumerate(fire_points):
        bone=rm.Bone(f'Flame{i}',0,(x,y,z));bones.append(bone);bid=len(bones)-1
        match=burning if i==0 else (lambda fx:fx=='inferno')
        wins=windows(fx=match)+[(death[1],death[1]+3500)]
        for a,b in wins:            # flicker: jittered scale every 90 ms
            t=a
            while t<b:
                k=.7+rng.random()*.7;bone.scale.append((t,k,k,k*(1+rng.random()*.5)));t+=90
            bone.scale.append((b,1,1,1))
        body=puff(0,0,6*scale,9*scale,(255,140,40))+puff(2*scale,1*scale,13*scale,5.5*scale,(255,206,90))
        layers.append(rm.Layer(body,rm.ADD,bid,rm.visible_in(wins,END)))
    # ---- secondary explosions (critical) at random moments.
    bone=rm.Bone('Blast',0,spots[5]);bones.append(bone);bid=len(bones)-1
    blast_keys=[]
    for a,b in windows(fx='inferno')+[(death[1],death[1]+2500)]:
        when=a+rng.randrange(100,max(150,(b-a)//2))
        bone.scale+=[(a,0,0,0),(when,0,0,0),(when+120,3,3,3),(when+380,0,0,0),(b,0,0,0)]
        blast_keys+=[(a,1.0),(b,1.0)]
    blast_alpha=sorted(dict([(0,0.0),(END,0.0)]+blast_keys+[(b+1,0.0) for a,b in windows(fx='inferno')]).items())
    layers.append(rm.Layer(puff(0,0,6*scale,12*scale,(255,228,150)),rm.ADD,bid,blast_alpha))

    # ---- sinking: steam from the funnels, bubbles, spreading oil and floating debris.
    funnel=(lo[0]+length*.45,0,hi[2]*.6)
    layers+=rising(2,*funnel,(236,238,240),11*scale,70*scale,rm.BLEND,lambda fx:False,.6,extra=[(death[1]+1500,death[2])])
    oil=rm.Bone('Oil',-1,(0,0,0));bones.append(oil);bid=len(bones)-1
    oil.scale+=[(0,.2,.2,1),(death[1],.2,.2,1),(death[2],1.4,1.1,1),(decay[2],2.2,1.7,1)]
    disc=[]
    for k in range(28):
        a0,a1=k*math.tau/28,(k+1)*math.tau/28
        r=length*.36*(0.94+.12*rng.random())
        disc.append((((0,0,.6),(math.cos(a0)*r,math.sin(a0)*r*.55,.6),(math.cos(a1)*r,math.sin(a1)*r*.55,.6)),(24,24,28),'oil'))
    layers.append(rm.Layer(disc,rm.BLEND,bid,[(0,0.0),(death[1]-1,0.0),(death[1],0.15),(death[2],.55),(decay[1]+600,.45),(decay[2]-1,.0),(decay[2],0.0)]))
    debris=rm.Bone('Debris',-1,(0,0,0));bones.append(debris);bid=len(bones)-1
    debris.translation+=[(0,0,0,0),(death[1],0,0,0),(decay[2],length*.08,beam*.15,0)]
    bits=sum((gi.boxes([(rng.uniform(lo[0],hi[0])*.6,rng.uniform(-beam,beam),.4,2*scale,1.2*scale,.8,(96,80,62))]) for _ in range(9)),[])
    bits+=sum((puff(rng.uniform(lo[0],hi[0])*.4,rng.uniform(-beam*.4,beam*.4),.5,1.4*scale,(214,226,230)) for _ in range(4)),[])
    layers.append(rm.Layer(bits,rm.OPAQUE,bid,[(0,0.0),(death[1]+1499,0.0),(death[1]+1500,1.0),(decay[2]-200,1.0),(decay[2],0.0)]))

    sequences_=[(n,a,b,speed,once) for n,a,b,speed,once,*_ in SEQUENCES]
    return rm.emit(name,layers,bones,sequences_)

def turret_mdx(name,tris):
    """Main-battery house: barrels recoil, muzzle flash and gun smoke in every Attack sequence."""
    lo,hi=gi.bounds(tris)
    barrels=[t for t in tris if min(p[0] for p in t[0])>hi[0]*.35]
    body=[t for t in tris if t not in barrels]
    tip=(hi[0],0,sum(p[2] for t in barrels for p in t[0])/max(1,3*len(barrels)))
    bones=[rm.Bone('Turret'),rm.Bone('Barrels',0),rm.Bone('Flash',0,tip),rm.Bone('GunSmoke',0,tip)]
    attacks=windows(primary='Attack')
    for a,b in attacks:
        bones[1].translation+=[(a,0,0,0),(a+50,-5,0,0),(a+420,0,0,0),(b,0,0,0)]
        bones[2].scale+=[(a,.4,.4,.4),(a+40,1.6,1.4,1.4),(a+110,.2,.2,.2),(b,.2,.2,.2)]
        bones[3].translation+=[(a,0,0,0),(a+70,6,0,1),(b,18,0,9)]
        bones[3].scale+=[(a,.3,.3,.3),(a+70,1,1,1),(b,3.2,3.2,3.2)]
    flash_alpha={0:0.0,END:0.0};smoke_alpha={0:0.0,END:0.0}
    for a,b in attacks:
        flash_alpha.update({a:1.0,a+110:1.0,a+111:0.0});smoke_alpha.update({a+60:.7,b:0.0,b+1:0.0})
        flash_alpha.setdefault(a-1,0.0);smoke_alpha.setdefault(a+59,0.0)
    flash=puff(6,0,0,4,(255,214,120))+puff(13,0,0,2.6,(255,244,190))
    smoke=puff(0,0,0,5,(150,148,142))
    team=[t for t in body if t[1]==gi.TEAM];plain=[t for t in body if t[1]!=gi.TEAM]
    layers=[rm.Layer(plain,rm.OPAQUE,0),rm.Layer(team,rm.TEAMCOL,0),rm.Layer(barrels,rm.OPAQUE,1),
            rm.Layer(flash,rm.ADD,2,sorted(flash_alpha.items())),rm.Layer(smoke,rm.BLEND,3,sorted(smoke_alpha.items()))]
    return rm.emit(name,layers,bones,[(n,a,b,speed,once) for n,a,b,speed,once,*_ in SEQUENCES])
