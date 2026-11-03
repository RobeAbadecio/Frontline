/*
 * s_aamount.c -- Frontline AA Mount: a structure buys one light anti-aircraft mount.
 *
 * Fmnt aliases (one per structure model, tools/frontline/catalog.py AA_MOUNT):
 * level 1 = offered, level 2 = installed. A..E follow the Fbaa volley layout
 * (range, damage per hit, volley s, base hit %, barrels), F/G = materiel/logistics
 * price, H/I = the mount's model-space Y/Z. The director draws the mount model at
 * that point and fires its volleys from there; it fires at aircraft only.
 */
#include "s_skills.h"

#define BZ_AA_MOUNT MAKEFOURCC('F','m','n','t')
#define AA_MOUNT_MODEL "Emberfield/Models/aa_mount.mdx"

static abilityLevel_t const *aa_mount_config(edict_t *ent) {
    abilityAliasRef_t const ref = ent ? S_ResolveAbilityAlias(ent, BZ_AA_MOUNT) : (abilityAliasRef_t){0};
    return ref.alias ? G_AbilityLevel(ref.alias, 1) : NULL;
}

bool S_AAMountInstalled(edict_t const *ent) {
    abilityAliasRef_t const ref = ent ? S_ResolveAbilityAlias((edict_t *)ent, BZ_AA_MOUNT) : (abilityAliasRef_t){0};
    return ref.alias && G_UnitAbilityLevel(ent, ref.alias) >= 2;
}

/* World position of the mount: model-space (0, H, I) through the structure's transform. */
bool S_AAMountPoint(edict_t *ent, vec3_t *out) {
    abilityLevel_t const *cfg = aa_mount_config(ent);
    mat4_t matrix;
    if (!cfg || !out) return false;
    M_GetEntityMatrix(&ent->s, &matrix);
    *out = Matrix4_multiply_vector3(&matrix, &(vec3_t){0, cfg->data[7].number, cfg->data[8].number});
    return true;
}

void aa_mount_think(edict_t *director) {
    edict_t *gun = S_SpellChannelOwner(director);
    edict_t *mount = S_SpellChannelTarget(director);
    abilityLevel_t const *cfg = gun ? aa_mount_config(gun) : NULL;
    vec3_t point;

    if (!gun || !cfg || M_IsDead(gun) || !S_AAMountInstalled(gun)) {
        if (mount && mount->inuse) G_FreeEdict(mount);
        G_FreeEdict(director);
        return;
    }
    if (gun->construction || G_BuildingUpgradeActive(gun) || G_UnitHasFlag(gun, UNIT_FLAG_PAUSED) ||
        G_Time() < director->freetime || !S_AAMountPoint(gun, &point)) return;
    if (!S_AntiAirVolley(gun, cfg, &point)) return;
    director->freetime = G_Time() + (uint32_t)(MAX(.2f, cfg->data[2].number) * 1000);
}

/* The director owns the drawn mount: one per installed structure, rebuilt after a load. */
static edict_t *aa_mount_director(edict_t *ent) {
    FILTER_EDICTS(d, d->inuse && d->think == aa_mount_think && S_SpellChannelOwner(d) == ent) return d;
    return NULL;
}

static void aa_mount_spawn(edict_t *ent) {
    vec3_t point;
    edict_t *director, *mount;
    if (aa_mount_director(ent) || !S_AAMountPoint(ent, &point)) return;
    mount = G_SpawnModelEffect(AA_MOUNT_MODEL, &(vec2_t){point.x, point.y}, NULL, NULL, false);
    if (mount) {
        mount->s.origin.z = point.z;
        mount->s.angle = ent->s.angle;
        G_InheritUnitTeamColor(mount, ent);
        gi.LinkEntity(mount);
    }
    director = S_SpellIdentityThinker(ent, BZ_AA_MOUNT, mount);
    if (!director) return;
    director->think = aa_mount_think;
    director->freetime = G_Time();
}

static bool aa_mount_install(gameClient_t *client, edict_t *ent, uint32_t code) {
    float const materiel = S_SpellData(code, 1, 6), logistics = S_SpellData(code, 1, 7);
    if (M_IsDead(ent) || ent->construction || G_BuildingUpgradeActive(ent) || S_AAMountInstalled(ent)) return false;
    if (client->ps.stats[PLAYERSTATE_RESOURCE_GOLD] < materiel ||
        client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER] < logistics) return false;
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD] -= (uint16_t)materiel;
    client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER] -= (uint16_t)logistics;
    G_UnitSetAbilityLevel(ent, code, 2);
    aa_mount_spawn(ent);
    return true;
}

BZ_ABILITY_PROC(CAbilityAAMount) {
    switch (msg) {
    case A_COMMAND: {
        edict_t *clent = call && call->entity ? call->entity : ent;
        uint32_t const code = call && call->item ? call->item->code : 0;
        bool installed = false, refused = false;
        if (!clent || !clent->client || !code) return false;
        FOR_CONTROLLABLE_SELECTED_UNITS(clent->client, building) {
            if (!G_UnitAbilityLevel(building, code) || S_AAMountInstalled(building)) continue;
            if (aa_mount_install(clent->client, building, code)) installed = true;
            else refused = true;
        }
        if (!installed && refused)
            G_ShowCommandErrorText(clent, "AA Mount needs a finished structure and enough materiel and logistics.");
        if (installed) G_RefreshResourceBar(clent);
        G_InvalidateCommands(clent->client);
        return installed;
    }
    case A_UPDATE:
        /* Restores the director after a load; once a second per installed structure. */
        if (!ent || M_IsDead(ent) || (G_Time() + (uint32_t)ent->s.number * 37) % 1000 >= FRAMETIME ||
            !S_AAMountInstalled(ent)) return false;
        aa_mount_spawn(ent);
        return true;
    default:
        return false;
    }
}
