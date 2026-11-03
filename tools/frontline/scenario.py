"""Map-owned match, deterministic bot doctrine and amphibious orders."""
from tools.emberfield.generate import AI_NATIVE
COMMON='''type texttag extends handle
native EndGame takes boolean scores returns nothing
native IsUnitHidden takes unit u returns boolean
native SelectUnit takes unit u, boolean selected returns nothing
native IsUnitLoaded takes unit u returns boolean
native GetUnitUserData takes unit u returns integer
native SetUnitUserData takes unit u, integer value returns nothing
native GetUnitCurrentOrder takes unit u returns integer
native IssueBuildOrderById takes unit u, integer building, real x, real y returns boolean
native OrderId takes string orderIdString returns integer
native SetUnitMoveSpeed takes unit u, real speed returns nothing
native GetUnitMoveSpeed takes unit u returns real
native SetUnitScale takes unit u, real scaleX, real scaleY, real scaleZ returns nothing
native CreateTrigger takes nothing returns trigger
native TriggerAddAction takes trigger t, code actionFunc returns triggeraction
native TriggerRegisterPlayerUnitEvent takes trigger t, player p, playerunitevent evt, boolexpr filter returns event
native GetKillingUnit takes nothing returns unit
native GetDyingUnit takes nothing returns unit
native GetTriggerUnit takes nothing returns unit
native GetOwningPlayer takes unit u returns player
native GetUnitName takes unit u returns string
native UnitAddAbility takes unit u, integer abilityId returns boolean
native UnitRemoveAbility takes unit u, integer abilityId returns boolean
native CreateTextTag takes nothing returns texttag
native SetTextTagText takes texttag t, string s, real height returns nothing
native SetTextTagPosUnit takes texttag t, unit whichUnit, real heightOffset returns nothing
native SetTextTagColor takes texttag t, integer red, integer green, integer blue, integer alpha returns nothing
native SetTextTagVelocity takes texttag t, real xvel, real yvel returns nothing
native SetTextTagPermanent takes texttag t, boolean flag returns nothing
native SetTextTagLifespan takes texttag t, real lifespan returns nothing
native SetTextTagFadepoint takes texttag t, real fadepoint returns nothing
'''
AI_SCRIPT='''globals
    // What this bot has actually seen of its opponent; production adapts to it.
    integer seenAir = 0
    integer seenArmor = 0
    integer seenInfantry = 0
    integer seenNavy = 0
    integer seenForts = 0
    integer sweeps = 0
    // Loops spent saving materiel for the island outpost Headquarters (bounded).
    integer saveTicks = 0
endglobals
// Counts only player units visible to the bot (no map hack). Memory keeps the largest sighting and
// forgets one unit of each kind every 30 seconds, so a scouted threat shapes the next few minutes.
function Intel takes nothing returns nothing
    local group enemies = CreateGroup()
    local unit u
    local integer id
    local integer air = 0
    local integer armor = 0
    local integer infantry = 0
    local integer navy = 0
    local integer forts = 0
    call GroupEnumUnitsOfPlayer(enemies, Player(0), null)
    loop
        set u = FirstOfGroup(enemies)
        exitwhen u == null
        call GroupRemoveUnit(enemies, u)
        if GetWidgetLife(u) > 0.0 and IsUnitVisible(u, Player(1)) then
            set id = GetUnitTypeId(u)
            if id == 'ffgt' or id == 'fbmb' or id == 'frec' or id == 'ftor' INTELAIR then
                set air = air + 1
            elseif id == 'ftnk' or id == 'fcar' or id == 'fhtk' then
                set armor = armor + 1
            elseif id == 'finf' or id == 'fmg0' or id == 'fmrt' or id == 'fcmd' then
                set infantry = infantry + 1
            elseif id == 'fbat' or id == 'fdst' or id == 'fcrs' or id == 'fcvr' NAVALTHREAT then
                set navy = navy + 1
            elseif id == 'fbnk' or id == 'fbn2' or id == 'fcst' or id == 'upbx' or id == 'upb2' or id == 'jpbx' or id == 'jpb2' or id == 'ucst' or id == 'jcst' or id == 'uaa2' or id == 'jaa2' or id == 'uaa4' or id == 'jaa4' or id == 'uaa9' or id == 'jaa8' then
                set forts = forts + 1
            endif
        endif
    endloop
    call DestroyGroup(enemies)
    set sweeps = sweeps + 1
    if sweeps - (sweeps/10)*10 == 0 then
        if seenAir > 0 then
            set seenAir = seenAir - 1
        endif
        if seenArmor > 0 then
            set seenArmor = seenArmor - 1
        endif
        if seenInfantry > 0 then
            set seenInfantry = seenInfantry - 1
        endif
        if seenNavy > 0 then
            set seenNavy = seenNavy - 1
        endif
        if seenForts > 0 then
            set seenForts = seenForts - 1
        endif
    endif
    if air > seenAir then
        set seenAir = air
    endif
    if armor > seenArmor then
        set seenArmor = armor
    endif
    if infantry > seenInfantry then
        set seenInfantry = infantry
    endif
    if navy > seenNavy then
        set seenNavy = navy
    endif
    if forts > seenForts then
        set seenForts = forts
    endif
endfunction
function AirThreat takes nothing returns integer
    if seenAir > 8 then
        return 8
    endif
    return seenAir
endfunction
function LandStrength takes nothing returns integer
    return GetUnitCount('finf') + GetUnitCount('fmg0') + 2*GetUnitCount('ftnk') + GetUnitCount('fart') + GetUnitCount('fmrt') + GetUnitCount('fcmd') + 3*GetUnitCount('fhtk') + GetUnitCount('frkt')
endfunction
// Enemy fleets seen near the AI's waters pull naval production forward; otherwise ships wait for the land force.
function NavalThreat takes nothing returns integer
    local group enemies = CreateGroup()
    local unit u
    local integer id
    local integer count = 0
    call GroupEnumUnitsOfPlayer(enemies, Player(0), null)
    loop
        set u = FirstOfGroup(enemies)
        exitwhen u == null
        call GroupRemoveUnit(enemies, u)
        set id = GetUnitTypeId(u)
        if GetWidgetLife(u) > 0.0 and IsUnitVisible(u, Player(1)) and (id == 'fbat' or id == 'fdst' or id == 'fcrs' or id == 'fcvr' NAVALTHREAT) then
            set count = count + 1
        endif
    endloop
    call DestroyGroup(enemies)
    return count
endfunction
function main takes nothing returns nothing
    local integer land
    local integer grow
    local boolean landReady
    local boolean navalStarted
    local boolean pressed
    call SetMeleeAI()
    loop
        call Intel()
        set land = LandStrength()
        // Phase 1, land first: workers, barracks, infantry, a factory, tanks and a bunker.
        set landReady = land >= 12 and GetUnitCount('fbnk') >= 1
        // Phase 2 starts once the base is defended; the land force grows further only after ships are afloat.
        set navalStarted = GetUnitCount('fdst') >= 2
        set grow = 0
        if navalStarted then
            set grow = land
        endif
        set pressed = NavalThreat() > 0
        call ClearHarvestAI()
        call HarvestGold(0, 4)
        call HarvestWood(0, 2)
        // Once a landing craft exists, pause spending until the outpost Headquarters stands,
        // for at most six minutes, so the settlers can afford it when they land.
        if landReady and GetUnitCount('flct') > 0 and GetUnitCount('fhq0') < 2 and saveTicks < 120 then
            set saveTicks = saveTicks + 1
        else
        // Two spare engineers beyond the harvest quota build and settle the flank island.
        if GetUnitCount('fwkr') < 8 then
            call SetProduce(1, 'fwkr', 0)
        elseif landReady and GetUnitCount('fwkr') < 10 then
            // Once the base is defended, spare engineers are ready to settle outposts across the water.
            call SetProduce(1, 'fwkr', 0)
        endif
        if GetUnitCount('fbar') < 1 then
            call SetProduce(1, 'fbar', 0)
        elseif GetUnitCount('finf') < 4 then
            call SetProduce(1, 'finf', 0)
        elseif GetUnitCount('ffac') < 1 then
            call SetProduce(1, 'ffac', 0)
        elseif GetUnitCount('fbnk') < 1 then
            call SetProduce(1, 'fbnk', 0)
        elseif landReady and GetUnitCount('fair') < 1 then
            call SetProduce(1, 'fair', 0)
        elseif navalStarted and GetUnitCount('fbnk') < 2 + grow/16 then
            call SetProduce(1, 'fbnk', 0)
        endif
        if GetUnitCount('finf') < 8 + grow/6 then
            call SetProduce(1, 'finf', 0)
        endif
        // Counters: machine guns and mortars against massed infantry, heavy armor and bombers against
        // armor, artillery against fortifications, destroyers and torpedo bombers against a fleet.
        if GetUnitCount('fmg0') < 2 + grow/10 + seenInfantry/6 then
            call SetProduce(1, 'fmg0', 0)
        endif
        if GetUnitCount('ftnk') < 2 + grow/8 then
            call SetProduce(1, 'ftnk', 0)
        endif
        if GetUnitCount('faa0') < 1 + AirThreat()/2 then
            call SetProduce(1, 'faa0', 0)
        endif
        if landReady and GetUnitCount('fart') < 1 + grow/16 + seenForts/3 then
            call SetProduce(1, 'fart', 0)
        endif
        // Heavy armor, rockets and capital ships need the Airfield (catalog.REQUIRES); a locked
        // SetProduce would stall the whole queue.
        if GetUnitCount('fair') > 0 and (navalStarted or (landReady and seenArmor >= 3)) and GetUnitCount('fhtk') < 1 + grow/12 + seenArmor/4 then
            call SetProduce(1, 'fhtk', 0)
        endif
        if GetUnitCount('fair') > 0 and (navalStarted or (landReady and seenForts >= 2)) and GetUnitCount('frkt') < 1 + grow/20 + seenForts/4 then
            call SetProduce(1, 'frkt', 0)
        endif
        if GetUnitCount('fmrt') < 1 + grow/14 + seenInfantry/8 then
            call SetProduce(1, 'fmrt', 0)
        endif
        if landReady and GetUnitCount('ffac') > 0 and GetUnitCount('fcmd') < 1 then
            call SetProduce(1, 'fcmd', 0)
        endif
        if landReady or AirThreat() > 0 then
            if GetUnitCount('ffgt') < 2 + AirThreat()/2 then
                call SetProduce(1, 'ffgt', 0)
            endif
            if landReady and GetUnitCount('fbmb') < 2 + seenArmor/4 then
                call SetProduce(1, 'fbmb', 0)
            endif
            // One recon aircraft keeps the intelligence picture fresh.
            if landReady and GetUnitCount('fair') > 0 and GetUnitCount('frec') < 1 then
                call SetProduce(1, 'frec', 0)
            endif
            if landReady and seenNavy > 0 and GetUnitCount('ftor') < 1 + seenNavy/3 then
                call SetProduce(1, 'ftor', 0)
            endif
        endif
        // Navy: the faction's Escort Shipyard (destroyers, cruisers) and Landing Craft Yard; capital
        // ships come from the Capital Shipyard below. There is no generic shipyard.
        // One coastal yard serves the bot: the Escort Shipyard also launches its landing craft.
        if (landReady or pressed) and GetUnitCount('fesc') < 1 then
            call SetProduce(1, 'fesc', 0)
        endif
        if (landReady or pressed) and GetUnitCount('fesc') > 0 then
            if GetUnitCount('fdst') < 2 or (seenNavy > 2 and GetUnitCount('fdst') < 2 + seenNavy/2 and GetUnitCount('fdst') < 6) then
                call SetProduce(1, 'fdst', 0)
            elseif landReady and GetUnitCount('flct') < 1 then
                // Landing craft before heavy ships: the army must be able to cross and settle outposts.
                call SetProduce(1, 'flct', 0)
            elseif landReady and GetUnitCount('fcrs') < 1 then
                call SetProduce(1, 'fcrs', 0)
            endif
        endif
        endif
        call Sleep(3.0)
    endloop
endfunction
'''
MAP_SCRIPT='''globals
    unit alliedHQ
    unit enemyHQ
    unit enemyDock
    unit alliedCarrier
    unit array homeOre
    destructable array homeTree
    integer elapsed = 0
    integer invasions = 0
    integer expansion = 0
    unit eastOre
    unit eastHQ
    unit settlerCraft
    boolean finished = false
    boolean botOpponent = true
    integer botLand = 0
    integer botDocks = 0
    integer botHeavy = 0
    integer botEscort = 0
    integer botLanding = 0
    // Bot doctrine: 0 build-up, 1 muster (fleet and air prepare the beach), 2 assault (landing craft ferry the army), 3 regroup.
    integer doctrine = 0
    integer doctrineSince = 0
    integer assaultNeed = 14
    integer assaultLand = 0
    integer assaults = 0
    // Intelligence: what the bot has actually seen of the player (decaying memory) and where to strike.
    integer seenLand = 0
    integer seenAir = 0
    integer seenNavy = 0
    integer seenForts = 0
    real objectiveX = -5400.0
    real objectiveY = 5400.0
    real navalX = 0.0
    real navalY = 0.0
    boolean navalSpotted = false
    integer scoutLeg = 0
    // Road boost / barbed wire slow — tracked unit arrays.
    integer roadCount = 0
    unit array roadUnit
    real array roadSpeed

    // Landing craft that stop making progress (wedged against a shore or yard) are nudged free.
    integer lcCount = 0
    unit array lcUnit
    real array lcX
    real array lcY
    integer array lcStill
    // Veterancy: kill tracking per unit (separate from UserData used by bot AI).
    integer vetCount = 0
    unit array vetUnit
    integer array vetKills
endglobals
// Rank callout above the unit, seen by everyone (enemy veterans are worth spotting).
function VetCallout takes unit u, string label, integer green returns nothing
    local texttag t = CreateTextTag()
    call SetTextTagText(t, label, 0.026)
    call SetTextTagPosUnit(t, u, 40.0)
    call SetTextTagColor(t, 255, green, 60, 255)
    call SetTextTagVelocity(t, 0.0, 0.03)
    call SetTextTagPermanent(t, false)
    call SetTextTagLifespan(t, 3.0)
    call SetTextTagFadepoint(t, 2.0)
endfunction
// Ranks: Veteran at 3 kills, Elite at 7. The Fvt1/Fvt2 abilities (s_veterancy.c) carry the
// firepower, armor and Elite self-repair; the command card shows the rank badge.
function VetGrant takes unit killer returns nothing
    local integer i = 0
    local integer slot = -1
    local integer kills
    if killer == null or GetWidgetLife(killer) <= 0.0 then
        return
    endif
    loop
        exitwhen i >= vetCount
        if vetUnit[i] == killer then
            set vetKills[i] = vetKills[i] + 1
            set kills = vetKills[i]
            if kills == 3 then
                call UnitAddAbility(killer, 'Fvt1')
                call SetUnitScale(killer, 1.08, 1.08, 1.08)
                call VetCallout(killer, "VETERAN", 220)
                call DisplayTimedTextToPlayer(GetOwningPlayer(killer), 0.12, 0.035, 4.0, GetUnitName(killer) + " promoted to Veteran.")
            elseif kills == 7 then
                call UnitRemoveAbility(killer, 'Fvt1')
                call UnitAddAbility(killer, 'Fvt2')
                call SetUnitScale(killer, 1.15, 1.15, 1.15)
                call VetCallout(killer, "ELITE", 150)
                call DisplayTimedTextToPlayer(GetOwningPlayer(killer), 0.12, 0.035, 4.0, GetUnitName(killer) + " promoted to Elite.")
            endif
            return
        endif
        // Dead units free their slot for the next fresh killer.
        if slot < 0 and GetWidgetLife(vetUnit[i]) <= 0.0 then
            set slot = i
        endif
        set i = i + 1
    endloop
    if slot < 0 and vetCount < 400 then
        set slot = vetCount
        set vetCount = vetCount + 1
    endif
    if slot >= 0 then
        set vetUnit[slot] = killer
        set vetKills[slot] = 1
    endif
endfunction
function OnKill takes nothing returns nothing
    call VetGrant(GetKillingUnit())
endfunction
// Advisor: construction complete (the engine plays JobDoneSound alongside).
function OnBuilt takes nothing returns nothing
    local unit u = GetTriggerUnit()
    call DisplayTimedTextToPlayer(GetOwningPlayer(u), 0.12, 0.035, 4.0, "Construction complete: " + GetUnitName(u) + ".")
endfunction
function config takes nothing returns nothing
endfunction
function FrontlineTestForces takes nothing returns nothing
    local integer i = 0
    local integer j = 0
    local real side
    local unit worker
    loop
        exitwhen i >= 2
        set side = -1.0 + 2.0*I2R(i)
        call CreateUnit(Player(i), 'fbar', side*2700.0, -side*2500.0, 0.0)
        if i == 1 then
            set enemyDock = CreateUnit(Player(i), 'fdoc', side*2400.0, -side*1900.0, 0.0)
        else
            call CreateUnit(Player(i), 'fdoc', side*2400.0, -side*1900.0, 0.0)
        endif
        call CreateUnit(Player(i), 'fdep', side*3600.0, -side*2500.0, 0.0)
        call CreateUnit(Player(i), 'fbnk', side*2900.0, -side*1650.0, 0.0)
        call CreateUnit(Player(i), 'fbat', side*1500.0, -side*1500.0, 0.0)
        call CreateUnit(Player(i), 'fdst', side*1900.0, -side*1000.0, 0.0)
        if i == 0 then
            set alliedCarrier = CreateUnit(Player(i), 'fcvr', side*1000.0, -side*1900.0, 0.0)
        else
            call CreateUnit(Player(i), 'fcvr', side*1000.0, -side*1900.0, 0.0)
        endif
        call CreateUnit(Player(i), 'flct', side*2000.0, -side*2150.0, 0.0)
        if i == 1 then
            // Player 1 is the IJN side: its land force uses the Japanese variants.
            call CreateUnit(Player(i), 'jinf', side*2450.0, -side*2500.0, 0.0)
            call CreateUnit(Player(i), 'jinf', side*2350.0, -side*2650.0, 0.0)
            call CreateUnit(Player(i), 'jtnk', side*2600.0, -side*2700.0, 0.0)
        else
            call CreateUnit(Player(i), 'finf', side*2450.0, -side*2500.0, 0.0)
            call CreateUnit(Player(i), 'finf', side*2350.0, -side*2650.0, 0.0)
            call CreateUnit(Player(i), 'ftnk', side*2600.0, -side*2700.0, 0.0)
        endif
        set j = 0
        loop
            exitwhen j >= 5
            set worker = CreateUnit(Player(i), 'fwkr', side*5650.0, -side*(5500.0+I2R(j)*100.0), 0.0)
            if j < 4 then
                call IssueTargetOrder(worker, "harvest", homeOre[i])
            else
                call IssueTargetOrder(worker, "harvest", homeTree[i])
            endif
            set j = j + 1
        endloop
        set i = i+1
    endloop
endfunction
// Victory Continue uses the same score/menu transition as Leave Match.
function CustomVictoryOkBJ takes nothing returns nothing
    call EndGame(true)
endfunction
function SettlersAboard takes nothing returns integer
    local group units = CreateGroup()
    local unit u
    local integer count = 0
    call GroupEnumUnitsOfPlayer(units, Player(1), null)
    loop
        set u = FirstOfGroup(units)
        exitwhen u == null
        call GroupRemoveUnit(units, u)
        if GetUnitTypeId(u) == 'fwkr' and IsUnitLoaded(u) then
            set count = count + 1
        endif
    endloop
    call DestroyGroup(units)
    return count
endfunction
// A sailing craft that has not moved for three ticks (9 s) is placed at the nearest legal water
// 200 units toward (tx, ty); the engine's unstuck search keeps it off land.
function LCUnstick takes unit u, real tx, real ty returns nothing
    local integer i = 0
    local real dx
    local real dy
    local real d
    loop
        exitwhen i >= lcCount or lcUnit[i] == u
        set i = i + 1
    endloop
    if i >= lcCount then
        if lcCount >= 32 then
            set i = 0
        else
            set lcCount = lcCount + 1
        endif
        set lcUnit[i] = u
        set lcX[i] = GetUnitX(u)
        set lcY[i] = GetUnitY(u)
        set lcStill[i] = 0
        return
    endif
    set dx = GetUnitX(u) - lcX[i]
    set dy = GetUnitY(u) - lcY[i]
    if dx*dx + dy*dy < 400.0 then
        set lcStill[i] = lcStill[i] + 1
    else
        set lcStill[i] = 0
    endif
    set lcX[i] = GetUnitX(u)
    set lcY[i] = GetUnitY(u)
    if lcStill[i] >= 3 then
        set dx = tx - GetUnitX(u)
        set dy = ty - GetUnitY(u)
        set d = SquareRoot(dx*dx + dy*dy)
        if d > 1.0 then
            call SetUnitPosition(u, GetUnitX(u) + dx/d*200.0, GetUnitY(u) + dy/d*200.0)
        endif
        set lcStill[i] = 0
    endif
endfunction
function BotMax takes integer a, integer b returns integer
    if a > b then
        return a
    endif
    return b
endfunction
// Intelligence sweep: only player units the bot can currently see count. Memory decays slowly, so a
// sighting keeps shaping production and doctrine for a while after the scout moves on.
function BotIntel takes nothing returns nothing
    local group units = CreateGroup()
    local unit u
    local integer id
    local integer land = 0
    local integer air = 0
    local integer navy = 0
    local integer forts = 0
    local real best = 1000000000.0
    local real d
    local boolean found = false
    call GroupEnumUnitsOfPlayer(units, Player(0), null)
    loop
        set u = FirstOfGroup(units)
        exitwhen u == null
        call GroupRemoveUnit(units, u)
        if GetWidgetLife(u) > 0.0 and IsUnitVisible(u, Player(1)) and not IsUnitLoaded(u) then
            set id = GetUnitTypeId(u)
            if id == 'finf' or id == 'fmg0' or id == 'fart' or id == 'fmrt' or id == 'fcmd' or id == 'frkt' or id == 'faa0' or id == 'fcar' then
                set land = land + 1
            elseif id == 'ftnk' then
                set land = land + 2
            elseif id == 'fhtk' then
                set land = land + 3
            elseif id == 'ffgt' or id == 'fbmb' or id == 'ftor' or id == 'frec' SEENAIR then
                set air = air + 1
            elseif id == 'fbat' or id == 'fdst' or id == 'fcrs' or id == 'fcvr' SEENNAVY then
                set navy = navy + 1
                // The nearest sighted warship to the bot's home waters is the carriers' first target.
                set d = (GetUnitX(u) - 1500.0)*(GetUnitX(u) - 1500.0) + (GetUnitY(u) + 1500.0)*(GetUnitY(u) + 1500.0)
                if not navalSpotted or d < (navalX - 1500.0)*(navalX - 1500.0) + (navalY + 1500.0)*(navalY + 1500.0) then
                    set navalX = GetUnitX(u)
                    set navalY = GetUnitY(u)
                    set navalSpotted = true
                endif
            elseif id == 'fbnk' or id == 'fbn2' or id == 'fcst' or id == 'fwat' or id == 'upbx' or id == 'upb2' or id == 'jpbx' or id == 'jpb2' or id == 'ucst' or id == 'jcst' or id == 'uaa2' or id == 'jaa2' or id == 'uaa4' or id == 'jaa4' or id == 'uaa9' or id == 'jaa8' then
                set forts = forts + 1
            endif
            if GetUnitDefaultMoveSpeed(u) <= 0.0 and id != 'eore' then
                // Assault objective: the sighted enemy structure closest to the landing beach.
                set d = (GetUnitX(u) + 2000.0)*(GetUnitX(u) + 2000.0) + (GetUnitY(u) - 2150.0)*(GetUnitY(u) - 2150.0)
                if d < best then
                    set best = d
                    set objectiveX = GetUnitX(u)
                    set objectiveY = GetUnitY(u)
                    set found = true
                endif
            endif
        endif
    endloop
    call DestroyGroup(units)
    // A scouted objective that has since been razed falls back to the headquarters.
    if not found and IsVisibleToPlayer(objectiveX, objectiveY, Player(1)) then
        set objectiveX = GetUnitX(alliedHQ)
        set objectiveY = GetUnitY(alliedHQ)
    endif
    if navalSpotted and navy == 0 and IsVisibleToPlayer(navalX, navalY, Player(1)) then
        set navalSpotted = false
    endif
    // Remember the largest force seen; forget one unit of each every 30 seconds.
    if elapsed - (elapsed/30)*30 == 0 then
        set seenLand = BotMax(0, seenLand - 1)
        set seenAir = BotMax(0, seenAir - 1)
        set seenNavy = BotMax(0, seenNavy - 1)
        set seenForts = BotMax(0, seenForts - 1)
    endif
    set seenLand = BotMax(seenLand, land)
    set seenAir = BotMax(seenAir, air)
    set seenNavy = BotMax(seenNavy, navy)
    set seenForts = BotMax(seenForts, forts)
endfunction
function BotTactics takes nothing returns nothing
    local group army = CreateGroup()
    local group nearby = CreateGroup()
    local unit actor
    local unit other
    local integer id
    local integer phase
    local integer threats = 0
    local integer order
    local integer attackOrder = OrderId("attack")
    local integer smartOrder = OrderId("smart")
    local integer moveOrder = OrderId("move")
    local real threatX = 3000.0
    local real threatY = -3000.0
    local real dx
    local real dy
    local boolean harborOrdered = false
    local integer settlers = 0
    local integer landNow = 0
    local integer harborSite = 0
    local integer docksNow = 0
    local integer heavyNow = 0
    local integer escortNow = 0
    local integer landingNow = 0
    local integer yard = 0
    local integer warshipsNow = 0
    local integer craftNow = 0
    local integer beachNow = 0
    call BotIntel()
    // Home defense covers the whole base, from the HQ in the corner down to the harbor on the coast.
    call GroupEnumUnitsInRange(nearby, 4000.0, -4000.0, 3000.0, null)
    loop
        set other = FirstOfGroup(nearby)
        exitwhen other == null
        call GroupRemoveUnit(nearby, other)
        if IsUnitEnemy(other, Player(1)) and GetWidgetLife(other) > 0.0 then
            set threats = threats + 1
            set threatX = GetUnitX(other)
            set threatY = GetUnitY(other)
        endif
    endloop
    call GroupEnumUnitsOfPlayer(army, Player(1), null)
    loop
        set actor = FirstOfGroup(army)
        exitwhen actor == null
        call GroupRemoveUnit(army, actor)
        set id = GetUnitTypeId(actor)
        if GetWidgetLife(actor) > 0.0 then
            // The Escort Shipyard is the bot's harbor: it counts as a dock and as an escort yard.
            if id == 'fdoc' or id == 'fesc' then
                set docksNow = docksNow + 1
            endif
            if id == 'fesc' then
                set escortNow = escortNow + 1
            elseif id == 'fhvy' then
                set heavyNow = heavyNow + 1
            elseif id == 'flnd' then
                set landingNow = landingNow + 1
            elseif id == 'finf' or id == 'fmg0' or id == 'fart' or id == 'fmrt' or id == 'fcmd' or id == 'frkt' then
                set landNow = landNow + 1
            elseif id == 'ftnk' then
                set landNow = landNow + 2
            elseif id == 'fhtk' then
                set landNow = landNow + 3
            endif
        endif
        // Hidden trainees are real edicts but not actors: orders would overwrite their queue link.
        if GetWidgetLife(actor) > 0.0 and not IsUnitLoaded(actor) and not IsUnitHidden(actor) then
            if id == 'fdoc' or id == 'fesc' then
                set enemyDock = actor
            elseif id == 'fhq0' and GetUnitX(actor) > 3000.0 and GetUnitY(actor) > 700.0 then
                set eastHQ = actor
            elseif id == 'fwkr' and botLand >= 12 and not harborOrdered and GetUnitX(actor) - GetUnitY(actor) > 3900.0 and botDocks == 0 and elapsed - (elapsed/15)*15 < 3 then
                // Backup harbor builder: when the AI has lost its harbor, an engineer rebuilds it at rotating shore sites
                // so a parked ship cannot stall it. The AI itself requests the first harbor and the heavy yard.
                set yard = 'fesc'
                set harborSite = elapsed/30 - (elapsed/120)*4
                if harborSite == 0 then
                    call IssueBuildOrderById(actor, yard, 2400.0, -1900.0)
                elseif harborSite == 1 then
                    call IssueBuildOrderById(actor, yard, 3000.0, -1400.0)
                elseif harborSite == 2 then
                    call IssueBuildOrderById(actor, yard, 1800.0, -2600.0)
                else
                    call IssueBuildOrderById(actor, yard, 2700.0, -1700.0)
                endif
                set harborOrdered = true
            elseif id == 'fwkr' and GetUnitX(actor) - GetUnitY(actor) > 3900.0 and GetUnitCurrentOrder(actor) == 0 and botLand >= 6 and elapsed > 90 then
                // Idle mainland engineer: build supply roads and defenses.
                set order = elapsed/45 - (elapsed/180)*4
                if order == 0 then
                    call IssueBuildOrderById(actor, 'frod', 4200.0, -3800.0)
                elseif order == 1 then
                    call IssueBuildOrderById(actor, 'frod', 3200.0, -2800.0)
                elseif order == 2 then
                    call IssueBuildOrderById(actor, 'fsbg', 5000.0, -5800.0)
                else
                    call IssueBuildOrderById(actor, 'fwir', 4600.0, -4400.0)
                endif
            elseif id == 'fwkr' and GetUnitX(actor) - GetUnitY(actor) < 3900.0 then
                // Settlers landed on the east island: raise an outpost HQ, then mine it.
                // The melee AI may borrow settlers for mainland builds they cannot reach;
                // keep re-issuing the outpost until it stands, then mine from it.
                set order = GetUnitCurrentOrder(actor)
                if GetWidgetLife(eastHQ) <= 0.0 then
                    // A build order searches for a legal site, which is costly when the site is unreachable: settlers
                    // already on the island keep the order every tick, any other engineer retries at most every 15 s.
                    set dx = GetUnitX(actor) - 3800.0
                    set dy = GetUnitY(actor) - 1650.0
                    if order != 'fhq0' and (dx*dx + dy*dy < 2250000.0 or elapsed - (elapsed/15)*15 < 3) then
                        call IssueBuildOrderById(actor, 'fhq0', 3800.0, 1650.0)
                    endif
                elseif order == 0 or (GetUnitUserData(actor) == 0 and GetWidgetLife(eastHQ) >= GetUnitState(eastHQ, ConvertUnitState(1)) - 1.0) then
                    call IssueTargetOrder(actor, "harvest", eastOre)
                    call SetUnitUserData(actor, 1)
                endif
            elseif id == 'fcvr' then
                if expansion >= 2 then
                    call IssueImmediateOrder(actor, "shipprotection")
                endif
                // Carriers embark their air group once; losses are never replaced.
                if threats > 0 then
                    call IssuePointOrder(actor, "airpatrol", threatX, threatY)
                elseif elapsed > 45 and elapsed - (elapsed/30)*30 == 0 then
                    // Every carrier is ordered in this same frame, so the strike is one coordinated wave.
                    // A sighted enemy fleet is hunted first; otherwise strikes only prepare and support a landing.
                    if navalSpotted then
                        call IssuePointOrder(actor, "airstrike", navalX, navalY)
                    elseif doctrine == 1 or doctrine == 2 then
                        call IssuePointOrder(actor, "airstrike", objectiveX, objectiveY)
                    endif
                endif
            elseif id == 'fbat' or id == 'fdst' or id == 'fcrs' then
                // Defend home waters, then push across the open ocean; idle ships
                // patrol toward the contested north island.
                // Each order is given once (stamped in user data) and renewed only when the ship goes idle:
                // re-issuing a far attack-move every tick made the route search the dominant cost of a late match.
                set warshipsNow = warshipsNow + 1
                set dx = GetUnitX(actor) + 1700.0
                set dy = GetUnitY(actor) - 1700.0
                if dx*dx + dy*dy < 3240000.0 then
                    set beachNow = beachNow + 1
                endif
                if threats > 0 then
                    if GetUnitUserData(actor) != 2 or GetUnitCurrentOrder(actor) == 0 then
                        call IssuePointOrder(actor, "attack", 1500.0, -1500.0)
                        call SetUnitUserData(actor, 2)
                    endif
                elseif doctrine == 1 or doctrine == 2 then
                    // Muster and assault: bombard the landing beach ahead of the landing craft.
                    if GetUnitUserData(actor) != 1 or GetUnitCurrentOrder(actor) == 0 then
                        call IssuePointOrder(actor, "attack", -1700.0, 1700.0)
                        call SetUnitUserData(actor, 1)
                    endif
                elseif doctrine == 3 then
                    // Regroup: fall back to home waters to repair and rejoin the next wave.
                    if GetUnitUserData(actor) != 4 then
                        call IssuePointOrder(actor, "move", 1500.0, -1500.0)
                        call SetUnitUserData(actor, 4)
                    endif
                elseif navalSpotted and elapsed > 55 then
                    // An enemy fleet in sight: engage it before it can threaten the home coast.
                    if GetUnitUserData(actor) != 5 or GetUnitCurrentOrder(actor) == 0 then
                        call IssuePointOrder(actor, "attack", navalX, navalY)
                        call SetUnitUserData(actor, 5)
                    endif
                elseif GetUnitCurrentOrder(actor) == 0 then
                    // Build-up: picket the contested north island, which also scouts the open ocean.
                    call IssuePointOrder(actor, "patrol", 1800.0, 2300.0)
                    call SetUnitUserData(actor, 3)
                endif
            elseif id == 'flct' or id == 'ftrn' then
                set craftNow = craftNow + 1
                set phase = GetUnitUserData(actor)
                if phase == 7 or phase == 10 or phase == 11 or phase == 12 or phase == 20 then
                    call LCUnstick(actor, 0.0, 0.0)
                endif
                if phase < 6 and threats > 0 then
                    // Hold the embarkation clock while the home island is under attack.
                    call IssuePointOrder(actor, "move", 1000.0, -1000.0)
                elseif phase < 6 then
                    call IssuePointOrder(actor, "move", 1000.0, -1000.0)
                    if expansion == 0 and (GetWidgetLife(settlerCraft) <= 0.0 or settlerCraft == actor) then
                        set settlerCraft = actor
                        // Two engineers board the first trip to claim the east island; the
                        // harvest quota leaves spares so the economy keeps running.
                        call GroupEnumUnitsOfPlayer(nearby, Player(1), null)
                        loop
                            set other = FirstOfGroup(nearby)
                            exitwhen other == null or settlers >= 2
                            call GroupRemoveUnit(nearby, other)
                            // Skip engineers holding a build order (ids are four-char codes): a
                            // pending mainland project would block the town builder.
                            if GetUnitTypeId(other) == 'fwkr' and GetWidgetLife(other) > 0.0 and not IsUnitLoaded(other) and GetUnitCurrentOrder(other) < 16777216 and GetUnitX(other) - GetUnitY(other) > 3900.0 then
                                call IssueTargetOrder(other, "smart", actor)
                                set settlers = settlers + 1
                            endif
                        endloop
                        call GroupClear(nearby)
                    endif
                    // The first craft carries only settlers until the island is claimed; the other craft takes the troops.
                    if expansion > 0 or actor != settlerCraft then
                        call GroupEnumUnitsInRange(nearby, 1800.0, -1800.0, 1200.0, null)
                        loop
                            set other = FirstOfGroup(nearby)
                            exitwhen other == null
                            call GroupRemoveUnit(nearby, other)
                            if IsUnitAlly(other, Player(1)) and (GetUnitTypeId(other) == 'finf' or GetUnitTypeId(other) == 'ftnk' or GetUnitTypeId(other) == 'fhtk' or GetUnitTypeId(other) == 'fmrt' or GetUnitTypeId(other) == 'fcmd') then
                                call IssueTargetOrder(other, "smart", actor)
                            endif
                        endloop
                    endif
                    call SetUnitUserData(actor, phase + 1)
                elseif phase == 6 and expansion == 0 and actor == settlerCraft then
                    if SettlersAboard() > 0 then
                        call IssuePointOrder(actor, "move", 3200.0, 870.0)
                        set expansion = 1
                        call SetUnitUserData(actor, 20)
                    else
                        // Build/harvest work can delay a settler beyond the embarkation
                        // clock. Retry recruitment instead of abandoning island expansion.
                        call IssueImmediateOrder(actor, "unloadall")
                        call SetUnitUserData(actor, 0)
                    endif
                elseif phase == 20 and (GetUnitX(actor) - 3200.0)*(GetUnitX(actor) - 3200.0) + (GetUnitY(actor) - 870.0)*(GetUnitY(actor) - 870.0) < 40000.0 then
                    call IssueImmediateOrder(actor, "unloadall")
                    call SetUnitUserData(actor, 21)
                elseif phase == 21 and SettlersAboard() == 0 then
                    set expansion = 2
                    call IssuePointOrder(actor, "move", 0.0, 0.0)
                    call SetUnitUserData(actor, 12)
                elseif phase == 21 then
                    // No legal landing within reach yet: nose into the island's shore, then unload again.
                    if elapsed - (elapsed/6)*6 == 0 then
                        call IssueImmediateOrder(actor, "unloadall")
                    else
                        call IssuePointOrder(actor, "move", 3400.0, 1150.0)
                    endif
                elseif phase == 20 then
                    call IssuePointOrder(actor, "move", 3200.0, 870.0)
                elseif phase == 6 and doctrine != 2 then
                    // Loaded and waiting: the craft sails only with an assault, behind the fleet.
                    call IssuePointOrder(actor, "move", 1000.0, -1000.0)
                elseif phase == 6 then
                    call IssuePointOrder(actor, "move", 0.0, 0.0)
                    call SetUnitUserData(actor, 11)
                elseif phase == 11 and GetUnitX(actor) < 500.0 and GetUnitX(actor) > -500.0 then
                    call IssuePointOrder(actor, "move", -2000.0, 2150.0)
                    call SetUnitUserData(actor, 7)
                elseif phase == 11 then
                    call IssuePointOrder(actor, "move", 0.0, 0.0)
                elseif phase == 7 and GetUnitX(actor) < -1750.0 then
                    call IssueImmediateOrder(actor, "unloadall")
                    call SetUnitUserData(actor, 8)
                    set invasions = invasions + 1
                elseif phase == 7 then
                    call IssuePointOrder(actor, "move", -2000.0, 2150.0)
                elseif phase == 8 then
                    call IssueImmediateOrder(actor, "unloadall")
                    call IssuePointOrder(actor, "move", 0.0, 0.0)
                    call SetUnitUserData(actor, 12)
                elseif phase == 12 and GetUnitX(actor) < 500.0 and GetUnitX(actor) > -500.0 then
                    call IssuePointOrder(actor, "move", 1000.0, -1000.0)
                    call SetUnitUserData(actor, 10)
                elseif phase == 12 then
                    call IssuePointOrder(actor, "move", 0.0, 0.0)
                elseif phase == 10 and GetUnitX(actor) > 800.0 then
                    call SetUnitUserData(actor, 0)
                elseif phase == 10 then
                    call IssuePointOrder(actor, "move", 1000.0, -1000.0)
                endif
            elseif id == 'finf' or id == 'fmg0' or id == 'ftnk' or id == 'fart' or id == 'faa0' or id == 'fhtk' or id == 'frkt' or id == 'fmrt' or id == 'fcmd' then
                // Rally points and unloading leave a lingering Smart order, and a
                // Move issued while its route was briefly blocked can stall, so
                // only an attack or an embarkation near the beach counts as busy.
                // Re-issuing the same staging Move is a cheap re-path.
                set order = GetUnitCurrentOrder(actor)
                set dx = GetUnitX(actor) - 2000.0
                set dy = GetUnitY(actor) + 2000.0
                if GetUnitY(actor) - GetUnitX(actor) > 3900.0 then
                    // Ashore on the enemy mainland: push to the scouted objective.
                    // Spread the target slightly so troops don't all pile into one tile;
                    // idle or move-stalled troops get a fresh attack-move to break jams.
                    if order != attackOrder then
                        set beachNow = beachNow + 1
                        call IssuePointOrder(actor, "attack", objectiveX + I2R(beachNow - (beachNow/5)*5) * 200.0 - 400.0, objectiveY + I2R(beachNow/5) * 200.0 - 400.0)
                    endif
                elseif GetUnitX(actor) - GetUnitY(actor) < 3900.0 then
                    // Garrison on a resource island: hold it rather than path home.
                elseif threats > 0 then
                    if order != attackOrder then
                        call IssuePointOrder(actor, "attack", threatX, threatY)
                    endif
                elseif order == 0 or ((order == smartOrder or order == moveOrder) and dx*dx + dy*dy > 640000.0) then
                    call IssuePointOrder(actor, "move", 2000.0, -2000.0)
                endif
            elseif id == 'frec' then
                // Scout: a circuit over the contested islands, the enemy beach, the enemy base and back home.
                if GetUnitCurrentOrder(actor) == 0 then
                    set phase = scoutLeg - (scoutLeg/6)*6
                    if phase == 0 then
                        call IssuePointOrder(actor, "move", 2400.0, 3100.0)
                    elseif phase == 1 then
                        call IssuePointOrder(actor, "move", -1800.0, 2400.0)
                    elseif phase == 2 then
                        call IssuePointOrder(actor, "move", -5000.0, 5000.0)
                    elseif phase == 3 then
                        call IssuePointOrder(actor, "move", -3600.0, -1400.0)
                    elseif phase == 4 then
                        call IssuePointOrder(actor, "move", -2400.0, -3100.0)
                    else
                        call IssuePointOrder(actor, "move", 2500.0, -2500.0)
                    endif
                    set scoutLeg = scoutLeg + 1
                endif
            elseif id == 'ffgt' then
                // Fighters hold air superiority: over a raid, over the beach during a landing, else over the base.
                if GetUnitCurrentOrder(actor) == 0 then
                    if threats > 0 then
                        call IssuePointOrder(actor, "patrol", threatX, threatY)
                    elseif doctrine == 1 or doctrine == 2 then
                        call IssuePointOrder(actor, "patrol", -1700.0, 1700.0)
                    else
                        call IssuePointOrder(actor, "patrol", 3000.0, -3000.0)
                    endif
                endif
            elseif id == 'fbmb' or id == 'ftor' then
                // Bombers are held back for a purpose: break a raid, sink a sighted fleet, or soften the objective.
                if GetUnitCurrentOrder(actor) == 0 then
                    if threats > 0 then
                        call IssuePointOrder(actor, "attack", threatX, threatY)
                    elseif navalSpotted and (id == 'ftor' or doctrine != 2) then
                        call IssuePointOrder(actor, "attack", navalX, navalY)
                    elseif doctrine == 1 or doctrine == 2 then
                        call IssuePointOrder(actor, "attack", objectiveX, objectiveY)
                    endif
                endif
            endif
        endif
    endloop
    set botLand = landNow
    set botDocks = docksNow
    set botHeavy = heavyNow
    set botEscort = escortNow
    set botLanding = landingNow
    // Doctrine: build up until the army outweighs what has been seen of the player, prepare the beach with
    // the fleet and carriers, then land in waves. A raid on the base or a bloody landing forces a regroup,
    // and every failed assault raises the force the next one waits for.
    if doctrine == 0 then
        if landNow >= assaultNeed + seenLand/2 + seenForts and craftNow > 0 then
            set doctrine = 1
            set doctrineSince = elapsed
        endif
    elseif doctrine == 1 then
        if threats >= 4 then
            set doctrine = 3
            set doctrineSince = elapsed
        elseif beachNow > 0 or warshipsNow == 0 or elapsed - doctrineSince >= 45 then
            set doctrine = 2
            set doctrineSince = elapsed
            set assaultLand = landNow
            set assaults = assaults + 1
        endif
    elseif doctrine == 2 then
        if threats >= 4 then
            set doctrine = 3
            set doctrineSince = elapsed
        elseif (elapsed - doctrineSince > 60 and landNow*3 < assaultLand) or elapsed - doctrineSince > 300 then
            set doctrine = 3
            set doctrineSince = elapsed
            if assaultNeed < 40 then
                set assaultNeed = assaultNeed + 4
            endif
        endif
    elseif elapsed - doctrineSince >= 45 then
        set doctrine = 0
        set doctrineSince = elapsed
    endif
    call SetUnitUserData(enemyHQ, botLand) // readable doctrine state for diagnostics and tests
    call DestroyGroup(army)
    call DestroyGroup(nearby)
endfunction
// Explicit cheat-console diagnostics; never run during a normal match.
function FrontlineFleetDemo takes nothing returns nothing
    if alliedCarrier == null then
        call FrontlineTestForces()
    endif
    call SelectUnit(alliedCarrier, true)
    call SetCameraPosition(-1300.0, 1300.0)
    // Carriers no longer produce — just select and position.
endfunction
function FrontlineBenchmark takes nothing returns nothing
    local integer i = 0
    local integer j = 0
    local real side
    local unit u
    call FogEnable(false)
    call FogMaskEnable(false)
    loop
        exitwhen i >= 2
        set side = -1.0 + 2.0*I2R(i)
        set j = 0
        loop
            exitwhen j >= 328
            set u = CreateUnit(Player(i), 'finf', side*(2500.0+I2R(j-(j/8)*8)*85.0), -side*(2600.0+I2R(j/8)*120.0), 0.0)
            call IssuePointOrder(u, "attack", -side*2500.0, side*2600.0)
            set j = j+1
        endloop
        set j = 0
        loop
            exitwhen j >= 16
            set u = CreateUnit(Player(i), 'fdst', side*(600.0+I2R(j-(j/2)*2)*240.0), -side*(600.0+I2R(j/2)*300.0), 0.0)
            call IssuePointOrder(u, "attack", -side*700.0, side*700.0)
            set j = j+1
        endloop
        set j = 0
        loop
            exitwhen j >= 32
            set u = CreateUnit(Player(i), 'ffgt', side*(200.0+I2R(j-(j/4)*4)*100.0), -side*(900.0+I2R(j/4)*240.0), 0.0)
            call IssuePointOrder(u, "patrol", -side*500.0, side*500.0)
            set j = j+1
        endloop
        set i = i+1
    endloop
    call FrontlineFleetDemo()
endfunction
// Same result rules for a bot or LAN opponent; a computer slot keeps the single-player screen flow.
function FrontlineDecide takes integer winner, string first, string second returns nothing
    set finished = true
    if first != "" then
        call DisplayTimedTextToPlayer(Player(0), 0.15, 0.2, 300.0, first)
    endif
    if not botOpponent and second != "" then
        call DisplayTimedTextToPlayer(Player(1), 0.15, 0.2, 300.0, second)
    endif
    call RemovePlayer(Player(1-winner), ConvertPlayerGameResult(1))
    if winner == 0 or not botOpponent then
        call RemovePlayer(Player(winner), ConvertPlayerGameResult(0))
    endif
endfunction
function RoadWireEffects takes nothing returns nothing
    local integer i = 0
    local integer p = 0
    local group g = CreateGroup()
    local group affected = CreateGroup()
    local unit u
    local unit r
    local real dx
    local real dy
    local real spd
    // Restore previously affected units to default speed.
    loop
        exitwhen i >= roadCount
        if GetWidgetLife(roadUnit[i]) > 0.0 then
            call SetUnitMoveSpeed(roadUnit[i], roadSpeed[i])
        endif
        set roadUnit[i] = null
        set i = i + 1
    endloop
    set roadCount = 0
    // Road boost: friendly ground units within 350 of a road move 35% faster.
    set p = 0
    loop
        exitwhen p >= 2
        call GroupEnumUnitsOfPlayer(g, Player(p), null)
        loop
            set r = FirstOfGroup(g)
            exitwhen r == null
            call GroupRemoveUnit(g, r)
            if GetUnitTypeId(r) == 'frod' and GetWidgetLife(r) > 0.0 then
                call GroupEnumUnitsInRange(affected, GetUnitX(r), GetUnitY(r), 350.0, null)
                loop
                    set u = FirstOfGroup(affected)
                    exitwhen u == null
                    call GroupRemoveUnit(affected, u)
                    set spd = GetUnitDefaultMoveSpeed(u)
                    if spd > 0.0 and GetWidgetLife(u) > 0.0 and IsUnitAlly(u, Player(p)) and GetUnitMoveSpeed(u) <= spd then
                        set roadUnit[roadCount] = u
                        set roadSpeed[roadCount] = spd
                        set roadCount = roadCount + 1
                        call SetUnitMoveSpeed(u, spd * 1.35)
                    endif
                endloop
            endif
        endloop
        set p = p + 1
    endloop
    // Barbed wire slow: enemy ground units within 280 of wire move 30% slower.
    set p = 0
    loop
        exitwhen p >= 2
        call GroupEnumUnitsOfPlayer(g, Player(p), null)
        loop
            set r = FirstOfGroup(g)
            exitwhen r == null
            call GroupRemoveUnit(g, r)
            if GetUnitTypeId(r) == 'fwir' and GetWidgetLife(r) > 0.0 then
                call GroupEnumUnitsInRange(affected, GetUnitX(r), GetUnitY(r), 280.0, null)
                loop
                    set u = FirstOfGroup(affected)
                    exitwhen u == null
                    call GroupRemoveUnit(affected, u)
                    set spd = GetUnitDefaultMoveSpeed(u)
                    if spd > 0.0 and GetWidgetLife(u) > 0.0 and IsUnitEnemy(u, Player(p)) then
                        set roadUnit[roadCount] = u
                        set roadSpeed[roadCount] = spd
                        set roadCount = roadCount + 1
                        call SetUnitMoveSpeed(u, spd * 0.70)
                    endif
                endloop
            endif
        endloop
        set p = p + 1
    endloop
    call DestroyGroup(g)
    call DestroyGroup(affected)
endfunction
function Tick takes nothing returns nothing
    if finished then
        return
    endif
    call RoadWireEffects()
    set elapsed = elapsed + 3
    if botOpponent then
        call BotTactics()
    elseif GetPlayerSlotState(Player(1)) == ConvertPlayerSlotState(2) then
        call FrontlineDecide(0, "VICTORY - The opposing commander left the match.", "")
        return
    elseif GetPlayerSlotState(Player(0)) == ConvertPlayerSlotState(2) then
        call FrontlineDecide(1, "", "VICTORY - The opposing commander left the match.")
        return
    endif
    if GetWidgetLife(enemyHQ) <= 0.0 then
        call FrontlineDecide(0, "VICTORY - Enemy Headquarters destroyed.", "DEFEAT - Headquarters lost.")
    elseif GetWidgetLife(alliedHQ) <= 0.0 then
        call FrontlineDecide(1, "DEFEAT - Headquarters lost.", "VICTORY - Enemy Headquarters destroyed.")
    endif
endfunction
function FrontlineNeutralAirfields takes nothing returns nothing
    call CreateUnit(Player(15), 'fair', 2200.0, 2850.0, 0.0)
    call CreateUnit(Player(15), 'fair', -2200.0, -2850.0, 0.0)
endfunction
function main takes nothing returns nothing
    local integer i = 0
    local integer j = 0
    local real side
    local unit ore
    local unit worker
    local destructable tree
    local trigger vetTrig
    call FogEnable(true)
    call FogMaskEnable(true)
    // Point-symmetric bases: Allied top-left, Opposing bottom-right; world = (side*x, -side*y).
    set alliedHQ = CreateUnit(Player(0), 'fhq0', -5400.0, 5400.0, 0.0)
    call FrontlineNeutralAirfields()
    set enemyHQ = CreateUnit(Player(1), 'fhq0', 5400.0, -5400.0, 180.0)
    loop
        exitwhen i >= 2
        set side = -1.0 + 2.0*I2R(i)
        call SetPlayerState(Player(i), ConvertPlayerState(1), 2400)
        call SetPlayerState(Player(i), ConvertPlayerState(2), 900)
        // Island stockpiles: north/south contested, east/west on each flank.
        set worker = CreateUnit(Player(15), 'eore', -side*2550.0, -side*3300.0, 0.0)
        call SetResourceAmount(worker, 20000)
        set worker = CreateUnit(Player(15), 'eore', side*3400.0, side*1150.0, 0.0)
        call SetResourceAmount(worker, 20000)
        if i == 1 then
            set eastOre = worker
        endif
        set ore = CreateUnit(Player(15), 'eore', side*6000.0, -side*6000.0, 0.0)
        call SetResourceAmount(ore, 50000)
        set homeOre[i] = ore
        set j = 0
        loop
            exitwhen j >= 16
            set tree = CreateDestructable('epin', side*(4800.0+I2R(j-(j/8)*8)*100.0), -side*(6000.0+I2R(j/8)*150.0), 0.0, 1.0, 0)
            set j = j + 1
        endloop
        set homeTree[i] = tree
        set i = i + 1
    endloop
    call SetCameraPosition(-4800.0, 4700.0)
    call DisplayTimedTextToPlayer(Player(0), 0.12, 0.035, 15.0, "FRONTLINE | Destroy enemy Headquarters.|nHQ trains Engineers. Right-click a mine to rally new workers.|nEngineers build Roads (speed boost), Sandbags (cover) and Wire (slows enemies).|n[ ] rotates a building. F10: Sound / Volume. AA fires while moving.")
    set botOpponent = GetPlayerController(Player(1)) != ConvertMapControl(0)
    if botOpponent then
        call StartMeleeAI(Player(1), "Scripts\\ember.ai")
    else
        call DisplayTimedTextToPlayer(Player(1), 0.12, 0.035, 15.0, "FRONTLINE LAN | Destroy the enemy Headquarters before yours falls.")
    endif
    call TimerStart(CreateTimer(), 3.0, true, function Tick)
    // Veterancy: units that score kills grow slightly (visual rank).
    set vetTrig = CreateTrigger()
    call TriggerAddAction(vetTrig, function OnKill)
    call TriggerRegisterPlayerUnitEvent(vetTrig, Player(0), ConvertPlayerUnitEvent(20), null)
    call TriggerRegisterPlayerUnitEvent(vetTrig, Player(1), ConvertPlayerUnitEvent(20), null)
    set vetTrig = CreateTrigger()
    call TriggerAddAction(vetTrig, function OnBuilt)
    call TriggerRegisterPlayerUnitEvent(vetTrig, Player(0), ConvertPlayerUnitEvent(28), null)
    call TriggerRegisterPlayerUnitEvent(vetTrig, Player(1), ConvertPlayerUnitEvent(28), null)
endfunction
'''

