#!/usr/bin/env python3
"""Build Frontline: Island Command using the original pack's proven emitters."""
from pathlib import Path
import argparse
import math
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.emberfield import generate as base
from tools.frontline import catalog, models, pacific, place_names
from tools.frontline.scenario import COMMON, AI_SCRIPT, MAP_SCRIPT
from PIL import Image,ImageDraw,ImageOps,ImageEnhance
import random,struct,wave,os
TITLE='Frontline: Island Command'
LICENSE='MIT original procedural content; Kenney audio, Quaternius meshes and ambientCG terrain CC0 (third_party/CREDITS.md); DejaVu font license included'
MAP_PATH='Maps/Frontline/IslandCommand.w3m'
IJN_MAP_PATH='Maps/Frontline/IslandCommandIJN.w3m'
SANDBOX_MAP_PATH='Maps/Frontline/IslandCommandSandbox.w3m'
# Pacific theatre maps (tools/frontline/pacific.py): same scenario, theatre-specific sites.
PACIFIC_MAP_PATH='Maps/Frontline/Pacific.w3m'
PACIFIC_IJN_MAP_PATH='Maps/Frontline/PacificIJN.w3m'
PACIFIC_SANDBOX_MAP_PATH='Maps/Frontline/PacificSandbox.w3m'

# Naval layout, point-symmetric so both sides get identical ground: mainlands fill
# the top-left and bottom-right corners behind a wavy diagonal coast, leaving a
# ~5800-wide open ocean between them. Resource islands sit in the north/south
# (contested, equidistant) and on each side's flank; every channel stays >=700
# wide so battleship and carrier groups never squeeze through a choke.
COAST=4200
# Playable half-size in world units (FRONTLINE_MAP_HALF overrides it); terrain extends 1792 beyond it.
# The original match used 4352. The bigger default keeps both HQs where they were and adds mainland
# depth for building and forests behind them, open ocean for fleets, and outer resource islands.
MAP_HALF=int(os.environ.get('FRONTLINE_MAP_HALF','8192'))
TERRAIN_HALF=MAP_HALF+1792
TILES=2*TERRAIN_HALF//128+1               # terrain vertices per side
CELLS=(TILES-1)*4                         # 32-unit pathing cells per side
ISLANDS=[(2400,3100,700),(3600,1400,600)]          # north (contested), east (B flank)
ISLANDS+=[(5200,5600,750),(5800,2600,650),(2600,5800,650)]   # outer ocean: corner, east and north rim
ISLANDS+=[(7200,7200,800),(7400,3800,700),(3800,7400,700)]   # far rim: deep corner, far east, far north
ISLANDS+=[(-x,-y,r) for x,y,r in ISLANDS]           # south (contested), west (A flank), mirrored rim
def mainland(x,y):return y-x>COAST+220*math.sin((x+y)/650)   # top-left; (-x,-y) is bottom-right
def island(x,y,cx,cy,r):
    a=math.atan2(y-cy,x-cx)
    return math.hypot(x-cx,y-cy)<r+70*math.sin(3*a+cx)+40*math.sin(7*a+cy)
def water(x,y):
    return not(mainland(x,y) or mainland(-x,-y) or any(island(x,y,*i) for i in ISLANDS))

# Forests: dense clumps with soft edges, in the land behind each HQ and on every island. Clearings
# stay open around the HQs (military construction), the coast belt (shipyards, landings) and mines.
# Headquarters sit deep in each mainland corner at (-HQ,HQ) / (HQ,-HQ), far from the coast and
# from each other (~15300 apart; the original HQs sat at +-3300, ~9300 apart). Home mine and grove follow the HQ.
HQ=5400
HOME=HQ-3300           # offset of the home mine/grove from their original positions
HQ_CLEAR=1000          # keep this radius around each HQ free for buildings
COAST_BELT=5120        # forests stay beyond |y-x| = COAST + wobble + 700 from the sea
FOREST_SPACING=78      # centre-to-centre; a 32-radius pine leaves a 14-unit gap, so forests thin out paths on purpose
FOREST_CLUSTERS=[      # (x, y, radius, trees) for the top-left mainland; the bottom-right side is its mirror
    (-4600,4300,520,30),(-3100,5100,620,36),(-5800,3700,560,32),(-4300,6000,720,44),(-6200,5600,820,50),
    (-2300,5600,620,32),(-7200,7000,900,52),(-5000,7400,820,42),(-1500,6800,700,32),(-6800,4300,700,38),
    (-7000,7600,650,32),(-6000,7400,550,26)]
