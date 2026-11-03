/* Frontline ship torpedoes (Ftps), authored by the original pack.
 * Destroyers and torpedo cruisers launch a spread salvo at the nearest enemy ship in
 * torpedo range, aimed at where it will be if it holds course and speed, then reload.
 * Torpedoes run straight and slowly along the surface, so a ship that turns, stops or
 * speeds up after the launch can comb the spread. A hit floods the ship; torpedo
 * protection reduces both (s_ballistics.c S_TorpedoStrike, docs/frontline-naval-damage.md).
 * Ftps: A=range, B=torpedoes per salvo, C=reload s, D=torpedo speed, E=damage per hit,
 * F=degrees between torpedoes in the spread. Reload state lives in a side table keyed by
 * edict and spawn time (like ballistics experience), so it is not part of the save format. */
#include "s_skills.h"

#define BZ_SHIP_TORPEDO MAKEFOURCC('F','t','p','s')
#define TORPEDO_SCAN_MS 500u        /* each ship looks for a target twice a second */
#define TORPEDO_RUN_BEYOND 1.15f    /* a torpedo runs a little past its firing range, then sinks */
#define TORPEDO_FUSE 10.0f          /* added to the hull radius */
#define TORPEDO_ARMING 120.0f       /* run before the warhead arms: never the launching ship */
#define TORPEDO_MAX_SALVO 8u

typedef struct { bool used; uint32_t spawn_time, ready_at; } torpedoTubes_t;
static torpedoTubes_t torpedo_tubes[MAX_ENTITIES];

static bool torpedo_is_ship(edict_t const *e) {
    return e && e->inuse && !M_IsDead(e) && !(e->aiflags & AI_FLYING) && !(e->s.renderfx & RF_HIDDEN) &&
           e->data.UnitBalance && e->data.UnitBalance->speed > 0 &&
           M_UnitStaticPathingFlags((edict_t *)e) == CM_PATHING_UNSWIMMABLE;
}

/* Present velocity of a ship under way along its heading; 0 when stopped. */
static vec2_t torpedo_target_velocity(edict_t const *ship) {
    bool const moving = ship->currentmove && ship->currentmove->animation && !strcmp(ship->currentmove->animation, "walk") &&
                        !G_UnitHasFlag((edict_t *)ship, UNIT_FLAG_PAUSED);
    float const speed = moving ? ship->data.UnitBalance->speed : 0.0f;
    return (vec2_t){cosf(ship->s.angle) * speed, sinf(ship->s.angle) * speed};
}

/* Heading that meets a target holding course and speed (the torpedo director's solution). */
static float torpedo_lead(vec2_t const *from, edict_t const *target, float speed) {
    vec2_t const d = {target->s.origin2.x - from->x, target->s.origin2.y - from->y};
    vec2_t const v = torpedo_target_velocity(target);
    float const a = v.x * v.x + v.y * v.y - speed * speed, b = 2 * (d.x * v.x + d.y * v.y), c = d.x * d.x + d.y * d.y;
    float t = 0;
    if (fabsf(a) < 1e-3f) t = b < 0 ? -c / b : 0;
    else {
        float const disc = b * b - 4 * a * c;
        if (disc >= 0) {
            float const r = sqrtf(disc), t1 = (-b - r) / (2 * a), t2 = (-b + r) / (2 * a);
            t = t1 > 0 && (t2 <= 0 || t1 < t2) ? t1 : MAX(0.0f, t2);
        }
    }
    return atan2f(d.y + v.y * t, d.x + v.x * t);
}

void ship_torpedo_think(edict_t *torpedo) {
    float const step = torpedo->velocity * FRAMETIME / 1000.0f;
    torpedo->s.origin.x += cosf(torpedo->s.angle) * step;
    torpedo->s.origin.y += sinf(torpedo->s.angle) * step;
    torpedo->s.origin2 = (vec2_t){torpedo->s.origin.x, torpedo->s.origin.y};
    torpedo->wait -= step;
    torpedo->freetime += (uint32_t)step; /* distance run, for arming */
    /* Spent, or run onto a shore: the torpedo sinks without a trace. */
    if (torpedo->wait <= 0 || !CM_TerrainPointIsSwimmable(&torpedo->s.origin2)) { G_FreeEdict(torpedo); return; }
    if ((float)torpedo->freetime >= TORPEDO_ARMING) {
        FILTER_EDICTS(e, torpedo_is_ship(e) && S_SpellIsEnemy(torpedo, e) &&
                         Vector2_distance(&e->s.origin2, &torpedo->s.origin2) <= MAX(8.0f, e->collision) + TORPEDO_FUSE) {
            edict_t impact = {0};
            impact.s = torpedo->s;
            impact.s.origin.z = 0;
            impact.s.model = G_RegisterModel("Emberfield/Models/splash.mdx");
            G_SpawnProjectileImpact(&impact);
            int const sound = G_UISoundIndex("FLHeavy");
            if (sound) G_PlaySound(NULL, e, CHAN_BODY, sound, 1, 1, 0);
            S_TorpedoStrike(e, S_SpellChannelOwner(torpedo), (int)torpedo->damage);
            G_FreeEdict(torpedo);
            return;
        }
    }
    gi.LinkEntity(torpedo);
}

