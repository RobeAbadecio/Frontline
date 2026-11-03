/* Frontline ballistics for shell, rocket, mortar and bomb weapons (Fbal family).
 * A shot lands somewhere in a dispersion circle around the aim point and hits only
 * when it falls on the target's hull plus a blast allowance. Every shot fired is
 * battle experience that tightens the circle, and so does standing still to aim. Hits on armour can ricochet; a
 * well-centred hit on a ship strikes its citadel. Experience lives in a side table
 * keyed by edict and spawn time, so it is not part of the save format. */
#include "s_skills.h"

#define BZ_BALLISTICS MAKEFOURCC('F','b','a','l')
#define BALLISTIC_BLAST 80.0f        /* shell burst radius added to the target's hull */
#define BALLISTIC_RICOCHET_SCALE 0.1f
#define BALLISTIC_CITADEL_SCALE 3.0f
#define BALLISTIC_CITADEL_CORE 0.5f  /* citadel hits land within this fraction of the hull */
/* Real gunnery factors (general naval-ordnance behaviour, tuned for an RTS):
 * - spread grows with range (shells scatter more at long range);
 * - a ship seen bow- or stern-on is a narrower target and deflects more shells, and only
 *   a broadside exposes the citadel (impact angle);
 * - a heavy armour-piercing shell passes straight through a thinly armoured hull
 *   (overpenetration) and does a fraction of its damage;
 * - shells and bombs start fires on ships and buildings; torpedoes flood ships.
 *   Both burn or flood for a while unless the unit is destroyed first. */
#define BALLISTIC_RANGE_NEAR 0.7f      /* spread multiplier point-blank ... */
#define BALLISTIC_RANGE_FAR 1.3f       /* ... and at the weapon's maximum range */
#define BALLISTIC_OVERPEN_DAMAGE 120   /* shells this heavy can overpenetrate */
#define BALLISTIC_OVERPEN_ARMOR 3.0f   /* hulls this thin let them through */
#define BALLISTIC_OVERPEN_CHANCE 40
#define BALLISTIC_OVERPEN_SCALE 0.3f
#define BALLISTIC_FIRE_MS 10000u
#define BALLISTIC_FIRE_RATE 0.008f     /* fraction of max health per second */
#define BALLISTIC_FLOOD_MS 20000u
#define BALLISTIC_FLOOD_RATE 0.004f    /* per torpedo hit, before torpedo protection */
#define BALLISTIC_FLOOD_MAX_HITS 3u
#define BZ_TORPEDO_BALLISTICS MAKEFOURCC('F','b','l','t')
#define BZ_BOMB_BALLISTICS MAKEFOURCC('F','b','l','b')
/* Carriers were not tanky: Yorktown was stopped by 3 bombs and 2 torpedoes, Hornet by
 * 4 bombs and 2 torpedoes, Akagi doomed by 1-2 bombs among fuelled aircraft, Taiho by one
 * torpedo and avgas vapour. Thin decks let bombs into the hangar and fuel and ordnance burn,
 * so bombs and torpedoes hit carriers much harder and their fires last longer; heavy shells
 * overpenetrate the thin hull (docs/frontline-carrier-durability.md). */
#define BALLISTIC_CARRIER_BOMB 3.0f
#define BALLISTIC_CARRIER_TORPEDO 3.0f
#define BALLISTIC_CARRIER_FIRE_CHANCE 60
#define BALLISTIC_CARRIER_FIRE_MS 15000u
#define BALLISTIC_CARRIER_FIRE_RATE 0.012f
static bool ballistic_is_carrier(edict_t const *ent) {
    return ent && G_UnitAbilityLevel((edict_t *)ent, MAKEFOURCC('F','c','a','p'));
}

#define BALLISTIC_SETTLE_MS 4000u      /* time standing still for the full aiming bonus */
#define BALLISTIC_SETTLE_BONUS 0.3f    /* spread reduction once settled */
#define BALLISTIC_STILL_DISTANCE 12.0f

typedef struct { bool used; uint32_t map; uint32_t spawn_time, shots, still_since; vec2_t position;
                 uint32_t fire_until, flood_until, next_tick, flood_hits; edict_t *source; uint32_t source_spawn, hit_at; } ballisticCrew_t;