# Neutral airfields (scenario.FrontlineNeutralAirfields) on the two contested islands stay clear of trees.
ISLAND_AIRFIELDS=[(2200,2850),(-2200,-2850)]
def forest_points():
    """Deterministic, point-symmetric forest positions: list of (x,y,facing,scale)."""
    rng=random.Random(11)
    hqs=[(-HQ,HQ),(HQ,-HQ)]
    # Mines, and the island outpost sites the AI and players settle (3800,1650), stay clear of trees.
    mines=[(2550,3300),(-2550,-3300),(3400,1150),(-3400,-1150),(HQ+600,-HQ-600),(-HQ-600,HQ+600),(3800,1650),(-3800,-1650)]+[(x,y) for x,y,r in ISLANDS]+ISLAND_AIRFIELDS
    # The original 16 home trees (map script) are already standing; keep spacing from them.
    placed=[(sd*(2700+HOME+(j%8)*100),-sd*(3900+HOME+(j//8)*150)) for sd in (-1,1) for j in range(16)];out=[]
    def ok(x,y):
        if abs(x)>MAP_HALF-250 or abs(y)>MAP_HALF-250:return False
        if any(math.hypot(x-hx,y-hy)<HQ_CLEAR for hx,hy in hqs):return False
        if any(math.hypot(x-mx,y-my)<420 for mx,my in mines):return False
        return all(math.hypot(x-px,y-py)>=FOREST_SPACING for px,py in placed)
    def add(x,y):
        placed.append((x,y));out.append((x,y,rng.uniform(0,360),rng.uniform(.85,1.3)))
    for cx,cy,r,n in FOREST_CLUSTERS:
        got=0
        for _ in range(n*30):
            a=rng.uniform(0,math.tau);d=r*math.sqrt(rng.random())
            x,y=cx+d*math.cos(a),cy+d*math.sin(a)
            if y-x<COAST_BELT or not ok(x,y):continue
            add(x,y);got+=1
            if got>=n:break
    for x,y,r in ISLANDS:                                   # every island carries a grove around its mine
        got=0
        for _ in range(400):
            a=rng.uniform(0,math.tau);d=rng.uniform(.5,.85)*r
            tx,ty=x+d*math.cos(a),y+d*math.sin(a)
            if island(tx,ty,x,y,r*.92) and ok(tx,ty):add(tx,ty);got+=1
            if got>=int(r/45):break
    mirrored=[(-x,-y,(f+180)%360,sc) for x,y,f,sc in out if y-x>0]   # top-left side mirrors to bottom-right
    return out+[m for m in mirrored if all(math.hypot(m[0]-x,m[1]-y)>=FOREST_SPACING for x,y,_,_ in out)]

def forest_script(pts=None,mines=None):
    """JASS for every forest tree (chunked: each function stays small) and the outer-island mines."""
    pts=forest_points() if pts is None else pts;chunks=[]
    for i in range(0,len(pts),60):
        body=''.join(f"    call CreateDestructable('epin', {x:.0f}.0, {y:.0f}.0, {f:.0f}.0, {sc:.2f}, 0)\n" for x,y,f,sc in pts[i:i+60])
        chunks.append(f"function FrontlineForest{i//60} takes nothing returns nothing\n{body}endfunction\n")
    calls=''.join(f"    call FrontlineForest{i}()\n" for i in range(len(chunks)))
    if mines is None:mines=[(x,y) for x,y,r in ISLANDS if abs(x)>4500 or abs(y)>4500]
    mines=''.join(f"    set ore = CreateUnit(Player(15), 'eore', {x:.0f}.0, {y:.0f}.0, 0.0)\n    call SetResourceAmount(ore, 20000)\n" for x,y in mines)
    rim=''.join(chunks)+"function FrontlineRimMines takes nothing returns nothing\n    local unit ore\n"+mines+"endfunction\n"
    return rim,calls+"    call FrontlineRimMines()\n"

def game_data(root):
    base.game_data(root,catalog.UNITS,catalog.SPELLS,catalog.SPELL_UI)
    with (root/'Units/HumanAbilityFunc.txt').open('a') as f:
        f.write('\n[Gyam]\nTargetArt=Emberfield/Models/yamato_turret.mdx,Emberfield/Models/yamato_turret_aa.mdx,Emberfield/Models/yamato_turret_aa.mdx\n')
    # Trees block movement with a 2x2-cell footprint and never run out: logging only scratches
    # an effectively unlimited trunk, so the forest is a renewable logistics source.
    base.write(root,'Units/DestructableData.slk',base.slk([dict(DestructableID='epin',Name='Logistics Grove',file='Emberfield\\Models\\pine.mdx',
        HP=TREE_HP,targType='tree',armor='Wood',numVar=0,selSize=90,minScale=1,maxScale=1,radius=32,fogVis=1,pathTex=TREE_PATHTEX)],'DestructableID'))
    header=struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,2,2,32,8)
    base.write(root,TREE_PATHTEX.replace('\\','/'),header+bytes([255,0,255,255])*4)  # red: blocks walking
    # Engineer build folders (catalog.BUILD_FOLDERS): profile-only entries, no UnitData rows.
    folders=''
    for code,name,key,art,(x,y),text,children in catalog.BUILD_FOLDERS:
        folders+=(f'[{code}]\nName={name}\nTip={name} ({key})\nUbertip={text}\nArt=Emberfield\\Icons\\{art}.blp\n'
                  f'Buttonpos={x},{y}\nHotkey={key}\nBuilds={",".join(c for c,_,_ in children)}\n\n')
    code,name,key,art,(x,y),text=catalog.BUILD_BACK
    folders+=f'[{code}]\nName={name}\nTip={name} ({key})\nUbertip={text}\nArt=Emberfield\\Icons\\{art}.blp\nButtonpos={x},{y}\nHotkey={key}\n\n'
    for name in ['HumanUnitFunc.txt','HumanUnitStrings.txt']:
        p=root/'Units'/name;p.write_text(p.read_text().replace(' - Emberfield',' - Frontline')+folders)
    # Keep the existing generic rally visualization available without retail art.
    base.write(root,'TerrainArt/Terrain.slk',base.slk([
        dict(terrainID='Egrs',dir='Emberfield\\Terrain',file='grass'),
        dict(terrainID='Esnd',dir='Emberfield\\Terrain',file='sand')],'terrainID'))

def coast_distance(sea):
    """Signed chamfer distance (world units) from each 32-unit cell to the coastline:
    positive on land, negative at sea."""
    n=len(sea);big=1e9;out=[]
    for target in (True,False):                   # distance to the nearest sea / land cell
        d=[[0 if sea[y][x]==target else big for x in range(n)] for y in range(n)]
        for y in range(n):
            row,up=d[y],d[y-1] if y else None
            for x in range(n):
                v=row[x]
                if v:
                    if x:v=min(v,row[x-1]+32)
                    if up:v=min(v,up[x]+32,up[x-1]+45 if x else big,up[x+1]+45 if x+1<n else big)
                    row[x]=v
        for y in range(n-1,-1,-1):
            row,down=d[y],d[y+1] if y+1<n else None
            for x in range(n-1,-1,-1):
                v=row[x]
                if v:
                    if x+1<n:v=min(v,row[x+1]+32)
                    if down:v=min(v,down[x]+32,down[x+1]+45 if x+1<n else big,down[x-1]+45 if x else big)
                    row[x]=v
        out.append(d)
    to_sea,to_land=out
    return [[(to_sea[y][x]-16 if not sea[y][x] else -(to_land[y][x]-16)) for x in range(n)] for y in range(n)]

def terrain_files(directory,sea,terrain_half):
    """W3E heights/flags and WPM pathing from a 32-unit sea grid (rows run south to north)."""
    cells=len(sea);tiles=cells//4+1
    coast=coast_distance(sea)
    terrain=bytearray(b'W3E!'+base.P('IcI',11,b'L',0)+base.P('I',2)+b'EgrsEsnd'+base.P('I',0)+base.P('2I2f',tiles,tiles,-terrain_half,-terrain_half))
    for y in range(tiles):
        for x in range(tiles):
            # Signed distance to the true coast (land +, sea -), averaged over the four pathing
            # cells meeting at this vertex. The ground slopes through the waterline, so the
            # water plane cuts a curved shore instead of the old 128-unit tile staircase.
            near=[coast[cy][cx] for cy in (4*y-1,4*y) for cx in (4*x-1,4*x) if 0<=cx<cells and 0<=cy<cells]
            d=sum(near)/len(near)
            z=max(-128,min(10,d*.42)) if d<0 else min(10,d*.12)
            # Water is flagged a little inland too: the plane is hidden under raised ground.
            flags=(64 if d<200 else 0)|(1 if d<210 else 0)
            # Variation (x%4, y%4) addresses one 4x4-tile seamless texture (image rows run top = +y).
            terrain+=base.P('2H3B',8192+int(round(z*4)),8192,flags,x%4+4*(3-y%4),2)
    base.write(directory,'war3map.w3e',bytes(terrain))
    path=bytearray()
    for row in sea:
        for wet in row:path.append(2|8 if wet else 64)
    base.write(directory,'war3map.wpm',b'MP3W'+base.P('3I',0,cells,cells)+path)

def map_info(directory,half,starts):
    """war3map.w3i: names, playable bounds and the two start locations (Player(0) first)."""
    info=(directory/'war3map.w3i').read_bytes().replace(b'Emberfield - First Light',(TITLE+' - USN').encode()).replace(b'Destroy the opposing Beacon. Gather ore and train guards.',b'Destroy enemy Headquarters. Rule the open ocean and seize the islands.').replace(b'Amber Expedition',b'United States Navy').replace(b'Azure Expedition',b'Imperial Japanese Navy').replace(b'Expedition 1',b'U.S. Navy').replace(b'Expedition 2',b'Japanese Navy')
    old=base.P('8f4i2IIcI',-2560,-2560,-2560,2560,2560,2560,2560,-2560,4,4,4,4,40,40,0x40,b'L',0xffffffff)
    # Fixed custom forces: LAN lobby rows are the two navies; players switch sides, not races.
    new=base.P('8f4i2IIcI',-half,-half,-half,half,half,half,half,-half,4,4,4,4,2*half//128+4,2*half//128+4,0x60,b'L',0xffffffff)
    info=info.replace(old,new)
    for i in range(2):info=info.replace(base.P('2f2I',-1500+3000*i,0,0,0),base.P('2f2I',*starts[i],0,0))
    base.write(directory,'war3map.w3i',info)

RAW_SCRIPTS={}   # theatre -> map script before set_theater, so variants can re-theatre after their swaps
def theater_script(script,theater,navy0):
    import tools.frontline.scenario as scenario
    return scenario.set_theater(script,theater,navy0) if hasattr(scenario,'set_theater') else script

def map_script(directory,pts,mines,theater):
    rim,calls=forest_script(pts,mines)
    script=MAP_SCRIPT.replace('function main takes nothing returns nothing',rim+'function main takes nothing returns nothing',1)
    script=script.replace('    call SetCameraPosition(-4800.0, 4700.0)\n',calls+'    call SetCameraPosition(-4800.0, 4700.0)\n',1)
    # scenario.set_theater(script, theatre, Player(0)'s navy) places HQs and bot sites per theatre.
    RAW_SCRIPTS[theater]=script
    base.write(directory,'war3map.j',theater_script(script,theater,'USN'))

# Island Command's scenario-owned sites for the map editor (tools/frontline/scenario.py main).
ISLAND_SITES=[('ore',-6000,6000,450),('ore',6000,-6000,450),('ore',2550,3300,450),('ore',-2550,-3300,450),
    ('ore',3400,1150,450),('ore',-3400,-1150,450),('land',3800,1650,450),('land',-3800,-1650,450),
    ('land',-5150,6075,400),('land',5150,-6075,400)]
def island_sites(swapped):
    hqs=[(-HQ,HQ),(HQ,-HQ)][::-1 if swapped else 1]
    rows=[('hq0',*hqs[0],700),('hq1',*hqs[1],700)]+ISLAND_SITES
    return ''.join(f'{k} {x} {y} {r}\n' for k,x,y,r in rows)

def pacific_sites(order):
    """order[0] is Player(0)'s navy."""
    owned=[(x,y) for name,x,y in pacific.ORE if name in pacific.OUTPOST_ISLAND.values()]
    rows=[(f'hq{i}',*pacific.HQ[n],700) for i,n in enumerate(order)]
    rows+=[('ore',x,y,450) for x,y in list(pacific.HOME_ORE.values())+owned]
    rows+=[('land',x,y,450) for x,y in pacific.OUTPOST.values()]
    rows+=[('land',x,y,250) for x,y in pacific.SHIPYARD.values()]   # the yard's shore stays put
    rows+=[('playable',pacific.HALF,0,0)]
    return ''.join(f'{k} {x} {y} {r}\n' for k,x,y,r in rows)

def minimap(directory,wet,terrain_half):
    image=Image.new('RGBA',(256,256));px=image.load()
    for y in range(256):
        for x in range(256):
            wx=x/256*2*terrain_half-terrain_half;wy=terrain_half-y/256*2*terrain_half
            if wet(wx,wy):
                px[x,y]=(45,81,108,255)
            elif any(wet(wx+dx,wy+dy) for dx,dy in [(200,0),(-200,0),(0,200),(0,-200)]):
                px[x,y]=(156,148,118,255)  # beach sand
            else:
                px[x,y]=(103,116,73,255)
    base.write(directory,'war3mapMap.blp',base.art.blp_bytes(image))

# ---- Pacific theatre ----
# 416 terrain tiles: the renderer's terrain chunks need sides that are multiples of 32 tiles.
PACIFIC_TERRAIN_HALF=pacific.HALF+2048
PACIFIC_CELLS=(2*PACIFIC_TERRAIN_HALF//128)*4
PACIFIC_TREES=3200      # the map editor allows 4000; JASS stays in 60-tree functions
def pacific_forest_points():
    """Deterministic clumps on the larger islands and the Asian coast, clear of HQs, mines and shores."""
    rng=random.Random(11)
    hqs=list(pacific.HQ.values())
    mines=list(pacific.HOME_ORE.values())+list(pacific.OUTPOST.values())+list(pacific.SHIPYARD.values())+[(x,y) for _,x,y in pacific.ORE]+pacific.airfield_sites()
    out=[];buckets={}
    def ok(x,y):
        if abs(x)>pacific.HALF-250 or abs(y)>pacific.HALF-250:return False
        if any(math.hypot(x-hx,y-hy)<HQ_CLEAR for hx,hy in hqs):return False
        if any(math.hypot(x-mx,y-my)<420 for mx,my in mines):return False
        key=(int(x//FOREST_SPACING),int(y//FOREST_SPACING))
        near=[p for dx in (-1,0,1) for dy in (-1,0,1) for p in buckets.get((key[0]+dx,key[1]+dy),())]
        return all(math.hypot(x-px,y-py)>=FOREST_SPACING for px,py in near) and pacific.coast_clear(x,y,350)
    tries=0
    while len(out)<PACIFIC_TREES and tries<4000:
        tries+=1
        cx,cy=rng.uniform(-pacific.HALF,pacific.HALF),rng.uniform(-pacific.HALF,pacific.HALF)
        if not pacific.coast_clear(cx,cy,600):continue
        r=rng.uniform(450,900);n=int(r/18)
        for _ in range(n*20):
            a=rng.uniform(0,math.tau);d=r*math.sqrt(rng.random())
            x,y=cx+d*math.cos(a),cy+d*math.sin(a)
            if ok(x,y):
                buckets.setdefault((int(x//FOREST_SPACING),int(y//FOREST_SPACING)),[]).append((x,y))
                out.append((x,y,rng.uniform(0,360),rng.uniform(.85,1.3)));n-=1
                if n<=0 or len(out)>=PACIFIC_TREES:break
    return out

def pacific_map_data(directory):
    base.map_data(directory)
    map_info(directory,pacific.HALF,[pacific.HQ['USN'],pacific.HQ['IJN']])
    terrain_files(directory,[[not v for v in row] for row in pacific.land_mask(PACIFIC_CELLS,-PACIFIC_TERRAIN_HALF,32)],PACIFIC_TERRAIN_HALF)
    # Island stockpiles; the outpost islands' fields belong to scenario.py (the bots track them).
    mines=[(x,y) for name,x,y in pacific.ORE if name not in pacific.OUTPOST_ISLAND.values()]
    map_script(directory,pacific_forest_points(),mines,'pacific')
    minimap(directory,lambda x,y:not pacific.land(x,y),PACIFIC_TERRAIN_HALF)
    base.write(directory,'war3mapSites.txt',pacific_sites(('USN','IJN')))
    base.write(directory,'war3mapLabels.txt',place_names.text())   # client place-name labels

def map_data(directory):
    base.map_data(directory)
    map_info(directory,MAP_HALF,[(-HQ,HQ),(HQ,-HQ)])
    terrain_files(directory,[[water(x*32-TERRAIN_HALF+16,y*32-TERRAIN_HALF+16) for x in range(CELLS)] for y in range(CELLS)],TERRAIN_HALF)
    map_script(directory,None,None,'island')
    base.write(directory,'war3mapSites.txt',island_sites(False))

def icon(name):
    # Material atlas colours (cells 0–7); cell 8 is team colour.
    MAT_COLORS=[(128,124,102),(106,119,120),(146,136,105),(94,82,58),(189,165,123),(40,47,46),(120,141,144),(88,105,63)]
    TEAM_COLOR=(87,152,186)
    # Category backgrounds: a subtle tint behind the unit so categories read at a glance.
    INFANTRY=('infantry',  (38,44,36))   # dark olive
    ARMOR   =('armor',     (36,40,44))   # dark steel
    ARTY    =('artillery', (44,38,32))   # dark brown
    AIR     =('air',       (32,40,48))   # dark sky blue
    NAVY    =('navy',      (28,38,46))   # dark navy
    BUILD   =('building',  (34,34,34))   # neutral dark
    CAT_MAP={
        'rifle':INFANTRY,'machinegun':INFANTRY,'mortar':INFANTRY,'commando':INFANTRY,'engineer':INFANTRY,
        'tank':ARMOR,'heavytank':ARMOR,'scoutcar':ARMOR,'rocketart':ARTY,'artillery':ARTY,'antiair':ARTY,
        'fighter':AIR,'bomber':AIR,'recon':AIR,'zero':AIR,'wildcat':AIR,'val':AIR,'dauntless':AIR,'kate':AIR,'avenger':AIR,
        'battleship':NAVY,'destroyer':NAVY,'cruiser':NAVY,'carrier':NAVY,'transport':NAVY,'landingcraft':NAVY,
        'iowa':NAVY,'yamato':NAVY,'nagato':NAVY,'yorktown':NAVY,'essex':NAVY,'fletcher':NAVY,'cleveland':NAVY,
        'akagi':NAVY,'kaga':NAVY,'soryu':NAVY,'hiryu':NAVY,'shokaku':NAVY,'mogami':NAVY,'fubuki':NAVY,
        'lcvp':NAVY,'lcm':NAVY,'daihatsu':NAVY,
        **{n:NAVY for n in ('northcarolina','southdakota','kongo','baltimore','atlanta','independence','sumner',
                            'takao','myoko','kagero','akizuki')},
        'headquarters':BUILD,'barracks':BUILD,'factory':BUILD,'airfield':BUILD,'shipyard':BUILD,
        'depot':BUILD,'bunker':BUILD,'coastalgun':BUILD,'watchtower':BUILD,'stockpile':BUILD,
        'road':BUILD,'sandbag':BUILD,'barbedwire':BUILD,**{n:BUILD for n in models.drydock.VARIANTS},
    }
    cat_name,bg=CAT_MAP.get(name,('other',(30,36,34)))
    # Category accent stripe color along the bottom.
    STRIPE={'infantry':(148,156,100),'armor':(130,140,155),'artillery':(170,140,100),
            'air':(100,150,200),'navy':(80,140,180),'building':(140,140,130),'other':(140,140,130)}
    im=Image.new('RGBA',(256,256),(*bg,255));d=ImageDraw.Draw(im)
    # Gradient overlay: lighter at the top.
    for row in range(256):
        t=row/255;c=tuple(int(bg[i]*(1.15-0.3*t)) for i in range(3))
        d.line((0,row,255,row),fill=(*c,255))
    d.rounded_rectangle((4,4,251,251),radius=13,outline=(168,157,115),width=4)
    # Category stripe at bottom.
    stripe=STRIPE.get(cat_name,(140,140,130))
    d.rectangle((14,236,241,244),fill=(*stripe,180))
    boxes=models.GEOMETRY.get(name)
    smooth=name in models.historical.GEOMETRY or name in models.ships.GENERIC
    if name in models.imported.RECIPES or smooth or name in models.drydock.MODELS or name in models.structures.MODELS:
        # Imported meshes and smooth ships: front three-quarter render (the unit's +X faces the viewer).
        source=(models.drydock.triangles(name) if name in models.drydock.MODELS else
                models.structures.icon_triangles(name) if name in models.structures.MODELS else
                (models.ships.generic(name) if name in models.ships.GENERIC else models.ships.triangles(name)) if smooth else models.imported.triangles(name))
        if name in models.BATTERIES:
            source=models.ships.complete(name)
        tris=models.gltf_import.transform(source,yaw=180 if not smooth else 205)
        art=models.gltf_import.preview(tris,224)
        im.alpha_composite(art,(16,8))
    elif boxes:
        if name in models.BATTERIES:
            mount=models.GEOMETRY[models.ships.battery_model(name)]
            boxes=boxes+[(x+sx,y+sy,z+sz,w,dep,h,cell) for sx,sy,sz in models.BATTERIES[name] for x,y,z,w,dep,h,cell in mount]
        # Project each box's top face in isometric and collect depth for sorting.
        faces=[]  # (depth, top_pts_2d, right_pts_2d, front_pts_2d, cell)
        for bx,by,bz,w,dep,h,cell in boxes:
            # 3D corners: top face
            tl=(bx-w,by-dep,bz+h);tr=(bx+w,by-dep,bz+h);br=(bx+w,by+dep,bz+h);bl=(bx-w,by+dep,bz+h)
            # bottom face
            btl=(bx-w,by-dep,bz);btr=(bx+w,by-dep,bz);bbr=(bx+w,by+dep,bz);bbl=(bx-w,by+dep,bz)
            def proj(p): return (p[0]*.75+p[1]*.35, -p[2]*.85+p[1]*.4-p[0]*.2)
            t2=[proj(p) for p in (tl,tr,br,bl)]  # top face
            r2=[proj(p) for p in (tr,btr,bbr,br)]  # right face
            f2=[proj(p) for p in (bl,br,bbr,bbl)]  # front face
            depth=by*0.6+bx*0.3-bz*0.1  # sort back-to-front
            faces.append((depth,t2,r2,f2,cell))
        faces.sort(key=lambda f:f[0],reverse=True)
        # Bounding box for scaling.
        all_pts=[p for _,t,r,f,_ in faces for p in t+r+f]
        xmin=min(p[0] for p in all_pts);xmax=max(p[0] for p in all_pts)
        ymin=min(p[1] for p in all_pts);ymax=max(p[1] for p in all_pts)
        scale=184/max(xmax-xmin,ymax-ymin,1);cx=(xmin+xmax)/2;cy=(ymin+ymax)/2
        def screen(pts): return [(128+(x-cx)*scale,122+(y-cy)*scale) for x,y in pts]
        for _,top,right,front,cell in faces:
            base_c=MAT_COLORS[cell] if cell<8 else TEAM_COLOR
            # Lit top face (brightest), right side (mid), front side (darkest).
            top_c=tuple(min(255,int(c*1.15)) for c in base_c)
            right_c=tuple(int(c*0.80) for c in base_c)
            front_c=tuple(int(c*0.60) for c in base_c)
            edge=tuple(int(c*0.40) for c in base_c)
            d.polygon(screen(right),fill=right_c,outline=edge)
            d.polygon(screen(front),fill=front_c,outline=edge)
            d.polygon(screen(top),fill=top_c,outline=edge)
    else:
        ink=(224,217,180);blue=(87,152,186)
        if name=='attack':
            d.ellipse((70,70,186,186),outline=ink,width=10)
            for line in [(128,42,128,91),(128,165,128,214),(42,128,91,128),(165,128,214,128)]:d.line(line,fill=ink,width=10)
            d.ellipse((117,117,139,139),fill=blue)
        elif name in ('load','unload'):
            d.rectangle((55,71,201,192),outline=ink,width=10)
            d.rectangle((92,61,163,98),fill=(25,34,32))
            arrow=[(116,44),(140,44),(140,117),(163,117),(128,151),(93,117),(116,117)]
            d.polygon(arrow if name=='load' else [(x,195-y) for x,y in arrow],fill=blue)
        elif name=='return':
            d.line([(200,181),(200,95),(78,95)],fill=ink,width=18,joint='curve')
            d.polygon([(55,95),(109,56),(109,134)],fill=ink)
            d.line((62,199,211,199),fill=blue,width=10)
        elif name=='airstrike':
            d.polygon([(128,38),(143,94),(205,130),(205,148),(141,132),(140,183),(163,199),(163,212),(128,202),(93,212),(93,199),(116,183),(115,132),(51,148),(51,130),(113,94)],fill=ink)
            d.line((63,184,87,161),fill=blue,width=8);d.line((191,184,167,161),fill=blue,width=8)
        elif name=='airgroup':
            # Three aircraft in echelon over a deck line: the carrier's air group.
            def plane(cx,cy,k):
                d.polygon([(cx,cy-30*k),(cx+5*k,cy-8*k),(cx+34*k,cy+4*k),(cx+34*k,cy+11*k),(cx+5*k,cy+6*k),(cx+4*k,cy+24*k),(cx+14*k,cy+30*k),(cx+14*k,cy+34*k),(cx,cy+30*k),(cx-14*k,cy+34*k),(cx-14*k,cy+30*k),(cx-4*k,cy+24*k),(cx-5*k,cy+6*k),(cx-34*k,cy+11*k),(cx-34*k,cy+4*k),(cx-5*k,cy-8*k)],fill=ink)
            plane(128,92,1.0);plane(72,128,.7);plane(184,128,.7)
            d.rectangle((40,190,216,204),fill=blue)
        elif name=='torpedo':
            d.ellipse((50,100,206,156),fill=ink);d.polygon([(206,114),(228,128),(206,142)],fill=ink)
            d.rectangle((78,96,98,160),fill=(25,34,32));d.rectangle((110,96,126,160),fill=blue)
            d.polygon([(50,112),(30,92),(30,164),(50,144)],fill=blue)
        elif name in ('supply','gather'):
            d.rectangle((61,83,195,199),fill=ink)
            d.line((68,90,188,192),fill=(94,82,58),width=9)
            d.line((188,90,68,192),fill=(94,82,58),width=9)
            d.rectangle((113,72,143,98),fill=blue)
        elif name in ('veteran','elite'):
            # Rank chevrons; Elite adds a second chevron and a star.
            def chevron(y):d.line([(60,y),(128,y+44),(196,y)],fill=ink,width=22,joint='curve')
            chevron(150 if name=='veteran' else 120)
            if name=='elite':
                chevron(170)
                d.polygon([(128,40),(140,74),(176,74),(147,95),(158,129),(128,108),(98,129),(109,95),(80,74),(116,74)],fill=blue)
        elif name=='rally':
            # A field flag on its staff.
            d.line((84,40,84,214),fill=ink,width=14)
            d.polygon([(91,48),(196,78),(91,124)],fill=blue)
            d.ellipse((60,196,108,222),fill=ink)
        elif name=='sell':
            # Structure handed back: a building outline over a returning arrow.
            d.rectangle((70,58,186,140),outline=ink,width=12)
            d.polygon([(100,58),(128,30),(156,58)],fill=ink)
            d.line([(70,190),(186,190)],fill=blue,width=16)
            d.polygon([(52,190),(88,164),(88,216)],fill=blue)
        else:return base.art.icon(name)
    return im

def menu_nodes(path,root_name):
    """Keep custom pack layouts consistent with the engine's named bindings."""
    import re
    header=(Path(__file__).resolve().parents[2]/path).read_text()
    nodes={'bind_root':dict(name=root_name,children=[])}
    for key,parent,name in re.findall(r'BZ_FDF_BIND_CHILD\(out, (\w+), (?:out->)?(\w+), "([^"]+)"\)',header):
        nodes[key]=dict(name=name,children=[])
        nodes[parent]['children'].append(key)
    return nodes

def front_menu(root):
    from tools.emberfield.ui import frame,text,button,backdrop
    nodes=menu_nodes('games/warcraft-3/menu/generated/main_menu.h','MainMenuFrame')
    supported={'bind_root','ControlLayer','SinglePlayerBackdrop','BattleNetBackdrop','LocalAreaNetworkBackdrop','CreditsBackdrop','OptionsBackdrop','ExitBackdrop'}
    def emit(key):
        name=nodes[key]['name']
        if key=='SinglePlayerButton':return button(name,'Command USN',.27,.21)
        if key=='BattleNetButton':return button(name,'Command IJN',.27,.27)
        if key=='LocalAreaNetworkButton':return button(name,'LAN Multiplayer',.27,.33)
        if key=='CreditsButton':return button(name,'Map Editor',.27,.39)   # bound by OfflineEditorLabel
        if key=='OptionsButton':return button(name,'Command Both',.27,.45)   # bound by OfflineSandboxMap
        if key=='ExitButton':return button(name,'Exit',.27,.51)   # bottom edge .551: clear of the 0.6 screen edge and iPad home bar
        body=''.join(emit(c) for c in nodes[key]['children'])
        if key=='bind_root':
            body=backdrop('OfflineMenuBackground')+text('OfflineTitle','FRONTLINE',.5,.065,.19,.13,.04)+text('OfflineSubtitle','ISLAND COMMAND',.4,.04,.25,.20,.02)+body
        return frame('FRAME',name,body,.8 if key in supported else 0,.6 if key in supported else 0,0 if key in supported else -2,0)
    base.write(root,'UI/FrameDef/Glue/MainMenu.fdf',emit('bind_root'))
    p=root/'UI/war3skins.txt';p.write_text(p.read_text()+'OfflineSkirmishMap='+PACIFIC_MAP_PATH+'\nOfflineAlternateSkirmishMap='+PACIFIC_IJN_MAP_PATH+'\nOfflineSkirmishLabel=Command USN\nOfflineAlternateSkirmishLabel=Command IJN\nOfflineEditorLabel=Map Editor\nOfflineSandboxMap='+PACIFIC_SANDBOX_MAP_PATH+'\nOfflineSandboxLabel=Command Both\n')

# LAN browser, create and lobby screens reuse the engine's LAN glue code. Their
# layouts are the repository's own test-authored FDFs, re-skinned with Frontline art.
LAN_FDF=Path(__file__).resolve().parents[2]/'games/warcraft-3/tests/resources-src'
LAN_STRINGS={'COLON_ELAPSED_TIME':'Elapsed:','COLON_GAMES':'Games found on this network:','COLON_GAME_CREATOR':'Host:','COLON_GAME_NAME':'Game:',
    'COLON_GAME_SPEED':'Speed:','COLON_MAP_DESC':'Briefing:','COLON_MAP_SIZE':'Map Size:','COLON_NUMBER_OF_PLAYERS':'Commanders:',
    'COLON_SELECT_MAP':'Select map (host commands this navy):','COLON_SUGGESTED_PLAYERS':'Suggested:','COLON_TILESET':'Theater:',
    'CREATE_GAME_SETTINGS':'LAN Game Settings','DASH_DASH':'--','KEY_ADVANCED_OPTIONS':'Options','KEY_CANCEL':'Back',
    'KEY_CREATE_GAME':'Host Game','KEY_JOIN_GAME':'Join Game','KEY_LOAD_GAME':'Join by IP','KEY_MAP_INFO':'Theater',
    'KEY_START_GAME':'Start Game','LAN_GAME_SETUP_INFO':'Host a match or join one found on this network.',
    'LAN_GAME_SETUP_TITLE':'LAN MULTIPLAYER','LOCAL_NETWORK_GAMES':'LAN GAMES','PLAYER_NAME':'Commander Name:',
    'UNKNOWNMAP_SUGGESTEDPLAYERS':'2','UNKNOWNMAP_MAPSIZE':'Large','UNKNOWNMAP_TILESET':'Pacific','UNKNOWNMAP_DESCRIPTION':' ',
    'GAMESPEED_SLOWEST':'Slow','GAMESPEED_NORMAL':'Normal','GAMESPEED_FASTEST':'Fast'}
def lan_texture(path):
    name=path.lower()
    if 'arrow' in name or 'pulldown' in name:return 'arrow'
    if 'knob' in name:return 'button'
    if name.endswith(('button1-border.blp','largebordersingle.blp','smallborder.blp')):return 'button'
    if 'border' in name:return 'frame-edge'
    if 'down' in name or 'highlight' in name:return 'button-pressed'
    if 'inputbox-back' in name or 'scrollbar-backdropbackground' in name or 'minimapcover' in name or 'slider-bar' in name:return 'panel'
    if 'icon-file' in name or 'chaticons' in name:return 'ore'
    if 'solid_white' in name:return 'bar'
    return 'button'
def lan_menus(root):
    import re
    def skin(text):
        return re.sub(r'"((?:TestUI|UI|ui)\\[^"]*\.blp)"',lambda m:'"Emberfield\\Textures\\'+lan_texture(m.group(1))+'.blp"',text)
    fdfs=[LAN_FDF/'TestUI/FrameDef/Glue/StandardTemplates.fdf']+sorted((LAN_FDF/'UI/FrameDef/Glue').glob('*.fdf'))
    for src in fdfs:
        text=skin(src.read_text())
        if src.name=='LocalMultiplayerJoin.fdf':
            # Shorter list leaves room for a direct host address under it.
            text=text.replace('            Height 0.275,\n            SetPoint TOPLEFT, "PlayerNameEditBox"','            Height 0.205,\n            SetPoint TOPLEFT, "PlayerNameEditBox"',1)
            text=text.replace('SetPoint RIGHT,"CreateBackdrop",LEFT, 0.0975, 0.0,','SetPoint RIGHT,"CreateBackdrop",LEFT, 0.0, 0.0,',1)
            cut=text.rstrip().rfind('}')
            text=text[:cut]+'''    Frame "TEXT" "DirectAddressLabel" INHERITS "StandardLabelTextTemplate" {
        SetPoint TOPLEFT, "GameListContainer", BOTTOMLEFT, 0.0, -0.008,
        Text "Host IP address (Join by IP):",
    }
    Frame "EDITBOX" "DirectAddressEditBox" INHERITS WITHCHILDREN "StandardEditBoxTemplate" {
        Width 0.37,
        SetPoint TOPLEFT, "DirectAddressLabel", BOTTOMLEFT, 0.0, -0.001,
    }
}
'''
        base.write(root,'UI/FrameDef/Glue/'+src.name,text)
    # WC3 edge strip: L,R,T,B,UL,UR,BL,BR cells; T/B are transposed by the renderer.
    edge=Image.new('RGBA',(256,32),(0,0,0,0));d=ImageDraw.Draw(edge);gold=(198,178,120,255)
    sides={0:'l',1:'r',2:'l',3:'r',4:'lt',5:'rt',6:'lb',7:'rb'}
    for cell,marks in sides.items():
        x=cell*32
        if 'l' in marks:d.rectangle((x,0,x+2,31),fill=gold)
        if 'r' in marks:d.rectangle((x+29,0,x+31,31),fill=gold)
        if 't' in marks:d.rectangle((x,0,x+31,2),fill=gold)
        if 'b' in marks:d.rectangle((x,29,x+31,31),fill=gold)
    base.write(root,'Emberfield/Textures/frame-edge.blp',base.art.blp_bytes(edge,True))
    arrow=Image.new('RGBA',(64,64),(0,0,0,0));ImageDraw.Draw(arrow).polygon([(16,22),(48,22),(32,44)],fill=(224,217,180,255))
    base.write(root,'Emberfield/Textures/arrow.blp',base.art.blp_bytes(arrow,True))
    p=root/'UI/FrameDef/GlobalStrings.fdf';text=p.read_text()
    extra=''.join(f'{k} "{v}", ' for k,v in LAN_STRINGS.items() if k+' ' not in text)
    p.write_text(text.replace('}',extra+'}',1))

def sound_menu(root):
    """Author the sound page against the existing mandatory FDF bindings."""
    import re
    from tools.emberfield.ui import frame,text,button
    nodes=menu_nodes('games/warcraft-3/game/generated/esc_menu_options_panel.h','EscMenuOptionsPanel')
    visible={'bind_root','OptionsPanel','OptionsTitleText','SoundButton','SoundButtonText','OptionsPreviousButton',
             'OptionsPreviousButtonText','SoundPanel','SoundTitleText','SoundVolumeLabel',
             'SoundVolumeSlider','MusicVolumeLabel','MusicVolumeSlider','BottomButtonPanel',
             'OptionsOKButton','OKButtonText','OptionsCancelButton','CancelButtonText'}
    labels={'OptionsTitleText':'OPTIONS','SoundButtonText':'Sound / Volume','OptionsPreviousButtonText':'Back',
            'SoundTitleText':'SOUND VOLUME','SoundVolumeLabel':'Effects','MusicVolumeLabel':'Music',
            'OKButtonText':'Apply','CancelButtonText':'Cancel'}
    boxes={'OptionsTitleText':(.035,.018,.27,.035),'SoundButton':(.035,.08,.26,.041),
           'OptionsPreviousButton':(.035,.20,.26,.041),'SoundTitleText':(.035,.018,.27,.035),
           'SoundCheckBox':(.035,.065,.022,.025),'SoundVolumeLabel':(.07,.065,.20,.024),
           'SoundVolumeSlider':(.035,.10,.26,.025),'MusicCheckBox':(.035,.15,.022,.025),
           'MusicVolumeLabel':(.07,.15,.20,.024),'MusicVolumeSlider':(.035,.185,.26,.025),
           'OptionsOKButton':(.035,.24,.12,.041),'OptionsCancelButton':(.175,.24,.12,.041),
           'OKButtonText':(.01,0,.10,.041),'CancelButtonText':(.01,0,.10,.041)}
    def emit(key):
        name=nodes[key]['name'];children=''.join(emit(c) for c in nodes[key]['children'])
        if key not in visible:return frame('FRAME',name,children,0,0,-2,0)
        if key.endswith('Slider'):
            x,y,w,h=boxes[key]
            return frame('SLIDER',name,'SliderMinValue 0, SliderMaxValue 1, SliderInitialValue 1, SliderStepSize 0.05, SliderLayoutHorizontal,'+children,w,h,x,y)
        if key.endswith('CheckBox'):
            x,y,w,h=boxes[key];return frame('CHECKBOX',name,children,w,h,x,y)
        if key in labels:
            x,y,w,h=boxes.get(key,(.01,0,.24,.041))
            return text(name,labels[key],w,h,x,y)+children
        if key.endswith('Button'):
            x,y,w,h=boxes[key]
            from tools.emberfield.ui import backdrop
            return frame('GLUETEXTBUTTON',name,'ControlBackdrop "'+name+'Backdrop", '+backdrop(name+'Backdrop','button')+children,w,h,x,y)
        return frame('FRAME',name,children,.33,.30,0,0)
    base.write(root,'UI/FrameDef/UI/EscMenuOptionsPanel.fdf',emit('bind_root'))
    p=root/'UI/FrameDef/UI/EscMenuMainPanel.fdf';ui=p.read_text()
    # Replace the original zero-size Options binding with an accessible row.
    ui=re.sub(r'Frame "GLUETEXTBUTTON" "OptionsButton" \{.*?Frame "TEXT" "OptionsButtonText" \{[^{}]*\}\s*\}',
              lambda m:button('OptionsButton','Sound / Volume',.035,.177),ui,flags=re.S)
    p.write_text(ui)
    p=root/'UI/war3skins.txt';p.write_text(p.read_text()+
        'EscMenuSliderBackground=Emberfield\\Textures\\button-pressed.blp\n'
        'EscMenuSliderBorder=Emberfield\\Textures\\button-pressed.blp\n'
        'EscMenuSliderThumbButton=Emberfield\\Textures\\button.blp\n')

# 4x4 naval atlas, 64 px cells: USN Measure 21 navy blue hull, ocean grey upperworks,
# deck-blue planking; IJN dark grey hull, light grey upperworks, wooden decks.
NAVAL_CELLS=[(52,64,86,'panel'),(132,140,150,'panel'),(70,80,98,'plank'),(72,80,96,'plank'),
             (108,113,118,'panel'),(150,154,156,'panel'),(166,132,90,'plank'),(122,92,72,'plank'),
             (255,255,255,'flat'),(26,26,28,'flat'),(122,48,40,'flat'),(96,100,104,'panel'),
             (226,226,214,'flat'),(178,42,36,'flat'),(32,38,46,'flat'),(20,20,22,'flat')]
def naval_atlas():
    im=Image.new('RGBA',(256,256));d=ImageDraw.Draw(im);rng=random.Random(7)
    for i,(r,g,b,kind) in enumerate(NAVAL_CELLS):
        x,y=i%4*64,i//4*64
        d.rectangle((x,y,x+63,y+63),fill=(r,g,b,255))
        if kind=='plank':
            for line in range(0,64,5):
                shade=rng.uniform(.88,1.06)
                d.rectangle((x,y+line,x+63,y+line+3),fill=(int(r*shade),int(g*shade),int(b*shade),255))
                d.line((x,y+line+4,x+63,y+line+4),fill=(int(r*.7),int(g*.7),int(b*.7),255))
        elif kind=='panel':
            for line in range(8,64,16):d.line((x,y+line,x+63,y+line),fill=(int(r*.86),int(g*.86),int(b*.86),255))
            for line in range(10,64,21):d.line((x+line,y,x+line,y+63),fill=(int(r*.9),int(g*.9),int(b*.9),255))
            d.line((x,y+1,x+63,y+1),fill=(min(255,int(r*1.15)),min(255,int(g*1.15)),min(255,int(b*1.15)),255))
    return im

AMBIENTCG=Path(__file__).resolve().parents[2]/'third_party'/'source'/'ambientcg'
def _wave_mask(size,seed,octaves=((2,1),(3,.6),(5,.35),(9,.18))):
    """Seamless low-frequency noise in 0..1 (integer wave numbers wrap exactly)."""
    rng=random.Random(seed);waves=[]
    for k,a in octaves:
        for _ in range(2):waves.append((rng.choice((-1,1))*k,rng.randint(-k,k),a,rng.uniform(0,math.tau)))
    total=sum(a for _,_,a,_ in waves)
    mask=Image.new('L',(size,size));px=mask.load()
    for y in range(size):
        for x in range(size):
            v=sum(a*math.sin(math.tau*(kx*x+ky*y)/size+ph) for kx,ky,a,ph in waves)/total
            px[x,y]=max(0,min(255,int(128+255*v)))
    return mask

def terrain_atlases():
    """Extended ground atlases: right half = one seamless 1024 px texture cut into a 4x4 grid
    (map vertices pick cell (x%4, y%4), so it spans 4x4 tiles without repeating); left half =
    16 corner-bitmask transition cells whose alpha blends smoothly between flagged corners."""
    def load(name):return Image.open(AMBIENTCG/f'{name}_1K_Color.jpg').convert('RGBA')
    lush=load('Grass004');worn=ImageEnhance.Color(load('Ground037')).enhance(.85)
    # A uniform blend: a large-scale mask would repeat visibly every 4 tiles.
    grass=ImageEnhance.Brightness(ImageEnhance.Color(Image.blend(lush,worn,.35)).enhance(.9)).enhance(.9)
    sand=ImageEnhance.Brightness(load('Ground093C')).enhance(.86)
    C=256
    def atlas(tex,transitions):
        im=Image.new('RGBA',(8*C,4*C),(0,0,0,0))
        im.paste(tex,(4*C,0))
        if not transitions:
            for cell in range(16):im.paste(tex.crop((cell%4*C,cell//4*C,cell%4*C+C,cell//4*C+C)),(cell%4*C,cell//4*C))
            return im
        rng=random.Random(9);rough=Image.new('L',(5,5));rough.putdata([rng.randint(70,185) for _ in range(25)])
        rough=rough.resize((C,C),Image.Resampling.BICUBIC)            # smooth value noise for ragged edges
        # Cell image corners: top-left = bit 8, top-right = 4, bottom-left = 2, bottom-right = 1.
        for cell in range(16):
            corners=Image.new('L',(2,2))
            corners.putdata([255*((cell>>3)&1),255*((cell>>2)&1),255*((cell>>1)&1),255*(cell&1)])
            # Bilinear corner weights (2x2 -> CxC, edge-aligned), roughened, then a soft threshold.
            weights=corners.resize((C,C),Image.Resampling.BILINEAR,box=(.5,.5,1.5,1.5))
            alpha=Image.blend(weights,rough,.25).point(lambda v:max(0,min(255,int((v-100)*255/90))))
            piece=tex.crop((cell%4*C,cell//4*C,cell%4*C+C,cell//4*C+C))
            piece.putalpha(alpha)
            im.paste(piece,(cell%4*C,cell//4*C))
        return im
    return atlas(grass,False),atlas(sand,True)

TREE_HP=1000000000
TREE_PATHTEX='PathTextures\\Frontline\\tree.tga'
# Troops are thin, so tapping or clicking their drawn mesh is fiddly. The engine picks a
# model by its MDX collision shapes first (MDLX_TraceModel): give foot soldiers an invisible
# box, a child of the animated root, wider than their silhouette.
TROOP_PICK=(34,90)  # half width/depth, height
TROOP_MODELS={u['model'] for u in catalog.UNITS.values() if u['speed']>0 and not u.get('flying')
              and u.get('movement')!='float' and u.get('classification')!='mechanical'}
def pick_box(data,half,height):
    chunks,pos=[],4
    while pos<len(data):
        tag,size=data[pos:pos+4],struct.unpack_from('<I',data,pos+4)[0]
        chunks.append([tag,data[pos+8:pos+8+size]]);pos+=8+size
    pivots=[c for c in chunks if c[0]==b'PIVT'][0]
    node=len(pivots[1])//12  # next node id: one pivot per node
    pivots[1]+=struct.pack('<3f',0,0,0)
    shape=struct.pack('<I',96)+b'Pick'.ljust(80,b'\0')+struct.pack('<3I',node,0,0x2000)
    shape+=struct.pack('<I6f',0,-half,-half,0,half,half,height)  # type 0 = box: min, max
    chunks.append([b'CLID',shape])
    return b'MDLX'+b''.join(t+struct.pack('<I',len(c))+c for t,c in chunks)

def assets(root,directory):
    for name in models.GEOMETRY:
        data=models.mesh(name)
        if name in TROOP_MODELS:data=pick_box(data,*TROOP_PICK)
        base.write(root,f'Emberfield/Models/{name}.mdx',data)
    # CC0 scenery (third_party/CREDITS.md): island palms replace the pine.
    for name in models.imported.SCENERY:
        base.write(root,f'Emberfield/Models/{name}.mdx',models.gltf_import.mdx(name,models.imported.triangles(name)))
    for code,u in catalog.UNITS.items():
        if u.get('pathtex'):base.write(root,u['pathtex'].replace('\\','/'),models.footprint_tga(u['model']))
    for name in set(models.GEOMETRY)|{'load','unload','return','airstrike','attack','gather','supply','spell','airgroup','torpedo','veteran','elite','sell','rally'}:
        im=icon(name)
        base.write(root,f'Emberfield/Icons/{name}.blp',base.art.blp_bytes(im,True))
        gray=ImageOps.grayscale(im).convert('RGBA')
        base.write(root,f'Emberfield/Icons/Disabled/DIS{name}.blp',base.art.blp_bytes(gray,True))
    # Original critical blast uses the existing timed projectile Death path.
    blast=models.base.mesh('critical',[(0,0,8,14,14,18,1)],scale=[(0,1),(3000,1),(3150,6),(3550,10),(3999,0),(4000,1)])
    blast=blast.replace(b'materials.blp',b'critical0.blp')
    base.write(root,'Emberfield/Models/critical.mdx',blast)
    base.write(root,'Emberfield/Textures/critical0.blp',base.art.blp_bytes(Image.new('RGBA',(256,256),(255,125,25,255)),True))
    # Damage effects: a dark smoke puff that rises and swells, and a short flame flicker.
    for name,boxes,texture,colour,keys,lift in [
        ('smoke',[(0,0,0,9,9,12,0),(4,3,10,7,7,10,0)],'smoke0',(58,58,60,215),[(0,1),(3000,1),(3150,1.1),(3700,2.3),(3999,0),(4000,1)],60),
        ('fire',[(0,0,0,5,5,10,0),(-3,2,4,3,3,9,0)],'fire0',(255,110,30,255),[(0,1),(3000,1),(3080,1.6),(3300,1),(3500,1.4),(3699,0),(4000,1)],10)]:
        # Rounded puffs drawn from the shared palette (boxes stacked into black slabs in big fights).
        base.write(root,f'Emberfield/Models/{name}.mdx',models.gltf_import.mdx(name,models.imported.EFFECTS[name],scale=keys,
            translation=[(0,0),(2999,0),(3000,0),(3999,lift),(4000,0)]))
        base.write(root,f'Emberfield/Textures/{texture}.blp',base.art.blp_bytes(Image.new('RGBA',(64,64),colour),True))
    # Near-miss impacts (s_naval.c S_NearMissEffect): a water splash and a land crater.
    base.write(root,'Emberfield/Models/splash.mdx',models.unit_anim.splash_mdx())
    base.write(root,'Emberfield/Models/crater.mdx',models.unit_anim.crater_mdx())
    # Ship status icons for the unit panel (tools/frontline/status_icons.py).
    from tools.frontline import status_icons
    for name,im in status_icons.all_icons().items():base.write(root,f'Emberfield/Icons/status_{name}.blp',base.art.blp_bytes(im,True))
    # Torpedo track, torpedo hit/launch and armour sparks (tools/frontline/naval_fx.py).
    from tools.frontline import naval_fx
    for name in naval_fx.MODELS:base.write(root,f'Emberfield/Models/{name}.mdx',naval_fx.mdx(name))
    # Flak and aircraft crashes (skills/s_air_effects.c): heavy/light bursts, sea/land wrecks.
    for name,data in (('flak_heavy',models.unit_anim.flak_mdx(True)),('flak_light',models.unit_anim.flak_mdx(False)),
                      ('crash_sea',models.unit_anim.crash_mdx(True)),('crash_land',models.unit_anim.crash_mdx(False))):
        base.write(root,f'Emberfield/Models/{name}.mdx',data)
    # Original area cursor; no fallback to a missing retail texture.
    cursor=Image.new('RGBA',(128,128),(0,0,0,0));draw=ImageDraw.Draw(cursor)
    draw.ellipse((4,4,123,123),outline=(120,220,160,220),width=4)
    draw.line((52,64,76,64),fill=(180,255,200,220),width=2)
    draw.line((64,52,64,76),fill=(180,255,200,220),width=2)
    base.write(root,'Emberfield/Textures/placement.blp',base.art.blp_bytes(cursor,True))
    skin=root/'UI/war3skins.txt'
    skin.write_text(skin.read_text()+"\nPlacementCursor=Emberfield\\Textures\\placement.blp\n")
    # ambientCG CC0 ground (third_party/CREDITS.md) in extended 1024x512 atlases.
    grass,sand=terrain_atlases()
    base.write(root,'Emberfield/Terrain/grass.blp',base.art.blp_bytes(grass,True))
    base.write(root,'Emberfield/Terrain/sand.blp',base.art.blp_bytes(sand,True))
    base.write(root,'Emberfield/Textures/CREDITS_THIRD_PARTY.md',(AMBIENTCG.parents[1]/'CREDITS.md').read_bytes())
    base.write(root,'Emberfield/Models/rally.mdx',base.models.mesh('rally',[(0,0,0,2,2,65,1),(13,0,43,13,2,20,8)]))
    # Original olive drab / steel / sand material atlas, no licensed war imagery.
    import random as _rng;_rng.seed(42)
    im=Image.new('RGBA',(256,256));d=ImageDraw.Draw(im)
    for i,c in enumerate([(128,124,102),(106,119,120),(146,136,105),(94,82,58),(189,165,123),(40,47,46),(120,141,144),(88,105,63)]):
        x,y=i%4*64,i//4*128
        d.rectangle((x,y,x+63,y+127),fill=(*c,255))
        # Subtle grain: per-pixel noise for a worn, painted-metal look.
        for py in range(y,y+128):
            for px in range(x,x+64):
                n=_rng.randint(-8,8)
                im.putpixel((px,py),tuple(max(0,min(255,v+n)) for v in c)+(255,))
        for line in range(16,128,24):
            d.line((x,y+line,x+63,y+line),fill=tuple(int(v*.86) for v in c),width=1)
        d.line((x+2,y+2,x+61,y+2),fill=tuple(min(255,int(v*1.12)) for v in c),width=2)
    base.write(root,'Emberfield/Textures/materials.blp',base.art.blp_bytes(im,True))
    base.write(root,'Emberfield/Textures/naval.blp',base.art.blp_bytes(naval_atlas(),True))
    # Shared colour atlas of every imported mesh; written after all models and icons registered their colours.
    base.write(root,models.gltf_import.PALETTE_TEXTURE.replace('\\','/'),base.art.blp_bytes(models.gltf_import.palette_image(),True))
    # Existing touchscreen geometry and touch groups stay intact; rename UI copy.
    for p in (root/'UI').rglob('*.fdf'):
        s=p.read_text().replace('EMBERFIELD','FRONTLINE').replace('Emberfield','Frontline').replace('"Ore"','"Materiel"').replace('"Timber"','"Logistics"').replace('"Ore:"','"Materiel:"')
        # The internal asset namespace is shared with the base pack emitter.
        s=s.replace('Frontline\\','Emberfield\\')
        p.write_text(s)
    front_menu(root)
    lan_menus(root)
    sound_menu(root)
    # The generated pack has no housing economy. Keep binding names, remove
    # obsolete icon/value geometry rather than changing the universal HUD.
    import re
    p=root/'UI/FrameDef/UI/ResourceBar.fdf';ui=p.read_text()
    ui=re.sub(r'Texture \{[^{}]*supply[.]blp[^{}]*\}', '', ui)
    ui=re.sub(r'(String "ResourceBarSupplyText" \{)[^{}]*\}',
              r'\1 Font "MasterFont",0, Width 0, Height 0, Anchor TOPLEFT,-0.9,0, }',ui)
    p.write_text(ui)
    minimap(directory,water,TERRAIN_HALF)
    p=root/'UI/war3skins.txt';p.write_text(p.read_text()+'CargoBackdrop=Emberfield\\Textures\\panel.blp\n')
    base.write(root,'UI/war3skins.txt',(root/'UI/war3skins.txt').read_text()+'RallyIndicatorDst=Emberfield\\Models\\rally.mdx\n')
    # Advisor callouts: the engine's attack alerts and construction/training "job done" hook.
    base.write(root,'UI/war3skins.txt',(root/'UI/war3skins.txt').read_text()+'UnderAttackSound=FLAlertUnit\nTownAttackSound=FLAlertTown\nJobDoneSound=FLJobDone\n')
    for name in ('CommandStrings.txt','CommandFunc.txt'):
        p=root/'Units'/name;p.write_text(p.read_text()+'[AdvisorStrings]\nUnitattack=Our forces are under fire.\nTownattack=Our base is under attack!\nAllyunderattack=%s reports forces under fire.\nAllytownattack=%s reports their base under attack.\n\n')

    # Visible water uses the engine's existing Water.slk renderer; the tint runs from a pale
    # lagoon at the shoreline through turquoise shallows to deep blue (the frames stay light).
    base.write(root,'TerrainArt/Water.slk',base.slk([dict(waterID='LSha',height=0,numTex=8,texRate=4,texFile='Emberfield\\Textures\\water',Dmin_R=34,Dmin_G=104,Dmin_B=128,Dmin_A=225,Dmax_R=18,Dmax_G=58,Dmax_B=92,Dmax_A=245,Smin_R=150,Smin_G=214,Smin_B=206,Smin_A=110,Smax_R=52,Smax_G=150,Smax_B=160,Smax_A=190)],'waterID'))
    # Seamless 8-frame loop: integer wave vectors in several directions (each advances a
    # whole number of cycles per loop) shaded by slope, with sparse crest glints.
    waves=[(1,2,9,1),(3,-1,6,-1),(-2,3,4,2),(5,1,2.5,-2),(-1,-6,1.8,3),(7,-4,1.2,-3)]
    for frame in range(8):
        wave=Image.new('RGBA',(256,256));px=wave.load();phase=frame*math.tau/8
        for y in range(256):
            for x in range(256):
                h=0;sx=0;sy=0
                for kx,ky,a,speed in waves:
                    t=math.tau*(kx*x+ky*y)/256+speed*phase
                    h+=a*math.sin(t);c=a*math.cos(t);sx+=c*kx;sy+=c*ky
                shade=(sx*.55+sy*.35)/40
                glint=max(0,h-16.5)*5
                r=196+26*shade+glint;g=214+24*shade+glint;b=224+20*shade+glint
                px[x,y]=(max(0,min(255,int(r))),max(0,min(255,int(g))),max(0,min(255,int(b))),255)
        base.write(root,f'Emberfield/Textures/water{frame:02}.blp',base.art.blp_bytes(wave,True))
    audio(root)
    # Crisper 128-pixel anti-aliased selection ring with a faint inner band.
    ring=Image.new('RGBA',(128,128));px=ring.load()
    for y in range(128):
        for x in range(128):
            d=math.hypot(x-63.5,y-63.5)
            a=max(0,1-abs(d-58)/3.2)*240+max(0,1-abs(d-51)/1.6)*70
            px[x,y]=(255,255,255,int(min(255,a)))
    for name in ['Small','Med','Large']:
        base.write(root,f'ReplaceableTextures/Selection/SelectionCircle{name}.blp',base.art.blp_bytes(ring,True))
    base.write(root,'UI/MiscData.txt',(root/'UI/MiscData.txt').read_text().replace('FoodCeiling=100','FoodCeiling=0'))

AUDIO=Path(__file__).resolve().parent/'audio'
# Weapon class -> (clips, volume, min/max audible distance). Impact sounds play at the
# target through UnitCombatSounds '<weapType1><armor>'; one channel per target bounds overlap.
WEAPON_SOUNDS={'FLSmall':('rifle1.wav,rifle2.wav',38,400,2400),'FLFlak':('flak1.wav,flak2.wav',42,500,3000),
               'FLShell':('shell1.wav,shell2.wav',58,700,4000),'FLHeavy':('heavy1.wav,heavy2.wav',70,900,5200)}
UI_SOUNDS={'InterfaceClick':'ui_click','InterfaceError':'ui_error','PlaceBuildingDefault':'ui_place',
           'RallyPointPlace':'ui_rally','SubGroupSelectionChange':'ui_select','AutoCastButtonClick':'ui_toggle','FLCritical':'explode2',
           'FLAlertUnit':'alert_unit','FLAlertTown':'alert_town','FLJobDone':'alert_done'}
ACK_SOUNDS={'What':'ack_what','Yes':'ack_yes','YesAttack':'ack_attack','Ready':'ack_ready'}

def rifle_shot(seed):
    # Original synthesized small-arms report: noise crack plus a short low thump.
    rng=random.Random(seed);rate=22050;n=int(rate*.22);last=0.0;out=bytearray()
    for i in range(n):
        t=i/rate;last+=.55*(rng.uniform(-1,1)-last)
        v=last*math.exp(-t*38)+.5*math.sin(2*math.pi*(95+20*seed)*t)*math.exp(-t*22)
        out+=struct.pack('<h',int(max(-1,min(1,v))*22000))
    return bytes(out)

def synth(n_seconds,voice,seed=0,rate=22050):
    # Original synthesized clip: voice(t, filtered_noise) -> sample in -1..1.
    rng=random.Random(seed);last=0.0;out=bytearray()
    for i in range(int(rate*n_seconds)):
        t=i/rate;last+=.3*(rng.uniform(-1,1)-last)
        out+=struct.pack('<h',int(max(-1,min(1,voice(t,last)))*22000))
    return bytes(out)

# Explosion: low rumbling noise with a sub-bass drop; body fall: short muffled thud;
# construction: two hammer knocks per 0.6 s loop.
CLIPS={'explode1':(1.1,lambda t,n:2.4*n*math.exp(-t*4)+.6*math.sin(2*math.pi*(60-25*t)*t)*math.exp(-t*5),3),
       'explode2':(.9,lambda t,n:2.6*n*math.exp(-t*5)+.6*math.sin(2*math.pi*(75-30*t)*t)*math.exp(-t*6),4),
       'bodyfall':(.3,lambda t,n:1.4*n*math.exp(-t*30)+.7*math.sin(2*math.pi*70*t)*math.exp(-t*20),5),
       'construct':(.6,lambda t,n:sum(1.8*n*math.exp(-(t-k)*60)+.5*math.sin(2*math.pi*420*(t-k))*math.exp(-(t-k)*45) for k in (0,.3) if t>=k),6)}
# Advisor tones (original): field-telephone warble for units under fire, a lower
# two-tone siren for the base, and a rising two-note chime when work is done.
def _tone(t,f,start,end):return .55*math.sin(2*math.pi*f*(t-start))*min(1,(t-start)*60,(end-t)*40) if start<=t<end else 0
CLIPS.update({'alert_unit':(.7,lambda t,n:sum(_tone(t,f,k*.17,k*.17+.15) for k,f in enumerate((880,660,880,660))),7),
              'alert_town':(1.0,lambda t,n:sum(_tone(t,f,k*.25,k*.25+.23) for k,f in enumerate((520,390,520,390))),8),
              'alert_done':(.5,lambda t,n:_tone(t,660,0,.2)+_tone(t,990,.22,.48),9)})

def pcm_wav(data):
    """Rewrite WAVE_FORMAT_EXTENSIBLE integer PCM as plain PCM; the engine loader accepts only tag 1."""
    chunks,pos={},12
    while pos+8<=len(data):
        tag,size=data[pos:pos+4],struct.unpack('<I',data[pos+4:pos+8])[0]
        chunks[tag]=data[pos+8:pos+8+size];pos+=8+size+(size&1)
    fmt=chunks[b'fmt '];tag,channels,rate,_,align,bits=struct.unpack('<HHIIHH',fmt[:16])
    if tag==1:return data
    assert tag==0xFFFE and fmt[24:26]==b'\x01\x00',f'unsupported WAV format {tag:#x}'
    import io
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setparams((channels,bits//8,rate,0,'NONE','not compressed'));w.writeframes(chunks[b'data'])
    return out.getvalue()

def audio(root):
    folder=root/'Emberfield/Sounds';folder.mkdir(parents=True,exist_ok=True)
    for clip in AUDIO.glob('*.wav'):(folder/clip.name).write_bytes(pcm_wav(clip.read_bytes()))
    (folder/'LICENSE_KENNEY.txt').write_text((AUDIO/'LICENSE.md').read_text())
    for name,(seconds,voice,seed) in CLIPS.items():
        with wave.open(str(folder/f'{name}.wav'),'wb') as w:
            w.setparams((1,2,22050,0,'NONE','not compressed'));w.writeframes(synth(seconds,voice,seed))
    for seed in (1,2):
        with wave.open(str(folder/f'rifle{seed}.wav'),'wb') as w:
            w.setparams((1,2,22050,0,'NONE','not compressed'));w.writeframes(rifle_shot(seed))
    row=lambda name,files,volume,lo=0,hi=0:dict(SoundName=name,DirectoryBase='Emberfield\\Sounds\\',FileNames=files,Volume=volume,Channel='0',Pitch=1,PitchVariance=.08 if lo else 0,MinDistance=lo,MaxDistance=hi,DistanceCutoff=hi)
    combat=[row(weapon+armor,*spec) for weapon,spec in WEAPON_SOUNDS.items() for armor in ('Flesh','Metal','Wood','Stone')]
    base.write(root,'UI/SoundInfo/UnitCombatSounds.slk',base.slk(combat,'SoundName'))
    base.write(root,'UI/SoundInfo/UISounds.slk',base.slk([row(k,v+'.wav',45) for k,v in UI_SOUNDS.items()]+[row('FLAAFire','flak1.wav,flak2.wav',40,600,3500)],'SoundName'))
    acks=[row(label+k,v+'.wav',40) for label in ('Ember','EmberMech') for k,v in ACK_SOUNDS.items()]
    acks+=[row('EmberDeath','bodyfall.wav',45,300,2400),row('EmberMechDeath','explode1.wav,explode2.wav',70,700,4500),
           row('FLConstruction','construct.wav',35,300,1800)]
    base.write(root,'UI/SoundInfo/UnitAckSounds.slk',base.slk(acks,'SoundName'))

def map_variants(root,directory,pack,theater,sites,paths):
    """IJN start (faction policy swapped) and Command Both sandbox from one theatre's USN map.
    sites(order) gives war3mapSites.txt; paths = (ijn map, sandbox map)."""
    import shutil
    from tools.frontline.scenario import faction_init
    alt=directory.parent/(directory.name+'-ijn')
    if alt.exists():shutil.rmtree(alt)
    shutil.copytree(directory,alt)
    script=RAW_SCRIPTS[theater]
    swapped=faction_init.replace('Player(0)','PLAYER_ZERO').replace('Player(1)','Player(0)').replace('PLAYER_ZERO','Player(1)')
    script=script.replace(faction_init,swapped).replace("SetPlayerAbilityAvailable(Player(0), 'Fkdo', false)","SetPlayerAbilityAvailable(Player(1), 'Fkdo', false)")
    script=script.replace('ember.ai','usn.ai')
    base.write(alt,'war3map.j',theater_script(script,theater,'IJN'))
    info=(alt/'war3map.w3i').read_bytes().replace(b'United States Navy',b'TEMP_NAVY').replace(b'Imperial Japanese Navy',b'United States Navy').replace(b'TEMP_NAVY',b'Imperial Japanese Navy')
    info=info.replace(b'U.S. Navy',b'TEMP_FORCE').replace(b'Japanese Navy',b'U.S. Navy').replace(b'TEMP_FORCE',b'Japanese Navy')
    if theater!='island':
        # Player(0) commands the IJN here, so the start locations swap with the navies.
        usn,ijn=(base.P('2f2I',*pacific.HQ[n],0,0) for n in ('USN','IJN'))
        info=info.replace(usn,b'TEMP_START_LOCATION').replace(ijn,usn).replace(b'TEMP_START_LOCATION',ijn)
    info=info.replace((TITLE+' - USN').encode(),(TITLE+' - IJN').encode(),1)
    base.write(alt,'war3map.w3i',info)
    base.write(alt,'war3mapSites.txt',sites(True))
    pack(alt,root/paths[0])
    # Sandbox: the USN map with no opposing AI and no fog; the menu's g_command_all lets the
    # player command both navies (engine G_UnitCanControl), so the sides still fight.
    sandbox=directory.parent/(directory.name+'-sandbox')
    if sandbox.exists():shutil.rmtree(sandbox)
    shutil.copytree(directory,sandbox)
    script=RAW_SCRIPTS[theater]
    # Fog stays on: View Side (Fviw on the headquarters) picks which navy's fog the player sees.
    for old,new in [('    set botOpponent = GetPlayerController(Player(1)) != ConvertMapControl(0)','    set botOpponent = false')]:
        assert old in script,old
        script=script.replace(old,new,1)
    old='call DisplayTimedTextToPlayer(Player(1), 0.12, 0.035, 15.0, "FRONTLINE LAN | Destroy the enemy Headquarters before yours falls.")'
    assert old in script
    script=script.replace(old,'call DisplayTimedTextToPlayer(Player(0), 0.12, 0.035, 15.0, "COMMAND BOTH | You command both navies: select and order any unit on either side. View Side (V) on a headquarters switches whose fog you see.")',1)
    base.write(sandbox,'war3map.j',theater_script(script,theater,'USN'))
    pack(sandbox,root/paths[1])

def extra_maps(root,directory,pack):
    """Island Command's IJN start and sandbox, then the Pacific theatre's three maps."""
    from tools.frontline.scenario import NAVAL, naval_production
    from tools.frontline.scenario import AI_SCRIPT_USN as AI_SCRIPT
    usn=''.join(f"        if GetUnitCount('{code}') < 1 then\n            call SetProduce(1, '{code}', 0)\n        endif\n" for code,u in NAVAL.items() if u['faction']=='USN')
    base.write(root,'Scripts/usn.ai',AI_SCRIPT.replace(naval_production,usn))
    map_variants(root,directory,pack,'island',island_sites,(IJN_MAP_PATH,SANDBOX_MAP_PATH))
    pacific_dir=directory.parent/'map-pacific'
    if pacific_dir.exists():
        import shutil;shutil.rmtree(pacific_dir)
    pacific_dir.mkdir(parents=True)
    pacific_map_data(pacific_dir)
    pack(pacific_dir,root/PACIFIC_MAP_PATH)
    map_variants(root,pacific_dir,pack,'pacific',lambda swapped:pacific_sites(('IJN','USN') if swapped else ('USN','IJN')),
                 (PACIFIC_IJN_MAP_PATH,PACIFIC_SANDBOX_MAP_PATH))

def app_icon(out):
    im=Image.new('RGB',(1024,1024),(28,42,44));d=ImageDraw.Draw(im)
    d.polygon([(512,140),(760,690),(512,830),(264,690)],fill=(170,165,126))
    d.line((512,240,512,695),fill=(37,52,54),width=38)
    d.line((340,535,684,535),fill=(37,52,54),width=30)
    im.save(out/'icon.png')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('build/frontline'))
    a=parser.parse_args();base.generate(a.out.resolve(),Path(__file__).resolve().parents[2],sys.modules[__name__])