# Generate faction policy and AI lists from the same roster as production.
from tools.frontline.catalog import NAVAL
COMMON += "type mapcontrol extends handle\ntype playerslotstate extends handle\nnative GetPlayerController takes player p returns mapcontrol\nnative ConvertMapControl takes integer i returns mapcontrol\nnative GetPlayerSlotState takes player p returns playerslotstate\nnative ConvertPlayerSlotState takes integer i returns playerslotstate\n"
COMMON += "native SetPlayerAbilityAvailable takes player p, integer abilid, boolean available returns nothing\n"
COMMON += "native SetPlayerTechMaxAllowed takes player p, integer techid, integer maximum returns nothing\n"
from tools.frontline.catalog import UNITS, LAND_IJN
LAND_FACTION={code:UNITS[code] for us,(ijn,_,_) in LAND_IJN.items() for code in (us,ijn)}
from tools.frontline.catalog import FORTIFICATIONS
faction_init='\n'.join(f"    call SetPlayerTechMaxAllowed(Player({0 if u['faction']=='IJN' else 1}), '{code}', 0)" for code,u in list(NAVAL.items())+list(LAND_FACTION.items())+list(FORTIFICATIONS.items()))
# Keep script functions above their callers (the VM is deliberately small).
MAP_SCRIPT=MAP_SCRIPT.replace('function main takes nothing returns nothing',
    'function ConfigureNavies takes nothing returns nothing\n'+faction_init+'\nendfunction\nfunction main takes nothing returns nothing')
