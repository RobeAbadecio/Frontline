/* Frontline aircraft combat: hit variance, critical damage, fuel and home base.
 *
 * Every hit on an aircraft (unit attacks, passive and ship AA tracers, splash) resolves
 * here after the pilot's evasive maneuver (Fevd): a direct hit, a near miss or a clean miss.
 * WWII air defence rarely scored clean hits: heavy flak bursts by time or proximity fuze
 * and its splinters wound at a distance, fighters land a few rounds of a deflection burst,
 * small arms need luck. Accuracy falls with the target's speed, a small airframe, maneuvering,
 * range and altitude (small arms cannot reach a high bomber; heavy flak cannot track a low,
 * crossing torpedo plane), and rises against a bomber committed to its straight attack run.
 * Veteran gunners shoot better and veteran pilots are harder to hit.
 *
 * A direct hit (or a flak splinter) can be critical: engine fire (damage over time), a
 * wounded pilot (evades and shoots worse), damaged controls (forced home; some spin in) or
 * a fuel leak (triple burn). Landing at home repairs all of them.
 *
 * Fuel: carrier flights keep their sortie tank in the flight thinker (s_carrier.c);
 * airfield aircraft carry it in their mana bar (seconds of flight, saved with the unit).
 * Fuel burns while airborne (half rate loitering over home); at bingo fuel the aircraft
 * flies home, is stored, refuels and takes off again; an empty tank ditches it.
 * Home is the carrier or airfield where the aircraft was last stored (nearest field until
 * then). Return Home (Fhom, Q) sends it there. Combat state lives in a side table keyed by
 * edict and spawn time, so it is not part of the save format. */
#include "s_skills.h"

#define AIRC_HOME_CODE MAKEFOURCC('F','h','o','m')
#define AIRC_CARRIER_CODE MAKEFOURCC('F','c','a','p')
#define AIRC_AIRFIELD_CODE MAKEFOURCC('F','a','c','p')
#define AIRC_FIRE_MS 10000u
#define AIRC_FIRE_RATE .025f        /* fraction of max health per second while burning */
#define AIRC_PILOT_AIM .7f          /* a wounded pilot's gunnery */
#define AIRC_PILOT_MISS 30          /* % of a wounded pilot's shots at surface targets that miss */
#define AIRC_CONTROLS_SPIN 25       /* % of control hits that are unrecoverable */
#define AIRC_LEAK_BURN 3.0f
#define AIRC_CRIT_SCALE 1.5f
#define AIRC_BINGO_MARGIN 1.3f      /* time home x margin ... */
#define AIRC_BINGO_RESERVE 5.0f     /* ... plus a reserve, in seconds of fuel */
#define AIRC_LOITER_RADIUS 900.0f
#define AIRC_LOITER_BURN .5f
#define AIRC_REFUEL_SECONDS 10.0f   /* empty to full in storage */
#define AIRC_RELAUNCH_FUEL .95f
#define AIRC_TICK_MS 500u

typedef enum { AIRC_FLAK, AIRC_GUNS, AIRC_SMALL_ARMS } aircSource_t;
/* Direct-hit and near-miss base chances, near-miss damage range, crit chance per direct hit. */
static struct { float direct, near, near_min, near_max, crit; uint8_t weights[5]; } const airc_sources[] = {
    [AIRC_FLAK] = { .50f, .35f, .35f, .55f, .10f, { 0, 35, 10, 20, 35 } },
    [AIRC_GUNS] = { .55f, .25f, .25f, .40f, .12f, { 0, 30, 30, 20, 20 } },
    [AIRC_SMALL_ARMS] = { .45f, .30f, .20f, .35f, .05f, { 0, 25, 20, 15, 40 } },
};

typedef struct {
    bool used, forced, relaunch;
    uint32_t map, class_id;
    uint32_t spawn_time, crits, fire_until, next_fire, next_tick, last_tick, next_order;
    edict_t *home, *source;
    uint32_t home_spawn, source_spawn;
    uint32_t sorties_shots; /* shots this crew has fired: pilots start green and learn */
} aircState_t;
static aircState_t airc_table[MAX_ENTITIES];

