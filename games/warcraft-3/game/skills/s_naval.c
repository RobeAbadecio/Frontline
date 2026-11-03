/* Original naval presentation and an existing-unit fleet preset. Game-owned
 * child edicts carry final position/heading/frame through the existing wire. */
#include "s_skills.h"
#include <float.h>
#define BZ_NAVAL_GUN MAKEFOURCC('F','g','u','n')

/* Ship condition presentation (tools/frontline/ship_states.py builds one sequence per
 * state). List levels: roll to starboard (deg), bow-down trim (deg), freeboard drop.
 * Must match ship_states.POSES. */
#define SHIP_LIST_LEVELS 4
#define SHIP_LIST_STEP_MS 800u /* one level per step: the hull settles gradually */
static float const SHIP_POSE[SHIP_LIST_LEVELS][3] = {{0,0,0},{3.5f,0.8f,2.5f},{7,1.6f,5},{11,2.6f,8}};
static cstring_t const SHIP_EFFECT[] = {"", "smoke", "fire", "inferno"};
typedef struct { bool used; uint32_t spawn_time, next_step, status; uint8_t level, effect; } shipCondition_t;
static shipCondition_t ship_condition[MAX_ENTITIES];
/* Map load: a new match's units must not inherit a previous match's slot records. */
void S_ShipConditionReset(void) { memset(ship_condition, 0, sizeof(ship_condition)); }

static shipCondition_t *ship_condition_of(edict_t const *ship) {
    uint32_t const index = ship ? (uint32_t)(ship - globals.edicts) : MAX_ENTITIES;
    if (index >= MAX_ENTITIES) return NULL;
    shipCondition_t *c = &ship_condition[index];
    if (!c->used || c->spawn_time != ship->spawn_time) *c = (shipCondition_t){ .used = true, .spawn_time = ship->spawn_time };
    return c;
}

/* Death plunge (bow first) as in ship_states.py: (fraction, roll, trim, z) over SHIP_DEATH_MS. */
#define SHIP_DEATH_MS 6000u
static float const SHIP_PLUNGE[][4] = {{0,0,0,0},{.2f,4,3,-6},{.5f,7,14,-26},{.8f,9,28,-70},{1,10,38,-130}};

static uint32_t ship_condition_level(edict_t const *ship);
/* Current presented pose (roll, trim, drop) for attachments; `mount->freetime` records
 * when it first saw its ship dead so turrets go down with the hull. */
void S_ShipPose(edict_t const *ship, edict_t *mount, float pose[3]) {
    if (!M_IsDead(ship)) {
        float const *p = SHIP_POSE[MIN(SHIP_LIST_LEVELS - 1, ship_condition_level(ship))];
        pose[0] = p[0]; pose[1] = p[1]; pose[2] = p[2];
        if (mount) mount->freetime = 0;
        return;
    }
    if (mount && !mount->freetime) mount->freetime = MAX(1u, G_Time());
    float const f = mount ? MIN(1.0f, (float)(G_Time() - mount->freetime) / SHIP_DEATH_MS) : 1.0f;
    uint32_t i = 1;
    while (i < sizeof(SHIP_PLUNGE) / sizeof(SHIP_PLUNGE[0]) - 1 && f > SHIP_PLUNGE[i][0]) i++;
    float const *a = SHIP_PLUNGE[i - 1], *b = SHIP_PLUNGE[i];
    float const t = (f - a[0]) / MAX(1e-4f, b[0] - a[0]);
    pose[0] = a[1] + (b[1] - a[1]) * t; pose[1] = a[2] + (b[2] - a[2]) * t; pose[2] = -(a[3] + (b[3] - a[3]) * t);
}

uint32_t S_ShipListLevel(edict_t const *ship) { shipCondition_t *c = ship_condition_of(ship); return c ? c->level : 0; }
static uint32_t ship_condition_level(edict_t const *ship) { return S_ShipListLevel(ship); }
uint32_t S_ShipEffect(edict_t const *ship) { shipCondition_t *c = ship_condition_of(ship); return c ? c->effect : 0; }