static ballisticCrew_t ballistic_experience[MAX_ENTITIES];
void S_BallisticReset(void) { memset(ballistic_experience, 0, sizeof(ballistic_experience)); }

static bool ballistic_walking(edict_t const *shooter) {
    return shooter->currentmove && shooter->currentmove->animation && !strcmp(shooter->currentmove->animation, "walk");
}

/* Per-shooter record; a moving unit restarts its settling time. A unit first seen
 * standing still (an ambush, a moored battery) is treated as already settled. */
static ballisticCrew_t *ballistic_crew(edict_t const *shooter) {
    uint32_t const index = (uint32_t)(shooter - globals.edicts);
    if (index >= MAX_ENTITIES) return NULL;
    ballisticCrew_t *crew = &ballistic_experience[index];
    uint32_t const now = G_Time();
    /* Spawn time 0 is valid (units created at map start), so a separate flag marks use. */
    /* A new map restarts spawn times: a reused slot must not inherit an old fire or hit. */
    if (!crew->used || crew->spawn_time != shooter->spawn_time || crew->map != S_SideTableGeneration()) {
        crew->used = true;
        crew->map = S_SideTableGeneration();
        crew->spawn_time = shooter->spawn_time;
        crew->shots = 0;
        crew->fire_until = crew->flood_until = crew->next_tick = crew->hit_at = crew->flood_hits = 0;
        crew->source = NULL;
        crew->still_since = ballistic_walking(shooter) ? now : now - BALLISTIC_SETTLE_MS; /* unsigned wrap is intended */
        crew->position = shooter->s.origin2;
    } else if (Vector2_distance(&crew->position, &shooter->s.origin2) > BALLISTIC_STILL_DISTANCE) {
        crew->still_since = now;
        crew->position = shooter->s.origin2;
    }
    return crew;
}

static uint32_t *ballistic_shots(edict_t const *shooter) {
    ballisticCrew_t *crew = ballistic_crew(shooter);
    return crew ? &crew->shots : NULL;
}

/* 0 while moving, 1 after standing still for BALLISTIC_SETTLE_MS. */
float S_BallisticSettle(edict_t const *shooter) {
    ballisticCrew_t *crew = shooter ? ballistic_crew(shooter) : NULL;
    if (!crew || ballistic_walking(shooter)) return 0.0f;
    return MIN(1.0f, (float)(G_Time() - crew->still_since) / BALLISTIC_SETTLE_MS);
}

/* 0 for a green crew, 1 once it has fired DataC shots. */
float S_BallisticExperience(edict_t const *shooter) {
    abilityAliasRef_t const ref = shooter ? S_ResolveAbilityAlias((edict_t *)shooter, BZ_BALLISTICS) : (abilityAliasRef_t){0};
    uint32_t *shots = ref.alias ? ballistic_shots(shooter) : NULL;
    float const mastery = ref.alias ? MAX(1.0f, S_SpellData(ref.alias, 1, 3)) : 1.0f;
    return shots ? MIN(1.0f, (float)*shots / mastery) : 0.0f;
}

/* Dispersion radius: DataA for a green crew, shrinking to DataA*DataB with experience;
 * standing still settles the aim and Veteran and Elite ranks (Fvt1/Fvt2) tighten it further. */
float S_BallisticDispersion(edict_t const *shooter) {
    abilityAliasRef_t const ref = shooter ? S_ResolveAbilityAlias((edict_t *)shooter, BZ_BALLISTICS) : (abilityAliasRef_t){0};
    if (!ref.alias) return 0.0f;
    float const base = S_SpellData(ref.alias, 1, 1), floor = S_SpellData(ref.alias, 1, 2);
    float dispersion = base * (1.0f - (1.0f - floor) * S_BallisticExperience(shooter));
    dispersion *= 1.0f - BALLISTIC_SETTLE_BONUS * S_BallisticSettle(shooter);
    if (G_UnitAbilityLevel((edict_t *)shooter, MAKEFOURCC('F','v','t','2'))) dispersion *= 0.7f;
    else if (G_UnitAbilityLevel((edict_t *)shooter, MAKEFOURCC('F','v','t','1'))) dispersion *= 0.85f;
    return dispersion;
}

