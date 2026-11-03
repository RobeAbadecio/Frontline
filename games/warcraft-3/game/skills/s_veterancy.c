/* Frontline combat ranks, structure salvage and shipyard repair, authored by the original pack.
 * The map script counts kills and swaps the rank alias (Fvt1 Veteran, Fvt2 Elite);
 * this procedure owns only the stat change, so ranks never touch the save layout
 * beyond the existing added-ability list and temporary bonus ledgers. */
#include "s_skills.h"

/* Average of the authored dice roll plus base: a percentage bonus stays fair
 * across rifles (17) and battleships (150). */
static float veterancy_base_damage(edict_t const *ent) {
    unitAttack_t const *attack = ent->unit_state->attack1.numberOfDice ? &ent->unit_state->attack1 : &ent->unit_state->attack2;
    if (!attack->numberOfDice) return 0;
    return (float)attack->damageBase + attack->numberOfDice * (attack->sidesPerDie + 1) * 0.5f;
}

/* Fvet: A=damage fraction, B=armor, C=fraction of max HP repaired per second. */
static void veterancy_apply(edict_t *ent, uint32_t code, float sign) {
    if (!ent || !ent->unit_state || !code) return;
    G_ApplyTemporaryAttackDamageBonus(ent, sign * roundf(veterancy_base_damage(ent) * S_SpellData(code, 1, 1)));
    G_ApplyTemporaryArmorBonus(ent, sign * S_SpellData(code, 1, 2));
}

BZ_ABILITY_PROC(CAbilityVeterancy) {
    uint32_t const code = call && call->item ? call->item->code : 0;
    switch (msg) {
    case A_ENABLE: veterancy_apply(ent, code, 1); return true;
    case A_DISABLE: veterancy_apply(ent, code, -1); return true;
    case A_UPDATE: {
        /* Updates run for every unit with no payload: gate to once a second per unit
         * and on missing health before resolving this unit's rank alias. */
        if (!ent || M_IsDead(ent) || ent->health.max_value <= 0 || ent->health.value >= ent->health.max_value || S_IsShip(ent) ||
            (G_Time() + (uint32_t)ent->s.number * 37) % 1000 >= FRAMETIME) return false;
        abilityAliasRef_t const ref = S_ResolveAbilityAlias(ent, MAKEFOURCC('F', 'v', 'e', 't'));
        float const repair = ref.alias ? S_SpellData(ref.alias, 1, 3) : 0;
        if (repair <= 0) return false;
        ent->health.value = MIN(ent->health.max_value, ent->health.value + ent->health.max_value * repair);
        return true;
    }
    default: return CAbilityPassive(ent, msg, call);
    }
}

/* Fsel salvage: A=refund fraction of the structure's materiel and logistics cost.
 * Busy or unfinished structures are refused; the existing Cancel covers those. */
static bool salvage_structure(gameClient_t *client, edict_t *building, uint32_t code) {
    UnitBalance_t const *cost = G_UnitBalance(building->class_id);
    float const fraction = S_SpellData(code, 1, 1);
    if (!cost || M_IsDead(building) || building->construction || building->build ||
        G_UnitHasFlag(building, UNIT_FLAG_TRAINING) || G_BuildingUpgradeActive(building)) return false;
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD] = (uint16_t)MIN(USHRT_MAX,
        (int32_t)client->ps.stats[PLAYERSTATE_RESOURCE_GOLD] + (int32_t)(MAX(0, cost->goldCost) * fraction));
    client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER] = (uint16_t)MIN(USHRT_MAX,
        (int32_t)client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER] + (int32_t)(MAX(0, cost->lumberCost) * fraction));
    unit_die(building, NULL);
    return true;
}

BZ_ABILITY_PROC(CAbilitySellStructure) {
    edict_t *clent = call && call->entity ? call->entity : ent;
    uint32_t const code = call && call->item ? call->item->code : 0;
    bool sold = false, refused = false;
    if (msg != A_COMMAND) return false;
    if (!clent || !clent->client || !code) return false;
    FOR_CONTROLLABLE_SELECTED_UNITS(clent->client, building) {
        if (!G_UnitAbilityLevel(building, code)) continue;
        if (salvage_structure(clent->client, building, code)) sold = true;
        else refused = true;
    }
    if (!sold && refused) G_ShowCommandErrorText(clent, "Finish or cancel production before selling this structure.");
    G_InvalidateCommands(clent->client);
    return sold;
}

