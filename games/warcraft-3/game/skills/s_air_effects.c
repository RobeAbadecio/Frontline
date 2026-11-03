/* Frontline air-defence presentation (docs/games/warcraft-3/frontline-visuals.md).
 *
 * Flak: anti-aircraft fire bursts around the aircraft it is aimed at, hit or miss.
 *   Heavy (5"/38, 90 mm, Type 88, 12.7 cm): big near-black bursts.
 *   Light (40/25/20 mm, .50 cal): small grey puffs; the tracer projectiles are the streams.
 *   A global live cap and a per-frame cap keep a big strike's flak cloud cheap.
 * Aircraft: critical-hit kinds 1-4 (engine fire + black smoke trail, pilot-hit wobble,
 *   control-loss spin, fuel-leak white vapour) and the evasive jink, published as
 *   animation tags that select tools/frontline/unit_anim.aircraft_mdx sequences. A
 *   crit-damaged aircraft that dies plays Death Spin / Death Wobble (else Death) and its
 *   wreck meets the surface: a crash splash at sea or an explosion on land.
 * Presentation only: nothing here changes damage, hit chance or movement. */
#define BZ_AIR_EFFECTS 1 /* real S_AircraftCritEffect/S_AircraftEvadeEffect (no stubs or weak fallbacks) */
#include "s_skills.h"
#include <float.h>

#define FLAK_HEAVY_MODEL "Emberfield/Models/flak_heavy.mdx"
#define FLAK_LIGHT_MODEL "Emberfield/Models/flak_light.mdx"
#define CRASH_SEA_MODEL "Emberfield/Models/crash_sea.mdx"
#define CRASH_LAND_MODEL "Emberfield/Models/crash_land.mdx"
#define BZ_SHIP_AA_BATTERY MAKEFOURCC('F','b','a','a')
/* The crash model holds invisible this long after the aircraft dies, while the Death /
 * Death Spin dive falls to the surface (tools/frontline/unit_anim.CRASH_AT). */
#define AIRCRAFT_CRASH_DELAY_MS 2700u

/* ------------------------------------------------------------------ flak */
static uint32_t flak_expiry[FLAK_MAX_LIVE];
static uint32_t flak_frame_time = UINT32_MAX, flak_frame_spawns;

static void air_fx_reset(void);
/* Map load (G_PrepareMap): game time restarts, so stale expiries would hold the cap full and
 * slot/spawn-time records could match a new unit. Tests also call it directly. */
void S_FlakReset(void) {
    memset(flak_expiry, 0, sizeof(flak_expiry));
    flak_frame_time = UINT32_MAX; flak_frame_spawns = 0;
    air_fx_reset();
}

uint32_t S_FlakLiveCount(void) {
    uint32_t live = 0, now = G_Time();
    FOR_LOOP(i, FLAK_MAX_LIVE) if (flak_expiry[i] > now) live++;
    return live;
}

/* Heavy vs light from existing data:
 *   attacker flying (fighters dogfighting)                -> none
 *   battleship AA battery (Fbaa, Biow, Byam, Bnag, Bnca, Bsdk, Bkon) tracer impacts -> light
 *     (their 5"/38 and 12.7 cm bursts come per volley from naval_aa_think)
 *   shell projectile (< FLAK_TRACER_SPEED: destroyers, cruisers, Atlanta, Akizuki) -> heavy
 *   tracer weapon with base damage >= FLAK_HEAVY_DAMAGE (Anti-Aircraft Gun)         -> heavy
 *   other tracers (MG squads, carrier galleries, bunkers, towers)                   -> light */
flakClass_t S_FlakClassify(bool attacker_flying, bool ship_battery, float damage, float projectile_speed) {
    if (attacker_flying) return FLAK_NONE;
    if (ship_battery) return FLAK_LIGHT;
    if (projectile_speed > 0 && projectile_speed < FLAK_TRACER_SPEED) return FLAK_HEAVY;
    return damage >= FLAK_HEAVY_DAMAGE ? FLAK_HEAVY : FLAK_LIGHT;
}

/* Admission: at most FLAK_MAX_PER_FRAME new bursts a frame and FLAK_MAX_LIVE alive;
 * light puffs stop at FLAK_LIGHT_LIVE so heavy bursts always keep some room. */
static int flak_admit(flakClass_t cls) {
    uint32_t const now = G_Time();
    if (cls == FLAK_NONE) return -1;
    if (flak_frame_time != now) { flak_frame_time = now; flak_frame_spawns = 0; }
    if (flak_frame_spawns >= FLAK_MAX_PER_FRAME) return -1;
    uint32_t live = 0; int slot = -1;
    FOR_LOOP(i, FLAK_MAX_LIVE) {
        if (flak_expiry[i] > now) live++;
        else if (slot < 0) slot = (int)i;
    }
    if (slot < 0 || (cls == FLAK_LIGHT && live >= FLAK_LIGHT_LIVE)) return -1;
    return slot;
}

/* Presentation jitter in [-1, 1] from a private stream: flak must never consume the
 * shared gameplay random sequence (combat rolls, AI choices, acceptance seeds). */