/* Target state from health and the ballistics fire/flooding records:
 * effect 0 healthy, 1 smoke (light damage), 2 fire (burning), 3 inferno (critical);
 * list level from flooding and critical damage. */
void S_ShipConditionTarget(edict_t const *ship, uint32_t *effect, uint32_t *level) {
    float const ratio = ship->health.max_value > 0 ? ship->health.value / ship->health.max_value : 1;
    bool const burning = S_BallisticBurning(ship), flooding = S_BallisticFlooding(ship);
    bool const critical = ratio < 0.25f;
    *effect = critical ? 3 : burning ? 2 : (ratio < 0.6f || flooding) ? 1 : 0;
    *level = flooding ? (ratio < 0.4f ? 3 : 2) : critical ? 2 : 0;
}

/* Step the presented list one level per SHIP_LIST_STEP_MS toward the target and
 * publish both as animation properties ("List2 Fire" selects that sequence). */
void S_ShipConditionUpdate(edict_t *ship) {
    shipCondition_t *c = ship_condition_of(ship);
    if (!c) return;
    /* The unit panel draws S_ShipStatusFlags as icons (hud_infopanel.c); repaint on change. */
    uint32_t const status = S_ShipStatusFlags(ship);
    if (status != c->status) { c->status = status; G_InvalidateUnitInfoPanel(ship); }
    uint32_t effect, level, now = G_Time();
    S_ShipConditionTarget(ship, &effect, &level);
    uint32_t new_level = c->level;
    if (level != c->level && now >= c->next_step) {
        new_level = level > c->level ? c->level + 1 : c->level - 1;
        c->next_step = now + SHIP_LIST_STEP_MS;
    }
    if (new_level == c->level && effect == c->effect) return;
    c->level = (uint8_t)new_level;
    c->effect = (uint8_t)effect;
    G_AddUnitAnimationProperties(ship, "list1 list2 list3 smoke fire inferno", false);
    char tags[32];
    snprintf(tags, sizeof(tags), "%s%s%s", c->level ? (c->level == 1 ? "list1" : c->level == 2 ? "list2" : "list3") : "",
             c->level && c->effect ? " " : "", SHIP_EFFECT[c->effect]);
    if (tags[0]) G_AddUnitAnimationProperties(ship, tags, true);
}

/* Main turrets knocked out by hits (S_BallisticHit): bit i = mount `variation` i. The ship
 * keeps firing while any main turret works, at the working fraction of its firepower; a
 * dry dock repairs them. Side table keyed by edict, spawn time and map generation. */
typedef struct { uint32_t map, spawn_time; uint8_t broken; } turretDamage_t;
static turretDamage_t turret_damage[MAX_ENTITIES];

static turretDamage_t *turret_record(edict_t const *ship) {
    uint32_t const index = ship ? (uint32_t)(ship - globals.edicts) : MAX_ENTITIES;
    if (index >= MAX_ENTITIES) return NULL;
    turretDamage_t *t = &turret_damage[index];
    if (t->spawn_time != ship->spawn_time || t->map != S_SideTableGeneration())
        *t = (turretDamage_t){ .map = S_SideTableGeneration(), .spawn_time = ship->spawn_time };
    return t;
}

uint32_t S_NavalMountCount(edict_t const *ship) {
    abilityAliasRef_t const ref = ship ? S_ResolveAbilityAlias((edict_t *)ship, BZ_NAVAL_GUN) : (abilityAliasRef_t){0};
    return ref.alias ? (uint32_t)MAX(0, MIN(4, G_AbilityLevel(ref.alias, ref.level)->data[0].number)) : 0;
}

bool S_NavalMountBroken(edict_t const *ship, uint32_t index) {
    turretDamage_t const *t = turret_record(ship);
    return t && index < 8 && (t->broken & (1u << index));
}

