#!/usr/bin/env python3
"""Generate original Emberfield content using Pillow and the bundled licensed font."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import subprocess
import wave
import zlib
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import art
import models
import ui
from catalog import UNITS, SPELLS, SPELL_UI

P = lambda fmt, *v: struct.pack('<' + fmt, *v)
S = lambda s, n: s.encode()[:n].ljust(n, b'\0')


def write(root, name, data):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data if isinstance(data, bytes) else data.encode())


def slk(rows, key):
    columns = [key] + sorted({k for r in rows for k in r if k != key})
    out = ['ID;PWXL;N;E', f'B;X{len(columns)};Y{len(rows)+1};D0']
    for y, row in enumerate([dict(zip(columns, columns))] + rows, 1):
        for x, col in enumerate(columns, 1):
            if col in row:
                value = str(row[col]).replace('"', '')
                out.append(f'C;X{x};Y{y};K"{value}"')
    return '\n'.join(out + ['E', ''])


def blp(width, height, pixels):
    # BLP2 BGRA8 with one mip; the engine supports uncompressed originals.
    offset = 148
    header = b'BLP2' + P('I4B2I', 1, 3, 8, 0, 0, width, height)
    header += P('16I', offset, *([0]*15)) + P('16I', len(pixels), *([0]*15))
    return header + bytes(pixels)


def texture(width, height, rgb, grid=False):
    data = bytearray()
    for y in range(height):
        for x in range(width):
            noise = ((x*37 + y*71 + x*y*3) % 13 - 6)
            shade = 0.73 if grid and (x % 64 < 2 or y % 64 < 2) else 1
            r,g,b = [max(0, min(255, int(c*shade)+noise)) for c in rgb]
            data += bytes([b,g,r,255])
    return blp(width, height, data)


def game_data(root, units=UNITS, spells=SPELLS, spell_ui=SPELL_UI):
    rows={k:[] for k in ['UnitData','UnitBalance','UnitUI','UnitWeapons','UnitAbilities']}
    profiles=''
    for code,u in units.items():
        building=u['speed']==0
        flying=u.get('flying',False)
        damage=u.get('damage',0)
        rows['UnitData'].append(dict(unitID=code,race='human' if code!='eore' else 'creeps',movetp=u.get('movement','fly' if flying else 'foot' if not building else ''),moveHeight=u.get('height',180 if flying else 0),moveFloor=0,targType='air' if flying else 'ground,structure' if building else 'ground',type=u.get('classification','peon' if code=='ewrk' else ''),propWin=60,turnRate=u.get('turnrate',1),death=1,deathType=3,requireWaterRadius=u.get('water',0),pathTex=u.get('pathtex','')))
        rows['UnitBalance'].append(dict(unitBalanceID=code,realHP=u['hp'],HP=u['hp'],spd=u['speed'],goldcost=u['cost'],lumbercost=u.get('wood',0),bldtm=u['time'],collision=u['collision'],fused=u.get('food',0),fmade=u.get('supply',0),defType=u.get('defense','fort' if building else 'large' if code=='eram' else 'normal'),realdef=u.get('armor',0),sight=u.get('sight',1400),nsight=u.get('sight',1400),level=1,STR=u.get('strength',0),AGI=u.get('agility',0),INT=u.get('intelligence',0),STRplus=2,AGIplus=1,INTplus=2,Primary=u.get('primary','STR'),manaN=u.get('mana',0),realM=u.get('mana',0),mana0=u.get('mana',0),regenMana=u.get('regen',0),regenHP=u.get('regenHP',.3),regenType='always'))
        rows['UnitUI'].append(dict(unitUIID=code,file=f'Emberfield\\Models\\{u["model"]}.mdx',isbldg=int(building),modelScale=1,unitSound=u.get('voice','Ember'),unitShadow='Shadow',shadowW=220 if building else 80,shadowH=190 if building else 80,shadowX=110 if building else 40,shadowY=95 if building else 40,scale=max(.6,u['collision']/45),name=u['name'],armor='Metal',weap1=int(damage>0),weap2=0,walk=270,run=270))
        ranged=u.get('range',100)>150
        rows['UnitWeapons'].append(dict(unitWeaponID=code,acquire=u.get('acquire',max(700,u.get('range',100))),atkType1=u.get('attack','normal'),dice1=1 if damage else 0,sides1=2 if damage else 0,dmgplus1=damage,dmgpt1=.2,backSw1=.2,cool1=u.get('cool',1),rangeN1=u.get('range',100 if damage else 0),weapTp1='missile' if ranged else 'normal',targs1=u.get('targets','ground,structure'),weapsOn=int(damage>0),weapType1=u.get('sound',''),launchX=u.get('launchx',0),launchY=u.get('launchy',0),launchZ=u.get('launchz',0)))
        rows['UnitAbilities'].append(dict(unitAbilID=code,abilList=u['ability'],heroAbilList=u.get('hero','')))
        x,y=u.get('slot',(0,0))
        profiles+=f'[{code}]\nName={u["name"]}\nPropernames={u["name"]}\nTip={u["name"]}\nUbertip={u.get("description",u["name"]+" - Emberfield")}\nArt=Emberfield\\Icons\\{u["model"]}.blp\nButtonpos={x},{y}\nHotkey={u.get("hotkey", "")}\n'
        if ranged:profiles+=f"Missileart=Emberfield\\Models\\{u.get('missile','bolt')}.mdx\nMissilespeed={u.get('mspeed',950)}\nMissilearc={u.get('arc',0.15)}\nMissileHoming=1\n"
        for field in ['trains','builds','upgrade','requires']:
            if field in u:profiles+=field.capitalize()+'='+u[field]+'\n'
        if 'buildsound' in u:profiles+=f"BuildingSoundLabel={u['buildsound']}\n"
        profiles+='\n'
    for name,rs in rows.items():write(root,f'Units/{name}.slk',slk(rs,next(iter(rs[0]))))
    write(root,'Units/HumanUnitFunc.txt',profiles)
    write(root,'Units/HumanUnitStrings.txt',profiles)
    abilities=[dict(alias='Ahar',code='Ahar',levels=1,DataA1=5,DataB1=20,DataC1=10,Dur1=1,Rng1=96,Area1=650,targs1='tree,ground'),dict(alias='Arep',code='Arep',levels=1,DataA1=1,DataB1=1,DataC1=1,DataD1=1.5,Rng1=96,targs1='structure,friend'),dict(alias='AHbu',code='AHbu',levels=1),dict(alias='Agld',code='Agld',levels=1,DataA1=30000,DataB1=1,DataC1=4),dict(alias='Argl',code='Argl',levels=1)]
    abilities=[row for row in abilities if row['alias'] not in {s['alias'] for s in spells}]+spells
    write(root,'Units/AbilityData.slk',slk(abilities,'alias'))
    write(root,'Units/DestructableData.slk',slk([dict(DestructableID='epin',Name='Timber Pine',file='Emberfield\\Models\\pine.mdx',HP=250,targType='tree',armor='Wood',numVar=0,selSize=90,minScale=1,maxScale=1,radius=32,fogVis=1)],'DestructableID'))
    commands=''
    for code,label,key,symbol,x,y in [('CmdMove','Move','M','move',0,0),('CmdAttack','Attack','A','attack',3,0),('CmdStop','Stop','S','stop',1,0),('CmdHoldPos','Hold Position','H','hold',2,0),('CmdPatrol','Patrol','P','patrol',0,1),('CmdBuild','Build','B','build',0,2),('CmdBuildHuman','Build','B','build',0,2),('CmdCancel','Cancel','X','cancel',3,2),('AHbu','Build','B','build',0,2),('Ahar','Gather','G','gather',2,1),('Arep','Repair','R','repair',1,1)]+spell_ui:
        commands+=f'[{code}]\nArt=Emberfield\\Icons\\{symbol}.blp\nTip={label}\nUbertip={label}\nHotkey={key}\nButtonpos={x},{y}\nResearchArt=Emberfield\\Icons\\{symbol}.blp\nResearchtip=Learn {label}\nResearchubertip=Improve {label}.\nResearchhotkey={key}\nResearchbuttonpos={x},{y}\nMissileart=Emberfield\\Models\\bolt.mdx\nMissilespeed=1000\n\n'
    write(root,'Units/CommandFunc.txt',commands)
    write(root,'Units/CommandStrings.txt',commands)
    write(root,'Units/HumanAbilityFunc.txt',commands)
    write(root,'Units/HumanAbilityStrings.txt',commands)
    write(root,'TerrainArt/Terrain.slk',slk([dict(terrainID='Egrs',dir='Emberfield\\Terrain',file='grass')],'terrainID'))
    write(root,'TerrainArt/CliffTypes.slk',slk([dict(cliffID='Eclf',texDir='Emberfield\\Terrain',texFile='grass')],'cliffID'))
    write(root,'TerrainArt/Water.slk',slk([dict(waterID='LSha',height=0)],'waterID'))
    write(root,'UI/MiscData.txt','[Misc]\nGoldMineMaxGold=30000\nGoldMineMaxMiners=4\nGoldMineMiningDuration=1\nGoldMineGoldPerInterval=10\nFoodCeiling=100\nDayLength=600\nDayHours=24\n')


def ui_data(root):
    base='Emberfield\\Textures\\'
    skin='[Default]\nMasterFont=Emberfield\\Fonts\\pixel.ttf\n'
    for k in ['GoldIcon','LumberIcon','SupplyIcon','ToolTipGoldIcon','ToolTipLumberIcon','ToolTipSupplyIcon','ToolTipManaIcon','MinimapHeroTexture','MinimapResourceTexture','MinimapEntangledResourceTexture','MinimapHauntedResourceTexture','MinimapNeutralTexture','CommandButtonDisabledArtPath']:
        skin+=k+'='+base+'gold.blp\n'
    for i in range(1,7):skin+=f'ConsoleTexture0{i}={base}panel.blp\n'
    for k in ['SimpleManaBarConsoleSmall','SimpleHpBarConsoleSmall','SimpleHpBarConsole','SimpleManaBarConsole','ConsoleInventoryCoverTexture','ToolTipBorder','ToolTipBackground']:
        skin+=k+'='+base+'panel.blp\n'
    write(root,'UI/war3skins.txt',skin)
    write(root,'UI/FrameDef/GlobalStrings.fdf','StringList { GOLD "Ore", LUMBER "Timber", FOOD "Supply", UPKEEP_NONE "Emberfield", }\n')
    write(root,'UI/FrameDef/UI/ConsoleUI.fdf','''Frame "SIMPLEFRAME" "ConsoleUI" {
        Texture { File "Emberfield\\Textures\\panel.blp", Width 0.8, Height 0.15, Anchor BOTTOMLEFT,0,0, }
        Texture { File "Emberfield\\Textures\\panel.blp", Width 0.8, Height 0.035, Anchor TOPLEFT,0,0, }
    }''')
    resource='Frame "SIMPLEFRAME" "ResourceBarFrame" { Width 0.39, Height 0.035,\n'
    for i,name in enumerate(['Gold','Lumber','Supply','Upkeep']):
        resource+=f'String "ResourceBar{name}Text" {{ Font "MasterFont",0.013, Width 0.09, Height 0.03, Anchor TOPLEFT,{i*0.095},0, Text "{name}", }}\n'
    write(root,'UI/FrameDef/UI/ResourceBar.fdf',resource+'}')
    write(root,'UI/FrameDef/Glue/StandardTemplates.fdf','// Emberfield defines its frames directly.\n')
    def text(name):
        return f'Frame "TEXT" "{name}" {{ Font "MasterFont",0.013, Width 0.3, Height 0.025, }}'
    custom='Frame "FRAME" "LoadingCustomPanel" {'+''.join(text(n) for n in ['LoadingTitleText','LoadingSubtitleText','LoadingText'])+'}'
    melee='Frame "FRAME" "LoadingMeleePanel" {'+''.join(text(n) for n in ['MinimapImage','LoadingMeleeMapName','LoadingMeleeGameTypeLabel','LoadingMeleeGameTypeValue'])+'Frame "FRAME" "LoadingMeleePlayerContainer" { Width 0.25, }}'
    loading='Frame "FRAME" "Loading" { Width 0.8, Height 0.6, Frame "FRAME" "LoadingBackground" {} Frame "FRAME" "LoadingBar" {'+text('LoadingBarText')+'}'+custom+melee+'}'
    slot='Frame "FRAME" "LoadingPlayerSlot" { Width 0.25, Height 0.03, Frame "FRAME" "LoadingPlayerSlotReadyHighlight" {} Frame "FRAME" "LoadingPlayerSlotBackdrop" {'+''.join(text(n) for n in ['LoadingPlayerSlotLevel','LoadingPlayerSlotName','LoadingPlayerSlotRace'])+'}}'
    write(root,'UI/FrameDef/Glue/Loading.fdf',loading+slot)
    result='Frame "DIALOG" "GameResultDialog" { Width 0.34, Height 0.25, Frame "BACKDROP" "GameResultBackdrop" { SetAllPoints, BackdropBackground "Emberfield\\Textures\\panel.blp", }'+text('GameResultText')
    for i,name in enumerate(['Continue','Restart','Quit']):
        result+=f'Frame "GLUETEXTBUTTON" "GameResult{name}Button" {{ Width 0.26, Height 0.04, Anchor TOPLEFT,0.04,{-0.07-i*0.055}, '+text(f'GameResult{name}ButtonText')+'}'
    write(root,'UI/FrameDef/UI/GameResultDialog.fdf',result+'}')
    # Upper bar is deliberately absent: no unimplemented retail menu buttons.
    write(root,'UI/FrameDef/UI/UpperButtonBar.fdf','// Emberfield starts directly in its match.\n')


def map_data(directory):
    info=P('3I',18,1,1)
    for t in ['Emberfield - First Light','Original OpenRealm content','Destroy the opposing Beacon. Gather ore and train guards.','2']:info+=t.encode()+b'\0'
    info+=P('8f4i2IIcI',-2560,-2560,-2560,2560,2560,2560,2560,-2560,4,4,4,4,40,40,0x40,b'L',0xffffffff)
    info+=b'\0'*3+P('I',0)+b'\0'*3+P('I',2)
    for number in range(2):
        info+=P('4I',number,number+1,1,1)+f'{"Amber" if number==0 else "Azure"} Expedition'.encode()+b'\0'
        info+=P('2f2I',-1500+3000*number,0,0,0)
    info+=P('I',2)
    for i in range(2):info+=P('2I',0,1<<i)+f'Expedition {i+1}'.encode()+b'\0'
    info+=P('4I',0,0,0,0)
    write(directory,'war3map.w3i',info)
    terrain=b'W3E!'+P('IcI',11,b'L',0)+P('I',1)+b'Egrs'+P('I',0)+P('2I2f',97,97,-6144,-6144)
    for y in range(97):
        for x in range(97):terrain+=P('2H3B',8192,8192,0,(x*7+y*11)%16,2)
    write(directory,'war3map.w3e',terrain)
    write(directory,'war3map.wpm',b'MP3W'+P('3I',0,384,384)+bytes(384*384))
    write(directory,'war3map.doo',b'W3do'+P('5I',8,11,0,0,0))
    write(directory,'war3mapUnits.doo',b'W3do'+P('3I',8,11,0))
    write(directory,'war3map.j',MAP_SCRIPT)


COMMON = '''type agent extends handle
type player extends agent
type widget extends agent
type unit extends widget
type destructable extends widget
type group extends agent
type boolexpr extends agent
type timer extends agent
type playerstate extends handle
type playergameresult extends handle
type camerafield extends handle
type alliancetype extends handle
native Player takes integer i returns player
native CreateUnit takes player p, integer id, real x, real y, real face returns unit
native SetPlayerState takes player p, playerstate s, integer v returns nothing
native GetPlayerState takes player p, playerstate s returns integer
native ConvertPlayerState takes integer i returns playerstate
native GetWidgetLife takes widget w returns real
native GetUnitX takes unit u returns real
native GetUnitY takes unit u returns real
native CreateDestructable takes integer id, real x, real y, real face, real scale, integer variation returns destructable
native SelectHeroSkill takes unit u, integer ability returns nothing
native GetUnitTypeId takes unit u returns integer
native GroupEnumUnitsOfPlayer takes group g, player p, boolexpr filter returns nothing
native GroupEnumUnitsInRange takes group g, real x, real y, real radius, boolexpr filter returns nothing
native CreateGroup takes nothing returns group
native FirstOfGroup takes group g returns unit
native GroupRemoveUnit takes group g, unit u returns nothing
native DestroyGroup takes group g returns nothing
native IsUnitEnemy takes unit u, player p returns boolean
native IsUnitAlly takes unit u, player p returns boolean
native IssueImmediateOrder takes unit u, string order returns boolean
native SetResourceAmount takes unit u, integer amount returns nothing
native IssueTargetOrder takes unit u, string order, widget target returns boolean
native IssuePointOrder takes unit u, string order, real x, real y returns boolean
native CreateTimer takes nothing returns timer
native TimerStart takes timer t, real timeout, boolean periodic, code callback returns nothing
native FogEnable takes boolean v returns nothing
native FogMaskEnable takes boolean v returns nothing
native SetCameraPosition takes real x, real y returns nothing
native PanCameraToTimed takes real x, real y, real duration returns nothing
native DisplayTimedTextToPlayer takes player p, real x, real y, real duration, string text returns nothing
native RemovePlayer takes player p, playergameresult r returns nothing
native ConvertPlayerGameResult takes integer i returns playergameresult
native StartMeleeAI takes player p, string script returns nothing
native I2R takes integer i returns real
native I2S takes integer i returns string
'''
AI_NATIVE = '''native GetAiPlayer takes nothing returns integer
native SetMeleeAI takes nothing returns nothing
native SetProduce takes integer qty, integer id, integer town returns boolean
native ClearHarvestAI takes nothing returns nothing
native HarvestGold takes integer town, integer qty returns nothing
native CreateCaptains takes nothing returns nothing
native InitAssault takes nothing returns nothing
native AddAssault takes integer qty, integer id returns boolean
native SuicidePlayer takes player p, boolean check returns boolean
native Sleep takes real seconds returns nothing
native HarvestWood takes integer town, integer qty returns nothing
native SetHeroLevels takes code callback returns nothing
native GetHeroId takes nothing returns integer
native GetHeroLevelAI takes nothing returns integer
native GetUnitCountDone takes integer id returns integer
native GetUnitCount takes integer id returns integer
'''
AI_SCRIPT = '''function hero_levels takes nothing returns integer
    local integer n = GetHeroLevelAI()
    if GetHeroId() == 'Ewar' then
        if n == 1 or n == 4 or n >= 7 then
            return 'AHtb'
        elseif n == 2 or n == 5 then
            return 'AHad'
        endif
        return 'AHtc'
    endif
    if n == 1 or n == 4 or n >= 7 then
        return 'AHhb'
    elseif n == 2 or n == 5 then
        return 'AHab'
    endif
    return 'AHbz'
endfunction
function main takes nothing returns nothing
    local integer ticks = 0
    call SetMeleeAI()
    call SetHeroLevels(function hero_levels)
    call CreateCaptains()
    loop
        call ClearHarvestAI()
        call HarvestGold(0, 4)
        call HarvestWood(0, 1)
        if GetUnitCount('etwr') < 2 then
            call SetProduce(1, 'etwr', 0)
        elseif GetUnitCount('esnc') < 1 then
            call SetProduce(1, 'esnc', 0)
        elseif GetUnitCount('ewsp') < 1 then
            call SetProduce(1, 'ewsp', 0)
        elseif GetUnitCount('eaer') < 1 then
            call SetProduce(1, 'eaer', 0)
        elseif GetUnitCount('ehom') < 1 then
            call SetProduce(1, 'ehom', 0)
        endif
        if GetUnitCount('etwr') >= 2 and GetUnitCount('esnc') >= 1 and GetUnitCount('ewsp') >= 1 and GetUnitCount('eaer') >= 1 then
            if GetUnitCount('ewrk') < 5 then
                call SetProduce(1, 'ewrk', 0)
            endif
            if GetUnitCount('emed') < 1 then
                call SetProduce(1, 'emed', 0)
            endif
            if GetUnitCount('eram') < 1 then
                call SetProduce(1, 'eram', 0)
            endif
            if GetUnitCount('ewng') < 1 then
                call SetProduce(1, 'ewng', 0)
            endif
            if GetUnitCount('Esee') < 1 then
                call SetProduce(1, 'Esee', 0)
            endif
            if GetUnitCount('ebow') < 3 then
                call SetProduce(1, 'ebow', 0)
            endif
            if GetUnitCount('egrd') < 6 then
                call SetProduce(1, 'egrd', 0)
            endif
        endif
        set ticks = ticks + 1
        if ticks >= 60 then
            call InitAssault()
            call AddAssault(6, 'egrd')
            call AddAssault(3, 'ebow')
            call AddAssault(1, 'emed')
            call AddAssault(1, 'eram')
            call AddAssault(1, 'ewng')
            call AddAssault(1, 'Ewar')
            call AddAssault(1, 'Esee')
            call SuicidePlayer(Player(1 - GetAiPlayer()), false)
            set ticks = 0
        endif
        call Sleep(2.0)
    endloop
endfunction
'''

MAP_SCRIPT = '''globals
    unit amberBase
    unit azureBase
    unit amberHero
    unit azureHero
    integer elapsed = 0
    boolean finished = false
endglobals
function config takes nothing returns nothing
endfunction
function BotTactics takes nothing returns nothing
    local group army = CreateGroup()
    local group nearby = CreateGroup()
    local unit actor
    local unit other
    local unit enemy
    local integer id
    call GroupEnumUnitsOfPlayer(army, Player(1), null)
    loop
        set actor = FirstOfGroup(army)
        exitwhen actor == null
        call GroupRemoveUnit(army, actor)
        set id = GetUnitTypeId(actor)
        if GetWidgetLife(actor) > 0.0 then
            if id == 'emed' then
                call IssueImmediateOrder(actor, "healon")
                if GetWidgetLife(azureHero) > 0.0 and GetWidgetLife(azureHero) < 600.0 then
                    call IssueTargetOrder(actor, "heal", azureHero)
                endif
            elseif id == 'Ewar' or id == 'Esee' then
                set enemy = null
                call GroupEnumUnitsInRange(nearby, GetUnitX(actor), GetUnitY(actor), 600.0, null)
                loop
                    set other = FirstOfGroup(nearby)
                    exitwhen other == null
                    call GroupRemoveUnit(nearby, other)
                    if IsUnitEnemy(other, Player(1)) and GetWidgetLife(other) > 0.0 then
                        set enemy = other
                    endif
                endloop
                if enemy != null then
                    if id == 'Ewar' then
                        call IssueTargetOrder(actor, "thunderbolt", enemy)
                    else
                        call IssuePointOrder(actor, "blizzard", GetUnitX(enemy), GetUnitY(enemy))
                    endif
                endif
                if id == 'Esee' and GetWidgetLife(azureHero) > 0.0 and GetWidgetLife(azureHero) < 500.0 then
                    call IssueTargetOrder(actor, "holybolt", azureHero)
                endif
            endif
        endif
    endloop
    call DestroyGroup(army)
    call DestroyGroup(nearby)
endfunction
function Tick takes nothing returns nothing
    if finished then
        return
    endif
    set elapsed = elapsed + 2
    call BotTactics()
    if GetWidgetLife(azureBase) <= 0.0 then
        set finished = true
        call DisplayTimedTextToPlayer(Player(0), 0.15, 0.2, 300.0, "VICTORY - Azure Beacon destroyed.")
        call RemovePlayer(Player(1), ConvertPlayerGameResult(1))
        call RemovePlayer(Player(0), ConvertPlayerGameResult(0))
    elseif GetWidgetLife(amberBase) <= 0.0 then
        set finished = true
        call DisplayTimedTextToPlayer(Player(0), 0.15, 0.2, 300.0, "DEFEAT - Amber Beacon destroyed.")
        call RemovePlayer(Player(0), ConvertPlayerGameResult(1))
    endif
endfunction
function main takes nothing returns nothing
    local integer i = 0
    local unit ore
    local unit worker
    local unit hero
    local destructable tree
    local integer j = 0
    call FogEnable(false)
    call FogMaskEnable(false)
    call SetPlayerState(Player(0), ConvertPlayerState(1), 800)
    call SetPlayerState(Player(1), ConvertPlayerState(1), 800)
    set amberBase = CreateUnit(Player(0), 'ehub', -1500.0, 0.0, 0.0)
    set azureBase = CreateUnit(Player(1), 'ehub', 1500.0, 0.0, 180.0)
    call CreateUnit(Player(0), 'efab', -1500.0, -420.0, 0.0)
    call CreateUnit(Player(1), 'efab', 1500.0, -420.0, 180.0)
    call SetPlayerState(Player(0), ConvertPlayerState(2), 320)
    call SetPlayerState(Player(1), ConvertPlayerState(2), 320)
    loop
        exitwhen i >= 2
        set ore = CreateUnit(Player(15), 'eore', -2050.0 + 4100.0*i, 250.0, 0.0)
        call SetResourceAmount(ore, 30000)
        call SetPlayerState(Player(i), ConvertPlayerState(4), 40)
        set worker = CreateUnit(Player(i), 'ewrk', -1750.0 + 3500.0*i, 150.0, 0.0)
        call IssueTargetOrder(worker, "harvest", ore)
        set worker = CreateUnit(Player(i), 'ewrk', -1750.0 + 3500.0*i, 0.0, 0.0)
        call IssueTargetOrder(worker, "harvest", ore)
        set worker = CreateUnit(Player(i), 'ewrk', -1750.0 + 3500.0*i, -150.0, 0.0)
        call IssueTargetOrder(worker, "harvest", ore)
        call CreateUnit(Player(i), 'egrd', -1100.0 + 2200.0*i, -100.0, 0.0)
        call CreateUnit(Player(i), 'egrd', -1100.0 + 2200.0*i, 100.0, 0.0)
        call CreateUnit(Player(i), 'egrd', -1100.0 + 2200.0*i, 300.0, 0.0)
        set hero = CreateUnit(Player(i), 'Ewar', -1350.0 + 2700.0*i, 450.0, 0.0)
        call SelectHeroSkill(hero, 'AHtb')
        if i == 0 then
            set amberHero = hero
        else
            set azureHero = hero
        endif
        call CreateUnit(Player(i), 'etwr', -1050.0 + 2100.0*i, -350.0, 0.0)
        set j = 0
        loop
            exitwhen j >= 10
            set tree = CreateDestructable('epin', -2450.0 + 4420.0*i + 120.0*I2R(j - (j/5)*5), 600.0 + 160.0*I2R(j/5), 0.0, 1.0, 0)
            set j = j + 1
        endloop
        set worker = CreateUnit(Player(i), 'ewrk', -2200.0 + 4400.0*i, 400.0, 0.0)
        call IssueTargetOrder(worker, "harvest", tree)
        set i = i + 1
    endloop
    call SetCameraPosition(-1350.0, -100.0)
    call DisplayTimedTextToPlayer(Player(0), 0.17, 0.035, 9.0, "EMBERFIELD | Destroy the blue Beacon to the east.|nTap to select. Two-finger tap to order. Pinch to zoom.")
    call StartMeleeAI(Player(1), "Scripts\\ember.ai")
    call TimerStart(CreateTimer(), 2.0, true, function Tick)
endfunction
'''


def generate(out, repo, content=None):
    out.mkdir(parents=True,exist_ok=True)
    root=out/'content'
    if root.exists():shutil.rmtree(root)
    root.mkdir(parents=True)
    if content: content.game_data(root)
    else: game_data(root)
    ui_data(root);ui.write(root);ui.simple_info(root)
    for target in ['Emberfield/Fonts/ui.ttf','Fonts/FRIZQT__.TTF']:
        write(root,target,(art.ASSETS/'fonts/DejaVuSans.ttf').read_bytes())
    write(root,'Emberfield/Fonts/LICENSE_DEJAVU.txt',(art.ASSETS/'fonts/LICENSE_DEJAVU').read_bytes())
    for name,key in [('Units/UpgradeData.slk','upgradeid'),('Units/ItemData.slk','itemID'),('Doodads/Doodads.slk','doodID'),('Splats/UberSplatData.slk','splatID'),('UI/SoundInfo/UnitAckSounds.slk','SoundName'),('UI/SoundInfo/UnitCombatSounds.slk','SoundName'),('UI/SoundInfo/UISounds.slk','SoundName')]:
        write(root,name,slk([],key))
    write(root,'Scripts/common.j',COMMON + (content.COMMON if content else ''))
    write(root,'Scripts/Blizzard.j','// Original game: all match logic is in the map.\n')
    write(root,'Scripts/common.ai',AI_NATIVE)
    write(root,'Scripts/ember.ai',content.AI_SCRIPT if content else AI_SCRIPT)
    colors={'steel':(111,160,175),'gold':(233,155,60),'panel':(18,29,39),'earth':(56,82,66),'ore':(94,172,203)}
    for name,color in colors.items():write(root,f'Emberfield/Textures/{name}.blp',texture(64,64,color))
    write(root,'Emberfield/Terrain/grass.blp',texture(512,256,colors['earth'],True))
    write(root,'Emberfield/Terrain/grass.blp',art.blp_bytes(art.terrain(),True))
    write(root,'Emberfield/Textures/materials.blp',art.blp_bytes(art.material_atlas(),True))
    for name in models.GEOMETRY:
        # The shared bolt vanishes in Death, so a projectile impact effect is invisible here.
        write(root,f'Emberfield/Models/{name}.mdx',models.mesh(name,scale=[(0,1),(2999,1),(3000,0),(3999,0),(4000,1)] if name=='bolt' else None))
    symbols=['move','attack','stop','hold','patrol','build','cancel','gather','repair','upgrade','spell','inventory','group','camera','supply','timber']+[name for name in models.GEOMETRY if name not in ['pine','bolt']]
    for name in symbols:
        for disabled in (False,True):
            path=f'Emberfield/Icons/{"Disabled/DIS" if disabled else ""}{name}.blp'
            write(root,path,art.blp_bytes(art.icon(name,disabled)))
    for file,size,kind in [('hud',(1600,300),'hud'),('top',(1600,76),'panel'),('dialog',(660,600),'panel'),('button',(520,82),'panel')]:
        write(root,f'Emberfield/Textures/{file}.blp',art.blp_bytes(art.panel(*size,kind)))
    from PIL import Image,ImageDraw,ImageEnhance
    write(root,'Emberfield/Textures/button-pressed.blp',art.blp_bytes(ImageEnhance.Brightness(art.panel(520,82)).enhance(.6)))
    bar=Image.new('RGBA',(128,16),(255,255,255,255))
    write(root,'Emberfield/Textures/bar.blp',art.blp_bytes(bar))
    border=Image.new('RGBA',(128,16));ImageDraw.Draw(border).rectangle((0,0,127,15),outline=(175,145,91,255),width=1)
    write(root,'Emberfield/Textures/bar-border.blp',art.blp_bytes(border))
    cover=Image.new('RGBA',(32,32))
    write(root,'Emberfield/Textures/inventory-cover.blp',art.blp_bytes(cover))
    shadow=Image.new('RGBA',(128,128));pixels=shadow.load()
    for y in range(128):
        for x in range(128):
            r=math.hypot((x-63.5)/60,(y-63.5)/60)
            pixels[x,y]=(0,0,0,int(max(0,1-r)**1.5*100))
    write(root,'ReplaceableTextures/Shadows/Shadow.blp',art.blp_bytes(shadow))
    for i in range(16):
        color=(235,157,55) if i==0 else (65,168,222) if i==1 else (150,150,150)
        for folder in ['TeamColor','TeamGlow']:
            write(root,f'ReplaceableTextures/{folder}/{folder}{i:02}.blp',texture(32,32,color))
    ring=bytearray()
    for y in range(64):
        for x in range(64):
            distance=math.hypot(x-31.5,y-31.5)
            ring+=bytes([255,255,255,230 if 26<distance<30 else 0])
    for name in ['Small','Med','Large']:write(root,f'ReplaceableTextures/Selection/SelectionCircle{name}.blp',blp(64,64,ring))
    write(root,'Textures/Black32.blp',texture(32,32,(0,0,0)))
    write(root,'war3mapMap.blp',texture(256,256,colors['earth']))
    # Original synthesized acknowledgement tone; not a recording/sample.
    sound=root/'Emberfield/Sounds/ack.wav';sound.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(sound),'wb') as w:
        w.setparams((1,2,22050,0,'NONE','not compressed'))
        w.writeframes(b''.join(P('h',int(4500*math.sin(2*math.pi*660*i/22050)*(1-i/3307))) for i in range(3307)))
    sounds=[dict(SoundName='Ember'+action,DirectoryBase='Emberfield\\Sounds\\',FileNames='ack.wav',Volume=50,Channel='2',Pitch=1) for action in ['What','Yes','YesAttack','Ready']]
    write(root,'UI/SoundInfo/UnitAckSounds.slk',slk(sounds,'SoundName'))
    directory=out/'map'
    if directory.exists():shutil.rmtree(directory)
    if content: content.map_data(directory)
    else: map_data(directory)
    write(directory,'war3mapMap.blp',art.blp_bytes(art.terrain().resize((256,256))))
    if content: content.assets(root, directory)
    map_path=content.MAP_PATH if content else 'Maps/Emberfield/FirstLight.w3m'
    tool=repo/'build/bin/mpqtool'
    def pack(source,dest):
        files=sorted(p for p in source.rglob('*') if p.is_file())
        args=[str(tool),'-mpq',str(dest),'pack']
        for p in files:args += [str(p),str(p.relative_to(source))]
        subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
    mapfile=root/map_path;mapfile.parent.mkdir(parents=True,exist_ok=True);pack(directory,mapfile)
    if content and hasattr(content,'extra_maps'):content.extra_maps(root,directory,pack)
    pack(root,out/'War3.mpq')
    write(out,'autoexec.cfg',f'seta cl_start_menu "map {map_path}"\nseta com_maxfps "60"\nseta skip_cutscene "1"\nseta fs_expansion "0"\nseta r_cursor "0"\n'+ ('seta cl_same_type_select "1"\n' if content and content.TITLE.startswith('Frontline') else ''))
    manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
    write(out,'manifest.json',json.dumps({'name':content.TITLE if content else 'Emberfield - First Light','license':getattr(content,'LICENSE','MIT original procedural content; DejaVu font license included'),'files':manifest},indent=2))
    # Original procedural app icon: a stepped amber beacon on a navy field.
    width=1024;raw=bytearray()
    for y in range(width):
        raw.append(0)
        for x in range(width):
            shape=(210<x<814 and 660<y<795) or (320<x<704 and 440<y<660) or (430<x<594 and 225<y<440)
            raw+=bytes((237,165,66) if shape else (16,30,43))
    def pngchunk(tag,data): return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    icon=b'\x89PNG\r\n\x1a\n'+pngchunk(b'IHDR',struct.pack('>2I5B',width,width,8,2,0,0,0))+pngchunk(b'IDAT',zlib.compress(raw))+pngchunk(b'IEND',b'')
    write(out,'icon.png',icon)
    if content: content.app_icon(out)
    print(f'Generated {len(manifest)} original files: {out / "War3.mpq"}')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('build/emberfield'))
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    a=parser.parse_args();generate(a.out.resolve(),a.repo.resolve())