static uint32_t flak_seed = 0x9e3779b9u;
static float flak_jitter(void) {
    flak_seed = flak_seed * 1664525u + 1013904223u;
    return (float)(flak_seed >> 8) / (float)(1u << 23) - 1.0f;
}

/* Scatter a burst around the aircraft; one wind for the whole sky (every burst drifts the same way). */
static void flak_place(edict_t *burst, edict_t const *target, bool heavy) {
    float const spread = heavy ? 70.0f : 38.0f, rise = heavy ? 40.0f : 22.0f;
    burst->s.origin = target->s.origin;
    burst->s.origin.x += flak_jitter() * spread;
    burst->s.origin.y += flak_jitter() * spread;
    burst->s.origin.z += G_UnitImpactZ(target->class_id) + (flak_jitter() * .5f + .1f) * rise;
    burst->s.origin2 = (vec2_t){burst->s.origin.x, burst->s.origin.y};
    burst->s.angle = 0.6f;
    burst->s.model = G_RegisterModel(heavy ? FLAK_HEAVY_MODEL : FLAK_LIGHT_MODEL);
}

static bool flak_account(flakClass_t cls, uint32_t extra_ms) {
    int const slot = flak_admit(cls);
    if (slot < 0) return false;
    flak_expiry[slot] = G_Time() + FLAK_LIFETIME_MS + extra_ms;
    flak_frame_spawns++;
    return true;
}

/* A stand-alone burst (its own effect edict), for AA sources without a projectile. */
bool S_FlakBurst(edict_t const *target, flakClass_t cls) {
    if (!target || cls == FLAK_NONE || !flak_account(cls, 0)) return false;
    edict_t burst = {0};
    burst.s = target->s;
    flak_place(&burst, target, cls == FLAK_HEAVY);
    G_SpawnProjectileImpact(&burst);
    return true;
}

/* Model for a time-fused heavy round (naval_aa_think's 5"/38 / 12.7 cm mounts): the
 * flak_heavy Stand is invisible, so the shell flies unseen and its impact is the burst.
 * Zero when the cap is full; the caller then fires an ordinary tracer. */
uint32_t S_FlakFuzedShellModel(void) {
    return flak_account(FLAK_HEAVY, FLAK_SHELL_FLIGHT_MS) ? (uint32_t)G_RegisterModel(FLAK_HEAVY_MODEL) : 0;
}

/* The round that is hitting `target` this frame: SV_Physics_Toss resolves the hit and then
 * spawns that projectile's impact effect from its model, so re-skinning it shows the burst
 * without a new edict (edict slot order, and everything keyed on it, stays unchanged). */
static edict_t *flak_impacting_round(edict_t const *attacker, edict_t const *target) {
    vec3_t aim = target->s.origin;
    aim.z += G_UnitImpactZ(target->class_id);
    edict_t *best = NULL; float best_d = FLT_MAX;
    FILTER_EDICTS(p, p->inuse && p->movetype == MOVETYPE_FLYMISSILE && p->owner == attacker && p->goalentity == target &&
                     !(p->aiflags & AI_PROJECTILE_FIXED_TARGET)) {
        vec3_t const d = Vector3_sub(&aim, &p->s.origin);
        float const dist = Vector3_len(&d);
        if (dist < p->velocity * FRAMETIME && dist < best_d) { best = p; best_d = dist; }
    }
    return best;
}

/* Frontline AA weapon slot that can hit this target (attack 1, else attack 2). */
static unitAttack_t const *flak_weapon(edict_t const *attacker, edict_t const *target) {
    uint32_t const flag = G_TargetFlagForType(G_UnitTargetType(target));
    unitAttack_t const *a1 = &attacker->unit_state->attack1, *a2 = &attacker->unit_state->attack2;
    if (a1->type != ATK_NONE && (a1->targetsAllowed & flag)) return a1;
    if (a2->type != ATK_NONE && (a2->targetsAllowed & flag)) return a2;
    return a1;
}

flakClass_t S_FlakClassForAttack(edict_t const *attacker, edict_t const *target) {
    if (!attacker || !attacker->unit_state || !target || !(target->aiflags & AI_FLYING)) return FLAK_NONE;
    bool const battery = S_ResolveAbilityAlias((edict_t *)attacker, BZ_SHIP_AA_BATTERY).alias != 0;
    /* Only Frontline anti-aircraft weapons (passive AA Faaa or a ship battery) burst. */
    if (!battery && !G_ActorHasSkill((edict_t *)attacker, "Faaa")) return FLAK_NONE;
    unitAttack_t const *atk = flak_weapon(attacker, target);
    return S_FlakClassify((attacker->aiflags & AI_FLYING) != 0, battery,
                          (float)atk->damageBase, atk->projectile.speed);
}