static bool ballistic_is_ship(edict_t const *target) {
    return target && !(target->aiflags & AI_FLYING) && target->data.UnitBalance && target->data.UnitBalance->speed > 0 &&
           M_UnitStaticPathingFlags((edict_t *)target) == CM_PATHING_UNSWIMMABLE;
}

/* Callouts share the map's text-tag registry with scripts: at most a few per second, so a
 * long naval battle never starves CreateTextTag (a full registry is a JASS runtime error). */
#define BALLISTIC_CALLOUTS_PER_SECOND 4u
static void ballistic_callout(edict_t const *target, cstring_t text, color32_t color) {
    static uint32_t window, shown;
    uint32_t const second = G_Time() / 1000;
    if (second != window) { window = second; shown = 0; }
    if (shown >= BALLISTIC_CALLOUTS_PER_SECOND) return;
    shown++;
    texttag_t *tag = G_AllocTextTag();
    if (!tag) return;
    tag->has_text = tag->has_position = true;
    tag->x = target->s.origin.x; tag->y = target->s.origin.y;
    tag->permanent = false; tag->height = .02f; tag->height_offset = 80;
    tag->lifespan = 1.6f; tag->fadepoint = .8f; tag->yvel = 28; tag->color = color;
    snprintf(tag->text, sizeof(tag->text), "%s", text);
    G_TextTagPresentation(tag, false);
}

/* 1 for a broadside, 0 for a target seen exactly bow- or stern-on. */
static float ballistic_broadside(edict_t const *shooter, edict_t const *target) {
    float const bearing = atan2f(target->s.origin.y - shooter->s.origin.y, target->s.origin.x - shooter->s.origin.x);
    return fabsf(sinf(bearing - target->s.angle));
}

static void ballistic_start(edict_t *target, edict_t *source, bool flood) {
    ballisticCrew_t *crew = ballistic_crew(target);
    if (!crew) return;
    uint32_t const now = G_Time();
    bool const fresh = flood ? crew->flood_until <= now : crew->fire_until <= now;
    /* Each further torpedo opens more compartments: flooding worsens up to three hits. */
    if (flood) crew->flood_hits = fresh ? 1 : MIN(BALLISTIC_FLOOD_MAX_HITS, crew->flood_hits + 1);
    if (flood) crew->flood_until = now + BALLISTIC_FLOOD_MS;
    else crew->fire_until = now + (ballistic_is_carrier(target) ? BALLISTIC_CARRIER_FIRE_MS : BALLISTIC_FIRE_MS);
    crew->source = source;
    crew->source_spawn = source ? source->spawn_time : 0;
    if (!crew->next_tick || crew->next_tick < now) crew->next_tick = now + 1000;
    if (fresh) ballistic_callout(target, flood ? "FLOODING" : "FIRE", flood ? (color32_t){90, 160, 255, 255} : (color32_t){255, 90, 40, 255});
}

/* Returns the damage this shot delivers: 0 for a miss, reduced for a ricochet or an
 * overpenetration, multiplied for a citadel hit; it may also start a fire or flooding.
 * Weapons without Fbal are unchanged. Fbal: A=green dispersion, B=veteran fraction of A,
 * C=shots to master, D=citadel %, E=ricochet base %, F=AP penetration mm (armour model below). */
static int ballistic_hit(edict_t *shooter, edict_t *target, int damage);

/* Torpedo protection and counter-flooding also slow the flooding that follows a hit. */
static float ballistic_flood_scale(edict_t const *ship) {
    float protection = 0;
    S_ShipArmour(ship, NULL, NULL, &protection);
    return 1.0f - MIN(0.9f, MAX(0.0f, protection));
}

