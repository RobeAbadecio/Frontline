#!/usr/bin/env python3
"""Render Frontline art contact sheets into docs/images/frontline/.

python3 tools/frontline/contact_sheets.py   (no game build needed)
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from PIL import Image,ImageDraw
from tools.frontline import generate,imported,models
from tools.frontline import gltf_import as gi

OUT=Path(__file__).resolve().parents[2]/'docs'/'images'/'frontline'
UNITS=('rifle','machinegun','commando','mortar','engineer','rifle_ijn','machinegun_ijn','commando_ijn','mortar_ijn',
       'tank','heavytank','tank_ijn','heavytank_ijn','scoutcar',
       'artillery','antiair','rocketart',
       'fighter','bomber','recon','wildcat','dauntless','avenger','zero','val','kate','pine')
SHIPS=('iowa','northcarolina','southdakota','yamato','nagato','kongo',
       'cleveland','baltimore','atlanta','mogami','takao','myoko',
       'fletcher','sumner','fubuki','kagero','akizuki',
       'yorktown','essex','independence','akagi','kaga','soryu','hiryu','shokaku','lcvp','lcm','daihatsu')
BUILDINGS=('headquarters','barracks','depot','factory','airfield','shipyard','bunker','coastalgun',
           'watchtower','stockpile','sandbag','drydock_usn','drydock_ijn','escortdock_usn','escortdock_ijn')

def sheet(names,render,cell=240,columns=6,background=(46,52,46)):
    rows=(len(names)+columns-1)//columns
    im=Image.new('RGB',(columns*cell,rows*(cell+22)),background);d=ImageDraw.Draw(im)
    for i,name in enumerate(names):
        x,y=i%columns*cell,i//columns*(cell+22)
        art=render(name,cell)
        im.paste(art,(x,y),art if art.mode=='RGBA' else None)
        d.text((x+8,y+cell+4),name,fill=(226,220,190))
    return im

def model(name,size):
    tris=models.drydock.triangles(name) if name in models.drydock.MODELS else imported.triangles(name)
    return gi.preview(gi.transform(tris,yaw=180),size)

def ship(name,size):
    from tools.frontline import ships
    tris=ships.complete(name)
    return gi.preview(gi.transform(tris,yaw=205),size)

def icon(name,size):
    return generate.icon(name).resize((size,size),Image.Resampling.LANCZOS)

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    sheet(UNITS,model).save(OUT/'unit_grid.png')
    sheet(BUILDINGS,model,cell=300,columns=4).save(OUT/'building_grid.png')
    sheet(SHIPS,ship,cell=320,columns=4,background=(26,58,84)).save(OUT/'ship_grid.png')
    sheet(UNITS[:-1]+BUILDINGS,icon,cell=128,columns=10,background=(20,22,20)).save(OUT/'icon_grid.png')
    from tools.frontline import structures
    sheet(structures.MODELS,structures.preview,cell=300,columns=6).save(OUT/'structure_grid.png')
    print('wrote',*sorted(p.name for p in OUT.glob('*_grid.png')))