/* Side tables keyed by edict and spawn time (here and s_ballistics.c) start over when a new
 * map loads or the clock restarts, since spawn times then repeat. */
#define AIRC_GREEN_AIM 0.5f
#define AIRC_SHOTS_TO_SEASON 40.0f
float S_AircrewExperience(edict_t const *plane);
void S_AircrewFired(edict_t const *plane);
uint32_t S_SideTableGeneration(void) {
    static uint32_t generation, last_time;
    static void const *last_map;
    uint32_t const now = G_Time();
    if (now < last_time || (void const *)level.vm != last_map) generation++;
    last_time = now; last_map = level.vm;
    return generation;
}
/* A slot reused by a new map (spawn times restart) never inherits an old aircraft's record. */
static bool airc_current(aircState_t const *st, edict_t const *plane) {
    return st->used && st->spawn_time == plane->spawn_time && st->map == S_SideTableGeneration() &&
           st->class_id == plane->class_id && st->last_tick <= G_Time();
}
static aircState_t *airc_state(edict_t const *plane) {
    uint32_t const index = plane ? (uint32_t)(plane - globals.edicts) : MAX_ENTITIES;
    if (index >= MAX_ENTITIES) return NULL;
    aircState_t *st = &airc_table[index];
    if (!airc_current(st, plane))
        *st = (aircState_t){ .used = true, .spawn_time = plane->spawn_time, .map = S_SideTableGeneration(), .class_id = plane->class_id };
    return st;
}
static aircState_t const *airc_record(edict_t const *plane) {
    uint32_t const index = plane ? (uint32_t)(plane - globals.edicts) : MAX_ENTITIES;
    aircState_t const *st = index < MAX_ENTITIES ? &airc_table[index] : NULL;
    return st && airc_current(st, plane) ? st : NULL;
}
static bool airc_alive(edict_t const *e, uint32_t spawn) {
    return e && e->inuse && e->spawn_time == spawn && !M_IsDead(e);
}
uint32_t S_AircraftCritStates(edict_t const *plane) {
    aircState_t const *st = airc_record(plane);
    return st ? st->crits : 0;
}
static bool airc_has(edict_t const *plane, airCritKind_t kind) { return S_AircraftCritStates(plane) & (1u << kind); }
void S_AircraftClearCrits(edict_t *plane) {
    aircState_t *st = airc_state(plane);
    if (st) { st->crits = 0; st->fire_until = 0; }
    S_AircraftClearEffects(plane); /* presentation tags (s_air_effects.c) */
}
float S_AircraftFuelBurn(edict_t const *plane) { return airc_has(plane, AIR_CRIT_FUEL_LEAK) ? AIRC_LEAK_BURN : 1.0f; }

static bool airc_mechanical(edict_t const *ent) {
    cstring_t const type = ent->data.UnitBalance ? ent->data.UnitBalance->type : NULL;
    cstring_t const classes = ent->data.UnitData ? ent->data.UnitData->unitClassification : NULL;
    return (type && strstr(type, "mechanical")) || (classes && strstr(classes, "mechanical"));
}
/* Gun AA vehicles, ship batteries and fortifications fire flak; infantry (even a machine gun
 * squad with an AA mount) fires small arms; aircraft fire their guns. */
static aircSource_t airc_source(edict_t *attacker) {
    if (attacker && (attacker->aiflags & AI_FLYING)) return AIRC_GUNS;
    if (attacker && ((G_UnitAbilityLevel(attacker, MAKEFOURCC('F','a','a','a')) && airc_mechanical(attacker)) ||
                     S_ResolveAbilityAlias(attacker, MAKEFOURCC('F','b','a','a')).alias ||
                     G_UnitIsStructure(attacker) || M_UnitStaticPathingFlags(attacker) == CM_PATHING_UNSWIMMABLE)) return AIRC_FLAK;
    return AIRC_SMALL_ARMS;
}
static bool airc_bomber(edict_t *plane) {
    return G_UnitAbilityLevel(plane, MAKEFOURCC('F','h','i','t')) || G_UnitAbilityLevel(plane, MAKEFOURCC('F','t','o','r'));
}
static float airc_rank(edict_t *ent, float elite, float veteran) {
    return G_UnitAbilityLevel(ent, MAKEFOURCC('F','v','t','2')) ? elite : G_UnitAbilityLevel(ent, MAKEFOURCC('F','v','t','1')) ? veteran : 1.0f;
}