/* Ships are repaired only in a dry dock (no regeneration at sea; ranks do not repair them).
 * Fdck on a shipyard: A=fraction of max HP restored per second while berthed, B=distance
 * beyond the yard's hull within which an idle damaged friendly ship is taken in, C..H=berth
 * centres (x,y) x3 in the yard model's space (tools/frontline/drydock.py BERTHS; berth 0 is the
 * graving dock, bow in). A berthed ship is held at its berth with the gate shut until repaired
 * (hull and turrets), then sails out; any player order that moves it away releases it. A ship
 * the yard has just built is launched from the slip and pushed out to sea. */
#define DOCK_UNDER_FIRE_MS 5000u
#define DOCK_SLIDE 40.0f        /* units per frame while warping into a berth */
#define DOCK_EXIT 520.0f        /* seaward distance a launched or repaired ship sails to */
#define DOCK_BERTHS 3
typedef struct { uint32_t map, spawn_time; edict_t *yard; uint32_t yard_spawn; uint8_t berth, settled; } dockState_t;
static dockState_t dock_state[MAX_ENTITIES];

bool S_IsShip(edict_t const *ent) {
    return ent && !(ent->aiflags & AI_FLYING) && ent->data.UnitBalance && ent->data.UnitBalance->speed > 0 &&
           M_UnitStaticPathingFlags((edict_t *)ent) == CM_PATHING_UNSWIMMABLE;
}

/* Fallbacks until the presentation lands; the game library is a unity build, so a weak and a
 * strong definition would collide: s_dock_fx.c (earlier in the unit) defines BZ_DOCK_FX. */
#ifndef BZ_DOCK_FX
__attribute__((weak)) void S_DockGate(edict_t *dock, bool open) { (void)dock; (void)open; }
__attribute__((weak)) void S_ShipLaunchFx(edict_t *ship, edict_t *dock) { (void)ship; (void)dock; }
#endif

static dockState_t *dock_record(edict_t const *ship) {
    uint32_t const index = ship ? (uint32_t)(ship - globals.edicts) : MAX_ENTITIES;
    if (index >= MAX_ENTITIES) return NULL;
    dockState_t *d = &dock_state[index];
    if (d->spawn_time != ship->spawn_time || d->map != S_SideTableGeneration())
        *d = (dockState_t){ .map = S_SideTableGeneration(), .spawn_time = ship->spawn_time };
    return d;
}

static edict_t *dock_yard(dockState_t const *d) {
    return d && d->yard && d->yard->inuse && d->yard->spawn_time == d->yard_spawn && !M_IsDead(d->yard) ? d->yard : NULL;
}

bool S_ShipDocked(edict_t const *ship) {
    dockState_t *d = dock_record(ship);
    return d && dock_yard(d) && d->settled;
}

/* Berth b of the yard in world space: model (x, y) rotated by the building's angle. */
static vec2_t dock_berth(edict_t const *yard, uint32_t alias, uint32_t b, float *heading) {
    float const x = S_SpellData(alias, 1, 3 + b * 2), y = S_SpellData(alias, 1, 4 + b * 2);
    float const c = cosf(yard->s.angle), s = sinf(yard->s.angle);
    if (heading) *heading = yard->s.angle + (b == 0 ? (float)M_PI : 0.0f);
    return (vec2_t){ yard->s.origin.x + c * x - s * y, yard->s.origin.y + s * x + c * y };
}

static vec2_t dock_exit(edict_t const *yard, vec2_t berth) {
    return (vec2_t){ berth.x + cosf(yard->s.angle) * DOCK_EXIT, berth.y + sinf(yard->s.angle) * DOCK_EXIT };
}

static bool dock_berth_taken(edict_t const *yard, uint32_t b, edict_t const *except) {
    FILTER_EDICTS(e, e->inuse && e != except && S_IsShip(e) && !M_IsDead(e)) {
        dockState_t *d = dock_record(e);
        if (d && dock_yard(d) == yard && d->berth == b) return true;
    }
    return false;
}

/* Berths are authored for the dock model; a hull too big for one, or a yard built against an
 * odd coastline, is put at the nearest spot its pathing allows so it never ends up stuck. */
static void dock_place(edict_t *ship, vec2_t at, float heading) {
    vec2_t free;
    if (!G_FindUnitUnstuckPosition(ship, &at, &free)) return;
    ship->s.origin.x = free.x; ship->s.origin.y = free.y; ship->s.origin2 = free;
    ship->s.angle = heading;
    gi.LinkEntity(ship);
}