bool S_NavalBreakMount(edict_t *ship) {
    uint32_t const count = S_NavalMountCount(ship);
    turretDamage_t *t = turret_record(ship);
    uint32_t idx[4], n = 0;
    if (!t || !count) return false;
    FOR_LOOP(i, count) if (!(t->broken & (1u << i))) idx[n++] = i;
    if (!n) return false;
    t->broken |= (uint8_t)(1u << idx[rand() % n]);
    G_InvalidateUnitInfoPanel(ship);
    return true;
}

void S_NavalRepairMounts(edict_t *ship) {
    turretDamage_t *t = turret_record(ship);
    if (t && t->broken) { t->broken = 0; G_InvalidateUnitInfoPanel(ship); }
}

/* Fraction of the main battery still in action (1 for ships without turret mounts). */
float S_NavalBatteryFraction(edict_t const *ship) {
    uint32_t const count = S_NavalMountCount(ship);
    if (!count) return 1.0f;
    uint32_t broken = 0;
    FOR_LOOP(i, count) if (S_NavalMountBroken(ship, i)) broken++;
    return (float)(count - broken) / (float)count;
}

/* Status for the unit panel icons (graphics) and tooltips: see s_skills.h SHIP_STATUS_*. */
uint32_t S_ShipStatusFlags(edict_t const *ship) {
    if (!ship || !S_IsShip(ship) || M_IsDead((edict_t *)ship)) return 0;
    uint32_t flags = 0;
    float const ratio = ship->health.max_value > 0 ? ship->health.value / ship->health.max_value : 1;
    if (S_BallisticBurning(ship)) flags |= SHIP_STATUS_BURNING;
    if (S_BallisticFlooding(ship)) flags |= SHIP_STATUS_FLOODING;
    FOR_LOOP(i, S_NavalMountCount(ship)) if (S_NavalMountBroken(ship, i)) flags |= SHIP_STATUS_TURRET_OUT;
    if (S_ShipListLevel(ship) >= 2) flags |= SHIP_STATUS_LISTING;
    if (ratio < 0.25f) flags |= SHIP_STATUS_CRITICAL;
    if (S_ShipDocked(ship)) flags |= SHIP_STATUS_DOCKED;
    return flags;
}

cstring_t S_ShipStatusTooltip(uint32_t flag) {
    switch (flag) {
    case SHIP_STATUS_BURNING: return "Burning: losing hull every second until the fire burns out.";
    case SHIP_STATUS_FLOODING: return "Flooding: taking on water; repeated torpedo hits make it worse.";
    case SHIP_STATUS_TURRET_OUT: return "Main turret out: firepower reduced; the ship fires with its remaining turrets. Repaired in dry dock.";
    case SHIP_STATUS_LISTING: return "Listing: heavy flooding or damage.";
    case SHIP_STATUS_DEAD_IN_WATER: return "Dead in the water.";
    case SHIP_STATUS_CRITICAL: return "Critical: under 25% hull. Send it to a shipyard.";
    case SHIP_STATUS_DOCKED: return "In dry dock: being repaired.";
    default: return "";
    }
}

