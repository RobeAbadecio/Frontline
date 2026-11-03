"""Emberfield skirmish balance. Amber and Azure use this same original roster."""
UNITS={
'ewrk':dict(name='Surveyor',hp=180,cost=40,speed=250,time=7,collision=15,food=1,damage=5,model='surveyor',ability='Ahar,Arep,AHbu',builds='ehub,efab,ehom,etwr,esnc,eaer,ewsp',hotkey='W'),
'egrd':dict(name='Ember Guard',hp=300,cost=65,speed=270,time=10,collision=20,food=2,damage=19,model='guard',ability='',slot=(0,0),hotkey='G'),
'ebow':dict(name='Trailbow',hp=230,cost=85,wood=15,speed=285,time=12,collision=18,food=2,damage=14,range=650,cool=1.3,attack='pierce',targets='ground,air,structure',model='ranger',ability='',slot=(1,0),hotkey='B'),
'ewng':dict(name='Skylark',hp=280,cost=135,wood=35,speed=330,time=18,collision=24,food=3,damage=18,range=500,cool=1.5,attack='pierce',targets='ground,air,structure',flying=True,model='skylark',ability='',slot=(0,0),hotkey='Y'),
'eram':dict(name='Stonecaster',hp=620,cost=170,wood=50,speed=180,time=22,collision=30,food=4,damage=46,range=850,cool=2.8,attack='siege',targets='ground,structure',armor=3,model='siege',ability='',slot=(0,0),classification='mechanical',hotkey='T'),
'emed':dict(name='Mender',hp=220,cost=100,wood=20,speed=270,time=15,collision=17,food=2,damage=7,range=450,cool=1.8,attack='magic',targets='ground,air',mana=220,regen=1.1,model='mender',ability='Ahea',slot=(0,0),hotkey='M'),
'Ewar':dict(name='Ember Marshal',hp=650,cost=250,wood=40,speed=285,time=28,collision=25,food=5,damage=22,armor=2,mana=280,regen=1,hero='AHtb,AHtc,AHad',strength=22,agility=14,intelligence=15,primary='STR',model='marshal',ability='',slot=(1,0),hotkey='H'),
'Esee':dict(name='Dawn Seer',hp=480,cost=250,wood=40,speed=280,time=28,collision=21,food=5,damage=15,range=550,cool=1.7,attack='magic',targets='ground,air',mana=400,regen=1.3,hero='AHhb,AHbz,AHab',strength=14,agility=14,intelligence=23,primary='INT',model='seer',ability='',slot=(2,0),hotkey='S'),
'ehub':dict(name='Beacon',hp=1600,cost=250,speed=0,time=25,collision=80,supply=30,model='beacon',ability='Argl',trains='ewrk',slot=(0,0),hotkey='B'),
'efab':dict(name='Forge',hp=850,cost=150,speed=0,time=18,collision=65,model='forge',ability='',trains='egrd,ebow',slot=(1,0),hotkey='F'),
'ehom':dict(name='Supply Pylon',hp=500,cost=60,speed=0,time=12,collision=40,supply=12,model='pylon',ability='',slot=(2,0),hotkey='P'),
'etwr':dict(name='Watchtower',hp=700,cost=120,wood=30,speed=0,time=20,collision=38,damage=22,range=750,cool=1.4,attack='pierce',targets='ground,air,structure',armor=3,model='tower',ability='',upgrade='ebst',slot=(3,0),hotkey='T'),
'ebst':dict(name='Bastion',hp=1100,cost=260,wood=70,speed=0,time=24,collision=38,damage=36,range=850,cool=1.2,attack='pierce',targets='ground,air,structure',armor=5,model='bastion',ability='',slot=(0,1),hotkey='U'),
'esnc':dict(name='Sanctum',hp=800,cost=170,wood=40,speed=0,time=22,collision=60,model='sanctum',ability='',trains='emed,Ewar,Esee',slot=(0,1),hotkey='S'),
'eaer':dict(name='Sky Roost',hp=750,cost=160,wood=40,speed=0,time=22,collision=60,model='roost',ability='',trains='ewng',slot=(1,1),hotkey='R'),
'ewsp':dict(name='Workshop',hp=900,cost=170,wood=40,speed=0,time=22,collision=65,model='workshop',ability='',trains='eram',slot=(2,1),hotkey='W'),
'eore':dict(name='Ore Seam',hp=100000,cost=0,speed=0,time=0,collision=80,model='ore',ability='Agld'),
}