static void dock_release(edict_t *ship, dockState_t *d, bool sail_out) {
    edict_t *yard = dock_yard(d);
    if (yard) {
        uint32_t const alias = S_ResolveAbilityAlias(yard, MAKEFOURCC('F', 'd', 'c', 'k')).alias;
        vec2_t const berth = dock_berth(yard, alias, d->berth, NULL);
        S_DockGate(yard, true);
        if (sail_out) { vec2_t const out = dock_exit(yard, berth); unit_issueorder(ship, "move", &out); }
    }
    d->yard = NULL; d->settled = 0;
}

/* A ship this yard has just trained (s_train.c) starts in the slip and is pushed out to sea;
 * a rally point, applied right after, replaces the seaward run. */
void S_DockLaunch(edict_t *yard, edict_t *ship) {
    abilityAliasRef_t const ref = yard ? S_ResolveAbilityAlias(yard, MAKEFOURCC('F', 'd', 'c', 'k')) : (abilityAliasRef_t){0};
    if (!ref.alias || !S_IsShip(ship)) return;
    float heading;
    /* The outboard berth (2) is open water beyond the pier, so even a fleet carrier clears it. */
    vec2_t const slip = dock_berth(yard, ref.alias, 2, &heading);
    vec2_t const out = dock_exit(yard, slip);
    dock_place(ship, slip, heading);
    S_DockGate(yard, true);
    S_ShipLaunchFx(ship, yard);
    unit_issueorder(ship, "move", &out);
}

static bool dock_needs_work(edict_t const *ship) {
    return ship->health.value < ship->health.max_value || S_NavalBatteryFraction(ship) < 1.0f;
}

static bool dock_idle(edict_t const *ship) {
    return !ship->currentmove || !ship->currentmove->animation || strcmp(ship->currentmove->animation, "walk");
}

/* Every frame: hold berthed ships and slide arriving ones in. Once a second: launch new
 * ships, take in idle damaged ones, repair, and release repaired ones. */
BZ_ABILITY_PROC(CAbilityDockRepair) {
    if (msg != A_UPDATE) return CAbilityPassive(ent, msg, call);
    /* Updates run for every unit every frame: rule out everything that is not a finished
     * structure before any ability lookup. */
    if (!ent || !G_UnitIsStructure(ent) || M_IsDead(ent) || ent->construction) return false;
    abilityAliasRef_t const ref = S_ResolveAbilityAlias(ent, MAKEFOURCC('F', 'd', 'c', 'k'));
    if (!ref.alias) return false;
    bool const second = (G_Time() + (uint32_t)ent->s.number * 31) % 1000 < FRAMETIME;
    float const rate = S_SpellData(ref.alias, 1, 1), reach = ent->collision + S_SpellData(ref.alias, 1, 2);
    bool worked = false, berthed = false;
    FILTER_EDICTS(ship, ship->inuse && S_IsShip(ship) && !M_IsDead(ship) && ship->s.player == ent->s.player &&
                  !(ship->s.renderfx & RF_HIDDEN) && Vector2_distance(&ship->s.origin2, &ent->s.origin2) <= reach + 600) {
        dockState_t *d = dock_record(ship);
        if (!d) continue;
        float heading;
        if (dock_yard(d) == ent) {
            vec2_t const berth = dock_berth(ent, ref.alias, d->berth, &heading);
            if (!dock_idle(ship)) { dock_release(ship, d, false); continue; } /* the player moved it */
            float const gap = Vector2_distance(&ship->s.origin2, &berth);
            if (!d->settled && gap > DOCK_SLIDE) {
                vec2_t const before = ship->s.origin2;
                vec2_t const step = { ship->s.origin2.x + (berth.x - ship->s.origin2.x) * DOCK_SLIDE / gap,
                                      ship->s.origin2.y + (berth.y - ship->s.origin2.y) * DOCK_SLIDE / gap };
                dock_place(ship, step, heading);
                /* Still sliding unless the hull can go no further (it then berths where it is). */
                if (Vector2_distance(&before, &ship->s.origin2) > 1.0f) continue;
            }
            if (!d->settled) dock_place(ship, gap <= DOCK_SLIDE ? berth : ship->s.origin2, heading);
            else { ship->s.angle = heading; }
            if (!d->settled) { d->settled = 1; S_DockGate(ent, false); G_InvalidateUnitInfoPanel(ship); }
            berthed = true;
            if (!second) continue;
            if (!S_BallisticUnderFire(ship, DOCK_UNDER_FIRE_MS)) {
                ship->health.value = MIN(ship->health.max_value, ship->health.value + ship->health.max_value * rate);
                if (ship->health.value >= ship->health.max_value) S_NavalRepairMounts(ship);
                worked = true;
            }
            if (!dock_needs_work(ship)) dock_release(ship, d, true);
            continue;
        }
        if (!second || dock_yard(d)) continue;
        /* An idle damaged ship alongside is taken into a free berth. */
        if (!dock_needs_work(ship) || !dock_idle(ship) || Vector2_distance(&ship->s.origin2, &ent->s.origin2) > reach) continue;
        FOR_LOOP(b, DOCK_BERTHS) if (!dock_berth_taken(ent, b, ship)) {
            d->yard = ent; d->yard_spawn = ent->spawn_time; d->berth = (uint8_t)b; d->settled = 0;
            order_stop(ship);
            S_DockGate(ent, true);
            break;
        }
    }
    /* The yard plays Stand Work while a ship is berthed (drydock.py), Stand otherwise. */
    if (second) G_AddUnitAnimationProperties(ent, "work", berthed);
    return worked;
}