void naval_battery_think(edict_t *mount) {
    edict_t *ship=S_SpellChannelOwner(mount);
    if (!ship || !S_ResolveAbilityAlias(ship,BZ_NAVAL_GUN).alias) { G_FreeEdict(mount);return; }
    float c=cosf(ship->s.angle),s=sinf(ship->s.angle);
    /* Ride the hull's condition pose (roll about the bow axis, then bow-down trim,
     * then the lower freeboard) so turrets stay seated on a listing deck. */
    float pose[3];
    S_ShipPose(ship,mount,pose);
    float const roll=pose[0]*(float)M_PI/180,trim=pose[1]*(float)M_PI/180;
    float const ox=mount->channel->origin.x,oz=mount->wait;
    float const y1=-oz*sinf(roll),z1=oz*cosf(roll);
    float const x2=ox*cosf(trim)+z1*sinf(trim),z2=-ox*sinf(trim)+z1*cosf(trim)-pose[2];
    mount->s.origin=(vec3_t){ship->s.origin.x+c*x2-s*y1,ship->s.origin.y+s*x2+c*y1,ship->s.origin.z+z2};
    float bearing=ship->s.angle+(mount->channel->origin.x<0 ? M_PI : 0);
    edict_t *underway=M_IsDead(ship) ? NULL : S_UnderwayTarget(ship);
    if (!M_IsDead(ship) && ship->goalentity && S_AttackCanTarget(ship,ship->goalentity) &&
        ship->currentmove && ship->currentmove->proc==CAbilityAttack)
        bearing=atan2f(ship->goalentity->s.origin.y-mount->s.origin.y,ship->goalentity->s.origin.x-mount->s.origin.x);
    else if (underway) /* firing on the move: turrets train on the target, the hull holds its course */
        bearing=atan2f(underway->s.origin.y-mount->s.origin.y,underway->s.origin.x-mount->s.origin.x);
    float delta=remainderf(bearing-mount->s.angle,2*M_PI);
    /* A knocked-out turret stays trained where it was hit. */
    if (!G_UnitHasFlag(ship,UNIT_FLAG_PAUSED) && !S_NavalMountBroken(ship,mount->variation)) mount->s.angle+=MAX(-.12f,MIN(.12f,delta));
    mount->s.frame=ship->s.frame;
    mount->s.renderfx=ship->s.renderfx;
    mount->s.player=ship->s.player;
    G_InheritUnitTeamColor(mount,ship);
    gi.LinkEntity(mount);
}

bool S_NavalMuzzle(edict_t *ship, vec2_t const *aim, vec3_t *start) {
    if (!ship || !aim || !start || !S_ResolveAbilityAlias(ship,BZ_NAVAL_GUN).alias) return false;
    edict_t *best=NULL;float distance=FLT_MAX;
    FILTER_EDICTS(m,m->inuse && m->think==naval_battery_think && S_SpellChannelOwner(m)==ship &&
                    !S_NavalMountBroken(ship,m->variation)) {
        float d=Vector2_distance(&m->s.origin2,aim);
        if (d<distance) {distance=d;best=m;}
    }
    if (!best) return false;
    *start=best->s.origin;
    /* Authored launch fields are turret-local for attached naval batteries. */
    float forward=G_UnitAttack1LaunchX(ship->class_id),height=G_UnitAttack1LaunchZ(ship->class_id);
    if (forward==0) forward=44;
    if (height==0) height=10;
    start->x+=cosf(best->s.angle)*forward;start->y+=sinf(best->s.angle)*forward;start->z+=height;
    return true;
}

BZ_ABILITY_PROC(CAbilityNavalBattery) {
    (void)call;
    /* Mounts are spawned once; check about once a second, and never for aircraft or buildings. */
    if (msg!=A_UPDATE || !ent || (ent->aiflags&AI_FLYING) || G_UnitIsStructure(ent) ||
        (G_Time()+(uint32_t)ent->s.number*41)%1000>=FRAMETIME || M_IsDead(ent) || (ent->s.renderfx&RF_HIDDEN)) return false;
    abilityAliasRef_t ref=S_ResolveAbilityAlias(ent,BZ_NAVAL_GUN);
    if (!ref.alias) return false;
    FILTER_EDICTS(m,m->inuse && m->think==naval_battery_think && S_SpellChannelOwner(m)==ent) return true;
    abilityLevel_t const *cfg=G_AbilityLevel(ref.alias,ref.level);
    uint32_t count=(uint32_t)MAX(0,MIN(4,cfg->data[0].number));
    FOR_LOOP(i,count) {
        edict_t *mount=S_SpellIdentityThinker(ent,BZ_NAVAL_GUN,NULL);
        if (!mount) break;
        mount->think=naval_battery_think;
        mount->variation=i;
        mount->channel->origin.x=cfg->data[2+i].number;
        mount->wait=i<3 ? cfg->data[6+i].number : cfg->data[6].number;
        cstring_t art=G_AbilityEffectArt(ref.alias,WC3_EFFECT_TARGET,i);
        mount->s.model=gi.ModelIndex(art ? art : cfg->data[1].number==2 ? "Emberfield/Models/naval_twin.mdx":"Emberfield/Models/naval_triple.mdx");
        mount->s.scale=1;mount->s.angle=ent->s.angle+(mount->channel->origin.x<0 ? M_PI : 0);
        mount->s.flags|=EF_NOT_SELECTABLE;
        naval_battery_think(mount);
    }
    return true;
}