static torpedoTubes_t *torpedo_tubes_of(edict_t const *ship) {
    uint32_t const index = (uint32_t)(ship - globals.edicts);
    if (index >= MAX_ENTITIES) return NULL;
    torpedoTubes_t *tubes = &torpedo_tubes[index];
    if (!tubes->used || tubes->spawn_time != ship->spawn_time)
        *tubes = (torpedoTubes_t){.used = true, .spawn_time = ship->spawn_time, .ready_at = 0};
    return tubes;
}

static void torpedo_salvo(edict_t *ship, edict_t *target, uint32_t code, uint32_t level) {
    float const range = S_SpellData(code, level, 1), speed = MAX(50.0f, S_SpellData(code, level, 4));
    uint32_t const count = (uint32_t)MAX(1, MIN(TORPEDO_MAX_SALVO, S_SpellData(code, level, 2)));
    float const spread = S_SpellData(code, level, 6) * (float)M_PI / 180.0f;
    float const aim = torpedo_lead(&ship->s.origin2, target, speed);
    uint32_t const model = G_RegisterModel("Emberfield/Models/bomb.mdx");
    FOR_LOOP(i, count) {
        edict_t *torpedo = S_SpellIdentityThinker(ship, code, target);
        if (!torpedo) return;
        torpedo->think = ship_torpedo_think;
        torpedo->s.angle = aim + spread * ((float)i - (float)(count - 1) * 0.5f);
        torpedo->s.origin = ship->s.origin;
        torpedo->s.origin.z = 0;
        torpedo->s.origin2 = ship->s.origin2;
        torpedo->s.model = model;
        torpedo->s.player = ship->s.player;
        G_InheritUnitTeamColor(torpedo, ship);
        torpedo->velocity = speed;
        torpedo->wait = range * TORPEDO_RUN_BEYOND;
        torpedo->damage = (uint32_t)MAX(0.0f, S_SpellData(code, level, 5));
        torpedo->freetime = 0;
        gi.LinkEntity(torpedo);
    }
}

BZ_ABILITY_PROC(CAbilityShipTorpedo) {
    (void)call;
    /* Updates run for every unit: stagger and gate to a scan twice a second first. */
    if (msg != A_UPDATE || !ent || (G_Time() + (uint32_t)ent->s.number * 37) % TORPEDO_SCAN_MS >= FRAMETIME) return false;
    if (M_IsDead(ent) || (ent->s.renderfx & RF_HIDDEN) || G_UnitHasFlag(ent, UNIT_FLAG_PAUSED) ||
        unit_hasstatusstate(ent, WC3_STATUS_STATE_STUNNED)) return false;
    abilityAliasRef_t const ref = S_ResolveAbilityAlias(ent, BZ_SHIP_TORPEDO);
    if (!ref.alias) return false;
    torpedoTubes_t *tubes = torpedo_tubes_of(ent);
    if (!tubes || G_Time() < tubes->ready_at) return false;
    uint32_t const level = MAX(1u, ref.level);
    float const range = S_SpellData(ref.alias, level, 1);
    edict_t *best = NULL;
    float nearest = range;
    FILTER_EDICTS(e, torpedo_is_ship(e) && S_SpellIsEnemy(ent, e)) {
        float const d = Vector2_distance(&ent->s.origin2, &e->s.origin2);
        if (d <= nearest) { nearest = d; best = e; }
    }
    if (!best) return false;
    torpedo_salvo(ent, best, ref.alias, level);
    tubes->ready_at = G_Time() + (uint32_t)(MAX(1.0f, S_SpellData(ref.alias, level, 3)) * 1000.0f);
    return true;
}
