/*
 * s_airfield.c -- Frontline airfield capture (Fcpt).
 *
 * Airfields are shared ground: the map's fields start with the passive neutral
 * player and any side takes one by holding ground troops beside it, uncontested,
 * for A seconds within B of its footprint. The owner's (or an ally's) troops
 * beside it, or two hostile sides at once, stop the count. Aircraft land, store
 * and take off only at their own side's field: cargo already requires the
 * holder's owner, so a captured field releases the previous owner's aircraft.
 *
 * State lives in the field's `resources` (an airfield is not a mine):
 * bits 0..4 = capturing player + 1, bits 8..23 = held time in 100 ms steps.
 */
#include "s_skills.h"

#define BZ_AIRFIELD_CAPTURE MAKEFOURCC('F','c','p','t')
#define BZ_AIRFIELD_CAP_TOGGLE MAKEFOURCC('F','a','c','p')
#define CAPTURE_STEP_MS 500
#define CAPTURE_PLAYER(state) ((int32_t)((state) & 0x1fu) - 1)
#define CAPTURE_TENTHS(state) (((state) >> 8) & 0xffffu)

static bool capture_holder(edict_t const *field, edict_t const *unit, float radius) {
    return unit->inuse && (unit->svflags & SVF_MONSTER) && !M_IsDead(unit) && unit != field &&
        !G_UnitIsStructure(unit) && !(unit->aiflags & AI_FLYING) && !(unit->s.renderfx & RF_HIDDEN) &&
        unit->s.player < PLAYER_NEUTRAL_AGGRESSIVE && unit->data.UnitBalance && unit->data.UnitBalance->speed > 0 &&
        Vector2_distance(&unit->s.origin2, &field->s.origin2) <= radius + field->collision;
}

static bool capture_friendly(uint32_t owner, uint32_t player) {
    return owner < PLAYER_NEUTRAL_AGGRESSIVE && (player == owner || G_PlayerTreatsPlayerAsAlly(owner, player));
}

/* The one hostile side holding the field, or -1 when nobody, the owner's side, or two sides are there. */
static int32_t capture_claimant(edict_t const *field, float radius) {
    int32_t claimant = -1;
    FILTER_EDICTS(unit, capture_holder(field, unit, radius)) {
        uint32_t const player = unit->s.player;
        if (capture_friendly(field->s.player, player)) return -1;
        if (claimant < 0) claimant = (int32_t)player;
        else if ((uint32_t)claimant != player && !G_PlayerTreatsPlayerAsAlly((uint32_t)claimant, player)) return -1;
    }
    return claimant;
}

static void capture_notice(uint32_t player, cstring_t text) {
    edict_t *ent = player < PLAYER_NEUTRAL_AGGRESSIVE ? G_GetPlayerEntityByNumber(player) : NULL;
    if (ent && ent->client) UI_ShowText(ent, &(vec2_t){0.15f, 0.25f}, text, 5.0f);
}

void S_AirfieldCapture(edict_t *field, uint32_t player) {
    uint32_t const previous = field->s.player;
    player_t *owner = G_GetPlayerByNumber(player);

    /* The previous owner's stored aircraft take off before the field changes hands. */
    for (int32_t i = field->cargo ? (int32_t)field->cargo->count - 1 : -1; i >= 0; i--)
        S_CargoUnloadAt(field, (uint32_t)i);
    if (G_ProductionQueueCount(field)) G_CancelTrainingQueue(field, true);
    G_SetUnitPlayer(field, player);
    G_ClearUnitColorOverride(field);
    if (owner) G_SetUnitTeamColor(field, owner->color);
    G_SetUnitFlag(field, UNIT_FLAG_INVULNERABLE, false);
    if (G_UnitAbilityLevel(field, BZ_AIRFIELD_CAP_TOGGLE)) G_UnitSetAbilityLevel(field, BZ_AIRFIELD_CAP_TOGGLE, 1);
    field->resources = 0;
    capture_notice(player, "Airfield captured: your aircraft can now land, store and take off here.");
    capture_notice(previous, "Airfield lost to the enemy.");
    G_InvalidateCommands(G_GetPlayerClientByNumber(previous));
    G_InvalidateCommands(G_GetPlayerClientByNumber(player));
}

/* Seconds held toward capture (tests and presentation). */
float S_AirfieldCaptureProgress(edict_t const *field, int32_t *player) {
    if (player) *player = field ? CAPTURE_PLAYER(field->resources) : -1;
    return field ? CAPTURE_TENTHS(field->resources) / 10.0f : 0;
}

BZ_ABILITY_PROC(CAbilityAirfieldCapture) {
    (void)call;
    if (msg != A_UPDATE || !ent || M_IsDead(ent) || ent->construction ||
        (G_Time() + (uint32_t)ent->s.number * 37) % CAPTURE_STEP_MS >= FRAMETIME) return false;
    abilityAliasRef_t const ref = S_ResolveAbilityAlias(ent, BZ_AIRFIELD_CAPTURE);
    if (!ref.alias) return false;
    float const seconds = MAX(1, S_SpellData(ref.alias, 1, 1)), radius = S_SpellData(ref.alias, 1, 2);
    /* An unclaimed field cannot be destroyed, only taken. */
    if (ent->s.player == PLAYER_NEUTRAL_PASSIVE) G_SetUnitFlag(ent, UNIT_FLAG_INVULNERABLE, true);
    int32_t const claimant = capture_claimant(ent, radius);
    if (claimant < 0) { ent->resources = 0; return false; }
    uint32_t tenths = CAPTURE_PLAYER(ent->resources) == claimant ? CAPTURE_TENTHS(ent->resources) : 0;
    if (!tenths) capture_notice((uint32_t)claimant, "Capturing airfield: hold the ground around it.");
    tenths += CAPTURE_STEP_MS / 100;
    if (tenths >= (uint32_t)(seconds * 10)) {
        S_AirfieldCapture(ent, (uint32_t)claimant);
        return true;
    }
    ent->resources = (uint32_t)(claimant + 1) | (MIN(tenths, 0xffffu) << 8);
    return true;
}