BZ_ABILITY_PROC(CAbilityNavalFormation) {
    if (msg!=A_COMMAND) return false;
    edict_t *clent=call && call->entity ? call->entity : ent;
    if (!clent || !clent->client) return false;
    gameClient_t *client=clent->client;
    static cstring_t const roster[]={"jakg","jkag","jsor","jhir","jsho","jzui","jmog","jfub"};
    edict_t *fleet[(sizeof(roster)/sizeof(roster[0]))];
    vec2_t center={0};
    FOR_LOOP(i,(sizeof(roster)/sizeof(roster[0]))) {
        fleet[i]=NULL;
        FILTER_EDICTS(ship,ship->inuse && ship->s.player==client->ps.number && ship->class_id==FS_SLKKey(roster[i]) &&
            !M_IsDead(ship) && !(ship->s.renderfx&RF_HIDDEN)) { fleet[i]=ship;break; }
        if (!fleet[i]) {
            G_ShowCommandErrorText(clent,"Kido Butai requires Akagi, Kaga, Soryu, Hiryu, Shokaku, Zuikaku, Mogami and Fubuki. Build them at the Capital and Escort Shipyards.");
            return false;
        }
        center.x+=fleet[i]->s.origin.x/(sizeof(roster)/sizeof(roster[0]));center.y+=fleet[i]->s.origin.y/(sizeof(roster)/sizeof(roster[0]));
    }
    FILTER_EDICTS(ship,ship->inuse && G_IsEntitySelected(client,ship)) G_DeselectEntity(client,ship);
    FOR_LOOP(i,(sizeof(roster)/sizeof(roster[0]))) {
        G_SelectEntity(client,fleet[i]);
        if (G_UnitAbilityLevel(fleet[i],MAKEFOURCC('F','c','a','p'))==2) unit_issueimmediateorder(fleet[i],"togglecap");
    }
    S_SetFormation(client,4,320);
    move_selectlocation(clent,&center);
    G_InvalidateCommands(client);
    return true;
}

#define BZ_SHIP_AA MAKEFOURCC('F','b','a','a')
#define BZ_AIR_EVASION MAKEFOURCC('F','e','v','d')
#define AA_MAX_TARGETS 8

/* Aircraft evasion: A=evade chance %, B=maneuver seconds, C=jink speed, D=recovery
 * seconds. While recovering a pilot cannot evade again, so evasion lowers hit rates
 * without making aircraft invulnerable. A maneuver delays the aircraft's own fire. */
bool S_AircraftEvades(edict_t *target, edict_t *attacker) {
    (void)attacker;
    if (!target || !(target->aiflags & AI_FLYING) || M_IsDead(target)) return false;
    abilityAliasRef_t ref=S_ResolveAbilityAlias(target,BZ_AIR_EVASION);
    if (!ref.alias) return false;
    abilityLevel_t const *cfg=G_AbilityLevel(ref.alias,ref.level);
    uint32_t const now=G_Time();
    bool const maneuvering=now<target->evade_until;
    if (!maneuvering && now<target->evade_ready) return false;
    /* A wounded pilot (s_air_combat.c) maneuvers half as often. */
    float const chance=cfg->data[0].number*(maneuvering ? 1.3f : 1.0f)*(S_AircraftCritStates(target)&(1u<<AIR_CRIT_PILOT) ? .5f : 1.0f);
    if ((float)(rand()%100)>=MIN(60.0f,chance)) return false;
    S_AircraftEvadeEffect(target);
    if (!maneuvering) {
        target->evade_until=now+(uint32_t)(cfg->data[1].number*1000);
        target->evade_ready=target->evade_until+(uint32_t)(cfg->data[3].number*1000);
        if (target->unit_state)
            target->unit_state->attack_cooldown_end_time=MAX(target->unit_state->attack_cooldown_end_time,target->evade_until);
    }
    return true;
}

