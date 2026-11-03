"""Original WWII-inspired symmetric roster; costs are materiel / logistics.

Ships use water-only movement. Aircraft are deliberately specialized; no
fiction-specific gameplay is added to the universal client or renderer.
"""
def troop(name,model,hp,cost,speed,damage=0,**kw):
    return dict(name=name,model=model,hp=hp,cost=cost,speed=speed,damage=damage,time=kw.pop('time',12),collision=kw.pop('collision',20),food=kw.pop('food',0),ability=kw.pop('ability',''),**kw)
def building(name,model,hp,cost,slot,**kw):
    return troop(name,model,hp,cost,0,time=kw.pop('time',20),food=0,collision=kw.pop('collision',65),slot=slot,**kw)
UNITS={
'fwkr':troop('Combat Engineer','engineer',200,45,250,6,ability='Ahar,Arep,AHbu',classification='peon',builds='fhq0,fbar,ffac,fair,fdoc,fbnk,fcst,fwat,frod,fsbg,fwir',hotkey='E',sound='FLSmall',missile='tracer',mspeed=1800,arc=.03),
'finf':troop('Rifle Squad','rifle',320,70,265,17,range=450,cool=1.1,slot=(0,0),hotkey='R',sound='FLSmall',missile='tracer',mspeed=1800,arc=.03),
'fmg0':troop('Machine Gun Squad','machinegun',350,100,220,12,range=600,cool=.45,targets='ground,air,structure',slot=(1,0),hotkey='M',sound='FLSmall',missile='tracer',mspeed=1800,arc=.03),
'ftnk':troop('Medium Tank','tank',1000,220,235,44,wood=35,armor=5,range=650,cool=2.2,classification='mechanical',defense='large',collision=35,food=0,slot=(0,0),hotkey='T',sound='FLShell',missile='shell',mspeed=1300,arc=.08),
'fcar':troop('Armored Scout','scoutcar',490,120,340,18,wood=15,range=500,cool=.9,armor=2,classification='mechanical',sight=1900,collision=26,slot=(1,0),hotkey='S',sound='FLSmall',missile='tracer',mspeed=1800,arc=.03),
'fart':troop('Field Artillery','artillery',400,180,170,90,wood=40,range=1250,cool=4,attack='siege',classification='mechanical',collision=25,food=0,slot=(2,0),hotkey='A',sound='FLShell',missile='shell',mspeed=950,arc=.35),
'faa0':troop('Anti-Aircraft Gun','antiair',360,130,190,34,wood=25,range=950,cool=.8,targets='air',attack='pierce',classification='mechanical',slot=(3,0),hotkey='G',sound='FLFlak',missile='tracer',mspeed=1700,arc=.02),
'fhtk':troop('Heavy Tank','heavytank',1800,380,180,85,wood=60,armor=8,range=700,cool=3.0,classification='mechanical',defense='large',collision=40,food=0,slot=(0,1),hotkey='H',sound='FLHeavy',missile='shell',mspeed=1300,arc=.08),
'frkt':troop('Rocket Artillery','rocketart',500,200,190,75,wood=45,range=1100,cool=3.5,attack='siege',classification='mechanical',collision=28,food=0,slot=(1,1),hotkey='K',sound='FLHeavy',missile='shell',mspeed=950,arc=.35,splash=180),
'fmrt':troop('Mortar Team','mortar',280,90,200,55,range=900,cool=3.0,attack='siege',slot=(2,0),hotkey='O',sound='FLShell',missile='shell',mspeed=950,arc=.35),
'fcmd':troop('Commando','commando',400,160,310,28,range=500,cool=.9,slot=(3,0),hotkey='C',sound='FLSmall',missile='tracer',mspeed=1800,arc=.03,sight=1900),
'ffgt':troop('Fighter Flight','fighter',380,110,480,36,wood=15,range=500,cool=.8,targets='air',attack='pierce',flying=True,height=240,food=0,slot=(0,0),hotkey='F',sound='FLFlak',missile='tracer',mspeed=1700,arc=.02),
'fbmb':troop('Dive Bomber Flight','bomber',520,170,360,95,ability='Fhit',wood=30,range=500,cool=3.2,targets='ground,structure',attack='siege',flying=True,height=210,food=0,slot=(1,0),hotkey='B',sound='FLHeavy',missile='bomb',mspeed=650,arc=.05),
'ftor':troop('Torpedo Bomber Flight','bomber',420,190,340,110,ability='Ftor',wood=40,range=400,cool=4,targets='ground,structure',attack='siege',flying=True,height=70,food=0,slot=(3,0),hotkey='T',sound='FLHeavy',missile='bomb',mspeed=500,arc=.01),
'frec':troop('Recon Aircraft','recon',230,75,520,sight=2600,flying=True,height=300,food=0,slot=(2,0),hotkey='R'),
'fbat':troop('Battleship','battleship',3200,650,175,150,ability='Fbaa',wood=100,range=1750,cool=4.5,attack='siege',armor=8,movement='float',classification='mechanical',collision=65,food=0,slot=(0,0),hotkey='B',sight=2000,sound='FLHeavy',missile='shell',mspeed=950,arc=.3),
'fdst':troop('Destroyer','destroyer',1400,260,280,35,wood=40,range=850,cool=1,targets='ground,air,structure',armor=3,movement='float',classification='mechanical',collision=38,food=0,slot=(1,0),hotkey='D',sound='FLShell',missile='shell',mspeed=1300,arc=.08),
'fcrs':troop('Cruiser','cruiser',2100,400,220,65,wood=65,range=1150,cool=2.2,targets='ground,air,structure',armor=5,movement='float',classification='mechanical',collision=48,food=0,slot=(2,0),hotkey='C',sound='FLShell',missile='shell',mspeed=1300,arc=.08),
'fcvr':troop('Fleet Carrier','carrier',2800,700,175,10,wood=140,range=650,cool=1.5,targets='air',armor=4,movement='float',classification='mechanical',collision=70,food=0,ability='Fcap,Frep,Fsqf,Fsqd,Fsqt,Faut,Fret,Fpat,Fstr,Fhld,Fcov,Fpro',slot=(3,0),hotkey='V',sight=2000,sound='FLFlak',missile='tracer',mspeed=1700,arc=.02),
'flct':troop('Landing Craft','landingcraft',800,150,230,wood=25,movement='float',classification='mechanical',collision=32,food=0,ability='Acar,Aloa,Adro',slot=(0,1),hotkey='L'),
'ftrn':troop('Troop Transport','transport',1500,240,200,wood=45,movement='float',classification='mechanical',collision=44,food=0,ability='Fcrg,Aloa,Adro',slot=(1,1),hotkey='T'),
'fhq0':building('Command Headquarters','headquarters',2000,300,(0,0),ability='Argl',trains='fwkr',hotkey='H'),
'fbar':building('Barracks','barracks',1000,150,(1,0),trains='finf,fmg0,fmrt,fcmd',hotkey='B'),
'fdep':building('Supply Depot','depot',700,80,(2,0),hotkey='S',collision=40),
'ffac':building('Vehicle Factory','factory',1300,200,(3,0),wood=40,trains='ftnk,fcar,fart,faa0,fhtk,frkt',hotkey='V'),
'fair':building('Airfield','airfield',1200,240,(0,1),wood=50,trains='ffgt,fbmb,frec,ftor',hotkey='A',ability='Fstk,Aloa,Facp'),
'fdoc':building('Shipyard','shipyard',1500,260,(1,1),wood=60,water=400,trains='fbat,fdst,fcrs,fcvr,flct,ftrn',hotkey='D',collision=50),
'fbnk':building('Machine Gun Bunker','bunker',1100,150,(2,1),wood=20,damage=24,range=750,cool=.6,armor=6,hotkey='K',upgrade='fbn2',collision=40,sound='FLSmall',missile='tracer',mspeed=1800,arc=.03),
'fbn2':building('Fortified Bunker','bunker',1800,280,(0,2),wood=50,damage=38,range=850,cool=.6,armor=10,collision=40,hotkey='U',sound='FLSmall',missile='tracer',mspeed=1800,arc=.03),
'fcst':building('Coastal Battery','coastalgun',1300,240,(3,1),wood=45,damage=130,range=1800,cool=5,armor=5,attack='siege',hotkey='C',collision=40,sound='FLHeavy',missile='shell',mspeed=950,arc=.3),
'fwat':building('Observation Tower','watchtower',500,70,(0,2),damage=8,range=550,cool=1.5,sight=2400,hotkey='W',collision=30,sound='FLSmall',missile='tracer',mspeed=1800,arc=.03),
'eore':building('Materiel Stockpile','stockpile',100000,0,(0,0),ability='Agld',collision=75,time=0),
# Engineer field constructions (WC4/HoI/Red Alert inspired).
'frod':building('Supply Road','road',120,10,(1,2),time=4,collision=24,hotkey='D',description='Paved supply route. Friendly ground units near a road move 35% faster.'),
'fsbg':building('Sandbag Wall','sandbag',400,20,(2,2),time=5,collision=20,armor=6,hotkey='N',description='Reinforced sandbag barrier. Absorbs enemy fire; infantry behind it gain cover.'),
'fwir':building('Barbed Wire','barbedwire',150,10,(3,2),time=3,collision=20,hotkey='W',description='Razor wire entanglement. Enemy ground units in range move 30% slower.'),
}
# Historical fleet additions retain the original symmetric units for old maps.
# Tuning uses RTS units, not real-world displacement or metres/second.
NAVAL={}
def navy(code,name,template,model,faction,role,slot,description,**tuning):
    u=dict(UNITS[template]);u.update(tuning)
    facility={'battleship':'fhvy','carrier':'fhvy','escort':'fesc','landing':'flnd'}[role]
    u.update(name=name,model=model,faction=faction,role=role,slot=slot,facility=facility,
             description=description,hotkey='QWERASDFZXCV'[slot[1]*4+slot[0]],food=0)
    if role=='battleship':u['ability']='Fgun,Fpro,'+{'iowa':'Biow','yamato':'Byam','nagato':'Bnag'}.get(model,'Fbaa')
    if role=='carrier':
        prefix='U' if faction=='USN' else 'J'
        u['ability']=f'Fcap,{prefix}rep,Fsqf,Fsqd,Fsqt,Faut,Fret,Fpat,Fstr,Fhld,Fcov,Fpro'
    NAVAL[code]=u;UNITS[code]=u