/* Every landed hit is remembered on the target, so a carrier knows it is under attack. */
int S_BallisticHit(edict_t *shooter, edict_t *target, int damage) {
    damage = ballistic_hit(shooter, target, damage);
    ballisticCrew_t *crew = damage > 0 && target && !M_IsDead(target) ? ballistic_crew(target) : NULL;
    if (crew) crew->hit_at = G_Time() | 1; /* 0 means never hit */
    /* A hit that gets through can knock out one main turret (s_naval.c): likelier from a
     * citadel or penetrating hit, never from a ricochet, shatter or a miss. */
    if (damage > 0 && target && !M_IsDead(target) && ballistic_is_ship(target)) {
        ballisticOutcome_t const outcome = S_BallisticLastOutcome(NULL);
        int const chance = outcome == BALLISTIC_CITADEL ? 30 : outcome == BALLISTIC_PENETRATION ? 8 :
                           outcome == BALLISTIC_HIT ? 5 : 0;
        if (chance && rand() % 100 < chance && S_NavalBreakMount(target))
            ballistic_callout(target, "TURRET OUT", (color32_t){255, 200, 60, 255});
    }
    return damage;
}

/* Armour penetration (docs/frontline-naval-damage.md). A gun's Fbal DataF is its armour-piercing
 * penetration in mm of vertical armour at point-blank range; a ship's Farm gives belt mm (A),
 * deck mm (B) and torpedo protection (C, fraction of a torpedo hit absorbed). Weapons without
 * DataF and targets without Farm keep the simple armour-value ricochet rule. */
#define BZ_ARMOUR MAKEFOURCC('F','a','r','m')
#define PEN_BELT_LOSS 0.45f        /* belt penetration lost by the weapon's maximum range */
#define PEN_DECK_GAIN 0.4f         /* deck penetration at maximum range, as a fraction of point-blank */
#define PEN_DECK_SHARE 0.6f        /* hull hits that plunge onto the deck at maximum range (x range^2) */
#define PEN_UPPER_SHARE 25         /* % of hits on unarmoured upperworks, bow and stern */
#define PEN_UPPER_SCALE 0.5f       /* those do not threaten buoyancy or machinery */
#define PEN_RICOCHET_ANGLE 0.42f   /* broadside factor below which (obliquity over ~65 deg) AP skids off a belt */
#define PEN_RICOCHET_CHANCE 60
#define PEN_SHATTER_RATIO 0.6f     /* penetration under 60% of the plate: the shell breaks up */
#define PEN_NO_PEN_SCALE 0.35f     /* stopped by the plate: blast and splinters only */
#define PEN_UNARMOURED 50.0f       /* thinner plating neither stops nor reliably arms an AP shell */
#define PEN_OVERPEN_RATIO 4.0f     /* four times the plate: the fuse may not act inside the hull */
#define PEN_OVERPEN_FLOOR 200.0f   /* lighter shells burst inside even thin hulls ... */
#define PEN_OVERPEN_SLOPE 5.0f     /* ... heavier ones pass through: +1% per 5 mm above the floor */
#define PEN_OVERPEN_MAX 70.0f
#define PEN_FIRE_HE 18.0f          /* % fire chance of a shell bursting outside the armour */

static struct { ballisticOutcome_t outcome; bool deck; } ballistic_last;
ballisticOutcome_t S_BallisticLastOutcome(bool *deck) {
    if (deck) *deck = ballistic_last.deck;
    return ballistic_last.outcome;
}
static int ballistic_result(ballisticOutcome_t outcome, int damage) {
    ballistic_last.outcome = outcome;
    return damage;
}

bool S_ShipArmour(edict_t const *ship, float *belt, float *deck, float *torpedo) {
    abilityAliasRef_t const ref = ship ? S_ResolveAbilityAlias((edict_t *)ship, BZ_ARMOUR) : (abilityAliasRef_t){0};
    if (!ref.alias) return false;
    if (belt) *belt = S_SpellData(ref.alias, 1, 1);
    if (deck) *deck = S_SpellData(ref.alias, 1, 2);
    if (torpedo) *torpedo = S_SpellData(ref.alias, 1, 3);
    return true;
}

/* Effective penetration at a distance: flat fire loses belt penetration with range while
 * plunging fire gains deck penetration. 0 for weapons without authored penetration. */
float S_BallisticPenetration(edict_t const *shooter, float distance, bool deck) {
    abilityAliasRef_t const ref = shooter ? S_ResolveAbilityAlias((edict_t *)shooter, BZ_BALLISTICS) : (abilityAliasRef_t){0};
    float const pen = ref.alias ? S_SpellData(ref.alias, 1, 6) : 0.0f;
    if (pen <= 0) return 0.0f;
    float const range = shooter->unit_state ? MAX(1.0f, shooter->unit_state->attack1.range) : 1.0f;
    float const t = MIN(1.0f, MAX(0.0f, distance) / range);
    return deck ? pen * PEN_DECK_GAIN * t : pen * (1.0f - PEN_BELT_LOSS * t);
}