/* 1 is a typical shot; lower is harder. */
float S_AircraftAccuracy(edict_t *attacker, edict_t *target) {
    if (!attacker || !target) return 1.0f;
    aircSource_t const source = airc_source(attacker);
    float accuracy = 1.0f;
    float const speed = target->data.UnitBalance ? MAX(0, target->data.UnitBalance->speed) : 0;
    accuracy *= 1.0f - .25f * MIN(1.0f, speed / 600.0f);                     /* deflection */
    if (airc_bomber(target)) accuracy *= 1.15f;                                /* bigger airframe */
    /* Cruise altitude, lower while taking off or landing. */
    float const cruise = target->data.UnitData ? target->data.UnitData->moveHeight : 0;
    float const height = target->unitinfo.FlyHeight > 0 && cruise > 0 ? MIN(cruise, target->unitinfo.FlyHeight) : cruise;
    if (source == AIRC_SMALL_ARMS) accuracy *= height > 200 ? .75f : height < 120 ? 1.15f : 1.0f;
    if (source == AIRC_FLAK && height < 120) accuracy *= .8f;                  /* too low and fast to track */
    float const range = attacker->unit_state ? MAX(1.0f, attacker->unit_state->attack1.range) : 600.0f;
    accuracy *= 1.0f - .3f * MIN(1.0f, Vector2_distance(&attacker->s.origin2, &target->s.origin2) / range);
    if (G_Time() < target->evade_until) accuracy *= .6f;                       /* jinking */
    else if (airc_bomber(target) && target->currentmove && target->currentmove->proc == CAbilityAttack)
        accuracy *= 1.15f;                                                     /* steady attack run */
    accuracy *= airc_rank(target, .8f, .9f);
    if (airc_has(target, AIR_CRIT_PILOT)) accuracy *= 1.2f;
    accuracy *= airc_rank(attacker, 1.2f, 1.1f) * (1.0f + .1f * S_BallisticExperience(attacker));
    /* Aircrew: a green pilot fires at half the accuracy of a seasoned one; each burst teaches. */
    if (attacker->aiflags & AI_FLYING) accuracy *= AIRC_GREEN_AIM + (1.0f - AIRC_GREEN_AIM) * S_AircrewExperience(attacker);
    if (airc_has(attacker, AIR_CRIT_PILOT)) accuracy *= AIRC_PILOT_AIM;
    return MAX(.25f, MIN(1.3f, accuracy));
}

static float airc_random(void) { return (float)(rand() % 10000) / 10000.0f; }

/* 0 for a new aircrew, 1 after AIRC_SHOTS_TO_SEASON shots fired (kept while the aircraft lives). */
float S_AircrewExperience(edict_t const *plane) {
    aircState_t const *st = plane && (plane->aiflags & AI_FLYING) ? airc_record(plane) : NULL;
    return st ? MIN(1.0f, (float)st->sorties_shots / AIRC_SHOTS_TO_SEASON) : 0.0f;
}

void S_AircrewFired(edict_t const *plane) {
    aircState_t *st = plane && (plane->aiflags & AI_FLYING) ? airc_state(plane) : NULL;
    if (st && st->sorties_shots < 100000) st->sorties_shots++;
}