navy('uiow','USS Iowa (BB-61)','fbat','iowa','USN','battleship',(0,0),'Iowa-class fast battleship; three triple 16-inch turrets. Long-range bombardment.',hp=3400,cost=740,wood=125,speed=205,damage=155,range=1800,time=36)
navy('umss','USS Missouri (BB-63)','fbat','iowa','USN','battleship',(1,0),'Iowa-class fast battleship; three triple 16-inch turrets. Durable fleet flagship.',hp=3550,cost=780,wood=135,speed=205,damage=155,range=1800,time=38)
navy('uent','USS Enterprise (CV-6)','fcvr','yorktown','USN','carrier',(2,0),'Yorktown-class carrier. Wildcat CAP, Dauntless dive bombers and Avenger torpedo aircraft.',hp=2850,cost=720,wood=145,speed=200,time=36)
navy('uykt','USS Yorktown (CV-5)','fcvr','yorktown','USN','carrier',(3,0),'Yorktown-class carrier. Mobile airfield; returning aircraft are repaired by condition.',hp=2750,cost=680,wood=135,speed=200,time=34)
navy('uesx','USS Essex (CV-9)','fcvr','essex','USN','carrier',(0,1),'Essex-class fleet carrier; enlarged flight deck, island and anti-aircraft galleries.',hp=3150,cost=820,wood=170,speed=200,time=40,armor=5)
navy('uflt','Fletcher-class','fdst','fletcher','USN','escort',(0,0),'Fast destroyer screen; five single gun mounts and dual torpedo banks. Anti-aircraft escort.',hp=1450,cost=280,wood=45,speed=285,time=18)
navy('uclv','Cleveland-class','fcrs','cleveland','USN','escort',(1,0),'Light cruiser; four triple 6-inch mounts. Sustained surface fire and anti-aircraft defense.',hp=2250,cost=430,wood=70,speed=230,time=25)
navy('ulcv','LCVP Higgins Boat','flct','lcvp','USN','landing',(0,2),'Infantry landing craft with bow ramp. Carries ten infantry or engineer units; no tanks.',hp=550,cost=100,wood=15,speed=240,time=12,collision=24,ability='Flcv,Aloa,Adro')
navy('ulcm','LCM','flct','lcm','USN','landing',(1,1),'Mechanized landing craft with a wide tank well and bow ramp. Carries eight troops or vehicles.',hp=900,cost=180,wood=30,speed=210,time=16,collision=34)
navy('jyam','Yamato','fbat','yamato','IJN','battleship',(0,0),'Yamato-class battleship; three triple 18.1-inch turrets and massive pagoda bridge. Heavy bombardment.',hp=4100,cost=900,wood=160,speed=175,damage=190,range=1850,time=44,armor=10,collision=72)
navy('jmus','Musashi','fbat','yamato','IJN','battleship',(1,0),'Yamato-class battleship; three triple 18.1-inch turrets. Heavy armor and siege firepower.',hp=4200,cost=930,wood=170,speed=175,damage=190,range=1850,time=46,armor=10,collision=72)
navy('jnag','Nagato','fbat','nagato','IJN','battleship',(2,0),'Nagato-class battleship; four twin 16.1-inch turrets and tall pagoda bridge.',hp=3150,cost=650,wood=105,speed=165,damage=145,range=1700,time=34)
for code,name,model,slot,hp,cost,speed in [
 ('jakg','Akagi','akagi',(3,0),2950,730,190),('jkag','Kaga','kaga',(0,1),3200,770,170),
 ('jsor','Sōryū','soryu',(1,1),2450,610,215),('jhir','Hiryū','hiryu',(2,1),2550,640,215),
 ('jsho','Shōkaku','shokaku',(3,1),2900,750,210),('jzui','Zuikaku','shokaku',(0,2),3000,780,210)]:
    navy(code,name,'fcvr',model,'IJN','carrier',slot,
         {'akagi':'Converted carrier with port island and long flight deck.',
          'kaga':'Broad converted carrier with starboard island and low exhaust galleries.',
          'soryu':'Compact fast carrier with starboard island.',
          'hiryu':'Fast carrier with port island.',
          'shokaku':'Shōkaku-class fleet carrier with starboard island and long bow.'}[model]+' Zero CAP, Val dive bombers and Kate torpedo aircraft.',hp=hp,cost=cost,wood=cost//5,speed=speed,time=36)
navy('jmog','Mogami-class','fcrs','mogami','IJN','escort',(0,0),'Heavy cruiser in WWII 8-inch configuration; five twin main mounts. Surface strike escort.',hp=2200,cost=420,wood=70,speed=240,damage=75,cool=2.5,time=26)
navy('jfub','Fubuki-class','fdst','fubuki','IJN','escort',(1,0),'Fast destroyer; three twin gun mounts and three triple torpedo banks. Light fleet screen.',hp=1350,cost=260,wood=40,speed=290,damage=38,cool=1.2,time=18)
navy('jdai','Daihatsu-class','flct','daihatsu','IJN','landing',(0,2),'Daihatsu landing barge; open cargo well, aft wheelhouse and bow ramp. Carries troops or vehicles.',hp=800,cost=150,wood=25,speed=230,time=12,collision=32)
# More 1941-45 classes. Each lists the art it wants; until that model exists the closest
# existing hull stands in (resolved below against historical_models.GEOMETRY).
NEW_SHIP_ART={}
def navy_art(code,art,*args,**kw):
    navy(code,*args,**kw);NEW_SHIP_ART[code]=art
navy_art('unca','northcarolina','USS North Carolina (BB-55)','fbat','iowa','USN','battleship',(1,1),'North Carolina-class fast battleship; three triple 16-inch turrets and a dense 5-inch/AA battery.',hp=3300,cost=700,wood=115,speed=190,damage=150,range=1750,time=34)
navy_art('usdk','southdakota','USS South Dakota (BB-57)','fbat','iowa','USN','battleship',(2,1),'South Dakota-class battleship; compact, heavily armoured hull with three triple 16-inch turrets.',hp=3400,cost=720,wood=120,speed=185,damage=150,range=1750,time=35,armor=9)
navy_art('uind','independence','USS Independence (CVL-22)','fcvr','yorktown','USN','carrier',(3,1),'Independence-class light carrier on a cruiser hull; fast, small air group.',hp=2000,cost=520,wood=100,speed=220,time=28)
navy_art('ubal','baltimore','Baltimore-class','fcrs','cleveland','USN','escort',(2,0),'Heavy cruiser; three triple 8-inch turrets. Hard-hitting surface escort.',hp=2400,cost=460,wood=75,speed=225,damage=80,range=1250,time=27)
navy_art('uatl','atlanta','Atlanta-class','fcrs','cleveland','USN','escort',(3,0),'Anti-aircraft light cruiser; eight twin 5-inch mounts. Shreds air attacks.',hp=1900,cost=380,wood=60,speed=250,damage=50,cool=1.4,range=1050,time=22)
navy_art('usum','sumner','Allen M. Sumner-class','fdst','fletcher','USN','escort',(0,1),'Destroyer with three twin 5-inch mounts; heavier gun and AA fit than Fletcher.',hp=1550,cost=300,wood=48,speed=280,damage=40,time=19)
navy_art('jkon','kongo','Kongō','fbat','nagato','IJN','battleship',(1,2),'Kongō-class fast battleship; four twin 14-inch turrets, the fastest IJN capital ship.',hp=2900,cost=600,wood=95,speed=230,damage=130,range=1650,time=32,armor=6)
navy_art('jtak','takao','Takao-class','fcrs','mogami','IJN','escort',(2,0),'Heavy cruiser; five twin 8-inch turrets and a massive bridge. Night-fighting torpedo cruiser.',hp=2300,cost=440,wood=72,speed=235,damage=78,cool=2.4,time=26)
navy_art('jmyo','myoko','Myōkō-class','fcrs','mogami','IJN','escort',(3,0),'Heavy cruiser; five twin 8-inch turrets. Robust surface strike escort.',hp=2250,cost=430,wood=70,speed=235,damage=76,cool=2.4,time=26)
navy_art('jkgr','kagero','Kagerō-class','fdst','fubuki','IJN','escort',(0,1),'Fleet destroyer; three twin 5-inch mounts and Long Lance torpedoes.',hp=1400,cost=270,wood=42,speed=290,damage=40,cool=1.2,time=18)
navy_art('jaki','akizuki','Akizuki-class','fdst','fubuki','IJN','escort',(1,1),'Anti-aircraft destroyer; four twin 3.9-inch high-angle mounts.',hp=1500,cost=300,wood=48,speed=275,damage=34,cool=.8,time=20)
for _code in ('uatl','jaki'):UNITS[_code]['targets']='ground,air,structure'
try:
    from tools.frontline import historical_models as _art
    for _code,_name in NEW_SHIP_ART.items():
        if _name in _art.GEOMETRY:UNITS[_code]['model']=_name
except ImportError:
    pass
UNITS['fhvy']=building('Capital Shipyard','shipyard',1700,340,(2,0),wood=90,water=400,hotkey='P',collision=50,ability='Fkdo',trains=','.join(k for k,u in NAVAL.items() if u['facility']=='fhvy'),description='USN / IJN battleships and fleet carriers. Faction roster follows your headquarters. Kidō Butai assembles existing IJN carriers and escorts.')
UNITS['fesc']=building('Escort Shipyard','shipyard',1400,240,(1,2),wood=55,water=400,hotkey='S',collision=50,trains=','.join(k for k,u in NAVAL.items() if u['facility']=='fesc'),description='Faction cruisers and destroyers: surface fire support and fast anti-aircraft screens.')
UNITS['flnd']=building('Landing Craft Yard','shipyard',1200,200,(2,2),wood=40,water=400,hotkey='L',collision=50,trains=','.join(k for k,u in NAVAL.items() if u['facility']=='flnd'),description='Faction infantry and vehicle landing craft. Build on an open coastline.')
# Japan vs USA: the generic Shipyard is gone; each navy builds at its Capital, Escort and Landing yards.
# The Escort Shipyard also launches landing craft, so one coastal yard can carry an invasion.
UNITS['fesc']['trains']+=','+','.join(k for k,u in NAVAL.items() if u['role']=='landing')
UNITS['fwkr']['builds']=UNITS['fwkr']['builds'].replace(',fdoc','')+',fhvy,fesc,flnd'
for prefix,faction,names,art in [('u','USN',['Wildcat Fighter','Dauntless Dive Bomber','Avenger Torpedo Bomber'],['wildcat','dauntless','avenger']),('j','IJN',['Zero Fighter','Val Dive Bomber','Kate Torpedo Bomber'],['zero','val','kate'])]:
    for suffix,template,name,model in zip(['fig','bom','tor'],['ffgt','fbmb','ftor'],names,art):
        UNITS[prefix+suffix]=dict(UNITS[template],name=name,model=model,faction=faction)
# Defensive maneuvering by airframe: the Zero is the most agile, torpedo bombers the least.
for code,alias in [('ffgt','Fevf'),('ufig','Fevf'),('jfig','Fevz'),('fbmb','Fevb'),('ubom','Fevb'),('jbom','Fevb'),('ftor','Fevt'),('utor','Fevt'),('jtor','Fevt')]:
    UNITS[code]['ability']=','.join(filter(None,[UNITS[code]['ability'],alias]))
# Fuel and home base (s_air_combat.c): every aircraft carries Fhom (Return Home, Q) and
# airfield aircraft show their fuel in seconds of flight as the mana bar (carrier flights
# keep their sortie tank instead; carriers reuse an embarked aircraft's mana as ammunition).
# Fighters had the shortest endurance, torpedo bombers more, long-range recon the most.
AIRCRAFT_FUEL={'ffgt':90,'ufig':90,'jfig':105,'fbmb':120,'ubom':120,'jbom':120,'ftor':120,'utor':120,'jtor':120,'frec':180}
for code,fuel in AIRCRAFT_FUEL.items():
    UNITS[code].update(mana=fuel,regen=0)
    UNITS[code]['ability']=','.join(filter(None,[UNITS[code]['ability'],'Fhom']))

# Japanese land variants: identical stats, own art and names. Each side's set is hidden from
# the other with SetPlayerTechMaxAllowed, like the navies (scenario.faction_init).
LAND_IJN={'finf':('jinf','Type 99 Rifle Squad','rifle_ijn'),'fmg0':('jmg0','Type 99 Light MG Squad','machinegun_ijn'),
          'fmrt':('jmrt','Type 89 Knee Mortar Team','mortar_ijn'),'fcmd':('jcmd','SNLF Commando','commando_ijn'),
          'ftnk':('jtnk','Type 97 Chi-Ha','tank_ijn'),'fhtk':('jhtk','Type 3 Chi-Nu','heavytank_ijn')}
for _us,(_ijn,_name,_model) in LAND_IJN.items():
    UNITS[_us]['faction']='USN'
    UNITS[_ijn]=dict(UNITS[_us],name=_name,model=_model,faction='IJN')
for _building in ('fbar','ffac'):
    UNITS[_building]['trains']+=','+','.join(LAND_IJN[c][0] for c in UNITS[_building]['trains'].split(',') if c in LAND_IJN)

# Faction fortifications replace the generic bunker, coastal battery and AA vehicle on the
# engineer's card (the old codes stay defined: maps and saves still create them). Each pair
# shares a button slot; scenario.faction_init hides the other navy's half, like the fleets.
# Anti-aircraft emplacements fire at aircraft only. Stats are RTS tuning, not ballistics tables.
_AA=dict(targets='air',attack='pierce',sound='FLFlak',missile='tracer',mspeed=1700,arc=.02)
_MG=dict(sound='FLSmall',missile='tracer',mspeed=1800,arc=.03,collision=40)
_GUN=dict(attack='siege',sound='FLHeavy',missile='shell',mspeed=950,arc=.3,collision=40)
FORTIFICATIONS={
 'upbx':building('M1919 MG Pillbox','pillbox_usn',1150,160,(0,0),wood=20,damage=24,range=750,cool=.55,armor=6,hotkey='P',upgrade='upb2',faction='USN',**_MG,
                 description='Concrete pillbox with a Browning M1919 machine gun. Holds a beach against infantry.'),
 'upb2':building('Reinforced Pillbox','pillbox_usn',1850,280,(0,2),wood=50,damage=40,range=850,cool=.55,armor=10,hotkey='U',faction='USN',**_MG,
                 description='Thickened walls and a .50 caliber Browning M2.'),
 'jpbx':building('Type 92 HMG Pillbox','pillbox_ijn',1100,150,(0,0),wood=20,damage=26,range=750,cool=.6,armor=6,hotkey='P',upgrade='jpb2',faction='IJN',**_MG,
                 description='Concrete pillbox with a Type 92 heavy machine gun. Holds a beach against infantry.'),
 'jpb2':building('Coconut-Log Bunker','pillbox_ijn',2000,300,(0,2),wood=55,damage=36,range=800,cool=.6,armor=11,hotkey='U',faction='IJN',**_MG,
                 description='Log, coral and sand revetment over the pillbox: very hard to crack.'),
 'uaa2':building('Oerlikon 20 mm AA Mount','aa_oerlikon',400,90,(0,0),wood=10,damage=14,range=750,cool=.35,armor=2,hotkey='L',faction='USN',**_AA,
                 description='Light automatic cannon. Fast tracer fire against low aircraft; cannot engage ground targets.'),
 'jaa2':building('Type 98 20 mm AA Mount','aa_type98',380,85,(0,0),wood=10,damage=15,range=720,cool=.4,armor=2,hotkey='L',faction='IJN',**_AA,
                 description='Light automatic cannon. Fast tracer fire against low aircraft; cannot engage ground targets.'),
 'uaa4':building('Bofors 40 mm AA Gun','aa_bofors',600,150,(1,0),wood=25,damage=30,range=950,cool=.7,armor=3,hotkey='M',faction='USN',**_AA,
                 description='The standard medium AA gun: clip-fed 40 mm shells. Anti-aircraft only.'),
 'jaa4':building('Type 96 25 mm Triple AA','aa_type96',560,140,(1,0),wood=22,damage=24,range=900,cool=.5,armor=3,hotkey='M',faction='IJN',**_AA,
                 description='Triple-barrel 25 mm mount, the IJN\'s standard AA gun. Anti-aircraft only.'),
 'uaa9':building('90 mm M1 AA Gun','aa_m1_90mm',900,260,(2,0),wood=55,damage=85,range=1500,cool=2.2,armor=4,hotkey='H',faction='USN',**_AA,
                 description='Heavy AA gun with predictor control; long-range bursts against high bombers. Anti-aircraft only.'),
 'jaa8':building('Type 88 75 mm AA Gun','aa_type88',850,240,(2,0),wood=50,damage=70,range=1400,cool=2.0,armor=4,hotkey='H',faction='IJN',**_AA,
                 description='Heavy AA gun; long-range bursts against high bombers. Anti-aircraft only.'),
 'ucst':building('155 mm GPF Seacoast Battery','coastal_usn',1300,240,(3,0),wood=45,damage=130,range=1800,cool=5,armor=5,hotkey='C',faction='USN',**_GUN,
                 description='155 mm guns on Panama mounts: long-range fire against ships and landings.'),
 'jcst':building('Vickers 8-inch Coastal Battery','coastal_ijn',1400,260,(3,0),wood=50,damage=150,range=1850,cool=5.5,armor=5,hotkey='C',faction='IJN',**_GUN,
                 description='Heavy 8-inch naval guns in a concrete emplacement: long-range fire against ships.'),
 'urad':building('SCR-270 Radar Station','radar_usn',450,120,(1,0),wood=30,sight=3200,hotkey='R',collision=40,faction='USN',
                 description='Early-warning radar: sees aircraft and ships far beyond the coast.'),
 'jrad':building('Type 11 Radar Station','radar_ijn',450,120,(1,0),wood=30,sight=3000,hotkey='R',collision=40,faction='IJN',
                 description='Early-warning radar: sees aircraft and ships far beyond the coast.'),
}
UNITS.update(FORTIFICATIONS)

# Engineer build menu: folders by kind (s_build.c). A folder is a Builds entry with its own
# Builds list and no UnitBalance row; its button opens the folder, Back (BUILD_BACK) returns.
# The engineer's own Builds lists the folders and every structure, so orders by id (the bot,
# hotkeys, the SC2 API) keep working without the menu.
BUILD_FOLDERS=[
 ('fzba','Base','B','headquarters',(0,0),'Headquarters, barracks, vehicle factory and supply roads.',[('fhq0',(0,0),'H'),('fbar',(1,0),'B'),('ffac',(2,0),'V'),('frod',(3,0),'R')]),
 ('fzdf','Defences','D','bunker',(1,0),'Pillboxes, sandbags, barbed wire and observation towers.',[('upbx',(0,0),'P'),('jpbx',(0,0),'P'),('fsbg',(1,0),'S'),('fwir',(2,0),'W'),('fwat',(3,0),'T')]),
 ('fzaa','Anti-Aircraft','A','antiair',(2,0),'Light, medium and heavy anti-aircraft guns. They fire at aircraft only.',[('uaa2',(0,0),'L'),('jaa2',(0,0),'L'),('uaa4',(1,0),'M'),('jaa4',(1,0),'M'),('uaa9',(2,0),'H'),('jaa8',(2,0),'H')]),
 ('fznv','Naval','N','shipyard',(3,0),'Shipyards and coastal batteries.',[('fhvy',(0,0),'P'),('fesc',(1,0),'S'),('flnd',(2,0),'L'),('ucst',(3,0),'C'),('jcst',(3,0),'C')]),
 ('fzai','Air','F','airfield',(0,1),'Airfield and early-warning radar.',[('fair',(0,0),'A'),('urad',(1,0),'R'),('jrad',(1,0),'R')]),
]
BUILD_BACK=('fzbk','Back','X','return',(3,2),'Back to the structure categories.')
for _folder,_name,_key,_icon,_slot,_text,_children in BUILD_FOLDERS:
    for _code,_pos,_hotkey in _children:UNITS[_code].update(slot=_pos,hotkey=_hotkey)
UNITS['fwkr']['builds']=','.join([f[0] for f in BUILD_FOLDERS]+[c for f in BUILD_FOLDERS for c,_,_ in f[6]])

# Every structure blocks exactly its drawn footprint (authored in generate.py from the model).
for _code,_u in UNITS.items():
    if _u['speed']==0:_u['pathtex']='PathTextures\\Frontline\\'+_code+'.tga'

# Death voice: infantry fall, everything mechanical or built explodes. Buildings
# loop a construction clip while scaffolded (UnitProfile BuildingSoundLabel).
for _u in UNITS.values():
    if _u.get('movement')=='float':
        _u['turnrate']=.12
        _u['ability']=','.join(filter(None,[_u['ability'],'Fsmk']))  # damage smoke and fire
    if 'air' in _u.get('targets','').split(',') and not _u.get('flying'):
        _u['ability']=','.join(filter(None,[_u['ability'],'Faaa']))
        _u['acquire']=_u['range']
    if _u['speed']==0 or _u.get('flying') or _u.get('classification')=='mechanical':_u['voice']='EmberMech'
    if _u['speed']==0 and _u['time']:_u['buildsound']='FLConstruction'
SPELLS=[
 dict(alias='Fcov',code='Fcov',levels=1,DataA1=2,DataB1=2,Rng1=1600,Area1=500),
 dict(alias='Fpro',code='Fpro',levels=2,DataA1=.65,DataB1=200,DataC1=50),
 dict(alias='Fhit',code='Fhit',levels=1,DataA1=12,DataB1=3600),
 dict(alias='Ftor',code='Ftor',levels=1,DataA1=18,DataB1=4200),
 dict(alias='Faaa',code='Faaa',levels=1),
 dict(alias='Arep',code='Arep',levels=1,DataA1=1,DataB1=1,DataC1=1,DataD1=1.5,Rng1=180,targs1='ground,air,structure,friend,mechanical'),
 dict(alias='Acar',code='Acar',levels=1,DataA1=8,Rng1=240,Dur1=.4,targs1='ground,friend,nonhero'),  # landing craft: 8 troops or vehicles
 dict(alias='Fcrg',code='Acar',levels=1,DataA1=12,Rng1=240,Dur1=.4,targs1='ground,friend,nonhero'),
 dict(alias='Aloa',code='Aloa',levels=1,Rng1=240),
 dict(alias='Adro',code='Adro',levels=1),
 # Fcap DataA=capacity (12 aircraft), B=sortie seconds, C=rearm seconds, D=takeoff seconds,
 # E=repair seconds per 100% damage (a returning wreck below 25% health is written off),
 # E=repair HP per service, F=reserved. Recovery is within Rng of the carrier.
 dict(alias='Fcap',code='Fcap',levels=2,DataA1=12,DataB1=45,DataC1=8,DataD1=2,DataE1=60,DataF1=8,Rng1=130),
 dict(alias='Fhld',code='Acar',levels=1,DataA1=24,Rng1=140,targs1='air,friend,nonhero'),  # fleet carrier hangar
 dict(alias='Fh18',code='Acar',levels=1,DataA1=18,Rng1=140,targs1='air,friend,nonhero'),  # mid-size carrier
 dict(alias='Fh12',code='Acar',levels=1,DataA1=12,Rng1=140,targs1='air,friend,nonhero'),  # light carrier
 dict(alias='Fstk',code='Acar',levels=1,DataA1=40,Rng1=240,targs1='air,friend,nonhero'),
 dict(alias='Ffig',code='Ffig',levels=1,UnitID1='ffgt',Cool1=1),
 dict(alias='Fbom',code='Fbom',levels=1,UnitID1='fbmb',Cool1=1),
 dict(alias='Fret',code='Fret',levels=1,Cool1=1),
 # Fpat A=fighters launched per carrier, B=orbit radius around the patrol point.
 dict(alias='Fpat',code='Fpat',levels=1,DataA1=2,DataB1=450,Rng1=30000,Cool1=1),
 # Fstr A=deck launch interval s, B=assembly deadline s, C=launch deadline s,
 # D=attack deadline s, E=escort fighters per carrier. Target an enemy or an area.
 dict(alias='Fstr',code='Fstr',levels=1,DataA1=.8,DataB1=25,DataC1=30,DataD1=75,DataE1=2,Rng1=30000,Cool1=1,targs1='ground,structure,air,enemy,vulnerable,invulnerable'),
 # Frep levels: 1 fighter, 2 dive bomber, 3 torpedo bomber. A=complement, B=payload per sortie.
 dict(alias='Frep',code='Frep',levels=3,UnitID1='ffgt',UnitID2='fbmb',UnitID3='ftor',DataA1=2,DataA2=1,DataA3=1,DataB1=8,DataB2=1,DataB3=1,Cool1=1,Cool2=1,Cool3=1),
 dict(alias='Fsts',code='Fsts',levels=1),
 dict(alias='Fgrp',code='Fgrp',levels=1),
 dict(alias='Fbak',code='Fbak',levels=1),
 dict(alias='Fldf',code='Fldf',levels=1),
 dict(alias='Fldd',code='Fldd',levels=1),
 dict(alias='Fldt',code='Fldt',levels=1),
 dict(alias='Fsif',code='Fsif',levels=1),
 dict(alias='Fsid',code='Fsid',levels=1),
 dict(alias='Fsit',code='Fsit',levels=1),
 dict(alias='Fsmk',code='Fsmk',levels=1),
 # Fevd evasion: A=chance %, B=maneuver s, C=jink speed, D=recovery s. Fighters agile; bombers far less.
 dict(alias='Fevf',code='Fevd',levels=1,DataA1=32,DataB1=1.2,DataC1=320,DataD1=2.5),
 dict(alias='Fevz',code='Fevd',levels=1,DataA1=40,DataB1=1.1,DataC1=360,DataD1=2.2),
 dict(alias='Fevb',code='Fevd',levels=1,DataA1=16,DataB1=.9,DataC1=180,DataD1=3.5),
 dict(alias='Fevt',code='Fevd',levels=1,DataA1=10,DataB1=.8,DataC1=140,DataD1=4),
 # Fbaa battleship AA: A=range, B=damage per hit, C=volley s, D=base hit %, E=mounts per volley.
 dict(alias='Fbaa',code='Fbaa',levels=1,DataA1=1000,DataB1=18,DataC1=1.4,DataD1=35,DataE1=3),
 dict(alias='Biow',code='Fbaa',levels=1,DataA1=1150,DataB1=22,DataC1=1.1,DataD1=45,DataE1=5),
 dict(alias='Byam',code='Fbaa',levels=1,DataA1=1100,DataB1=18,DataC1=1.2,DataD1=34,DataE1=5),
 dict(alias='Bnag',code='Fbaa',levels=1,DataA1=950,DataB1=16,DataC1=1.5,DataD1=30,DataE1=3),
]
SPELL_UI=[('Fpro','Reinforced protection (200 materiel, 50 logistics)','P','hold',0,2),('Aloa','Embark friendly troop','L','load',1,1),('Adro','Disembark at shore','U','unload',2,1),('Fhld','Load Aircraft: picks up a nearby friendly aircraft onto the carrier deck','L','load',1,1),('Fsts','Air Status: shows aircraft on deck, airborne and loaded','S','airgroup',2,1),('Fret','Return Aircraft: recall all airborne flights to the carrier','R','return',3,1),('Ffig','Launch Fighter: sends one fighter airborne on patrol (no target needed)','F','fighter',0,2),('Fbom','Launch Bomber: sends one dive bomber airborne on patrol (no target needed)','B','bomber',1,2),('Fstr','Air Strike (K): click an enemy or area; carriers launch their strike package together','K','airstrike',2,2),('Fcov','CAP: toggle fighter cover','C','fighter',3,2),('Fpat','Air Patrol: click a point; fighters fly there and guard it','Y','patrol',3,2),('Fstk','Aircraft Storage: airfield holds up to 40 aircraft','S','airgroup',3,1)]

# Faction air groups: Replenish levels name the faction's fighter, dive and torpedo aircraft.
for prefix in ('U','J'):
    p=prefix.lower()
    SPELLS.append(dict(alias=prefix+'rep',code='Frep',levels=3,UnitID1=p+'fig',UnitID2=p+'bom',UnitID3=p+'tor',DataA1=2,DataA2=1,DataA3=1,DataB1=8,DataB2=1,DataB3=1,Cool1=1,Cool2=1,Cool3=1))
    names=[UNITS[p+k]['name'] for k in ('fig','bom','tor')]
    # Replenish ability kept for engine compatibility but no button — carriers are transport-only.
# Faction-specific launch commands share behavior while retaining authored aircraft.
for prefix in ('U','J'):
    for suffix,basecode,order,slot in [('fig','Ffig','fighter',(0,2)),('bom','Fbom','bomber',(1,2)),('tor','Ftrp','torpedo',(3,2))]:
        SPELLS.append(dict(alias=prefix+suffix,code=basecode,levels=1,UnitID1=prefix.lower()+suffix,Cool1=1))
        u=UNITS[prefix.lower()+suffix]
        SPELL_UI.append((prefix+suffix,f'Launch / replace {u["name"]} ({u["cost"]} materiel, {u.get("wood",0)} logistics)',{'fig':'F','bom':'B','tor':'T'}[suffix],u['model'],*slot))
SPELLS.extend([
 dict(alias='Fgun',code='Fgun',levels=1),
 dict(alias='Fkdo',code='Fkdo',levels=1),
 dict(alias='Flcv',code='Acar',levels=1,DataA1=10,Rng1=240,Dur1=.4,targs1='ground,friend,nonhero,organic'),
])
SPELL_UI.extend([
 ('Fgrp','Air Group (G): choose loadout (12 aircraft total)','G','airgroup',3,2),
 ('Fldf','Fighters: click +1 fighter in the loadout, Shift-click -1. At 12 total it takes the slot from the largest other type','F','wildcat',0,0),
 ('Fldd','Dive bombers: click +1, Shift-click -1','D','dauntless',1,0),
 ('Fldt','Torpedo bombers: click +1, Shift-click -1','T','torpedo',2,0),
 ('Fsif','Strike package: toggle FIGHTERS (air sweep / escort). Only the chosen types launch on Air Strike','Q','fighter',0,1),
 ('Fsid','Strike package: toggle DIVE BOMBERS (attack ships and ground targets)','W','bomber',1,1),
 ('Fsit','Strike package: toggle TORPEDO BOMBERS (attack ships only)','E','torpedo',2,1),
 ('Fbak','Done: back to the carrier commands','B','return',3,2)])
SPELL_UI.append(('Frep','Replenish Aircraft','R','supply',0,2))
SPELL_UI.append(('Fkdo','Kidō Butai: assemble six existing IJN carriers plus Mogami and Fubuki escorts','K','carrier',3,2))

from tools.frontline.yamato import BATTERIES as YAMATO_BATTERIES, MUZZLE_M, WORLD_SCALE
for _code in ('jyam','jmus'):
    UNITS[_code]['launchx']=MUZZLE_M[0]*WORLD_SCALE
    UNITS[_code]['launchz']=MUZZLE_M[2]*WORLD_SCALE

# Battery data: mount count, barrels, four local forward offsets, three heights.
for model,alias,barrels,offsets,heights in [
 ('iowa','Giow',3,[106,75,-94,0],[17,27,17]),
 ('yamato','Gyam',3,[p[0] for p in YAMATO_BATTERIES]+[0],[p[2] for p in YAMATO_BATTERIES]),
 ('nagato','Gnag',2,[92,62,-59,-91],[17,27,27]),
 # historical_models.STATIONS: North Carolina / South Dakota triples, Kongo's four twins.
 ('northcarolina','Gnca',3,[96,66,-82,0],[17,27,17]),
 ('southdakota','Gsdk',3,[88,60,-74,0],[17,27,17]),
 ('kongo','Gkon',2,[94,68,-52,-86],[17,25,17])]:
    values=[len([v for v in offsets if v]),barrels]+offsets+heights
    SPELLS.append(dict(alias=alias,code='Fgun',levels=1,**{f'Data{chr(65+i)}1':v for i,v in enumerate(values)}))
    for u in NAVAL.values():
        if u['model']==model:u['ability']=u['ability'].replace('Fgun',alias)
# Their AA batteries (Fbaa: A=range, B=damage per hit, C=volley s, D=base hit %, E=mounts per volley):
# North Carolina and South Dakota carried Iowa-like 5"/38 and 40 mm fits; Kongo a lighter late-war one.
for model,aa,stand_in,data in [('northcarolina','Bnca','Biow',(1100,20,1.2,42,5)),
                               ('southdakota','Bsdk','Biow',(1100,21,1.15,44,5)),
                               ('kongo','Bkon','Bnag',(950,15,1.5,30,3))]:
    SPELLS.append(dict(alias=aa,code='Fbaa',levels=1,**{f'Data{c}1':v for c,v in zip('ABCDE',data)}))
    for u in NAVAL.values():
        if u['model']==model:u['ability']=','.join(aa if a in (stand_in,'Fbaa') else a for a in u['ability'].split(','))

# Squadron carriers: every carrier embarks 4 fighters, 4 dive bombers and 4 torpedo bombers once
# (the Replenish levels' DataA). Losses are permanent, so the air group is priced into the hull.
for _rep in [s for s in SPELLS if s['code']=='Frep']:
    _rep.update(DataA1=4,DataA2=4,DataA3=4)
# Hangar by class, scaled from historical air groups (Essex/Yorktown/Shokaku/Akagi/Kaga ~70-90
# aircraft, Soryu/Hiryu ~60-70, Independence ~33): the carrier embarks a third of it per type.
CARRIER_HOLD={'jsor':'Fh18','jhir':'Fh18','uind':'Fh12'}
for _c,_u in [('fcvr',UNITS['fcvr'])]+[(c,u) for c,u in NAVAL.items() if u['role']=='carrier']:
    _u['cost']+=400;_u['wood']=_u.get('wood',0)+60
    _hold=CARRIER_HOLD.get(_c,'Fhld')
    _u['armor']=3 if _c=='uesx' else 2  # thin hull and decks: heavy shells overpenetrate
    _u['ability']=_u['ability'].replace('Fhld',_hold)
    _n={'Fhld':24,'Fh18':18,'Fh12':12}[_hold]//3
    _u['description']=_u.get('description','')+f' Air group: {_n} fighters, {_n} dive bombers, {_n} torpedo bombers; losses are not replaced.'
CARRIER_STRIKE_RANGE=8000  # also s_carrier.c CARRIER_STRIKE_RANGE
SPELLS.extend([dict(alias=a,code=a,levels=1,Rng1=CARRIER_STRIKE_RANGE,Cool1=1,targs1=t) for a,t in
    [('Fsqf','ground,air,enemy,vulnerable,invulnerable'),('Fsqd','ground,structure,enemy,vulnerable,invulnerable'),('Fsqt','ground,enemy,vulnerable,invulnerable')]])
# Carrier card: one button per squadron, then Recall, Air Status and Reinforced Protection.
# Patrol/Air Strike stay as orders for the bot but have no button (no art), like Replenish.
SPELL_UI[:]=[e for e in SPELL_UI if e[0] not in ('Fpat','Fstr','Fcov','Frep','Fgrp','Fpro','Ffig','Fbom','Ufig','Ubom','Utor','Jfig','Jbom','Jtor')]
SPELL_UI.extend([('Fsqf','Fighter Squadron (F): click an area; every ready fighter flies there, guards it against aircraft and returns when fuel runs low','F','fighter',0,2),
 ('Fsqd','Dive Bomber Squadron (D): click a target; every ready dive bomber attacks it once and returns','D','bomber',1,2),
 ('Fsqt','Torpedo Squadron (T): click a ship; every ready torpedo bomber attacks it once and returns','T','torpedo',2,2),
 ('Fpro','Reinforced protection (200 materiel, 50 logistics)','P','hold',3,2),
 ('Fcov','CAP (C): toggle fighters circling the carrier; they return to refuel, are repaired by condition and relaunch','C','fighter',1,1)])
SPELLS.append(dict(alias='Facp',code='Facp',levels=2))
SPELLS.append(dict(alias='Fhom',code='Fhom',levels=1))
SPELL_UI.append(('Fhom','Return Home (Q): fly back to the carrier or airfield where this aircraft was last stored, land and refuel. Aircraft also turn for home on their own at bingo fuel','Q','return',3,1))
SPELLS.append(dict(alias='Faut',code='Faut',levels=1))
SPELL_UI.append(('Faut','Auto Launch (U): toggle; aircraft attack whatever the carrier or its planes spot (battleships first, then cruisers, destroyers)','U','airgroup',2,1))
# Attack with a carrier picks the aircraft: its gun must accept surface targets so the order is valid.
for _u in [UNITS['fcvr']]+[u for u in NAVAL.values() if u['role']=='carrier']:
    _u['targets']='ground,structure,air'
SPELL_UI.append(('Facp','Airfield CAP (C): toggle; stored and nearby fighters take off and circle the airfield, intercepting raiders','C','fighter',2,1))

for u in NAVAL.values():
    facility=UNITS[u['facility']]['name']
    u['description']+=f"|nHP {u['hp']} | Armor {u.get('armor',0)} | Speed {u['speed']} | Damage {u['damage']} | Range {u.get('range',0)} | Build {u['time']}s | Housing 0.|n{u['cost']} materiel / {u.get('wood',0)} logistics. Requires {facility}."

# Classic-RTS tech tree: each tier unlocks the next, and the command card shows "Requires ...".
# The bot's build order (scenario.AI_SCRIPT) already climbs barracks -> factory -> airfield.
REQUIRES={'ffac':'fbar','fair':'ffac','fdoc':'fbar','fesc':'fbar','flnd':'fbar','fcst':'ffac',
          'fhvy':'fair','fhtk':'fair','frkt':'fair','fcmd':'ffac',
          'ucst':'ffac','jcst':'ffac','uaa4':'fbar','jaa4':'fbar','uaa9':'ffac','jaa8':'ffac','urad':'fbar','jrad':'fbar'}
for _code,_need in REQUIRES.items():
    for _c in [_code]+[LAND_IJN[_code][0]] if _code in LAND_IJN else [_code]:
        UNITS[_c]['requires']=_need

# Combat ranks (scenario.VetGrant swaps the alias): Fvet A=damage fraction, B=armor, C=HP/s fraction.
SPELLS.extend([dict(alias='Fvt1',code='Fvet',levels=1,DataA1=.2,DataB1=2,DataC1=0),
               dict(alias='Fvt2',code='Fvet',levels=1,DataA1=.4,DataB1=4,DataC1=.01),
               dict(alias='Fsel',code='Fsel',levels=1,DataA1=.5)])
SPELL_UI.extend([('Fvt1','Veteran: +20% firepower, +2 armor (3 kills)','V','veteran',1,1),
                 ('Fvt2','Elite: +40% firepower, +4 armor, self-repairs 1% per second (7 kills)','V','elite',1,1),
                 ('CmdRally','Set Rally Point: new units from this building move there (right-click a resource to send engineers to work)','Y','rally',2,2),
                 ('Fsel','Sell Structure: demolish it and recover half its cost','X','sell',1,2)])
# Every finished structure can be sold except the Headquarters (losing it ends the match).
for _code,_u in UNITS.items():
    if _u['speed']==0 and _code not in ('fhq0','eore','fhvy'):  # the Capital Shipyard card is full
        _u['ability']=','.join(filter(None,[_u['ability'],'Fsel']))

# Ballistics (s_ballistics.c, Fbal): A=green dispersion radius, B=veteran fraction of A,
# C=shots to master, D=citadel % on ships, E=ricochet base % against armour 3+, F=AP penetration mm (below).
SPELLS.extend([dict(alias='Fbls',code='Fbal',levels=1,DataA1=130,DataB1=.3,DataC1=40,DataD1=12,DataE1=10),
               dict(alias='Fbla',code='Fbal',levels=1,DataA1=120,DataB1=.35,DataC1=30,DataD1=0,DataE1=6),
               # Aircrews start green: wide bomb and torpedo scatter that tightens as they fly.
               dict(alias='Fblb',code='Fbal',levels=1,DataA1=160,DataB1=.3,DataC1=16,DataD1=12,DataE1=15),
               dict(alias='Fblt',code='Fbal',levels=1,DataA1=170,DataB1=.3,DataC1=16,DataD1=0,DataE1=-100)])
for _code,_u in UNITS.items():
    _targets=_u.get('targets','ground,structure').split(',')
    if not _u.get('damage') or _targets==['air'] or 'Fcap' in _u['ability']:continue
    if _u.get('movement')=='float' or _code in ('fcst','ucst','jcst'):_alias='Fbls'
    elif _u.get('model','').startswith(('artillery','rocketart','mortar')):_alias='Fbla'
    elif _code in ('ftor','utor','jtor'):_alias='Fblt'
    elif _code in ('fbmb','ubom','jbom'):_alias='Fblb'
    else:continue
    _u['ability']=','.join(filter(None,[_u['ability'],_alias]))

# Armour penetration (s_ballistics.c, docs/frontline-naval-damage.md). Each main battery gets its
# own Fbal alias, identical to Fbls but with F = AP penetration in mm of vertical armour at
# point-blank range (it falls with range on the belt and grows on the deck as fire plunges).
GUN_PENETRATION={'Fp04':110,'Fp05':130,'Fp06':220,'Fp08':300,'Fp14':480,'Fp16':650,'Fp18':720}
SHIP_GUN={'fdst':'Fp05','uflt':'Fp05','usum':'Fp05','uatl':'Fp05','jfub':'Fp05','jkgr':'Fp05','jaki':'Fp04',
          'fcrs':'Fp06','uclv':'Fp06','ubal':'Fp08','jmog':'Fp08','jtak':'Fp08','jmyo':'Fp08','fcst':'Fp08',
          'fbat':'Fp16','uiow':'Fp16','umss':'Fp16','unca':'Fp16','usdk':'Fp16','jnag':'Fp16','jkon':'Fp14',
          'jyam':'Fp18','jmus':'Fp18'}
_fbls=next(s for s in SPELLS if s['alias']=='Fbls')
SPELLS.extend(dict(_fbls,alias=a,DataF1=mm) for a,mm in GUN_PENETRATION.items())
for _code,_alias in SHIP_GUN.items():
    UNITS[_code]['ability']=UNITS[_code]['ability'].replace('Fbls',_alias)
# Farm ship protection: A=belt mm, B=deck mm, C=torpedo protection (fraction of a torpedo hit
# absorbed by bulges and bulkheads; flooding slows by the same fraction). Belts are nominal plate;
# inclined belts (Iowa, South Dakota, Yamato) are rounded up for their slope.
SHIP_ARMOUR={'Fadd':(15,13,0),            # destroyers: splinter plating only
             'Faca':(95,32,.05),          # Atlanta AA cruiser
             'Facl':(127,51,.1),          # light cruiser (Cleveland)
             'Facu':(152,64,.15),         # Baltimore heavy cruiser
             'Facj':(102,35,.15),         # IJN heavy cruisers (Mogami, Takao, Myoko)
             'Fabk':(203,80,.15),         # Kongo battlecruiser
             'Fabn':(305,100,.25),        # Nagato
             'Fabu':(330,150,.35),        # Iowa, North Carolina, South Dakota
             'Faby':(410,200,.4),         # Yamato
             'Facv':(102,38,.2),          # Yorktown-class carrier
             'Face':(102,64,.25),         # Essex
             'Facs':(165,100,.25),        # Shokaku: armoured magazines, good torpedo system
             'Facx':(152,79,.15),         # Akagi / Kaga: battlecruiser and battleship hulls
             'Facf':(50,25,.05)}          # Soryu, Hiryu, Independence: light, fast, thin
UNIT_ARMOUR={'fdst':'Fadd','uflt':'Fadd','usum':'Fadd','jfub':'Fadd','jkgr':'Fadd','jaki':'Fadd',
             'uatl':'Faca','fcrs':'Facl','uclv':'Facl','ubal':'Facu','jmog':'Facj','jtak':'Facj','jmyo':'Facj',
             'jkon':'Fabk','jnag':'Fabn','fbat':'Fabu','uiow':'Fabu','umss':'Fabu','unca':'Fabu','usdk':'Fabu',
             'jyam':'Faby','jmus':'Faby','fcvr':'Facv','uent':'Facv','uykt':'Facv','uesx':'Face',
             'jsho':'Facs','jzui':'Facs','jakg':'Facx','jkag':'Facx','jsor':'Facf','jhir':'Facf','uind':'Facf'}
SPELLS.extend(dict(alias=a,code='Farm',levels=1,DataA1=b,DataB1=d,DataC1=t) for a,(b,d,t) in SHIP_ARMOUR.items())
for _code,_alias in UNIT_ARMOUR.items():
    UNITS[_code]['ability']=','.join(filter(None,[UNITS[_code]['ability'],_alias]))
# Ship torpedoes (s_torpedo.c Ftps): A=range, B=torpedoes per salvo, C=reload s, D=speed,
# E=damage per hit, F=degrees between torpedoes. US Mk 15: short-ranged, no reloads carried
# (a long reload stands in). IJN Type 93 "Long Lance": oxygen-fuelled, far longer, heavier
# warhead, and IJN ships carried reloads with quick-reload gear.
SPELLS.extend([dict(alias='Ftus',code='Ftps',levels=1,DataA1=1300,DataB1=4,DataC1=35,DataD1=420,DataE1=180,DataF1=4),
               dict(alias='Ftuc',code='Ftps',levels=1,DataA1=1300,DataB1=4,DataC1=40,DataD1=420,DataE1=180,DataF1=4),
               dict(alias='Ftjd',code='Ftps',levels=1,DataA1=1900,DataB1=4,DataC1=30,DataD1=460,DataE1=260,DataF1=4),
               dict(alias='Ftja',code='Ftps',levels=1,DataA1=1900,DataB1=2,DataC1=30,DataD1=460,DataE1=260,DataF1=5),
               dict(alias='Ftjc',code='Ftps',levels=1,DataA1=1900,DataB1=4,DataC1=35,DataD1=460,DataE1=260,DataF1=4)])
SHIP_TORPEDOES={'fdst':'Ftus','uflt':'Ftus','usum':'Ftus','uatl':'Ftuc',
                'jfub':'Ftjd','jkgr':'Ftjd','jaki':'Ftja','jmog':'Ftjc','jtak':'Ftjc','jmyo':'Ftjc'}
for _code,_alias in SHIP_TORPEDOES.items():
    UNITS[_code]['ability']=','.join(filter(None,[UNITS[_code]['ability'],_alias]))
# AA Mount (s_aamount.c, code Fmnt): one light AA mount per structure, bought from its card.
# Level 1 = offered, level 2 = installed. A=range, B=damage per hit, C=volley s, D=base hit %,
# E=barrels per volley (the Fbaa layout), F=materiel, G=logistics, H=mount model-space Y,
# I=mount model-space Z. The mount draws AA_MOUNT_MODEL at (0, H, I) in the structure's model
# space (front -Y, up +Z) and its tracers leave from there. One alias per structure model.
AA_MOUNT_MODEL='aa_mount'
AA_MOUNT_COST=(120,30)
AA_MOUNT={'headquarters':(0,112),'barracks':(0,65),'depot':(0,49),'factory':(0,93),'airfield':(0,75),
          'shipyard':(0,69),'bunker':(0,47),'coastalgun':(0,48),'watchtower':(0,139),
          'pillbox_usn':(0,27),'pillbox_ijn':(0,46),'coastal_usn':(0,36),'coastal_ijn':(0,40),
          'radar_usn':(-22,6),'radar_ijn':(-20,6)}
# Field works and the stockpile carry no crew; AA guns already are AA; the Capital Shipyard card is full.
AA_MOUNT_EXCLUDED={'eore','frod','fsbg','fwir','fhvy'}
AA_MOUNT_ALIAS={}
for _i,_model in enumerate(AA_MOUNT):
    _alias=f'Fm{_i:02d}';AA_MOUNT_ALIAS[_model]=_alias
    SPELLS.append(dict(alias=_alias,code='Fmnt',levels=2,DataA1=800,DataB1=16,DataC1=.8,DataD1=45,DataE1=2,
                       DataF1=AA_MOUNT_COST[0],DataG1=AA_MOUNT_COST[1],DataH1=AA_MOUNT[_model][0],DataI1=AA_MOUNT[_model][1]))
    SPELL_UI.append((_alias,f'AA Mount (Z): light anti-aircraft guns on this structure ({AA_MOUNT_COST[0]} materiel, {AA_MOUNT_COST[1]} logistics)','Z','antiair',3,2))
for _code,_u in UNITS.items():
    if _u['speed']!=0 or _code in AA_MOUNT_EXCLUDED or 'air' in _u.get('targets','').split(','):continue
    _u['ability']=','.join(filter(None,[_u['ability'],AA_MOUNT_ALIAS[_u['model']]]))

# Airfields are shared ground (s_airfield.c, Fcpt): the map's fields start neutral and any side
# takes one by holding it. A=seconds of uncontested presence, B=radius. Aircraft land, store and
# take off only at their own side's airfield (cargo is same-owner). Engineers can still build one.
SPELLS.append(dict(alias='Fcpt',code='Fcpt',levels=1,DataA1=12,DataB1=450))
UNITS['fair']['ability']=','.join([UNITS['fair']['ability'],'Fcpt'])
UNITS['fair']['description']=('Trains aircraft and stores up to 40. Neutral airfields on the map are captured by holding '
                              'ground troops beside them, uncontested, for 12 seconds.')

# The UI font has no macron glyphs (ō, ū): write romanized names in plain letters.
_PLAIN=str.maketrans({'ō':'o','ū':'u','Ō':'O','Ū':'U'})
for _u in UNITS.values():
    for _k in ('name','description'):
        if isinstance(_u.get(_k),str):_u[_k]=_u[_k].translate(_PLAIN)
SPELL_UI[:]=[(e[0],e[1].translate(_PLAIN))+tuple(e[2:]) for e in SPELL_UI]

# Ships are repaired only at a shipyard (dry dock): no regeneration at sea, and every
# shipyard restores parked friendly ships. Fdck A=fraction of max HP per second, B=berth
# radius beyond the yard (s_veterancy.c). A battleship is fully repaired in about 50 s.
from tools.frontline import drydock as _drydock
_berths=_drydock.BERTHS['shipyard']
# A=HP fraction per second while berthed, B=take-in reach beyond the yard, C..H=berth centres.
SPELLS.append(dict(alias='Fdck',code='Fdck',levels=1,DataA1=.03,DataB1=450,
                   **{f'Data{c}1':v for c,v in zip('CDEFGH',[n for x,y,*_ in _berths for n in (x,y)])}))
for _code,_u in UNITS.items():
    if _u.get('movement')=='float':_u['regenHP']=0
    if _u.get('model')=='shipyard':
        _u['ability']=','.join(filter(None,[_u['ability'],'Fdck']))
        _u['description']=_u.get('description',_u['name'])+'|nDry dock: an idle damaged friendly ship brought alongside sails into a berth, the gate shuts and it is repaired (hull and turrets), then it sails out. New ships launch from the slip. Ships do not repair anywhere else.'

# Firepower follows condition (s_attack.c S_ConditionFirepower): every unit's and structure's
# damage scales with its remaining health, down to A at zero; B=1 enables it.
SPELLS.append(dict(alias='Fhpf',code='Fhpf',levels=1,DataA1=.35,DataB1=1))
# Underway fire (Fuwf): armed warships engage surface targets while sailing, turrets training
# on the target; the hull never has to turn to fire. Carriers keep their guns for AA only.
SPELLS.append(dict(alias='Fuwf',code='Fuwf',levels=1))
for _code,_u in UNITS.items():
    if _u.get('movement')=='float' and _u.get('damage') and 'Fcap' not in _u['ability'] and _u.get('targets','ground,structure')!='air':
        _u['ability']=','.join(filter(None,[_u['ability'],'Fuwf']))

# Command Both (sandbox): View Side on the headquarters switches whose fog you see, USN or IJN,
# while you keep command of both (s_veterancy.c Fviw). Refused outside Command Both.
SPELLS.append(dict(alias='Fviw',code='Fviw',levels=1))
SPELL_UI.append(('Fviw','View Side (V): Command Both only. See the battle through the other navy\'s fog of war; you still command both','V','airgroup',1,2))
UNITS['fhq0']['ability']=','.join(filter(None,[UNITS['fhq0']['ability'],'Fviw']))

# Leash (s_veterancy.c Flsh): troops, vehicles and ships that engage on their own from idle
# return once A beyond where they stood, instead of chasing across the map.
SPELLS.append(dict(alias='Flsh',code='Flsh',levels=1,DataA1=0))  # 0 = off until the chase detection is fixed (700 when on)
for _code,_u in UNITS.items():
    if _u['speed']>0 and _u.get('damage') and not _u.get('flying') and 'Fcap' not in _u['ability']:
        _u['ability']=','.join(filter(None,[_u['ability'],'Flsh']))