static bool ballistic_overpenetrates(float pen) {
    float const chance = MIN(PEN_OVERPEN_MAX, (pen - PEN_OVERPEN_FLOOR) / PEN_OVERPEN_SLOPE);
    return chance > 0 && (float)(rand() % 100) < chance;
}
static void ballistic_maybe_fire(edict_t *target, edict_t *shooter, float chance) {
    if ((float)(rand() % 100) < chance) ballistic_start(target, shooter, false);
}
static int ballistic_overpen(edict_t *target, int damage) {
    ballistic_callout(target, "OVERPEN", (color32_t){230, 230, 120, 255});
    return ballistic_result(BALLISTIC_OVERPENETRATION, MAX(1, (int)(damage * BALLISTIC_OVERPEN_SCALE)));
}

/* Where the shell strikes (upperworks, belt or deck) and whether it defeats the plate there. */
static int ballistic_armour_hit(edict_t *shooter, edict_t *target, int damage, float distance, float broadside,
                                bool centred, float experience, float citadel_chance) {
    float belt = 0, deck = 0;
    S_ShipArmour(target, &belt, &deck, NULL);
    float const range = shooter->unit_state ? MAX(1.0f, shooter->unit_state->attack1.range) : 1.0f;
    float const t = MIN(1.0f, distance / range);
    if (rand() % 100 < PEN_UPPER_SHARE) {
        if (ballistic_overpenetrates(S_BallisticPenetration(shooter, distance, false))) return ballistic_overpen(target, damage);
        ballistic_maybe_fire(target, shooter, PEN_FIRE_HE);
        return ballistic_result(BALLISTIC_UPPERWORKS, MAX(1, (int)(damage * PEN_UPPER_SCALE)));
    }
    bool const on_deck = (float)(rand() % 10000) < PEN_DECK_SHARE * t * t * 10000.0f;
    ballistic_last.deck = on_deck;
    float const pen = S_BallisticPenetration(shooter, distance, on_deck);
    bool const armoured = (on_deck ? deck : belt) >= PEN_UNARMOURED;
    /* A belt seen at an angle is thicker along the shell's path, and at a steep angle deflects it. */
    float const plate = on_deck ? deck : belt / MAX(0.25f, broadside);
    if (!on_deck && armoured && broadside < PEN_RICOCHET_ANGLE && rand() % 100 < PEN_RICOCHET_CHANCE) {
        ballistic_callout(target, "RICOCHET", (color32_t){200, 200, 210, 255});
        return ballistic_result(BALLISTIC_RICOCHET, MAX(1, (int)(damage * BALLISTIC_RICOCHET_SCALE)));
    }
    if ((!armoured || pen >= plate * PEN_OVERPEN_RATIO) && ballistic_overpenetrates(pen)) return ballistic_overpen(target, damage);
    if (!armoured) { /* no armoured box to hold a citadel: the shell bursts in the hull */
        ballistic_maybe_fire(target, shooter, 6.0f + (float)damage / 50.0f);
        return ballistic_result(BALLISTIC_PENETRATION, damage);
    }
    if (pen < plate * PEN_SHATTER_RATIO) {
        ballistic_maybe_fire(target, shooter, PEN_FIRE_HE);
        ballistic_callout(target, "SHATTERED", (color32_t){170, 170, 180, 255});
        return ballistic_result(BALLISTIC_SHATTER, MAX(1, (int)(damage * BALLISTIC_RICOCHET_SCALE)));
    }
    if (pen < plate) {
        ballistic_maybe_fire(target, shooter, PEN_FIRE_HE);
        return ballistic_result(BALLISTIC_NO_PENETRATION, MAX(1, (int)(damage * PEN_NO_PEN_SCALE)));
    }
    ballistic_maybe_fire(target, shooter, 6.0f + (float)damage / 50.0f);
    if ((on_deck || broadside > 0.5f) && centred && (float)(rand() % 100) < citadel_chance * (0.5f + 0.5f * experience)) {
        ballistic_callout(target, "CITADEL!", (color32_t){255, 140, 40, 255});
        return ballistic_result(BALLISTIC_CITADEL, (int)(damage * BALLISTIC_CITADEL_SCALE));
    }
    return ballistic_result(BALLISTIC_PENETRATION, damage);
}