MAP_SCRIPT=MAP_SCRIPT.replace('    call FogEnable(true)',"    call ConfigureNavies()\n    call SetPlayerAbilityAvailable(Player(0), 'Fkdo', false)\n    call FogEnable(true)")
# These facilities are built normally by the map AI. Legacy shipyard doctrine
# retains priority, preserving the earlier campaign and amphibious timings.
naval_production=''
for code,u in NAVAL.items():
    if u['faction']!='IJN':continue
    naval_production+=f"        if GetUnitCount('{u['facility']}') > 0 and GetUnitCount('{code}') < 1 then\n            call SetProduce(1, '{code}', 0)\n        endif\n"
MAP_SCRIPT=MAP_SCRIPT.replace(' SEENNAVY',''.join(f" or id == '{code}'" for code in NAVAL))
MAP_SCRIPT=MAP_SCRIPT.replace(' SEENAIR',''.join(f" or id == '{p}{k}'" for p in 'uj' for k in ('fig','bom','tor')))
AI_SCRIPT=AI_SCRIPT.replace(' INTELAIR',''.join(f" or id == '{p}{k}'" for p in 'uj' for k in ('fig','bom','tor')))
AI_SCRIPT=AI_SCRIPT.replace(' NAVALTHREAT',''.join(f" or id == '{code}'" for code in NAVAL))
AI_SCRIPT=AI_SCRIPT.replace('        call Sleep(3.0)',
    "        if GetUnitCount('fesc') > 0 and GetUnitCount('flct') > 0 then\n            if GetUnitCount('fhvy') < 1 and GetUnitCount('fair') > 0 then\n                call SetProduce(1, 'fhvy', 0)\n            endif\n"+naval_production+'        endif\n        call Sleep(3.0)')