/* The jink: a lateral S-turn across the flight path that breaks formation briefly. */
BZ_ABILITY_PROC(CAbilityAircraftEvasion) {
    (void)call;
    if (msg==A_UPDATE) S_AircraftEffectsUpdate(ent); /* jink expiry, pending crash */
    if (msg!=A_UPDATE || !ent || M_IsDead(ent) || G_Time()>=ent->evade_until) return false;
    abilityAliasRef_t ref=S_ResolveAbilityAlias(ent,BZ_AIR_EVASION);
    if (!ref.alias) return false;
    abilityLevel_t const *cfg=G_AbilityLevel(ref.alias,ref.level);
    float const duration=MAX(.1f,cfg->data[1].number)*1000;
    float const phase=1-(ent->evade_until-G_Time())/duration;
    float const side=(ent->evade_ready/100)&1 ? 1 : -1;
    float const step=cfg->data[2].number*FRAMETIME/1000.0f*sinf(phase*2*M_PI)*side;
    ent->s.origin.x+=-sinf(ent->s.angle)*step;ent->s.origin.y+=cosf(ent->s.angle)*step;
    ent->s.origin2=(vec2_t){ent->s.origin.x,ent->s.origin.y};
    gi.LinkEntity(ent);
    return true;
}

/* Battleship AA: A=range, B=damage per hit, C=volley seconds, D=base hit %, E=mounts.
 * Runs independently of the main battery. Faster targets and longer ranges lower
 * the hit chance; target evasion is then applied on impact like any other hit. */
/* One AA volley in the Fbaa layout (A=range, B=damage per hit, C=volley seconds, D=base
 * hit %, E=barrels). A NULL mount spreads the barrels along a hull; a structure's AA Mount
 * passes its model-space mount point. Returns whether anything was in range. */
bool S_AntiAirVolley(edict_t *gun, abilityLevel_t const *cfg, vec3_t const *mount) {
    float const range=cfg->data[0].number;
    edict_t *targets[AA_MAX_TARGETS];float distances[AA_MAX_TARGETS];uint32_t count=0;
    FILTER_EDICTS(e,e->inuse && !M_IsDead(e) && (e->aiflags&AI_FLYING) && !(e->s.renderfx&RF_HIDDEN) &&
                    S_SpellIsEnemy(gun,e)) {
        /* Within AA range is well inside the ship's sight, like ordinary passive acquisition. */
        float d=Vector2_distance(&gun->s.origin2,&e->s.origin2);
        if (d>range) continue;
        uint32_t i=count<AA_MAX_TARGETS ? count++ : AA_MAX_TARGETS-1;
        if (i==AA_MAX_TARGETS-1 && count==AA_MAX_TARGETS && d>=distances[i]) continue;
        for (;i>0 && distances[i-1]>d;i--) { targets[i]=targets[i-1];distances[i]=distances[i-1]; }
        targets[i]=e;distances[i]=d;
    }
    if (!count) return false;
    uint32_t const mounts=(uint32_t)MAX(1,MIN(8,cfg->data[4].number));
    uint32_t const model=G_RegisterModel("Emberfield/Models/tracer.mdx");
    float const c=cosf(gun->s.angle),s=sinf(gun->s.angle),length=MAX(30.0f,gun->collision);
    FOR_LOOP(i,mounts) {
        edict_t *target=targets[i%count];
        float const speed=MAX(0,target->data.UnitBalance ? target->data.UnitBalance->speed : 0);
        float const chance=cfg->data[3].number*(1-.35f*MIN(1.0f,speed/500))*(1-.3f*distances[i%count]/MAX(1,range));
        /* Mounts spread along both beams of the hull. */
        float const along=((float)(i%3)-1)*length*.7f,across=(i&1 ? 1.0f : -1.0f)*length*.25f;
        vec3_t start={gun->s.origin.x+c*along-s*across,gun->s.origin.y+s*along+c*across,gun->s.origin.z+22};
        if (mount) start=*mount;
        /* Even barrels stand for the dual-purpose 5"/38, 12.7 cm or 90 mm guns: an unseen
         * time-fused round that bursts black at the target; odd barrels are the 40/25 mm
         * tracer streams (s_air_effects.c). The hit roll is unchanged. */
        uint32_t const fuzed=(i&1) ? 0 : S_FlakFuzedShellModel();
        S_FireTracer(gun,&start,target,fuzed ? fuzed : model,(float)(rand()%100)<chance ? (int)cfg->data[1].number : 0);
    }
    int sound=G_UISoundIndex("FLAAFire");
    if (sound) G_PlaySound(NULL,gun,CHAN_BODY,sound,1,1,0);
    return true;
}