airHitKind_t S_AircraftRollHit(edict_t *attacker, edict_t *target, float *fraction) {
    aircSource_t const source = airc_source(attacker);
    S_AircrewFired(attacker);
    float const accuracy = S_AircraftAccuracy(attacker, target);
    float const direct = MIN(.9f, airc_sources[source].direct * accuracy);
    float const near = MIN(.97f - direct, airc_sources[source].near + airc_sources[source].direct * (1.0f - MIN(1.0f, accuracy)) * .5f);
    float const roll = airc_random();
    airHitKind_t const kind = roll < direct ? AIR_HIT_DIRECT : roll < direct + near ? AIR_HIT_NEAR : AIR_HIT_MISS;
    if (fraction) *fraction = kind == AIR_HIT_DIRECT ? .85f + .3f * airc_random()
        : kind == AIR_HIT_NEAR ? airc_sources[source].near_min + (airc_sources[source].near_max - airc_sources[source].near_min) * airc_random() : 0.0f;
    return kind;
}

void S_AircraftApplyCrit(edict_t *plane, edict_t *attacker, airCritKind_t kind) {
    aircState_t *st = airc_state(plane);
    if (!st || kind <= AIR_CRIT_NONE || kind > AIR_CRIT_FUEL_LEAK || M_IsDead(plane)) return;
    st->crits |= 1u << kind;
    if (kind == AIR_CRIT_ENGINE_FIRE) {
        st->fire_until = G_Time() + AIRC_FIRE_MS;
        st->next_fire = G_Time() + 1000;
        st->source = attacker; st->source_spawn = attacker ? attacker->spawn_time : 0;
    }
    S_AircraftCritEffect(plane, kind);
    if (kind == AIR_CRIT_CONTROLS) { st->forced = st->relaunch = true; st->next_order = 0; S_AircraftReturnHome(plane, true); }
}

static airCritKind_t airc_pick_crit(aircSource_t source) {
    uint32_t total = 0, roll;
    FOR_LOOP(i, 5) total += airc_sources[source].weights[i];
    roll = (uint32_t)rand() % MAX(1u, total);
    FOR_LOOP(i, 5) { if (roll < airc_sources[source].weights[i]) return (airCritKind_t)i; roll -= airc_sources[source].weights[i]; }
    return AIR_CRIT_ENGINE_FIRE;
}

/* The damage an attack delivers to an aircraft (0 = evaded or missed). A wounded pilot's
 * own fire at surface targets also misses more often. */
int S_AircraftHit(edict_t *attacker, edict_t *target, int damage) {
    if (damage <= 0 || !target) return damage;
    if (!(target->aiflags & AI_FLYING)) {
        bool const shaky = attacker && (attacker->aiflags & AI_FLYING) && airc_has(attacker, AIR_CRIT_PILOT);
        return shaky && rand() % 100 < AIRC_PILOT_MISS ? 0 : damage;
    }
    if (M_IsDead(target)) return damage;
    if (S_AircraftEvades(target, attacker)) return 0;
    float fraction = 0;
    aircSource_t const source = airc_source(attacker);
    airHitKind_t const kind = S_AircraftRollHit(attacker, target, &fraction);
    if (kind == AIR_HIT_MISS) return 0;
    int result = MAX(1, (int)((float)damage * fraction));
    float chance = kind == AIR_HIT_DIRECT
        ? airc_sources[source].crit + .2f * (float)damage / MAX(1.0f, target->health.max_value)
        : source == AIRC_FLAK ? .04f : 0.0f;                                   /* flak splinters */
    chance = MIN(.3f, chance * (attacker ? airc_rank(attacker, 1.3f, 1.15f) : 1.0f));
    if (airc_random() >= chance) return result;
    airCritKind_t const crit = kind == AIR_HIT_NEAR ? (rand() & 1 ? AIR_CRIT_FUEL_LEAK : AIR_CRIT_ENGINE_FIRE) : airc_pick_crit(source);
    result = (int)((float)result * AIRC_CRIT_SCALE);
    if (crit == AIR_CRIT_CONTROLS && rand() % 100 < AIRC_CONTROLS_SPIN) {
        S_AircraftCritEffect(target, crit);
        return (int)(target->health.max_value * 2 + 1); /* spins in */
    }
    S_AircraftApplyCrit(target, attacker, crit);
    return result;
}