def condition(role):
    return ' or '.join(f"id == '{code}'" for code,u in NAVAL.items() if u['role'] in role)
MAP_SCRIPT=MAP_SCRIPT.replace("elseif id == 'fcvr' then", "elseif id == 'fcvr' or "+condition(['carrier'])+" then")
MAP_SCRIPT=MAP_SCRIPT.replace("elseif id == 'fbat' or id == 'fdst' or id == 'fcrs' then", "elseif id == 'fbat' or id == 'fdst' or id == 'fcrs' or "+condition(['battleship','escort'])+" then")
MAP_SCRIPT=MAP_SCRIPT.replace("elseif id == 'flct' or id == 'ftrn' then", "elseif id == 'flct' or id == 'ftrn' or "+condition(['landing'])+" then")

# Bounded visual diagnostics; none execute in a normal HQ-only match.
COMMON += "native ConvertCameraField takes integer i returns camerafield\nnative SetCameraField takes camerafield field, real value, real duration returns nothing\n"
visual=''
for page in range(7):
    visual+=f'function FrontlineHistoricalGallery{page} takes nothing returns nothing\n    local unit u\n    set finished = true\n    call FogEnable(false)\n    call FogMaskEnable(false)\n'
    for j,(code,u) in enumerate(list(NAVAL.items())[page*3:page*3+3]):
        visual+=f"    set u = CreateUnit(Player(0), '{code}', 0.0, {float((j-1)*420):.1f}, 0.0)\n"
        if j==0:visual+='    call SelectUnit(u, true)\n'
    visual+='    call SetCameraPosition(0.0, 0.0)\n    call SetCameraField(ConvertCameraField(0), 1700.0, 0.0)\nendfunction\n'