# Existing native ability implementations, original names, costs and tuning.
SPELLS=[
 dict(alias='AHtb',code='AHtb',levels=3,hero=1,reqLevel=1,levelSkip=2,Cost1=60,Cost2=70,Cost3=80,Cool1=8,Cool2=8,Cool3=8,Rng1=600,Rng2=600,Rng3=600,DataA1=90,DataA2=150,DataA3=210,Dur1=1.5,Dur2=2,Dur3=2.5,HeroDur1=1,HeroDur2=1.2,HeroDur3=1.5,targs1='ground,air,enemy'),
 dict(alias='AHtc',code='AHtc',levels=3,hero=1,reqLevel=1,levelSkip=2,Cost1=80,Cost2=90,Cost3=100,Cool1=12,Cool2=12,Cool3=12,Area1=250,Area2=275,Area3=300,DataA1=60,DataA2=100,DataA3=140,DataB1=.2,DataB2=.25,DataB3=.3,DataC1=.2,DataC2=.25,DataC3=.3,Dur1=3,Dur2=3,Dur3=3,targs1='ground,enemy'),
 dict(alias='AHad',code='AHad',levels=3,hero=1,reqLevel=1,levelSkip=2,Area1=700,Area2=700,Area3=700,DataA1=1,DataA2=2,DataA3=3,targs1='ground,air,friend'),
 dict(alias='AHhb',code='AHhb',levels=3,hero=1,reqLevel=1,levelSkip=2,Cost1=50,Cost2=60,Cost3=70,Cool1=6,Cool2=6,Cool3=6,Rng1=650,Rng2=650,Rng3=650,DataA1=140,DataA2=220,DataA3=300,targs1='ground,air,friend'),
 dict(alias='AHbz',code='AHbz',levels=3,hero=1,reqLevel=1,levelSkip=2,Cost1=90,Cost2=100,Cost3=110,Cool1=12,Cool2=12,Cool3=12,Rng1=650,Rng2=650,Rng3=650,Area1=220,Area2=250,Area3=280,DataA1=3,DataA2=4,DataA3=5,DataB1=25,DataB2=30,DataB3=35,DataC1=6,DataC2=6,DataC3=6,DataD1=.6,DataD2=.6,DataD3=.6,targs1='ground,air,enemy'),
 dict(alias='AHab',code='AHab',levels=3,hero=1,reqLevel=1,levelSkip=2,Area1=700,Area2=700,Area3=700,DataA1=.5,DataA2=.9,DataA3=1.3,DataB1=0,DataB2=0,DataB3=0,targs1='ground,air,friend'),
 dict(alias='Ahea',code='Ahea',levels=1,Cost1=5,Cool1=1,Rng1=600,DataA1=20,targs1='ground,air,friend,organic'),
]
SPELL_UI=[('AHtb','Ember Bolt','T','spell',0,2),('AHtc','Quake Pulse','C','attack',1,2),('AHad','Iron Resolve','D','hold',2,2),('AHhb','Dawn Mend','H','repair',0,2),('AHbz','Shardfall','B','spell',1,2),('AHab','Clear Mind','R','supply',2,2),('Ahea','Mend','E','repair',0,2),('CmdSelectSkill','Learn Ability','K','upgrade',3,2)]

for spell in SPELLS:
    for rank in range(2,spell['levels']+1):
        spell.setdefault(f'targs{rank}',spell.get('targs1',''))