void S_FlakOnAttack(edict_t const *attacker, edict_t const *target) {
    if (!attacker || !target || !(target->aiflags & AI_FLYING)) return;
    edict_t *round = flak_impacting_round(attacker, target);
    if (!round) return;
    uint32_t const heavy = (uint32_t)G_RegisterModel(FLAK_HEAVY_MODEL), light = (uint32_t)G_RegisterModel(FLAK_LIGHT_MODEL);
    if (round->s.model == heavy || round->s.model == light) {   /* a fuzed shell: already counted */
        flak_place(round, target, round->s.model == heavy);
        return;
    }
    flakClass_t const cls = S_FlakClassForAttack(attacker, target);
    if (cls != FLAK_NONE && flak_account(cls, 0)) flak_place(round, target, cls == FLAK_HEAVY);
}

/* ------------------------------------------------------------------ aircraft */
typedef struct { uint32_t spawn_time, jink_until, crit_mask; bool used, crashed; } airFx_t;
static airFx_t air_fx[MAX_ENTITIES];
static void air_fx_reset(void) { memset(air_fx, 0, sizeof(air_fx)); }

static airFx_t *air_fx_of(edict_t const *aircraft) {
    uint32_t const index = aircraft ? (uint32_t)(aircraft - globals.edicts) : MAX_ENTITIES;
    if (index >= MAX_ENTITIES) return NULL;
    airFx_t *fx = &air_fx[index];
    if (!fx->used || fx->spawn_time != aircraft->spawn_time) *fx = (airFx_t){ .used = true, .spawn_time = aircraft->spawn_time };
    return fx;
}

/* The wreck reaches the surface below where the aircraft died. */
static void air_spawn_crash(edict_t const *aircraft) {
    edict_t crash = {0};
    crash.s = aircraft->s;
    uint8_t flags = 0;
    bool const water = CM_GetTerrainPathingFlagsAt(&crash.s.origin2, &flags) &&
                       (flags & CM_PATHING_UNWALKABLE) && !(flags & CM_PATHING_UNSWIMMABLE);
    crash.s.origin.z = water ? 0 : CM_GetHeightAtPoint(crash.s.origin.x, crash.s.origin.y);
    crash.s.model = G_RegisterModel(water ? CRASH_SEA_MODEL : CRASH_LAND_MODEL);
    G_SpawnProjectileImpact(&crash);
}

/* Kind -> sequence tag (unit_anim.AIR_TAGS); index 0 unused. */
static cstring_t const AIR_CRIT_TAG[AIRCRAFT_CRIT_KINDS + 1] = {"", "fire", "wobble", "spin", "vapour"};

void S_AircraftCritEffect(edict_t *aircraft, int kind) {
    if (!aircraft || !aircraft->inuse || kind < AIRCRAFT_CRIT_ENGINE_FIRE || kind > AIRCRAFT_CRIT_FUEL_LEAK) return;
    airFx_t *fx = air_fx_of(aircraft);
    if (!fx) return;
    if (kind == AIRCRAFT_CRIT_CONTROL_LOSS && fx->jink_until) {
        fx->jink_until = 0; /* no evasive roll out of a spin */
        G_AddUnitAnimationProperties(aircraft, "jink", false);
    }
    G_AddUnitAnimationProperties(aircraft, AIR_CRIT_TAG[kind], true);
    fx->crit_mask |= 1u << kind;
    /* A damaged aircraft that goes down meets the surface: splash at sea, explosion on land. */
    if (M_IsDead(aircraft)) { if (!fx->crashed) { fx->crashed = true; air_spawn_crash(aircraft); } }
}

/* Repaired (S_AircraftClearCrits): drop the crit tags; a later death is an ordinary one. */
void S_AircraftClearEffects(edict_t *aircraft) {
    if (!aircraft || !aircraft->inuse || M_IsDead(aircraft)) return;
    airFx_t *fx = air_fx_of(aircraft);
    if (!fx || !fx->crit_mask) return;
    fx->crit_mask = 0;
    G_AddUnitAnimationProperties(aircraft, "fire wobble spin vapour", false);
}

void S_AircraftEvadeEffect(edict_t *aircraft) {
    if (!aircraft || !aircraft->inuse || M_IsDead(aircraft)) return;
    airFx_t *fx = air_fx_of(aircraft);
    if (!fx || (fx->crit_mask & (1u << AIRCRAFT_CRIT_CONTROL_LOSS))) return;
    uint32_t const now = G_Time();
    fx->jink_until = MAX(now + AIRCRAFT_JINK_MS, aircraft->evade_until);
    G_AddUnitAnimationProperties(aircraft, "jink", true);
}

void S_AircraftEffectsUpdate(edict_t *aircraft) {
    if (!aircraft || !(aircraft->aiflags & AI_FLYING)) return;
    uint32_t const index = (uint32_t)(aircraft - globals.edicts);
    if (index >= MAX_ENTITIES || !air_fx[index].used || air_fx[index].spawn_time != aircraft->spawn_time) return;
    airFx_t *fx = &air_fx[index];
    if (fx->jink_until && (G_Time() >= fx->jink_until || M_IsDead(aircraft))) {
        fx->jink_until = 0;
        G_AddUnitAnimationProperties(aircraft, "jink", false);
    }
    if (fx->crit_mask && !fx->crashed && M_IsDead(aircraft)) {
        fx->crashed = true;
        air_spawn_crash(aircraft);
    }
}