visual+='''// Both fleets launch a coordinated carrier strike once their air groups are built.
function FrontlineHistoricalStrike takes nothing returns nothing
    local group g = CreateGroup()
    local unit u
    local integer p = 0
    loop
        exitwhen p >= 2
        call GroupEnumUnitsOfPlayer(g, Player(p), null)
        loop
            set u = FirstOfGroup(g)
            exitwhen u == null
            call GroupRemoveUnit(g, u)
            call IssuePointOrder(u, "airstrike", 0.0, 0.0)
        endloop
        set p = p + 1
    endloop
    call DestroyGroup(g)
endfunction
'''
visual+='function FrontlineHistoricalBattle takes nothing returns nothing\n    local unit u\n    set finished = true\n    call FogEnable(false)\n    call FogMaskEnable(false)\n'
for owner,codes in [(0,['uiow','umss','uflt','uclv','uent']),(1,['jyam','jnag','jfub','jmog','jakg'])]:
    for j,code in enumerate(codes):
        x=(-700 if owner==0 else 700) if j<4 else (-1450 if owner==0 else 1450)
        y=(j-1.5)*380 if j<4 else 850
        visual+=f"    set u = CreateUnit(Player({owner}), '{code}', {float(x):.1f}, {y:.1f}, {float(owner*180):.1f})\n"
        visual+=f'    call IssuePointOrder(u, "attack", {float(-x):.1f}, {y:.1f})\n'