/* Command Both "View Side" (Fviw on the headquarters): the human keeps command of both
 * navies but sees the fog of one side at a time; each press switches USN <-> IJN. */
BZ_ABILITY_PROC(CAbilityViewSide) {
    edict_t *clent = call && call->entity ? call->entity : ent;
    if (msg != A_COMMAND || !clent || !clent->client) return false;
    if (!game.command_all) {
        G_ShowCommandErrorText(clent, "View Side is only available in Command Both.");
        return false;
    }
    uint32_t const current = game.view_side ? game.view_side - 1 : clent->client->ps.number;
    uint32_t const next = current == 0 ? 1 : 0;
    game.view_side = next + 1;
    UI_ShowText(clent, &(vec2_t){0.15f, 0.25f}, next == 0 ? "Viewing the USN side: you see what US forces see." :
                                                           "Viewing the IJN side: you see what Japanese forces see.", 4.0f);
    G_FowSendFull(clent);
    G_InvalidateCommands(clent->client);
    return true;
}

/* Leash (Flsh, Frontline only): a unit that engaged an enemy on its own, from idle, gives up
 * the chase once it is A beyond where it stood and walks back, so idle troops hold their
 * ground instead of drifting across the map after targets. Player orders are untouched:
 * only the auto-acquired target is tracked. */
typedef struct { edict_t *target; uint32_t spawn_time, target_spawn; vec2_t anchor; } leash_t;
static leash_t leash[MAX_ENTITIES];

void S_LeashNoteAutoAttack(edict_t *unit, edict_t *target) {
    uint32_t const index = unit ? (uint32_t)(unit - globals.edicts) : MAX_ENTITIES;
    if (index >= MAX_ENTITIES || !target || S_SpellData(MAKEFOURCC('F', 'l', 's', 'h'), 1, 1) <= 0) return;
    leash_t *l = &leash[index];
    /* A unit already on a leash keeps its first anchor while it switches targets. */
    bool const held = l->target && l->spawn_time == unit->spawn_time;
    if (!held) l->anchor = unit->s.origin2;
    l->target = target; l->spawn_time = unit->spawn_time; l->target_spawn = target->spawn_time;
}

BZ_ABILITY_PROC(CAbilityLeash) {
    if (msg != A_UPDATE) return CAbilityPassive(ent, msg, call);
    uint32_t const index = ent ? (uint32_t)(ent - globals.edicts) : MAX_ENTITIES;
    if (index >= MAX_ENTITIES || (G_Time() + (uint32_t)ent->s.number * 23) % 500 >= FRAMETIME) return false;
    leash_t *l = &leash[index];
    if (!l->target || l->spawn_time != ent->spawn_time || M_IsDead(ent)) return false;
    bool const target_alive = l->target->inuse && l->target->spawn_time == l->target_spawn && !M_IsDead(l->target);
    vec2_t const home = l->anchor;
    if (ent->goalentity == l->target && target_alive) {
        /* Still after the target it picked: give up past the leash and walk back. */
        if (Vector2_distance(&ent->s.origin2, &home) <= S_SpellData(MAKEFOURCC('F', 'l', 's', 'h'), 1, 1)) return false;
        l->target = NULL;
        unit_issueorder(ent, "move", &home);
        return true;
    }
    /* The goal changed: either the fight ended (target dead or lost, unit standing) and it
     * returns to its post, or the player gave it an order, which is left alone. */
    l->target = NULL;
    bool const standing = !ent->currentmove || !ent->currentmove->animation || !strncmp(ent->currentmove->animation, "stand", 5);
    if (standing && !ent->goalentity && Vector2_distance(&ent->s.origin2, &home) > 150.0f) {
        unit_issueorder(ent, "move", &home);
        return true;
    }
    return false;
}