/* ---- Home and fuel ---- */

static bool airc_is_home(edict_t const *e, edict_t const *plane) {
    return e && e->inuse && !M_IsDead(e) && e->s.player == plane->s.player && !e->construction &&
           (G_UnitAbilityLevel((edict_t *)e, AIRC_CARRIER_CODE) ||
            (G_UnitIsStructure(e) && G_UnitAbilityLevel((edict_t *)e, AIRC_AIRFIELD_CODE)));
}

/* A full hangar cannot take the aircraft: a carrier counts its whole air group (aircraft
 * aloft come back to their slots), an airfield what is stored. */
static bool airc_has_room(edict_t *home) {
    uint32_t const capacity = S_CargoCapacity(home);
    return G_UnitAbilityLevel(home, AIRC_CARRIER_CODE) ? S_CarrierAircraftCount(home) < capacity
                                                       : (home->cargo ? home->cargo->count : 0) < capacity;
}

edict_t *S_AircraftHome(edict_t *plane) {
    if (!plane) return NULL;
    edict_t *flight = S_CarrierFlightForPlane(plane);
    if (flight) return S_SpellChannelOwner(flight);
    aircState_t *st = airc_state(plane);
    edict_t *stored = (plane->s.renderfx & RF_HIDDEN) ? S_CargoTransportForUnit(plane) : NULL;
    if (airc_is_home(stored, plane)) return stored;
    if (st && airc_alive(st->home, st->home_spawn) && airc_is_home(st->home, plane) && airc_has_room(st->home)) return st->home;
    edict_t *best = NULL;
    float nearest = FLT_MAX;
    FILTER_EDICTS(e, airc_is_home(e, plane) && airc_has_room(e)) {
        float const d = Vector2_distance(&e->s.origin2, &plane->s.origin2);
        if (d < nearest) { nearest = d; best = e; }
    }
    return best;
}

static bool airc_boarding(edict_t *plane, edict_t *home) {
    return plane->currentmove && plane->currentmove->proc == CAbilityBattlestations && plane->orders &&
           plane->orders->resource_goal == home;
}

/* Q: fly back to the home base and land. Forced returns (fuel, controls) keep reissuing. */
bool S_AircraftReturnHome(edict_t *plane, bool forced) {
    if (!plane || M_IsDead(plane) || !(plane->aiflags & AI_FLYING)) return false;
    if (S_CarrierFlightForPlane(plane)) return S_CarrierRecallFlight(plane);
    edict_t *home = S_AircraftHome(plane);
    aircState_t *st = airc_state(plane);
    if (!home || !st) return false;
    if (!forced) st->relaunch = st->forced = false;
    return airc_boarding(plane, home) || S_CargoOrderBoard(plane, home);
}

static void airc_stored(edict_t *plane, aircState_t *st, edict_t *transport, float dt) {
    if (airc_is_home(transport, plane)) { st->home = transport; st->home_spawn = transport->spawn_time; }
    st->crits = 0; st->fire_until = 0; st->forced = false;
    if (S_CarrierFlightForPlane(plane) || plane->mana.max_value <= 0) return;
    plane->mana.value = MIN(plane->mana.max_value, plane->mana.value + plane->mana.max_value * dt / AIRC_REFUEL_SECONDS);
    if (!st->relaunch || plane->mana.value < plane->mana.max_value * AIRC_RELAUNCH_FUEL || !transport->cargo) return;
    FOR_LOOP(i, transport->cargo->count) if (S_CargoUnitAt(transport, i) == plane) { S_CargoUnloadAt(transport, i); break; }
    st->relaunch = false;
}