visual+='    call SetCameraPosition(0.0, 0.0)\n    call SetCameraField(ConvertCameraField(0), 2400.0, 0.0)\n    call TimerStart(CreateTimer(), 25.0, false, function FrontlineHistoricalStrike)\nendfunction\n'
MAP_SCRIPT=MAP_SCRIPT.replace('function Tick takes nothing returns nothing',visual+'function Tick takes nothing returns nothing')

# Client connection applies its initial camera after map main. Reassert the
# diagnostic view from a timer after that lifecycle has completed.
# Close inspection of the gallery's middle hull (cheat-console diagnostics only).
MAP_SCRIPT=MAP_SCRIPT.replace('function Tick takes nothing returns nothing','function FrontlineCloseView takes nothing returns nothing\n    call SetCameraField(ConvertCameraField(0), 620.0, 0.0)\nendfunction\nfunction Tick takes nothing returns nothing')
view='function FrontlineHistoricalView takes nothing returns nothing\n    call FogEnable(false)\n    call FogMaskEnable(false)\n    call SetCameraPosition(0.0, 0.0)\n    call SetCameraField(ConvertCameraField(0), 1700.0, 0.0)\nendfunction\n'
MAP_SCRIPT=MAP_SCRIPT.replace('function FrontlineHistoricalGallery0',view+'function FrontlineHistoricalGallery0')
MAP_SCRIPT=MAP_SCRIPT.replace('    call SetCameraField(ConvertCameraField(0), 1700.0, 0.0)\nendfunction',
    '    call SetCameraField(ConvertCameraField(0), 1700.0, 0.0)\n    call TimerStart(CreateTimer(), 2.0, false, function FrontlineHistoricalView)\nendfunction')