void naval_aa_think(edict_t *director) {
    edict_t *ship=S_SpellChannelOwner(director);
    abilityAliasRef_t ref=ship ? S_ResolveAbilityAlias(ship,BZ_SHIP_AA) : (abilityAliasRef_t){0};
    if (!ship || !ref.alias || M_IsDead(ship)) { G_FreeEdict(director);return; }
    if ((ship->s.renderfx&RF_HIDDEN) || G_UnitHasFlag(ship,UNIT_FLAG_PAUSED) ||
        unit_hasstatusstate(ship,WC3_STATUS_STATE_STUNNED) || G_Time()<director->freetime) return;
    abilityLevel_t const *cfg=G_AbilityLevel(ref.alias,ref.level);
    if (!S_AntiAirVolley(ship,cfg,NULL)) return;
    director->freetime=G_Time()+(uint32_t)(MAX(.2f,cfg->data[2].number)*1000);
}

BZ_ABILITY_PROC(CAbilityShipAntiAir) {
    (void)call;
    if (msg!=A_UPDATE || !ent || M_IsDead(ent) || !S_ResolveAbilityAlias(ent,BZ_SHIP_AA).alias) return false;
    FILTER_EDICTS(d,d->inuse && d->think==naval_aa_think && S_SpellChannelOwner(d)==ent) return true;
    edict_t *director=S_SpellIdentityThinker(ent,BZ_SHIP_AA,NULL);
    if (!director) return false;
    director->think=naval_aa_think;
    director->freetime=G_Time();
    return true;
}

/* A shot that misses (ballistic dispersion) lands beside its target: a water splash
 * at sea, a dirt burst with a lingering crater on land. Presentation only. */
void S_NearMissEffect(edict_t const *attacker, edict_t const *target) {
    if (!target || (target->aiflags & AI_FLYING)) return;
    float const angle = (float)(rand() % 6283) / 1000.0f;
    float const distance = MAX(8.0f, target->collision) + 30.0f + (float)(rand() % 90);
    edict_t impact = {0};
    impact.s = target->s;
    impact.s.origin.x += cosf(angle) * distance;
    impact.s.origin.y += sinf(angle) * distance;
    impact.s.origin2 = (vec2_t){impact.s.origin.x, impact.s.origin.y};
    uint8_t flags = 0;
    bool const water = CM_GetTerrainPathingFlagsAt(&impact.s.origin2, &flags) &&
                       (flags & CM_PATHING_UNWALKABLE) && !(flags & CM_PATHING_UNSWIMMABLE);
    if (water) impact.s.origin.z = 0;
    impact.s.model = G_RegisterModel(water ? "Emberfield/Models/splash.mdx" : "Emberfield/Models/crater.mdx");
    (void)attacker;
    G_SpawnProjectileImpact(&impact);
}

#define BZ_SHIP_DAMAGE MAKEFOURCC('F','s','m','k')
/* Damage presentation: the hull model carries smoke, fire, list and sinking for
 * every condition; this only publishes the condition (see S_ShipConditionUpdate). */
BZ_ABILITY_PROC(CAbilityShipDamage) {
    (void)call;
    if (msg!=A_UPDATE || !ent || M_IsDead(ent) || (ent->s.renderfx&RF_HIDDEN) || ent->health.max_value<=0) return false;
    S_ShipConditionUpdate(ent);
    return false;
}