/* Torpedo protection (bulges, layered bulkheads, liquid loading) absorbs part of a hit;
 * a carrier's avgas and open hangar still make every hit far worse. */
int S_TorpedoDamage(edict_t const *target, int damage) {
    float protection = 0;
    S_ShipArmour(target, NULL, NULL, &protection);
    float scale = 1.0f - MIN(0.9f, MAX(0.0f, protection));
    if (ballistic_is_carrier(target)) scale *= BALLISTIC_CARRIER_TORPEDO;
    return MAX(1, (int)(damage * scale));
}

/* A ship-launched torpedo (s_torpedo.c) detonates against a hull: damage and flooding. */
void S_TorpedoStrike(edict_t *target, edict_t *source, int damage) {
    if (!target || M_IsDead(target)) return;
    ballistic_start(target, source, true);
    ballisticCrew_t *crew = ballistic_crew(target);
    if (crew) crew->hit_at = G_Time() | 1;
    T_Damage(target, source ? source : target, S_TorpedoDamage(target, damage));
}

static int ballistic_hit(edict_t *shooter, edict_t *target, int damage) {
    abilityAliasRef_t const ref = shooter ? S_ResolveAbilityAlias(shooter, BZ_BALLISTICS) : (abilityAliasRef_t){0};
    ballistic_last.outcome = BALLISTIC_HIT;
    ballistic_last.deck = false;
    /* Aircraft are engaged by flak and fighters, which keep their own hit rules. */
    if (!ref.alias || !target || damage <= 0 || (target->aiflags & AI_FLYING)) return damage;
    uint32_t *shots = ballistic_shots(shooter);
    float const experience = S_BallisticExperience(shooter);
    float const range = shooter->unit_state ? MAX(1.0f, shooter->unit_state->attack1.range) : 1.0f;
    float const distance = Vector2_distance(&shooter->s.origin2, &target->s.origin2);
    float const dispersion = S_BallisticDispersion(shooter) *
        (BALLISTIC_RANGE_NEAR + (BALLISTIC_RANGE_FAR - BALLISTIC_RANGE_NEAR) * MIN(1.0f, distance / range));
    bool const ship = ballistic_is_ship(target), torpedo = ref.alias == BZ_TORPEDO_BALLISTICS;
    float const broadside = ship ? ballistic_broadside(shooter, target) : 1.0f;
    if (shots) (*shots)++;
    /* Uniform landing point inside the dispersion circle; a ship end-on is narrower. */
    float const offset = dispersion * sqrtf((float)(rand() % 10000) / 10000.0f);
    float const hull = MAX(8.0f, target->collision) * (ship ? 0.6f + 0.4f * broadside : 1.0f);
    if (offset > hull + BALLISTIC_BLAST) return ballistic_result(BALLISTIC_MISS, 0);
    bool const carrier = ballistic_is_carrier(target);
    if (torpedo) {
        if (ship) ballistic_start(target, shooter, true);
        return ship ? S_TorpedoDamage(target, damage) : damage;
    }
    if (carrier && ref.alias == BZ_BOMB_BALLISTICS) {
        if (rand() % 100 < BALLISTIC_CARRIER_FIRE_CHANCE) ballistic_start(target, shooter, false);
        return (int)(damage * BALLISTIC_CARRIER_BOMB);
    }
    if (ship && S_SpellData(ref.alias, 1, 6) > 0 && S_ShipArmour(target, NULL, NULL, NULL))
        return ballistic_armour_hit(shooter, target, damage, distance, broadside, offset <= hull * BALLISTIC_CITADEL_CORE,
                                    experience, S_SpellData(ref.alias, 1, 4));
    float const armor = target->unit_state ? target->unit_state->armor_value : 0.0f;
    if (armor >= 3.0f) {
        float const ricochet = S_SpellData(ref.alias, 1, 5) + armor * 1.5f - (float)damage / 20.0f + (1.0f - broadside) * 25.0f;
        if ((float)(rand() % 100) < MIN(45.0f, ricochet)) {
            ballistic_callout(target, "RICOCHET", (color32_t){200, 200, 210, 255});
            return ballistic_result(BALLISTIC_RICOCHET, MAX(1, (int)(damage * BALLISTIC_RICOCHET_SCALE)));
        }
    }
    if (ship && damage >= BALLISTIC_OVERPEN_DAMAGE && armor <= BALLISTIC_OVERPEN_ARMOR &&
        rand() % 100 < BALLISTIC_OVERPEN_CHANCE) return ballistic_overpen(target, damage);
    if ((ship || G_UnitIsStructure(target)) && (float)(rand() % 100) < 6.0f + (float)damage / 50.0f)
        ballistic_start(target, shooter, false);
    if (ship && broadside > 0.5f && offset <= hull * BALLISTIC_CITADEL_CORE &&
        (float)(rand() % 100) < S_SpellData(ref.alias, 1, 4) * (0.5f + 0.5f * experience)) {
        ballistic_callout(target, "CITADEL!", (color32_t){255, 140, 40, 255});
        return ballistic_result(BALLISTIC_CITADEL, (int)(damage * BALLISTIC_CITADEL_SCALE));
    }
    return damage;
}