# Do not let the camera callback recursively schedule itself.
MAP_SCRIPT=MAP_SCRIPT.replace(view.replace('endfunction','    call TimerStart(CreateTimer(), 2.0, false, function FrontlineHistoricalView)\nendfunction'),view)

COMMON += "native ClearTextMessages takes nothing returns nothing\n"
MAP_SCRIPT=MAP_SCRIPT.replace('    set finished = true\n    call FogEnable(false)',
    '    set finished = true\n    call ClearTextMessages()\n    call FogEnable(false)')

# Art showcase (cheat-console diagnostics only): a close land battle and a dressed
# base on the USN mainland, fog off. The camera is reasserted from a timer after
# client connection, like FrontlineHistoricalView.
def _showcase(name,x,y,distance,units):
    body=''.join(f"    call CreateUnit(Player({p}), '{code}', {ux:.1f}, {uy:.1f}, {facing:.1f})\n" for p,code,ux,uy,facing in units)
    camera=f'function {name}View takes nothing returns nothing\n    call ClearTextMessages()\n    call FogEnable(false)\n    call FogMaskEnable(false)\n    call SetCameraPosition({x:.1f}, {y:.1f})\n    call SetCameraField(ConvertCameraField(0), {distance:.1f}, 0.0)\nendfunction\n'
    return camera+f'function {name} takes nothing returns nothing\n'+body+f'    call TimerStart(CreateTimer(), 2.0, false, function {name}View)\nendfunction\n'
_battle=[(p,code,-3000+(1 if p==1 else -1)*(140+col*75),3300+(row-2)*75,180.0 if p==1 else 0.0)
         for p in (0,1) for row,code in enumerate(('finf','fmg0','fcmd','fmrt','finf')) for col in range(2)]
_battle+=[(p,code,-3000+(1 if p==1 else -1)*x,3300+y,180.0 if p==1 else 0.0) for p in (0,1)
          for code,x,y in (('ftnk',360,-90),('fhtk',380,110),('fcar',330,260),('fart',470,-250),('fwkr',520,40))]
_air=[(0,code,-3600+i*170,4700+(i%2)*120,90.0) for i,code in enumerate(('ffgt','fbmb','frec','ufig','ubom','utor'))]
_air+=[(1,code,-3600+i*170,4350+(i%2)*120,90.0) for i,code in enumerate(('ffgt','fbmb','frec','jfig','jbom','jtor'))]
_base=[(0,code,x,y,270.0) for code,x,y in (('fhq0',-4300,3900),('fbar',-3950,3550),('fdep',-4650,3550),('ffac',-3900,4250),
        ('fbn2',-4300,3420),('fwat',-4600,3350),('fsbg',-4150,3330),('fwat',-4000,3300),('eore',-4700,4200))]
_base+=[(0,'fwkr',-4450+i*55,3700,270.0) for i in range(4)]+[(0,'ftnk',-4050,3950,240.0)]
from tools.frontline.catalog import LAND_IJN as _LAND_IJN
_battle=[(p,_LAND_IJN[code][0] if p==1 and code in _LAND_IJN else code,x,y,f) for p,code,x,y,f in _battle]   # player 1 fields the IJN set
MAP_SCRIPT=MAP_SCRIPT.replace('function Tick takes nothing returns nothing',
    _showcase('FrontlineVisualBattle',-3000,3250,1050,_battle)+_showcase('FrontlineVisualAir',-3200,4500,1050,_air)+_showcase('FrontlineVisualBase',-4300,3700,1250,_base)+'function Tick takes nothing returns nothing',1)

# Japanese land variants: every type check accepts either side's code, and the map AI
# (the IJN side on IslandCommand) counts and trains its own Japanese units. usn.ai, for
# the swapped map, keeps the US codes (generate.extra_maps).
import re as _re
_LAND=_re.compile(r"((?:\w+\([^()]*\))|\b\w+) == '("+'|'.join(LAND_IJN)+r")'")
def _either(script):
    # Every match sits in an or-chain (or inside its parentheses), so no new grouping is needed;
    # the small JASS parser rejects a parenthesised term followed by `or`.
    return _LAND.sub(lambda m:f"{m[1]} == '{m[2]}' or {m[1]} == '{LAND_IJN[m[2]][0]}'",script)
MAP_SCRIPT=_either(MAP_SCRIPT)
AI_SCRIPT_USN=_either(AI_SCRIPT)
AI_SCRIPT=AI_SCRIPT_USN
for _us,(_ijn,_,_) in LAND_IJN.items():
    AI_SCRIPT=AI_SCRIPT.replace(f"GetUnitCount('{_us}')",f"GetUnitCount('{_ijn}')").replace(f"SetProduce(1, '{_us}'",f"SetProduce(1, '{_ijn}'")

# No generic ships: each bot counts and builds its own navy's escort and landing classes.
NAVY_FOR={'IJN':{'fdst':'jfub','fcrs':'jmog','flct':'jdai'},'USN':{'fdst':'uflt','fcrs':'uclv','flct':'ulcm'}}
def _navy(script,faction):
    for generic,code in NAVY_FOR[faction].items():
        script=script.replace(f"GetUnitCount('{generic}')",f"GetUnitCount('{code}')").replace(f"SetProduce(1, '{generic}'",f"SetProduce(1, '{code}'")
    return script
AI_SCRIPT=_navy(AI_SCRIPT,'IJN')
AI_SCRIPT_USN=_navy(AI_SCRIPT_USN,'USN')

# No generic bunker on the engineer card: each bot builds its own navy's pillbox, and the
# map-start bunker still counts toward its defences.
def _pillbox(script,code):
    return script.replace("SetProduce(1, 'fbnk', 0)",f"SetProduce(1, '{code}', 0)").replace("GetUnitCount('fbnk')",f"GetUnitCount('fbnk') + GetUnitCount('{code}')")
AI_SCRIPT=_pillbox(AI_SCRIPT,'jpbx')
AI_SCRIPT_USN=_pillbox(AI_SCRIPT_USN,'upbx')