static void airc_update(edict_t *plane) {
    aircState_t *st = airc_state(plane);
    uint32_t const now = G_Time();
    if (!st) return;
    if (st->fire_until > now && now >= st->next_fire && !(plane->s.renderfx & RF_HIDDEN)) {
        st->next_fire = now + 1000;
        edict_t *source = airc_alive(st->source, st->source_spawn) ? st->source : plane;
        T_Damage(plane, source, (int)MAX(1.0f, plane->health.max_value * AIRC_FIRE_RATE));
        if (M_IsDead(plane)) return;
    }
    if (st->fire_until && st->fire_until <= now) { st->fire_until = 0; st->crits &= ~(1u << AIR_CRIT_ENGINE_FIRE); }
    if (now < st->next_tick) return;
    float const dt = st->last_tick ? (float)(now - st->last_tick) / 1000.0f : 0.0f;
    st->last_tick = now; st->next_tick = now + AIRC_TICK_MS;
    if (plane->s.renderfx & RF_HIDDEN) {
        edict_t *transport = S_CargoTransportForUnit(plane);
        if (transport) airc_stored(plane, st, transport, dt);
        return;
    }
    if (S_CarrierFlightForPlane(plane) || plane->mana.max_value <= 0) return; /* the carrier owns its tank */
    edict_t *home = S_AircraftHome(plane);
    float const distance = home ? Vector2_distance(&plane->s.origin2, &home->s.origin2) : FLT_MAX;
    float const burn = S_AircraftFuelBurn(plane);
    plane->mana.value -= burn * dt * (distance < AIRC_LOITER_RADIUS ? AIRC_LOITER_BURN : 1.0f);
    if (plane->mana.value <= 0) {
        plane->mana.value = 0;
        T_Damage(plane, plane, (int)plane->health.max_value + 1); /* out of fuel: ditched */
        return;
    }
    if (!home) return;
    float const speed = plane->data.UnitBalance ? MAX(1.0f, plane->data.UnitBalance->speed) : 300.0f;
    if (!st->forced && plane->mana.value / burn <= distance / speed * AIRC_BINGO_MARGIN + AIRC_BINGO_RESERVE)
        st->forced = st->relaunch = true, st->next_order = 0;
    if (st->forced && now >= st->next_order && !airc_boarding(plane, home)) {
        st->next_order = now + 2000;
        S_AircraftReturnHome(plane, true);
    }
}

bool S_AircraftStatusLabel(edict_t *plane, string_t text, uint32_t size) {
    if (!plane || !text || !size || !(plane->aiflags & AI_FLYING) || !G_UnitAbilityLevel(plane, AIRC_HOME_CODE)) return false;
    edict_t *flight = S_CarrierFlightForPlane(plane), *home = S_AircraftHome(plane);
    int used = flight ? snprintf(text, size, "Fuel %.0fs", MAX(0.0f, flight->wait))
                      : snprintf(text, size, "Fuel %.0f/%.0f", plane->mana.value, plane->mana.max_value);
    if (used > 0 && (uint32_t)used < size)
        used += snprintf(text + used, size - used, " | Home: %s", home ? G_UnitName(home->class_id) : "none");
    static cstring_t const names[] = { "", "ENGINE FIRE", "PILOT WOUNDED", "CONTROLS DAMAGED", "FUEL LEAK" };
    for (uint32_t kind = AIR_CRIT_ENGINE_FIRE; kind <= AIR_CRIT_FUEL_LEAK; kind++)
        if (airc_has(plane, kind) && used > 0 && (uint32_t)used < size) used += snprintf(text + used, size - used, " | %s", names[kind]);
    return true;
}

cstring_t const aircraft_home_orders[] = { "returnhome", NULL };
/* Fhom: Return Home command (Q) and the per-aircraft fuel, fire and home bookkeeping. */
BZ_ABILITY_PROC(CAbilityAircraftHome) {
    switch (msg) {
    case A_VALIDATE: return ent && (ent->aiflags & AI_FLYING) && !M_IsDead(ent) && S_AircraftHome(ent);
    case A_EXECUTE: return S_AircraftReturnHome(ent, false);
    case A_UPDATE:
        if (ent && (ent->aiflags & AI_FLYING) && !M_IsDead(ent) && G_UnitAbilityLevel(ent, AIRC_HOME_CODE)) airc_update(ent);
        return false;
    default: return CAbilitySimpleSpell(ent, msg, call);
    }
}