/* Read-only presentation state (ship condition animation in s_naval.c). */
static ballisticCrew_t const *ballistic_record(edict_t const *ent) {
    uint32_t const index = ent ? (uint32_t)(ent - globals.edicts) : MAX_ENTITIES;
    ballisticCrew_t const *crew = index < MAX_ENTITIES ? &ballistic_experience[index] : NULL;
    return crew && crew->used && crew->spawn_time == ent->spawn_time && crew->map == S_SideTableGeneration() ? crew : NULL;
}
bool S_BallisticBurning(edict_t const *ent) {
    ballisticCrew_t const *crew = ballistic_record(ent);
    return crew && crew->fire_until > G_Time();
}
bool S_BallisticUnderFire(edict_t const *ent, uint32_t window_ms) {
    ballisticCrew_t const *crew = ballistic_record(ent);
    return crew && crew->hit_at && G_Time() - crew->hit_at < window_ms;
}
bool S_BallisticFlooding(edict_t const *ent) {
    ballisticCrew_t const *crew = ballistic_record(ent);
    return crew && crew->flood_until > G_Time();
}

/* Fires and flooding tick once a second on the burning or flooding unit itself. */
static void ballistic_tick(edict_t *ent) {
    uint32_t const index = (uint32_t)(ent - globals.edicts);
    if (index >= MAX_ENTITIES) return;
    ballisticCrew_t *crew = &ballistic_experience[index];
    uint32_t const now = G_Time();
    if (!crew->used || crew->spawn_time != ent->spawn_time || crew->map != S_SideTableGeneration() || (crew->fire_until <= now && crew->flood_until <= now) ||
        now < crew->next_tick || M_IsDead(ent) || ent->health.max_value <= 0) return;
    crew->next_tick = now + 1000;
    float rate = 0;
    if (crew->fire_until > now) {
        rate += ballistic_is_carrier(ent) ? BALLISTIC_CARRIER_FIRE_RATE : BALLISTIC_FIRE_RATE;
        edict_t puff = { 0 };
        puff.s = ent->s;
        puff.s.origin.z += 20;
        puff.s.origin2 = (vec2_t){ ent->s.origin.x, ent->s.origin.y };
        puff.s.model = G_RegisterModel("Emberfield/Models/fire.mdx");
        G_SpawnProjectileImpact(&puff);
    }
    if (crew->flood_until > now) rate += BALLISTIC_FLOOD_RATE * (float)MAX(1u, crew->flood_hits) * ballistic_flood_scale(ent);
    edict_t *source = crew->source && crew->source->inuse && crew->source->spawn_time == crew->source_spawn ? crew->source : ent;
    T_Damage(ent, source, (int)MAX(1.0f, ent->health.max_value * rate));
}

BZ_ABILITY_PROC(CAbilityBallistics) {
    if (msg == A_UPDATE) { if (ent) ballistic_tick(ent); return false; }
    return CAbilityPassive(ent, msg, call);
}