# ---------------------------------------------------------------------------------------------
# Pacific theatre (tools/frontline/pacific.py). The Island Command script above keeps its literal
# coordinates (the acceptance tests run on that map); theater_script() rewrites every map-specific
# position into the Pacific site table, by the navy each player commands. Player(1) is the bot.
def theater_script(script, p0_navy):
    import math
    from tools.frontline import pacific
    p1_navy = 'IJN' if p0_navy == 'USN' else 'USN'
    hq0, hq1 = pacific.HQ[p0_navy], pacific.HQ[p1_navy]
    sea0, sea1 = pacific.STAGING[p0_navy], pacific.STAGING[p1_navy]
    yard1, outpost1 = pacific.SHIPYARD[p1_navy], pacific.OUTPOST[p1_navy]
    ore_at = {name: (x, y) for name, x, y in pacific.ORE}
    out_ore = {n: ore_at[pacific.OUTPOST_ISLAND[n]] for n in ('USN', 'IJN')}
    def offshore(x, y, tx, ty, beyond=250):
        """Step from (x, y) toward (tx, ty) until open water, then `beyond` further: a landing approach."""
        d = math.hypot(tx - x, ty - y) or 1
        for s in range(0, int(d), 25):
            px, py = x + (tx - x) * s / d, y + (ty - y) * s / d
            if not pacific.land(px, py):
                return px + (tx - x) * beyond / d, py + (ty - y) * beyond / d
        return tx, ty
    land1 = getattr(pacific, 'LANDING', {}).get(p1_navy) or offshore(*outpost1, *sea1)
    mid = ((sea0[0] + sea1[0]) / 2, (sea0[1] + sea1[1]) / 2)
    # Invasion beach: just off the player's coast between their HQ and their staging waters, close
    # enough for the craft to unload (hull + passenger + 192 world units).
    beach0 = offshore(*hq0, *sea0, 110)
    def trees(n):
        hx, hy = pacific.HOME_ORE[n]
        pts = []
        for ring in (450, 600, 750, 900):
            for a in range(24):
                x, y = hx + ring * math.cos(a * math.pi / 12), hy + ring * math.sin(a * math.pi / 12)
                if len(pts) < 16 and pacific.coast_clear(x, y, 150) and math.hypot(x - pacific.HQ[n][0], y - pacific.HQ[n][1]) > 600:
                    pts.append((x, y))
        return pts
    f = lambda v: f'{v:.1f}'
    xy = lambda p: f'{f(p[0])}, {f(p[1])}'
    near = lambda x, y, r: f'IsUnitInRangeXY(actor, {f(x)}, {f(y)}, {f(r)})'
    home = near(*hq1, 4500)
    # Island literal -> Pacific site. Each pair is an exact substring of the Island script.
    subs = [
        ('real objectiveX = -5400.0', f'real objectiveX = {f(hq0[0])}'), ('real objectiveY = 5400.0', f'real objectiveY = {f(hq0[1])}'),
        ('(GetUnitX(u) - 1500.0)*(GetUnitX(u) - 1500.0) + (GetUnitY(u) + 1500.0)*(GetUnitY(u) + 1500.0)',
         f'(GetUnitX(u) - {f(sea1[0])})*(GetUnitX(u) - {f(sea1[0])}) + (GetUnitY(u) - {f(sea1[1])})*(GetUnitY(u) - {f(sea1[1])})'),
        ('(navalX - 1500.0)*(navalX - 1500.0) + (navalY + 1500.0)*(navalY + 1500.0)',
         f'(navalX - {f(sea1[0])})*(navalX - {f(sea1[0])}) + (navalY - {f(sea1[1])})*(navalY - {f(sea1[1])})'),
        ('(GetUnitX(u) + 2000.0)*(GetUnitX(u) + 2000.0) + (GetUnitY(u) - 2150.0)*(GetUnitY(u) - 2150.0)',
         f'(GetUnitX(u) - {f(sea0[0])})*(GetUnitX(u) - {f(sea0[0])}) + (GetUnitY(u) - {f(sea0[1])})*(GetUnitY(u) - {f(sea0[1])})'),
        ('local real threatX = 3000.0', f'local real threatX = {f(hq1[0])}'), ('local real threatY = -3000.0', f'local real threatY = {f(hq1[1])}'),
        ('GroupEnumUnitsInRange(nearby, 4000.0, -4000.0, 3000.0, null)', f'GroupEnumUnitsInRange(nearby, {xy(hq1)}, 4500.0, null)'),
        ("id == 'fhq0' and GetUnitX(actor) > 3000.0 and GetUnitY(actor) > 700.0", f"id == 'fhq0' and {near(*outpost1, 1500)}"),
        ('GetUnitX(actor) - GetUnitY(actor) > 3900.0', home),
        ('GetUnitX(actor) - GetUnitY(actor) < 3900.0', f'not {home}'),
        ('GetUnitX(other) - GetUnitY(other) > 3900.0', f'IsUnitInRangeXY(other, {xy(hq1)}, 4500.0)'),
        ('GetUnitY(actor) - GetUnitX(actor) > 3900.0', near(*hq0, 4500)),
        ('call IssueBuildOrderById(actor, yard, 2400.0, -1900.0)', f'call IssueBuildOrderById(actor, yard, {xy(yard1)})'),
        ('call IssueBuildOrderById(actor, yard, 3000.0, -1400.0)', f'call IssueBuildOrderById(actor, yard, {xy((yard1[0]+250, yard1[1]+250))})'),
        ('call IssueBuildOrderById(actor, yard, 1800.0, -2600.0)', f'call IssueBuildOrderById(actor, yard, {xy((yard1[0]-250, yard1[1]-250))})'),
        ('call IssueBuildOrderById(actor, yard, 2700.0, -1700.0)', f'call IssueBuildOrderById(actor, yard, {xy((yard1[0]+250, yard1[1]-250))})'),
    ]
    lerp = lambda t: (hq1[0] + (yard1[0] - hq1[0]) * t, hq1[1] + (yard1[1] - hq1[1]) * t)
    subs += [
        ("'frod', 4200.0, -3800.0", f"'frod', {xy(lerp(.3))}"), ("'frod', 3200.0, -2800.0", f"'frod', {xy(lerp(.6))}"),
        ("'fsbg', 5000.0, -5800.0", f"'fsbg', {xy(lerp(.15))}"), ("'fwir', 4600.0, -4400.0", f"'fwir', {xy(lerp(.45))}"),
        ('set dx = GetUnitX(actor) - 3800.0\n                    set dy = GetUnitY(actor) - 1650.0',
         f'set dx = GetUnitX(actor) - {f(outpost1[0])}\n                    set dy = GetUnitY(actor) - {f(outpost1[1])}'),
        ("IssueBuildOrderById(actor, 'fhq0', 3800.0, 1650.0)", f"IssueBuildOrderById(actor, 'fhq0', {xy(outpost1)})"),
        ('set dx = GetUnitX(actor) + 1700.0\n                set dy = GetUnitY(actor) - 1700.0',
         f'set dx = GetUnitX(actor) - {f(sea0[0])}\n                set dy = GetUnitY(actor) - {f(sea0[1])}'),
        ('"attack", 1500.0, -1500.0', f'"attack", {xy(sea1)}'), ('"move", 1500.0, -1500.0', f'"move", {xy(sea1)}'),
        ('"attack", -1700.0, 1700.0', f'"attack", {xy(sea0)}'), ('"patrol", -1700.0, 1700.0', f'"patrol", {xy(sea0)}'),
        ('"patrol", 1800.0, 2300.0', f'"patrol", {xy(mid)}'),
        ('"move", 1000.0, -1000.0', f'"move", {xy(sea1)}'),
        ('GroupEnumUnitsInRange(nearby, 1800.0, -1800.0, 1200.0, null)', f'GroupEnumUnitsInRange(nearby, {xy(yard1)}, 1500.0, null)'),
        ('"move", 3200.0, 870.0', f'"move", {xy(land1)}'),
        ('(GetUnitX(actor) - 3200.0)*(GetUnitX(actor) - 3200.0) + (GetUnitY(actor) - 870.0)*(GetUnitY(actor) - 870.0) < 40000.0', near(*land1, 300)),
        ('"move", 3400.0, 1150.0', f'"move", {xy(outpost1)}'),
        ('"move", 0.0, 0.0', f'"move", {xy(mid)}'),
        ('call LCUnstick(actor, 0.0, 0.0)', f'call LCUnstick(actor, {xy(mid)})'),
        ('GetUnitX(actor) < 500.0 and GetUnitX(actor) > -500.0', near(*mid, 1200)),
        ('"move", -2000.0, 2150.0', f'"move", {xy(beach0)}'),
        ('GetUnitX(actor) < -1750.0', near(*beach0, 300)),
        ('GetUnitX(actor) > 800.0', near(*sea1, 1500)),
        ('set dx = GetUnitX(actor) - 2000.0\n                set dy = GetUnitY(actor) + 2000.0',
         f'set dx = GetUnitX(actor) - {f(yard1[0])}\n                set dy = GetUnitY(actor) - {f(yard1[1])}'),
        ('"move", 2000.0, -2000.0', f'"move", {xy(yard1)}'),
        ('"move", 2400.0, 3100.0', f'"move", {xy(mid)}'), ('"move", -1800.0, 2400.0', f'"move", {xy(out_ore[p0_navy])}'),
        ('"move", -5000.0, 5000.0', f'"move", {xy(hq0)}'), ('"move", -3600.0, -1400.0', f'"move", {xy(sea0)}'),
        ('"move", -2400.0, -3100.0', f'"move", {xy(outpost1)}'), ('"move", 2500.0, -2500.0', f'"move", {xy(sea1)}'),
        ('"patrol", 3000.0, -3000.0', f'"patrol", {xy(hq1)}'),
    ]
    # main(): headquarters, home and outpost stockpiles and the home groves, by navy.
    ore = lambda p, n: f"CreateUnit(Player(15), 'eore', {xy(p)}, 0.0)"
    grove = lambda i, n: ''.join(f"            set tree = CreateDestructable('epin', {xy(p)}, 0.0, 1.0, 0)\n" for p in trees(n))
    subs += [
        ("set alliedHQ = CreateUnit(Player(0), 'fhq0', -5400.0, 5400.0, 0.0)", f"set alliedHQ = CreateUnit(Player(0), 'fhq0', {xy(hq0)}, 0.0)"),
        ("set enemyHQ = CreateUnit(Player(1), 'fhq0', 5400.0, -5400.0, 180.0)", f"set enemyHQ = CreateUnit(Player(1), 'fhq0', {xy(hq1)}, 180.0)"),
        ("        set worker = CreateUnit(Player(15), 'eore', -side*2550.0, -side*3300.0, 0.0)\n        call SetResourceAmount(worker, 20000)\n",
         ''),
        ("set worker = CreateUnit(Player(15), 'eore', side*3400.0, side*1150.0, 0.0)",
         f"if i == 0 then\n            set worker = {ore(out_ore[p0_navy], p0_navy)}\n        else\n            set worker = {ore(out_ore[p1_navy], p1_navy)}\n        endif"),
        ("set ore = CreateUnit(Player(15), 'eore', side*6000.0, -side*6000.0, 0.0)",
         f"if i == 0 then\n            set ore = {ore(pacific.HOME_ORE[p0_navy], p0_navy)}\n        else\n            set ore = {ore(pacific.HOME_ORE[p1_navy], p1_navy)}\n        endif"),
        ("        set j = 0\n        loop\n            exitwhen j >= 16\n            set tree = CreateDestructable('epin', side*(4800.0+I2R(j-(j/8)*8)*100.0), -side*(6000.0+I2R(j/8)*150.0), 0.0, 1.0, 0)\n            set j = j + 1\n        endloop\n",
         f"        if i == 0 then\n{grove(0, p0_navy)}        else\n{grove(1, p1_navy)}        endif\n"),
        ('call SetCameraPosition(-4800.0, 4700.0)', f'call SetCameraPosition({xy(hq0)})'),
    ]
    island_fields = ''.join(f"    call CreateUnit(Player(15), 'fair', {x:.1f}, {y:.1f}, 0.0)\n" for x, y in ((2200, 2850), (-2200, -2850)))
    subs.append(('function FrontlineNeutralAirfields takes nothing returns nothing\n' + island_fields,
                 'function FrontlineNeutralAirfields takes nothing returns nothing\n' +
                 ''.join(f"    call CreateUnit(Player(15), 'fair', {xy(p)}, 0.0)\n" for p in pacific.airfield_sites())))
    for old, new in subs:
        assert old in script, old
        script = script.replace(old, new)
    return script
COMMON += "native IsUnitInRangeXY takes unit whichUnit, real x, real y, real distance returns boolean\n"
def set_theater(script, theater, navy0):
    """generate.py hook: Island Command keeps its literal coordinates; the Pacific maps are re-targeted."""
    return theater_script(script, navy0) if theater == 'pacific' else script
