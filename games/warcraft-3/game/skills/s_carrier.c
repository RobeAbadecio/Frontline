#include "s_skills.h"

#define BZ_FLIGHT_CAP MAKEFOURCC('F','c','a','p') // original capability row; configures carrier lifecycle
#define BZ_FLIGHT_FIGHTER MAKEFOURCC('F','f','i','g') // original command; unitID identifies fighter
#define BZ_FLIGHT_BOMBER MAKEFOURCC('F','b','o','m') // original command; unitID identifies bomber
#define BZ_FLIGHT_TORPEDO MAKEFOURCC('F','t','r','p')
#define BZ_FLIGHT_RECALL MAKEFOURCC('F','r','e','t') // original command; cancels active sorties
#define BZ_FLIGHT_PATROL MAKEFOURCC('F','p','a','t') // original command; one-time fighter area patrol
#define BZ_FLIGHT_STRIKE MAKEFOURCC('F','s','t','r') // original command; coordinated fleet air strike
#define BZ_FLIGHT_REPLENISH MAKEFOURCC('F','r','e','p') // levels 1-3: fighter/dive/torpedo airframe, A=complement, B=payload
#define BZ_FLIGHT_STATUS MAKEFOURCC('F','s','t','s') // original command; reports the air group
#define BZ_FLIGHT_GROUP MAKEFOURCC('F','g','r','p')  // opens the Air Group page (loadout + strike package)
#define BZ_FLIGHT_BACK MAKEFOURCC('F','b','a','k')   // returns to the main carrier card
#define BZ_LOAD_F MAKEFOURCC('F','l','d','f')        // +1 fighter in the loadout (Shift: -1)
#define BZ_LOAD_D MAKEFOURCC('F','l','d','d')        // +1 dive bomber
#define BZ_LOAD_T MAKEFOURCC('F','l','d','t')        // +1 torpedo bomber
#define BZ_STRIKE_F MAKEFOURCC('F','s','i','f')      // toggle fighters in the strike package
#define BZ_STRIKE_D MAKEFOURCC('F','s','i','d')
#define BZ_STRIKE_T MAKEFOURCC('F','s','i','t')

/* The flight thinker owns these states and uses existing save-safe edict fields:
 * owner/goalentity + channel generations = carrier/aircraft; damage = stage;
 * freetime = transition deadline ms; wait = fuel seconds; resources = observed
 * attack cooldown; variation = flight role; channel->origin = mission target point (s.origin = rally);
 * combatentity + channel serial = strike mission identity. */
typedef enum { FLIGHT_BUILD, FLIGHT_READY, FLIGHT_TAKEOFF, FLIGHT_MISSION, FLIGHT_RETURN, FLIGHT_SERVICE } flightStage_t;
/* ROLE_DECK aircraft were bought by Replenish and wait on deck for an order. */
typedef enum { ROLE_PATROL, ROLE_ATTACK, ROLE_CAP, ROLE_STRIKE, ROLE_DECK } flightRole_t;
/* A strike mission edict: damage = stage, freetime = stage deadline, resources = creation ms,
 * variation = next deck launch ms, origin2 = target point, origin = rally point,
 * goalentity + channel target generation = optional explicit target. */
typedef enum { STRIKE_PREPARE, STRIKE_LAUNCH, STRIKE_ASSEMBLE, STRIKE_ATTACK, STRIKE_RECOVER } strikeStage_t;
enum { AIR_FIGHTER = 1, AIR_DIVE, AIR_TORPEDO };
/* The carrier's own plan lives in its otherwise unused `resources` word (saved with the edict):
 * bits 0-23 target counts of fighters/dive/torpedo bombers, bit 24 set once the player chose,
 * bit 25 Air Group page open, bits 26-28 which types join a strike. Unset = 2/1/1, bombers only. */
#define LOAD_INIT (1u<<24)
#define LOAD_PAGE (1u<<25)
#define LOAD_STRIKE_SHIFT 26
#define LOAD_DEFAULT_MASK 6u
#define CARRIER_CAPACITY_DEFAULT 12
#define BZ_FLIGHT_COVER MAKEFOURCC('F','c','o','v')
#define BZ_SHIP_PROTECTION MAKEFOURCC('F','p','r','o')
#define STRIKE_RALLY_RADIUS 450.0f
#define STRIKE_ESCORT_RADIUS 900.0f
#define FLIGHT_DAMAGED_RETURN 0.3f
/* Squadrons: the whole ready complement of one type launches, attacks once and returns.
 * Losses are permanent. A returning airframe below FLIGHT_WRITE_OFF of its health is a
 * wreck and is written off; anything better is repaired for Fcap DataE seconds per 100%
 * of damage (plus the DataC rearm time). */
#define BZ_SQUADRON_F MAKEFOURCC('F','s','q','f')
#define BZ_SQUADRON_D MAKEFOURCC('F','s','q','d')
#define BZ_SQUADRON_T MAKEFOURCC('F','s','q','t')
#define FLIGHT_WRITE_OFF 0.25f
#define GROUP_ISSUED (1u<<29) /* carrier->resources: the authored air group has been embarked */
#define AUTO_LAUNCH_OFF (1u<<30) /* carrier->resources: the player switched automatic launches off */
#define BZ_AUTO_LAUNCH MAKEFOURCC('F','a','u','t')
#define AUTO_SPOT_RANGE 1400.0f  /* an airborne aircraft spots enemies this close */
#define FLIGHT_RELEASE_MS 1500
/* Striking range: squadron orders (catalog Rng) and automatic or Attack launches reach this
 * far; an Attack order on anything further sails the carrier into range first. */
#define CARRIER_STRIKE_RANGE 8000.0f
#define CARRIER_UNDER_FIRE_MS 5000u  /* a carrier hit this recently cannot launch */
cstring_t const carrier_cover_orders[] = { "togglecap", NULL };
cstring_t const carrier_protection_orders[] = { "shipprotection", NULL };
cstring_t const carrier_replenish_orders[] = { "replenishair", NULL };
cstring_t const carrier_group_orders[] = { "airgroup", NULL };
cstring_t const carrier_back_orders[] = { "airgroupdone", NULL };
cstring_t const carrier_load_f_orders[] = { "loadoutfighter", NULL };
cstring_t const carrier_load_d_orders[] = { "loadoutdive", NULL };
cstring_t const carrier_load_t_orders[] = { "loadouttorpedo", NULL };
cstring_t const carrier_strike_f_orders[] = { "strikefighters", NULL };
cstring_t const carrier_strike_d_orders[] = { "strikedive", NULL };
cstring_t const carrier_strike_t_orders[] = { "striketorpedo", NULL };
cstring_t const carrier_status_orders[] = { "airstatus", NULL };
cstring_t const carrier_squadron_f_orders[] = { "fightersquadron", NULL };
cstring_t const carrier_auto_orders[] = { "autolaunch", NULL };
cstring_t const carrier_squadron_d_orders[] = { "divesquadron", NULL };
cstring_t const carrier_squadron_t_orders[] = { "torpedosquadron", NULL };
static bool carrier_launch(edict_t *, uint32_t);
static abilityLevel_t const *carrier_config(edict_t *carrier);
static uint32_t carrier_capacity(edict_t *carrier);
static void loadout_read(edict_t const *carrier, uint32_t target[3], uint32_t *mask) {
    uint32_t const v=carrier->resources;
    FOR_LOOP(i,3) target[i]=(v&LOAD_INIT) ? (v>>(8*i))&255u : (i==0 ? 2u : 1u);
    if (mask) *mask=(v&LOAD_INIT) ? (v>>LOAD_STRIKE_SHIFT)&7u : LOAD_DEFAULT_MASK;
}
static void loadout_write(edict_t *carrier, uint32_t const target[3], uint32_t mask) {
    carrier->resources=(carrier->resources&LOAD_PAGE)|LOAD_INIT|target[0]|(target[1]<<8)|(target[2]<<16)|(mask<<LOAD_STRIKE_SHIFT);
}
bool S_CarrierLoadoutPageOpen(edict_t const *carrier) {
    return carrier && G_UnitAbilityLevel((edict_t *)carrier,BZ_FLIGHT_CAP) && (carrier->resources&LOAD_PAGE);
}
void S_CarrierLoadoutPage(edict_t *carrier, bool open) {
    if (!carrier) return;
    carrier->resources=open ? carrier->resources|LOAD_PAGE : carrier->resources&~LOAD_PAGE;
    G_InvalidateCommands(G_GetPlayerClientByNumber(carrier->s.player));
    G_InvalidateUnitInfoPanel(carrier);
}
/* +1: grow the type; at capacity it takes the slot from the largest other type (replace).
 * -1: shrink the type. Aircraft already built stay until lost or scrapped by Replenish. */
bool S_CarrierAdjustLoadout(edict_t *carrier, uint32_t role, int delta) {
    abilityLevel_t const *cfg=carrier_config(carrier);
    uint32_t target[3],mask,total=0;
    if (!cfg || role<AIR_FIGHTER || role>AIR_TORPEDO) return false;
    uint32_t const capacity=MIN(255u,carrier_capacity(carrier));
    loadout_read(carrier,target,&mask);
    FOR_LOOP(i,3) total+=target[i];
    uint32_t const i=role-1;
    if (delta<0) { if (!target[i]) return false;target[i]--; }
    else {
        if (total>=capacity) {
            uint32_t donor=3,best=0;
            FOR_LOOP(k,3) if (k!=i && target[k]>best) { best=target[k];donor=k; }
            if (donor==3) return false;
            target[donor]--;
        }
        target[i]++;
    }
    loadout_write(carrier,target,mask);
    G_InvalidateUnitInfoPanel(carrier);
    return true;
}
void S_CarrierToggleStrikeType(edict_t *carrier, uint32_t role) {
    uint32_t target[3],mask;
    loadout_read(carrier,target,&mask);
    mask^=1u<<(role-1);
    loadout_write(carrier,target,mask);
    G_InvalidateUnitInfoPanel(carrier);
}
/* Aircraft types are faction aliases of Replenish: level 1 fighter, 2 dive bomber, 3 torpedo bomber. */
static uint32_t carrier_aircraft_type(edict_t *carrier, uint32_t role) {
    abilityAliasRef_t ref=S_ResolveAbilityAlias(carrier,BZ_FLIGHT_REPLENISH);
    return ref.alias ? G_AbilityLevel(ref.alias,role)->unitID : 0;
}
static abilityLevel_t const *carrier_role_config(edict_t *carrier, uint32_t role) {
    abilityAliasRef_t ref=S_ResolveAbilityAlias(carrier,BZ_FLIGHT_REPLENISH);
    return ref.alias ? G_AbilityLevel(ref.alias,role) : NULL;
}
/* An aircraft's role on this carrier: its own faction types, or the Airfield's generic
 * fighter / dive bomber / torpedo bomber when one lands to reinforce the air group. */
static uint32_t carrier_plane_role(edict_t *carrier, edict_t const *plane) {
    static cstring_t const generic[3][3]={{"ffgt","ufig","jfig"},{"fbmb","ubom","jbom"},{"ftor","utor","jtor"}};
    if (!plane) return 0;
    FOR_LOOP(role,3) {
        if (plane->class_id==carrier_aircraft_type(carrier,role+1)) return role+1;
        FOR_LOOP(i,3) if (plane->class_id==FS_SLKKey(generic[role][i])) return role+1;
    }
    return 0;
}
static bool carrier_is_fighter(edict_t *carrier, edict_t *plane) {
    return carrier_plane_role(carrier,plane)==AIR_FIGHTER;
}
static bool carrier_cap_enabled(edict_t *carrier) { return G_UnitAbilityLevel(carrier,BZ_FLIGHT_CAP)==1; }
cstring_t const carrier_fighter_orders[] = { "launchfighter", NULL };
cstring_t const carrier_torpedo_orders[] = { "launchtorpedo", NULL };
cstring_t const carrier_bomber_orders[] = { "launchbomber", NULL };
cstring_t const carrier_recall_orders[] = { "recallaircraft", NULL };
cstring_t const carrier_patrol_orders[] = { "airpatrol", NULL };
cstring_t const carrier_strike_orders[] = { "airstrike", NULL };

/* A landed or released member no longer belongs to any strike. */
static edict_t *flight_strike(edict_t const *flight) {
    edict_t *mission=flight ? flight->combatentity : NULL;
    if (!flight || flight->variation!=ROLE_STRIKE || !mission || !mission->inuse ||
        mission->think!=strike_mission_think || !flight->channel || flight->channel->serial!=mission->spawn_time) return NULL;
    return mission;
}

#define FOR_CARRIER_FLIGHTS(carrier, f) \
    FILTER_EDICTS(f, f->inuse && f->think == carrier_flight_think && S_SpellChannelOwner(f) == (carrier))

/* A removed/reused aircraft never reserves a live slot. */
uint32_t S_CarrierAircraftCount(edict_t *carrier) {
    uint32_t count = 0;
    FOR_CARRIER_FLIGHTS(carrier, f) {
        edict_t *plane = S_SpellChannelTarget(f);
        if (plane && !M_IsDead(plane)) count++;
    }
    return count;
}

/* The flight thinker that owns this airframe, if it belongs to a carrier air group. */
edict_t *S_CarrierFlightForPlane(edict_t const *plane) {
    if (!plane) return NULL;
    FILTER_EDICTS(f, f->inuse && f->think == carrier_flight_think && S_SpellChannelTarget(f) == plane) return f;
    return NULL;
}

/* Return Home (Q) on a carrier aircraft: an airborne flight breaks off and recovers. */
bool S_CarrierRecallFlight(edict_t *plane) {
    edict_t *flight = S_CarrierFlightForPlane(plane);
    if (!flight) return false;
    if (flight->damage == FLIGHT_TAKEOFF || flight->damage == FLIGHT_MISSION) { flight->damage = FLIGHT_RETURN; flight->freetime = 0; }
    return true;
}

static cstring_t strike_stage_name(edict_t const *mission) {
    static cstring_t const names[]={"preparing","launching","assembling","attacking","recovering"};
    return mission && mission->damage<=STRIKE_RECOVER ? names[mission->damage] : "";
}

/* Hangar size: the hull's aircraft hold (Fhld 24 fleet, Fh18 mid-size, Fh12 light),
 * else the Fcap default. */
static uint32_t carrier_capacity(edict_t *carrier) {
    abilityLevel_t const *cfg=carrier_config(carrier);
    uint32_t const hold=S_CargoCapacity(carrier);
    return hold ? hold : cfg ? (uint32_t)MAX(0,cfg->data[0].number) : 0;
}

/* The air group the carrier embarks once: a third of the hangar per type, so a fleet
 * carrier flies 8/8/8 and a light carrier 4/4/4. Replenish DataA is the fallback. */
static uint32_t carrier_complement(edict_t *carrier, uint32_t role) {
    abilityLevel_t const *cfg=carrier_role_config(carrier,role);
    if (S_CargoCapacity(carrier)) return S_CargoCapacity(carrier)/3;
    return cfg ? (uint32_t)MAX(0,cfg->data[0].number) : 0;
}

/* Hangar by type (ready / repairing), losses, airborne aircraft and the active mission,
 * authored by the game for the info panel and the Air Status command. */
bool S_CarrierStatusLabel(edict_t *carrier, string_t text, uint32_t size) {
    if (!carrier || !G_UnitAbilityLevel(carrier, BZ_FLIGHT_CAP)) return S_AircraftStatusLabel(carrier, text, size); /* fuel, home, damage */
    static cstring_t const names[3]={"Fighters","Dive","Torpedo"};
    uint32_t ready[3]={0},repair[3]={0},aloft=0,total=0,complement=0;
    uint32_t soonest=UINT32_MAX;
    edict_t *mission=NULL;
    FOR_CARRIER_FLIGHTS(carrier,f) {
        edict_t *plane=S_SpellChannelTarget(f);
        if (!plane || M_IsDead(plane)) continue;
        total++;
        FOR_LOOP(role,3) if (carrier_plane_role(carrier,plane)==role+1) {
            if (f->damage==FLIGHT_READY) ready[role]++;
            if (f->damage==FLIGHT_SERVICE || f->damage==FLIGHT_BUILD) {
                repair[role]++;
                if (f->freetime>G_Time()) soonest=MIN(soonest,f->freetime-G_Time());
            }
        }
        if (f->damage==FLIGHT_TAKEOFF || f->damage==FLIGHT_MISSION || f->damage==FLIGHT_RETURN) aloft++;
        if (!mission) mission=flight_strike(f);
    }
    FOR_LOOP(role,3) complement+=carrier_complement(carrier,role+1);
    /* Repair counts appear only where present, keeping the line short. */
    int used=snprintf(text,size,"Hangar:");
    FOR_LOOP(role,3) if (used>0 && (uint32_t)used<size) {
        used+=repair[role] ? snprintf(text+used,size-used," %s %u ready (+%u repairing)%s",names[role],ready[role],repair[role],role<2?",":"")
                           : snprintf(text+used,size-used," %s %u ready%s",names[role],ready[role],role<2?",":"");
    }
    if (used>0 && (uint32_t)used<size && aloft) used+=snprintf(text+used,size-used," | aloft %u",aloft);
    if (used>0 && (uint32_t)used<size) used+=snprintf(text+used,size-used," | CAP %s",carrier_cap_enabled(carrier)?"ON":"OFF");
    if (used>0 && (uint32_t)used<size) used+=snprintf(text+used,size-used," | auto %s",(carrier->resources&AUTO_LAUNCH_OFF)?"OFF":"ON");
    if (used>0 && (uint32_t)used<size && soonest!=UINT32_MAX) used+=snprintf(text+used,size-used," | next ready %us",(soonest+999)/1000);
    if (used>0 && (uint32_t)used<size && carrier->resources&GROUP_ISSUED && complement>total)
        used+=snprintf(text+used,size-used," | lost %u",complement-total);
    if (used>0 && (uint32_t)used<size && mission)
        snprintf(text+used,size-used," | STRIKE %s",strike_stage_name(mission));
    return true;
}

static abilityLevel_t const *carrier_config(edict_t *carrier) {
    return carrier && G_UnitAbilityLevel(carrier, BZ_FLIGHT_CAP) ? G_AbilityLevel(BZ_FLIGHT_CAP, 1) : NULL;
}

static void carrier_refresh(edict_t *carrier) {
    abilityLevel_t const *cfg = carrier_config(carrier);
    if (!cfg) return;
    carrier->mana.max_value = (float)carrier_capacity(carrier);
    carrier->mana.value = (float)S_CarrierAircraftCount(carrier);
    G_InvalidateUnitInfoPanel(carrier);
    G_InvalidateCommands(G_GetPlayerClientByNumber(carrier->s.player));
}

/* Fighters carry gun bursts; bombers carry their whole authored payload for one run. */
static void carrier_arm(edict_t *carrier, edict_t *plane) {
    abilityLevel_t const *cfg=carrier_config(carrier);
    float ammo=cfg ? cfg->data[5].number : 1;
    FOR_LOOP(role,3) if (carrier_plane_role(carrier,plane)==role+1) {
        abilityLevel_t const *loadout=carrier_role_config(carrier,role+1);
        if (loadout && loadout->data[1].number>0) ammo=loadout->data[1].number;
    }
    plane->mana.max_value=plane->mana.value=ammo;
}

static void carrier_notice(edict_t *carrier, cstring_t text) {
    edict_t *player=carrier ? G_GetPlayerEntityByNumber(carrier->s.player) : NULL;
    if (player && player->client) UI_ShowText(player,&(vec2_t){0.15f,0.25f},text,6.0f);
}

/* Reuse a ready airframe of this type before charging for a new one. */
static edict_t *carrier_ready(edict_t *carrier, uint32_t type) {
    FOR_CARRIER_FLIGHTS(carrier, f) {
        edict_t *plane = S_SpellChannelTarget(f);
        if (plane && !M_IsDead(plane) && plane->class_id == type && f->damage == FLIGHT_READY && !flight_strike(f)) return f;
    }
    return NULL;
}

/* Cargo UI may inspect deck airframes but cannot bypass construction/service.
 * Only the carrier's launch transition authorizes a managed aircraft to exit. */
bool S_CarrierCanUnload(edict_t *carrier, edict_t *plane) {
    FOR_CARRIER_FLIGHTS(carrier, f) {
        if (S_SpellChannelTarget(f) == plane) return f->damage == FLIGHT_TAKEOFF;
    }
    return true;
}

/* A burning carrier, or one being hit, cannot spot, arm and launch a deck load; it
 * still recovers its aircraft. Fires burn out (s_ballistics.c). */
static cstring_t carrier_deck_closed(edict_t const *carrier) {
    if (S_BallisticBurning(carrier)) return "Flight deck on fire: launches suspended until the fire is out.";
    if (S_BallisticUnderFire(carrier,CARRIER_UNDER_FIRE_MS)) return "Carrier under attack: launches suspended.";
    return NULL;
}

static void carrier_start_launch(edict_t *flight, edict_t *carrier, edict_t *plane) {
    abilityLevel_t const *cfg = carrier_config(carrier);
    if (!cfg || !carrier->cargo || carrier_deck_closed(carrier)) return;
    FOR_LOOP(i, carrier->cargo->count) {
        if (carrier->cargo->units[i] != plane) continue;
        flight->damage = FLIGHT_TAKEOFF;
        if (!S_CargoUnloadAt(carrier, i)) { flight->damage = FLIGHT_READY; return; }
        plane->unitinfo.FlyHeight = 24.0f;
        plane->s.origin2 = carrier->s.origin2;
        gi.LinkEntity(plane);
        flight->damage = FLIGHT_TAKEOFF;
        flight->freetime = G_Time() + (uint32_t)(cfg->data[3].number * 1000);
        bool other_cover = false;
        if (flight->variation==ROLE_CAP) {
            FILTER_EDICTS(other, other!=flight && other->inuse && other->think==carrier_flight_think &&
                          S_SpellChannelOwner(other)==carrier && other->variation==ROLE_CAP &&
                          (other->damage==FLIGHT_MISSION || other->damage==FLIGHT_TAKEOFF)) other_cover=true;
        }
        /* Offset the initial rotation by half a sortie, avoiding synchronized
         * fuel exhaustion. Subsequent serviced sorties receive a full tank.
         * A strike's launch and assembly time is covered by a long-range tank. */
        flight->wait = cfg->data[1].number * (flight->variation==ROLE_CAP && !other_cover ? .5f :
                                             flight->variation==ROLE_STRIKE ? 2 : 1);
        flight->resources = plane->unit_state->attack_cooldown_end_time;
        order_move(plane, Waypoint_add(&(vec2_t){carrier->s.origin.x, carrier->s.origin.y - 300}));
        return;
    }
}

/* Patrol and CAP orbit a centre and intercept visible enemy aircraft near it. */
static void flight_guard(edict_t *flight, edict_t *carrier, edict_t *plane) {
    abilityLevel_t const *cover=G_AbilityLevel(BZ_FLIGHT_COVER,1);
    vec2_t const center=flight->variation==ROLE_CAP ? carrier->s.origin2 : flight->s.origin2;
    edict_t *threat=NULL;
    float nearest=cover->range;
    FILTER_EDICTS(e, e->inuse && !M_IsDead(e) && (e->aiflags & AI_FLYING) &&
                   S_SpellIsEnemy(plane,e) && G_FowPlayerCanSeeEntity(plane->s.player,e)) {
        float distance = Vector2_distance(&center,&e->s.origin2);
        if (distance < nearest) {nearest=distance;threat=e;}
    }
    if (threat && carrier_is_fighter(carrier,plane)) G_IssueUnitTargetOrder(plane,"attack",threat,false,plane->s.player);
    else if (flight->variation==ROLE_CAP) {
        flight->s.origin2 = (vec2_t){carrier->s.origin.x+((flight->s.number&1)?1:-1)*cover->area,carrier->s.origin.y+250};
        unit_issueorder(plane,"patrol",&flight->s.origin2);
    } else {
        float const radius=MAX(150.0f,S_SpellData(BZ_FLIGHT_PATROL,1,2));
        float const angle=G_Time()*.0006f+flight->s.number;
        unit_issueorder(plane,"move",&(vec2_t){center.x+cosf(angle)*radius,center.y+sinf(angle)*radius});
    }
    flight->freetime = G_Time()+1000;
}

/* Seconds of fuel at which a flight turns for home: the time to reach the carrier with a margin. */
#define FLIGHT_FUEL_RESERVE 15.0f
static float flight_bingo(edict_t *plane, edict_t *carrier) {
    float const speed = plane->data.UnitBalance ? MAX(1.0f, plane->data.UnitBalance->speed) : 300.0f;
    return Vector2_distance(&plane->s.origin2, &carrier->s.origin2) / speed * 1.3f;
}

/* Fuel and ammunition bound a sortie. Returning aircraft follow a moving
 * carrier, descend to deck height, then enter the existing hidden cargo hold. */
void carrier_flight_think(edict_t *flight) {
    edict_t *carrier = S_SpellChannelOwner(flight);
    edict_t *plane = S_SpellChannelTarget(flight);
    abilityLevel_t const *cfg = carrier_config(carrier);
    if (!plane || M_IsDead(plane)) {
        G_FreeEdict(flight);
        if (carrier && !M_IsDead(carrier)) carrier_refresh(carrier);
        return;
    }
    if (!cfg || M_IsDead(carrier) || carrier->s.player != plane->s.player) {
        S_CargoReleaseUnit(plane);
        T_Damage(plane, carrier ? carrier : plane, (int)plane->health.max_value + 1);
        G_FreeEdict(flight);
        return;
    }
    if (G_UnitHasFlag(carrier, UNIT_FLAG_PAUSED) || unit_hasstatusstate(carrier, WC3_STATUS_STATE_STUNNED) ||
        ((G_UnitHasFlag(plane, UNIT_FLAG_PAUSED) || unit_hasstatusstate(plane, WC3_STATUS_STATE_STUNNED)) && !S_CargoTransportForUnit(plane))) {
        flight->freetime += FRAMETIME;
        return;
    }
    edict_t *mission=flight_strike(flight);
    if (flight->variation==ROLE_STRIKE && !mission) flight->variation=ROLE_PATROL;
    switch ((flightStage_t)flight->damage) {
    case FLIGHT_BUILD:
        if (G_Time() < flight->freetime) break;
        flight->damage = FLIGHT_READY;
        if (mission) { carrier_refresh(carrier); break; } /* the strike launches it with the wave */
        if (flight->variation==ROLE_DECK) flight->variation=ROLE_PATROL;
        else if (flight->variation != ROLE_CAP || carrier_cap_enabled(carrier)) carrier_start_launch(flight, carrier, plane);
        carrier_refresh(carrier);
        break;
    case FLIGHT_SERVICE:
        if (G_Time() < flight->freetime) break;
        /* Each serviced sortie spends logistics; a dry deck waits safely. */
        gameClient_t *supply = G_GetPlayerClientByNumber(carrier->s.player);
        uint32_t service_cost=(uint32_t)MAX(0,G_AbilityLevel(BZ_FLIGHT_COVER,1)->data[1].number);
        if (!supply || supply->ps.stats[PLAYERSTATE_RESOURCE_LUMBER] < service_cost) break;
        supply->ps.stats[PLAYERSTATE_RESOURCE_LUMBER] -= service_cost;
        plane->health.value = plane->health.max_value; /* repair time was set by its condition on landing */
        carrier_arm(carrier, plane);
        flight->damage = FLIGHT_READY;
        carrier_refresh(carrier);
        break;
    case FLIGHT_READY:
        if (mission) break; /* the strike controller owns this deck slot */
        if (carrier_cap_enabled(carrier) && carrier_is_fighter(carrier,plane)) {
            flight->variation = ROLE_CAP;
            flight->s.origin2 = (vec2_t){carrier->s.origin.x+G_AbilityLevel(BZ_FLIGHT_COVER,1)->area,carrier->s.origin.y};
            carrier_start_launch(flight,carrier,plane);
            break;
        }
        if (S_CargoTransportForUnit(plane) != carrier) {
            flight->damage = FLIGHT_RETURN;
            flight->freetime = 0;
        }
        break;
    case FLIGHT_TAKEOFF:
        plane->unitinfo.FlyHeight = MIN(plane->data.UnitData->moveHeight, plane->unitinfo.FlyHeight + 20.0f);
        if (G_Time() < flight->freetime) break;
        plane->unitinfo.FlyHeight = plane->data.UnitData->moveHeight;
        flight->damage = FLIGHT_MISSION;
        flight->freetime = 0;
        if (mission) unit_issueorder(plane, "move", &(vec2_t){mission->s.origin.x, mission->s.origin.y});
        else if (flight->variation == ROLE_ATTACK) unit_issueorder(plane, "attack", &flight->s.origin2);
        else if (flight->variation == ROLE_CAP) unit_issueorder(plane, "patrol", &flight->s.origin2);
        break;
    case FLIGHT_MISSION:
        /* CAP follows the carrier; an area patrol orbits its point. Attack orders
         * are only assigned to visible airborne threats, never to surface targets. */
        if ((flight->variation == ROLE_CAP || flight->variation == ROLE_PATROL) && G_Time() >= flight->freetime)
            flight_guard(flight, carrier, plane);
        flight->wait -= FRAMETIME / 1000.0f * S_AircraftFuelBurn(plane); /* a fuel leak burns faster */
        if (plane->unit_state->attack_cooldown_end_time != flight->resources) {
            flight->resources = plane->unit_state->attack_cooldown_end_time;
            /* An evasive maneuver delays the guns; it does not spend ammunition. */
            if (plane->unit_state->attack_cooldown_end_time != plane->evade_until)
                plane->mana.value = MAX(0, plane->mana.value - 1);
            /* Hold the attack run long enough for the release to leave the aircraft. */
            if (plane->mana.value <= 0) flight->freetime = G_Time() + FLIGHT_RELEASE_MS;
        }
        if (plane->mana.value <= 0 && G_Time() < flight->freetime) break;
        /* Bingo fuel (enough for the way home plus a margin), an empty magazine or heavy
         * damage end the sortie. */
        if (flight->wait > flight_bingo(plane, carrier) && plane->mana.value > 0 &&
            plane->health.value > plane->health.max_value * FLIGHT_DAMAGED_RETURN) break;
        flight->damage = FLIGHT_RETURN;
        flight->freetime = 0;
        /* fall through */
    case FLIGHT_RETURN: {
        float const distance = Vector2_distance(&plane->s.origin2, &carrier->s.origin2);
        /* The way home burns the reserve; a flight that runs it dry ditches. */
        flight->wait -= FRAMETIME / 1000.0f * S_AircraftFuelBurn(plane);
        if (flight->wait <= -FLIGHT_FUEL_RESERVE && distance > cfg->range + carrier->collision) {
            char text[128];
            snprintf(text, sizeof(text), "%s ditched: out of fuel.", G_UnitName(plane->class_id));
            carrier_notice(carrier, text);
            T_Damage(plane, plane, (int)plane->health.max_value + 1);
            break;
        }
        if (distance <= cfg->range + carrier->collision) {
            order_stop(plane);
            plane->unitinfo.FlyHeight = MAX(24, plane->unitinfo.FlyHeight - 25);
            float const condition = plane->health.max_value > 0 ? plane->health.value / plane->health.max_value : 0;
            if (plane->unitinfo.FlyHeight <= 24 && condition < FLIGHT_WRITE_OFF) {
                /* A wreck lands but cannot be repaired: it is written off and never replaced. */
                char text[128];
                snprintf(text, sizeof(text), "%s written off: too badly damaged to repair.", G_UnitName(plane->class_id));
                carrier_notice(carrier, text);
                G_FreeEdict(plane);
                G_FreeEdict(flight);
                carrier_refresh(carrier);
                return;
            }
            if (plane->unitinfo.FlyHeight <= 24 && S_CargoTryLoad(carrier, plane)) {
                flight->damage = FLIGHT_SERVICE;
                flight->freetime = G_Time() + (uint32_t)((cfg->data[2].number + (1 - condition) * cfg->data[4].number) * 1000);
                if (flight->variation == ROLE_STRIKE || flight->variation == ROLE_ATTACK) flight->variation = ROLE_PATROL;
                carrier_refresh(carrier);
            }
        } else if (G_Time() >= flight->freetime) {
            order_move(plane, Waypoint_add(&carrier->s.origin2));
            flight->freetime = G_Time() + 1000;
        }
        break;
    }
    }
}

/* A new airframe needs a free hangar slot and its paid cost. */
static bool carrier_can_buy(edict_t *carrier, uint32_t type) {
    abilityLevel_t const *cfg = carrier_config(carrier);
    gameClient_t *client = carrier ? G_GetPlayerClientByNumber(carrier->s.player) : NULL;
    UnitBalance_t const *balance = G_UnitBalance(type);
    if (!cfg || !client || !type || !balance || !balance->id) return false;
    return S_CarrierAircraftCount(carrier) < carrier_capacity(carrier) &&
        client->ps.stats[PLAYERSTATE_RESOURCE_GOLD] >= (uint32_t)MAX(0,balance->goldCost) &&
        client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER] >= (uint32_t)MAX(0,balance->lumberCost) &&
        G_PlayerHasFoodFor(client, MAX(0,balance->foodUsed));
}

static bool carrier_can_launch(edict_t *carrier, uint32_t type) {
    return carrier_ready(carrier, type) != NULL;
}

/* UnitBalance owns cost, supply and build time; losses require another purchase.
 * The airframe is built in the hangar and then follows its role. */
static edict_t *carrier_add(edict_t *carrier, uint32_t type, flightRole_t role, bool paid) {
    edict_t *flight, *plane;
    abilityLevel_t const *cfg = carrier_config(carrier);
    gameClient_t *client = G_GetPlayerClientByNumber(carrier->s.player);
    if (!cfg || S_CarrierAircraftCount(carrier) >= carrier_capacity(carrier)) return NULL;
    if (paid && (!carrier_can_buy(carrier, type) || !G_ChargeBuilding(client, type))) return NULL;
    plane = unit_create(carrier->s.player, type, &carrier->s.origin2, 0);
    if (!plane || !(flight = S_SpellIdentityThinker(carrier, BZ_FLIGHT_CAP, plane))) {
        if (plane) G_FreeEdict(plane);
        if (paid) G_RefundBuilding(client, type);
        return NULL;
    }
    if (!S_CargoTryLoad(carrier, plane)) {
        G_FreeEdict(plane); G_FreeEdict(flight);
        if (paid) G_RefundBuilding(client, type);
        return NULL;
    }
    carrier_arm(carrier, plane);
    flight->variation = role;
    flight->think = carrier_flight_think;
    flight->damage = FLIGHT_BUILD;
    flight->freetime = G_Time() + (paid ? (uint32_t)(MAX(1,plane->data.UnitBalance->buildTime)*1000) : 0);
    flight->s.origin2 = (vec2_t){carrier->s.origin.x, carrier->s.origin.y + 700};
    carrier_refresh(carrier);
    return flight;
}

/* Launch / replace flight: reuse a ready airframe, otherwise buy one. */
static bool carrier_launch(edict_t *carrier, uint32_t type) {
    edict_t *flight = carrier_ready(carrier, type);
    bool const cap = type==carrier_aircraft_type(carrier,AIR_FIGHTER) && carrier_cap_enabled(carrier);
    if (flight) {
        flight->variation = cap ? ROLE_CAP : ROLE_PATROL;
        carrier_start_launch(flight, carrier, S_SpellChannelTarget(flight));
        return true;
    }
    return false; /* lost aircraft are never replaced at the carrier */
}

static uint32_t carrier_have(edict_t *carrier, uint32_t role) {
    uint32_t have=0;
    FOR_CARRIER_FLIGHTS(carrier,f) {
        edict_t *plane=S_SpellChannelTarget(f);
        if (plane && !M_IsDead(plane) && carrier_plane_role(carrier,plane)==role) have++;
    }
    return have;
}
static edict_t *strike_target(edict_t *mission) {
    edict_t *target=mission->goalentity;
    if (!target || !target->inuse || !mission->channel || target->spawn_time!=mission->channel->target_spawn_time || M_IsDead(target)) return NULL;
    return target;
}

static void strike_refresh_carriers(edict_t *mission) {
    FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission) {
        edict_t *carrier=S_SpellChannelOwner(f);
        if (carrier) G_InvalidateUnitInfoPanel(carrier);
    }
}

static void strike_set_stage(edict_t *mission, strikeStage_t stage, uint32_t duration) {
    mission->damage=stage;
    mission->freetime=G_Time()+duration;
    strike_refresh_carriers(mission);
}

/* Release every member back to its carrier and retire the controller. */
static void strike_end(edict_t *mission, cstring_t reason) {
    edict_t *player=G_GetPlayerEntityByNumber(mission->s.player);
    FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission) {
        if (f->damage==FLIGHT_TAKEOFF || f->damage==FLIGHT_MISSION) { f->damage=FLIGHT_RETURN; f->freetime=0; }
        f->variation=ROLE_PATROL;
        if (S_SpellChannelOwner(f)) carrier_refresh(S_SpellChannelOwner(f));
    }
    if (reason && player && player->client) UI_ShowText(player,&(vec2_t){0.15f,0.25f},reason,6.0f);
    G_FreeEdict(mission);
}

static void strike_ping(edict_t *mission) {
    gameClient_t *client=G_GetPlayerClientByNumber(mission->s.player);
    if (!client) return;
    vec2_t const rally={mission->s.origin.x,mission->s.origin.y};
    G_SendMinimapPing(client,&rally,4,(color32_t){255,210,90,255},0);
    G_SendMinimapPing(client,&mission->channel->origin,6,(color32_t){255,80,60,255},0);
}

/* One controller per fleet strike: launch everything, wait until it is airborne,
 * assemble at a rally point so fast and slow types arrive together, attack as one
 * wave, then recover. Every wait has a deadline, so lost aircraft never stall it. */
void strike_mission_think(edict_t *mission) {
    abilityLevel_t const *cfg=G_AbilityLevel(BZ_FLIGHT_STRIKE,1);
    edict_t *target=strike_target(mission);
    vec2_t const rally={mission->s.origin.x,mission->s.origin.y};
    uint32_t members=0,bombers=0,pending=0,aloft=0,gathered=0,attacking=0,returning=0,fighters_out=0;
    vec2_t wave={0,0},fighter_wave={0,0};
    FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission) {
        edict_t *plane=S_SpellChannelTarget(f),*carrier=S_SpellChannelOwner(f);
        if (!plane || M_IsDead(plane)) continue;
        bool const fighter=carrier_is_fighter(carrier,plane);
        members++;
        if (!fighter) bombers++;
        if (f->damage==FLIGHT_READY || f->damage==FLIGHT_BUILD || f->damage==FLIGHT_SERVICE) pending++;
        if (f->damage==FLIGHT_TAKEOFF || f->damage==FLIGHT_MISSION) aloft++;
        if (f->damage==FLIGHT_RETURN) returning++;
        if (f->damage==FLIGHT_MISSION && Vector2_distance(&plane->s.origin2,&rally)<=STRIKE_RALLY_RADIUS) gathered++;
        if (f->damage==FLIGHT_MISSION) {
            if (!fighter) { attacking++;wave.x+=plane->s.origin.x;wave.y+=plane->s.origin.y; }
            else { fighters_out++;fighter_wave.x+=plane->s.origin.x;fighter_wave.y+=plane->s.origin.y; }
        }
    }
    /* A package with no bombers is an air sweep: the fighters themselves are the attack wave. */
    bool const sweep=!bombers;
    if (sweep) { attacking=fighters_out;wave=fighter_wave; }
    if (attacking) { wave.x/=attacking;wave.y/=attacking; }
    if (mission->damage!=STRIKE_PREPARE && !members) { strike_end(mission,NULL); return; }
    switch ((strikeStage_t)mission->damage) {
    case STRIKE_PREPARE:
        if (G_Time()<=mission->resources) break; /* other carriers of the same order join this frame */
        if (!members) {
            strike_end(mission,"Air strike cancelled: no aircraft of the selected types are aboard.");
            return;
        }
        {
            /* Rally between the launching carriers and the target. */
            vec2_t fleet={0,0};uint32_t ships=0;
            FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission) {
                edict_t *carrier=S_SpellChannelOwner(f);
                if (!carrier) continue;
                fleet.x+=carrier->s.origin.x;fleet.y+=carrier->s.origin.y;ships++;
            }
            fleet.x/=MAX(1,ships);fleet.y/=MAX(1,ships);
            float const distance=Vector2_distance(&fleet,&mission->channel->origin);
            float const lead=distance>1 ? MIN(MAX(distance*.35f,500.0f),MIN(1500.0f,distance*.8f))/distance : 0;
            mission->s.origin.x=fleet.x+(mission->channel->origin.x-fleet.x)*lead;
            mission->s.origin.y=fleet.y+(mission->channel->origin.y-fleet.y)*lead;
        }
        mission->variation=G_Time();
        strike_set_stage(mission,STRIKE_LAUNCH,(uint32_t)(cfg->data[2].number*1000));
        strike_ping(mission);
        break;
    case STRIKE_LAUNCH:
        /* Each deck launches one aircraft per interval; every carrier works in parallel. */
        if (G_Time()>=mission->variation) {
            mission->variation=G_Time()+(uint32_t)(MAX(.1f,cfg->data[0].number)*1000);
            edict_t *launched[MAX_PLAYERS*8];uint32_t decks=0;
            FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission && f->damage==FLIGHT_READY) {
                edict_t *carrier=S_SpellChannelOwner(f);
                bool busy=false;
                FOR_LOOP(i,decks) if (launched[i]==carrier) busy=true;
                if (busy || decks>=sizeof(launched)/sizeof(launched[0])) continue;
                launched[decks++]=carrier;
                carrier_start_launch(f,carrier,S_SpellChannelTarget(f));
            }
        }
        if (pending && G_Time()<mission->freetime) break;
        /* Deadline: anything still on deck stays home rather than holding the wave. */
        FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission &&
                         (f->damage==FLIGHT_READY || f->damage==FLIGHT_BUILD || f->damage==FLIGHT_SERVICE)) f->variation=ROLE_PATROL;
        FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission && f->damage==FLIGHT_TAKEOFF) return;
        strike_set_stage(mission,STRIKE_ASSEMBLE,(uint32_t)(cfg->data[1].number*1000));
        break;
    case STRIKE_ASSEMBLE:
        if (gathered<aloft && G_Time()<mission->freetime) break;
        strike_set_stage(mission,STRIKE_ATTACK,(uint32_t)(cfg->data[3].number*1000));
        mission->wait=0;
        FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission && f->damage==FLIGHT_MISSION) {
            edict_t *plane=S_SpellChannelTarget(f),*carrier=S_SpellChannelOwner(f);
            if (carrier_is_fighter(carrier,plane)) {
                if (sweep) unit_issueorder(plane,"attack",&mission->channel->origin);
                continue;
            }
            if (target) G_IssueUnitTargetOrder(plane,"attack",target,false,plane->s.player);
            else unit_issueorder(plane,"attack",&mission->channel->origin);
        }
        break;
    case STRIKE_ATTACK:
        if (!attacking || G_Time()>=mission->freetime) {
            strike_set_stage(mission,STRIKE_RECOVER,0);
            FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission &&
                             (f->damage==FLIGHT_MISSION || f->damage==FLIGHT_TAKEOFF)) { f->damage=FLIGHT_RETURN;f->freetime=0; }
            break;
        }
        /* An explicit target that sinks retargets the remaining payloads onto the area. */
        if (!target && mission->goalentity && mission->wait==0) {
            mission->wait=1;
            FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission && f->damage==FLIGHT_MISSION) {
                edict_t *plane=S_SpellChannelTarget(f);
                if (!carrier_is_fighter(S_SpellChannelOwner(f),plane)) unit_issueorder(plane,"attack",&mission->channel->origin);
            }
        }
        break;
    case STRIKE_RECOVER:
        if (!aloft && !returning) { strike_end(mission,NULL); return; }
        break;
    }
    /* Escorts stay with the bombers and intercept aircraft threatening them. */
    if (!sweep && (mission->damage==STRIKE_ASSEMBLE || mission->damage==STRIKE_ATTACK) && G_Time()%500<FRAMETIME) {
        vec2_t const guard=mission->damage==STRIKE_ATTACK && attacking ? wave : rally;
        float const escort=STRIKE_ESCORT_RADIUS;
        FILTER_EDICTS(f, f->inuse && f->think==carrier_flight_think && flight_strike(f)==mission && f->damage==FLIGHT_MISSION) {
            edict_t *plane=S_SpellChannelTarget(f),*carrier=S_SpellChannelOwner(f);
            if (!carrier_is_fighter(carrier,plane)) {
                if (mission->damage==STRIKE_ASSEMBLE) unit_issueorder(plane,"move",&rally);
                continue;
            }
            edict_t *threat=NULL;float nearest=escort;
            FILTER_EDICTS(e, e->inuse && !M_IsDead(e) && (e->aiflags & AI_FLYING) && S_SpellIsEnemy(plane,e) &&
                             G_FowPlayerCanSeeEntity(plane->s.player,e)) {
                float d=Vector2_distance(&guard,&e->s.origin2);
                if (d<nearest) { nearest=d;threat=e; }
            }
            if (threat) G_IssueUnitTargetOrder(plane,"attack",threat,false,plane->s.player);
            else unit_issueorder(plane,"move",&(vec2_t){guard.x+((f->s.number&1)?140.0f:-140.0f),guard.y+120.0f});
        }
    }
}

/* All carriers ordered in the same frame against the same target share one mission. */
static edict_t *strike_join(edict_t *carrier, spellTarget_t const *target) {
    edict_t *unit=target->type==SPELL_TARGET_UNIT ? target->entity : NULL;
    vec2_t const point=unit ? unit->s.origin2 : target->point;
    FILTER_EDICTS(m, m->inuse && m->think==strike_mission_think && m->s.player==carrier->s.player &&
                     m->damage==STRIKE_PREPARE && m->resources==G_Time() && m->goalentity==unit &&
                     Vector2_distance(&m->channel->origin,&point)<1) return m;
    edict_t *mission=G_Spawn();
    if (!mission) return NULL;
    mission->channel=G_AllocChannel();
    assert(mission->channel);
    mission->think=strike_mission_think;
    mission->class_id=BZ_FLIGHT_STRIKE;
    mission->s.player=carrier->s.player;
    mission->goalentity=unit;
    mission->channel->target_spawn_time=unit ? unit->spawn_time : 0;
    mission->channel->origin=point;
    mission->resources=G_Time();
    mission->damage=STRIKE_PREPARE;
    return mission;
}

/* Enlist exactly the aircraft of the types in this carrier's strike package: everything of those
 * types aboard (ready, still building or in service; the wave waits up to the launch deadline for
 * them). Nothing else launches and nothing is added. */
static uint32_t strike_enlist(edict_t *carrier, edict_t *mission, uint32_t mask, bool squadron) {
    uint32_t enlisted=0;
    FOR_CARRIER_FLIGHTS(carrier,f) {
        edict_t *plane=S_SpellChannelTarget(f);
        if (!plane || M_IsDead(plane) || flight_strike(f)) continue;
        bool const fighter=carrier_is_fighter(carrier,plane);
        uint32_t const role=carrier_plane_role(carrier,plane);
        /* A squadron takes only what is ready on deck; aircraft under repair stay home. */
        bool const aboard=f->damage==FLIGHT_READY || (!squadron && (f->damage==FLIGHT_BUILD || f->damage==FLIGHT_SERVICE));
        /* Fighters already aloft on CAP are drafted when the package includes fighters. */
        bool const on_cap=fighter && f->variation==ROLE_CAP && (f->damage==FLIGHT_TAKEOFF || f->damage==FLIGHT_MISSION);
        if (!(aboard || on_cap) || !(mask&(1u<<(role-1)))) continue;
        f->variation=ROLE_STRIKE;
        f->combatentity=mission;
        f->channel->serial=mission->spawn_time;
        enlisted++;
    }
    return enlisted;
}

/* A squadron is one aircraft type; the legacy Air Strike uses the carrier's stored package. */
static uint32_t carrier_strike_mask(edict_t *carrier, uint32_t code) {
    uint32_t plan[3],mask;
    if (code == BZ_SQUADRON_D) return 1u<<(AIR_DIVE-1);
    if (code == BZ_SQUADRON_T) return 1u<<(AIR_TORPEDO-1);
    loadout_read(carrier,plan,&mask);
    return mask;
}
static uint32_t carrier_ready_count(edict_t *carrier, uint32_t mask) {
    uint32_t ready=0;
    FOR_CARRIER_FLIGHTS(carrier,f) {
        edict_t *plane=S_SpellChannelTarget(f);
        if (!plane || M_IsDead(plane) || f->damage!=FLIGHT_READY || flight_strike(f)) continue;
        FOR_LOOP(r,3) if ((mask&(1u<<r)) && carrier_plane_role(carrier,plane)==r+1) ready++;
    }
    return ready;
}

/* Why a strike package cannot hit its target, or NULL when it can. Aircraft are never swapped
 * silently: the player is told what to change. */
static cstring_t strike_ineligible(edict_t *carrier, spellTarget_t const *target, uint32_t mask) {
    uint32_t have[3]={0};
    FOR_LOOP(r,3) if (mask&(1u<<r)) have[r]=carrier_have(carrier,r+1);
    if (!have[0] && !have[1] && !have[2]) return "No aircraft of that type left aboard. Lost aircraft cannot be replaced.";
    edict_t *unit=target && target->type==SPELL_TARGET_UNIT ? target->entity : NULL;
    if (!unit) return NULL; /* an area: bombers hit what they find, fighters sweep for aircraft */
    bool const air=(unit->aiflags&AI_FLYING)!=0,ship=M_UnitStaticPathingFlags(unit)==CM_PATHING_UNSWIMMABLE && unit->data.UnitBalance && unit->data.UnitBalance->speed>0;
    if (air) return have[0] ? NULL : "Bombers cannot attack aircraft. Send the Fighter squadron.";
    if (!have[1] && !have[2]) return "Fighters cannot attack surface targets. Send dive or torpedo bombers.";
    if (!have[1] && !ship) return "Torpedo bombers can only attack ships. Send the Dive Bomber squadron.";
    return NULL;
}

/* Area patrol: retask airborne patrols and launch ready fighters to the point. */
static bool carrier_patrol(edict_t *carrier, vec2_t const *point, bool squadron) {
    uint32_t sent=0;
    uint32_t const want=squadron ? UINT32_MAX : (uint32_t)MAX(1,S_SpellData(BZ_FLIGHT_PATROL,1,1));
    FOR_CARRIER_FLIGHTS(carrier,f) {
        edict_t *plane=S_SpellChannelTarget(f);
        /* A squadron order also draws the fighters flying CAP; they resume it once serviced. */
        if (!plane || M_IsDead(plane) || flight_strike(f) || (f->variation==ROLE_CAP && !squadron)) continue;
        if (f->damage!=FLIGHT_TAKEOFF && f->damage!=FLIGHT_MISSION) continue;
        f->variation=ROLE_PATROL;f->s.origin2=*point;f->freetime=0;
        if (carrier_is_fighter(carrier,plane)) sent++;
    }
    FOR_CARRIER_FLIGHTS(carrier,f) {
        edict_t *plane=S_SpellChannelTarget(f);
        if (sent>=want) break;
        if (!plane || M_IsDead(plane) || f->damage!=FLIGHT_READY || flight_strike(f) || !carrier_is_fighter(carrier,plane)) continue;
        f->variation=ROLE_PATROL;f->s.origin2=*point;
        carrier_start_launch(f,carrier,plane);
        sent++;
    }
    if (!sent) carrier_notice(carrier,"No fighters ready on deck: they are aloft, under repair or lost.");
    return sent>0;
}

/* Name=Return / Patrol / Air Strike / CAP / Replenish / Status. Point missions are
 * per carrier; strikes from several selected carriers merge into one mission. */
BZ_ABILITY_PROC(CAbilityCarrierCommand) {
    uint32_t const code = call && call->item ? call->item->code : 0;
    uint32_t const type = code ? G_AbilityLevel(code, 1)->unitID : 0;
    uint32_t const behavior = code ? G_AbilityCode(code) : 0;
    bool const launch = behavior == BZ_FLIGHT_FIGHTER || behavior == BZ_FLIGHT_BOMBER || behavior == BZ_FLIGHT_TORPEDO;
    if (msg == A_VALIDATE) {
        if (code == BZ_SHIP_PROTECTION) {
            gameClient_t *client=G_GetPlayerClientByNumber(ent->s.player);
            return client && G_UnitAbilityLevel(ent,code)==1 && client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]>=(uint32_t)S_SpellData(code,1,2) && client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]>=(uint32_t)S_SpellData(code,1,3);
        }
        /* A strike the carrier's package cannot perform is refused before any order is accepted. */
        if ((code == BZ_FLIGHT_STRIKE || code == BZ_SQUADRON_D || code == BZ_SQUADRON_T) && call && call->target && carrier_config(ent)) {
            cstring_t const reason=strike_ineligible(ent,call->target,carrier_strike_mask(ent,code));
            if (reason) { carrier_notice(ent,reason);return false; }
        }
        if ((launch || code == BZ_FLIGHT_STRIKE || code == BZ_FLIGHT_PATROL || code == BZ_SQUADRON_F ||
             code == BZ_SQUADRON_D || code == BZ_SQUADRON_T) && carrier_config(ent) && carrier_deck_closed(ent)) {
            carrier_notice(ent,carrier_deck_closed(ent));
            return false;
        }
        if (behavior == BZ_FLIGHT_REPLENISH && carrier_config(ent)) {
            carrier_notice(ent,"Carriers cannot replace lost aircraft.");
            return false;
        }
        return carrier_config(ent) && (!launch || carrier_can_launch(ent, type));
    }
    if (msg != A_EXECUTE) return CAbilitySimpleSpell(ent, msg, call);
    if (launch) return carrier_launch(ent, type);
    if (code == BZ_SHIP_PROTECTION) {
        gameClient_t *client=G_GetPlayerClientByNumber(ent->s.player);
        if (!client || G_UnitAbilityLevel(ent,code)!=1 || client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]<(uint32_t)S_SpellData(code,1,2) || client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]<(uint32_t)S_SpellData(code,1,3)) return false;
        client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]-=(uint32_t)S_SpellData(code,1,2);
        client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]-=(uint32_t)S_SpellData(code,1,3);
        G_UnitSetAbilityLevel(ent,code,2);
        carrier_refresh(ent);
        return true;
    }
    if (code == BZ_FLIGHT_STATUS) {
        char text[256];
        if (S_CarrierStatusLabel(ent,text,sizeof(text))) carrier_notice(ent,text);
        return true;
    }
    /* Targeted spells have one caster; a carrier ordered from its owner's selection
     * brings every other selected carrier into the same patrol or strike. */
    gameClient_t *owner=G_GetPlayerClientByNumber(ent->s.player);
    bool const from_selection=owner && G_IsEntitySelected(owner,ent);
    if (code == BZ_AUTO_LAUNCH) {
        ent->resources ^= AUTO_LAUNCH_OFF;
        carrier_notice(ent,(ent->resources&AUTO_LAUNCH_OFF) ? "Automatic launches OFF." : "Automatic launches ON: aircraft attack enemies the carrier or its planes spot.");
        carrier_refresh(ent);
        return true;
    }
    if (code == BZ_FLIGHT_GROUP || code == BZ_FLIGHT_BACK) { S_CarrierLoadoutPage(ent,code==BZ_FLIGHT_GROUP);return true; }
    if (code == BZ_LOAD_F || code == BZ_LOAD_D || code == BZ_LOAD_T)
        return S_CarrierAdjustLoadout(ent,code==BZ_LOAD_F ? AIR_FIGHTER : code==BZ_LOAD_D ? AIR_DIVE : AIR_TORPEDO,1);
    if (code == BZ_STRIKE_F || code == BZ_STRIKE_D || code == BZ_STRIKE_T) {
        S_CarrierToggleStrikeType(ent,code==BZ_STRIKE_F ? AIR_FIGHTER : code==BZ_STRIKE_D ? AIR_DIVE : AIR_TORPEDO);
        return true;
    }
    if (code == BZ_FLIGHT_PATROL || code == BZ_SQUADRON_F) {
        bool const squadron=code == BZ_SQUADRON_F;
        vec2_t const point=call->target ? (call->target->type==SPELL_TARGET_UNIT && call->target->entity ? call->target->entity->s.origin2 : call->target->point) : ent->s.origin2;
        bool sent=call->target && carrier_patrol(ent,&point,squadron);
        if (from_selection) FOR_CONTROLLABLE_SELECTED_UNITS(owner,other)
            if (other!=ent && carrier_config(other) && G_ActorHasSkill(other,squadron ? "Fsqf" : "Fpat")) sent=carrier_patrol(other,&point,squadron) || sent;
        return sent;
    }
    if (code == BZ_FLIGHT_STRIKE || code == BZ_SQUADRON_D || code == BZ_SQUADRON_T) {
        bool const squadron=code != BZ_FLIGHT_STRIKE;
        cstring_t const skill=code == BZ_SQUADRON_D ? "Fsqd" : code == BZ_SQUADRON_T ? "Fsqt" : "Fstr";
        edict_t *group[MAX_PLAYERS*4];
        uint32_t members=0;
        if (!call->target || call->target->type == SPELL_TARGET_NONE) return false;
        /* Every ordered carrier is checked against its own strike package; the reason is
         * reported for each one that cannot take part, and the others still launch. */
        edict_t *ordered[MAX_PLAYERS*4];uint32_t ordered_count=0;
        ordered[ordered_count++]=ent;
        if (from_selection) FOR_CONTROLLABLE_SELECTED_UNITS(owner,other)
            if (other!=ent && ordered_count<sizeof(ordered)/sizeof(ordered[0]) && carrier_config(other) && G_ActorHasSkill(other,skill)) ordered[ordered_count++]=other;
        cstring_t last_reason=NULL;
        FOR_LOOP(i,ordered_count) {
            cstring_t reason=strike_ineligible(ordered[i],call->target,carrier_strike_mask(ordered[i],code));
            if (!reason && squadron && !carrier_ready_count(ordered[i],carrier_strike_mask(ordered[i],code)))
                reason="That squadron has no aircraft ready on deck: they are aloft or under repair.";
            if (reason) { if (reason!=last_reason) carrier_notice(ordered[i],reason);last_reason=reason; }
            else group[members++]=ordered[i];
        }
        if (!members) return false;
        edict_t *mission=strike_join(group[0],call->target);
        if (!mission) return false;
        FOR_LOOP(i,members) { strike_enlist(group[i],mission,carrier_strike_mask(group[i],code),squadron);carrier_refresh(group[i]); }
        int sound=G_UISoundIndex("RallyPointPlace");
        if (sound) G_PlaySound(NULL,ent,CHAN_BODY,sound,1,1,0);
        return true;
    }
    if (code == BZ_FLIGHT_COVER || code == BZ_FLIGHT_RECALL) {
        G_UnitSetAbilityLevel(ent,BZ_FLIGHT_CAP,code == BZ_FLIGHT_RECALL || carrier_cap_enabled(ent) ? 2 : 1);
        carrier_refresh(ent);
    }
    FOR_CARRIER_FLIGHTS(ent, f) {
        edict_t *plane = S_SpellChannelTarget(f);
        if (!plane || M_IsDead(plane)) continue;
        if (code == BZ_FLIGHT_RECALL || (code == BZ_FLIGHT_COVER && !carrier_cap_enabled(ent))) {
            /* Return cancels this carrier's part of any strike. */
            if (code == BZ_FLIGHT_RECALL && flight_strike(f)) f->variation = ROLE_PATROL;
            if (f->damage == FLIGHT_TAKEOFF || f->damage == FLIGHT_MISSION) { f->damage = FLIGHT_RETURN; f->freetime = 0; }
        } else if (code == BZ_FLIGHT_COVER && carrier_cap_enabled(ent)) {
            if (carrier_is_fighter(ent,plane) && !flight_strike(f)) {
                f->variation=ROLE_CAP;
                if (f->damage==FLIGHT_MISSION) f->freetime=0;
            }
        }
    }
    return true;
}

static bool carrier_target_is_ship(edict_t const *e) {
    return e && !(e->aiflags & AI_FLYING) && e->data.UnitBalance && e->data.UnitBalance->speed > 0 &&
           M_UnitStaticPathingFlags((edict_t *)e) == CM_PATHING_UNSWIMMABLE;
}

/* Aircraft by target: ships get dive and torpedo bombers, land targets dive bombers
 * with fighter escort, aircraft fighters. */
static uint32_t carrier_mask_for(edict_t const *target) {
    if (target->aiflags & AI_FLYING) return 1u<<(AIR_FIGHTER-1);
    if (carrier_target_is_ship(target)) return (1u<<(AIR_DIVE-1))|(1u<<(AIR_TORPEDO-1));
    return (1u<<(AIR_DIVE-1))|(1u<<(AIR_FIGHTER-1));
}

/* Battleships, then cruisers, then destroyers, then other ships (by authored hull
 * strength; carriers rank with the escorts), then aircraft, then land targets. */
static uint32_t carrier_target_priority(edict_t const *e) {
    if (e->aiflags & AI_FLYING) return 2;
    if (!carrier_target_is_ship(e)) return 1;
    if (G_UnitAbilityLevel((edict_t *)e,BZ_FLIGHT_CAP)) return 4;
    float const hp=e->health.max_value;
    return hp>=3000 ? 7 : hp>=1800 ? 6 : hp>=1300 ? 5 : 3;
}

static bool carrier_engaged(edict_t *carrier, edict_t const *target) {
    FOR_CARRIER_FLIGHTS(carrier,f) {
        edict_t *mission=flight_strike(f);
        if (mission && (!target || mission->goalentity==target)) return true;
    }
    return false;
}

/* Launch the ready aircraft that suit this target; fighters alone patrol over an air threat. */
static bool carrier_launch_at(edict_t *carrier, edict_t *target) {
    uint32_t mask=carrier_mask_for(target);
    if (carrier_deck_closed(carrier) || Vector2_distance(&carrier->s.origin2,&target->s.origin2)>CARRIER_STRIKE_RANGE) return false;
    if (mask==(1u<<(AIR_FIGHTER-1))) {
        FOR_CARRIER_FLIGHTS(carrier,f)
            if (f->variation==ROLE_PATROL && (f->damage==FLIGHT_TAKEOFF || f->damage==FLIGHT_MISSION)) return false;
        return carrier_ready_count(carrier,mask) && carrier_patrol(carrier,&target->s.origin2,true);
    }
    spellTarget_t const aim={ .type=SPELL_TARGET_UNIT, .entity=target };
    if (carrier_engaged(carrier,target) || strike_ineligible(carrier,&aim,mask) || !carrier_ready_count(carrier,mask & ~(1u<<(AIR_FIGHTER-1))))
        return false;
    edict_t *mission=strike_join(carrier,&aim);
    if (!mission) return false;
    strike_enlist(carrier,mission,mask,true);
    carrier_refresh(carrier);
    return true;
}

/* An enemy the carrier sees, or one near any of its airborne aircraft, by priority then distance. */
static edict_t *carrier_spotted_enemy(edict_t *carrier) {
    float const sight=carrier->data.UnitBalance ? MAX(1400.0f,carrier->data.UnitBalance->sightRadius) : 2000.0f;
    edict_t *best=NULL;uint32_t best_rank=0;float best_distance=0;
    FILTER_EDICTS(e,e->inuse && (e->svflags&SVF_MONSTER) && !M_IsDead(e) && !(e->s.renderfx&RF_HIDDEN) &&
                    S_SpellIsEnemy(carrier,e) &&
                    (!G_FowPlayerTracked(carrier->s.player) || G_FowPlayerCanSeeEntity(carrier->s.player,e))) {
        float distance=Vector2_distance(&carrier->s.origin2,&e->s.origin2);
        if (distance>CARRIER_STRIKE_RANGE) continue;
        bool spotted=distance<=sight;
        if (!spotted) FOR_CARRIER_FLIGHTS(carrier,f) {
            edict_t *plane=S_SpellChannelTarget(f);
            if (plane && !(plane->s.renderfx&RF_HIDDEN) && Vector2_distance(&plane->s.origin2,&e->s.origin2)<=AUTO_SPOT_RANGE) { spotted=true;break; }
        }
        if (!spotted) continue;
        uint32_t const rank=carrier_target_priority(e);
        if (!best || rank>best_rank || (rank==best_rank && distance<best_distance)) { best=e;best_rank=rank;best_distance=distance; }
    }
    return best;
}

/* Airfield aircraft landed in the hold (Load / right-click onto the carrier) join the air
 * group while there is room: they are rearmed and repaired by condition like returning
 * flights. A carrier never builds aircraft; this is the only way to make good its losses. */
static void carrier_adopt_landed(edict_t *carrier) {
    abilityLevel_t const *cfg=carrier_config(carrier);
    if (!cfg || !carrier->cargo) return;
    FOR_LOOP(i,carrier->cargo->count) {
        edict_t *plane=S_CargoUnitAt(carrier,i);
        bool managed=false;
        if (!plane || M_IsDead(plane) || !carrier_plane_role(carrier,plane)) continue;
        FOR_CARRIER_FLIGHTS(carrier,f) if (S_SpellChannelTarget(f)==plane) { managed=true;break; }
        if (managed || S_CarrierAircraftCount(carrier)>=carrier_capacity(carrier)) continue;
        edict_t *flight=S_SpellIdentityThinker(carrier,BZ_FLIGHT_CAP,plane);
        if (!flight) return;
        float const condition=plane->health.max_value>0 ? plane->health.value/plane->health.max_value : 1;
        flight->think=carrier_flight_think;
        flight->variation=ROLE_PATROL;
        flight->damage=FLIGHT_SERVICE;
        flight->freetime=G_Time()+(uint32_t)((cfg->data[2].number+(1-condition)*cfg->data[4].number)*1000);
        flight->s.origin2=(vec2_t){carrier->s.origin.x,carrier->s.origin.y+700};
        carrier_notice(carrier,"Airfield aircraft joined the carrier's air group.");
        carrier_refresh(carrier);
    }
}

/* Carriers avoid gun range of surface warships: an idle carrier with an armed enemy ship
 * inside CARRIER_STANDOFF sails directly away from it. A player Move or Patrol is obeyed. */
#define CARRIER_STANDOFF 2200.0f
#define CARRIER_WITHDRAW 1600.0f
static void carrier_keep_clear(edict_t *carrier) {
    if (G_UnitHasFlag(carrier,UNIT_FLAG_PAUSED) || (carrier->currentmove && carrier->currentmove->animation &&
        !strcmp(carrier->currentmove->animation,"walk"))) return;
    edict_t *threat=NULL;float nearest=CARRIER_STANDOFF;
    FILTER_EDICTS(e,e->inuse && !M_IsDead(e) && !(e->s.renderfx&RF_HIDDEN) && carrier_target_is_ship(e) &&
                    !G_UnitAbilityLevel(e,BZ_FLIGHT_CAP) && e->unit_state && e->unit_state->attack1.type!=ATK_NONE &&
                    S_SpellIsEnemy(carrier,e) &&
                    (!G_FowPlayerTracked(carrier->s.player) || G_FowPlayerCanSeeEntity(carrier->s.player,e))) {
        float const d=Vector2_distance(&carrier->s.origin2,&e->s.origin2);
        if (d<nearest) { nearest=d;threat=e; }
    }
    if (!threat) return;
    float const away=atan2f(carrier->s.origin.y-threat->s.origin.y,carrier->s.origin.x-threat->s.origin.x);
    vec2_t const to={carrier->s.origin.x+cosf(away)*CARRIER_WITHDRAW,carrier->s.origin.y+sinf(away)*CARRIER_WITHDRAW};
    unit_issueorder(carrier,"move",&to);
}

/* A finished carrier embarks its authored air group once, at no extra cost (it is part
 * of the carrier's price), with fighter cover off. Nothing is ever bought afterwards.
 * An Attack order (or the carrier's own target acquisition) sends the aircraft that
 * suit the target and keeps the hull out of the fight; with automatic launches on,
 * anything the carrier or its aircraft spot is attacked by priority. */
BZ_ABILITY_PROC(CAbilityCarrierCover) {
    (void)call;
    if (msg != A_UPDATE || !ent || !carrier_config(ent) || M_IsDead(ent) ||
        (ent->s.renderfx & RF_HIDDEN) || ent->construction) return false;
    edict_t *target=ent->goalentity;
    if (target && ent->currentmove && ent->currentmove->proc==CAbilityAttack && target->inuse && !M_IsDead(target) &&
        S_SpellIsEnemy(ent,target)) {
        /* A carrier never chases: Attack (ordered or acquired) launches the suitable aircraft
         * if the target is within striking range, and the hull stays where it is. */
        carrier_launch_at(ent,target);
        if (!(target->aiflags & AI_FLYING)) order_stop(ent);
    }
    if ((G_Time()+(uint32_t)ent->s.number*29)%1000 >= FRAMETIME) return false;
    if (!(ent->resources & GROUP_ISSUED)) {
        ent->resources |= GROUP_ISSUED;
        G_UnitSetAbilityLevel(ent,BZ_FLIGHT_CAP,2);
        for (uint32_t role=AIR_FIGHTER; role<=AIR_TORPEDO; role++)
            FOR_LOOP(i,carrier_complement(ent,role)) { (void)i; carrier_add(ent,carrier_aircraft_type(ent,role),ROLE_DECK,false); }
        carrier_refresh(ent);
        return true;
    }
    carrier_adopt_landed(ent);
    if (!(ent->resources & AUTO_LAUNCH_OFF) && !G_UnitHasFlag(ent,UNIT_FLAG_PAUSED)) {
        edict_t *spotted=carrier_spotted_enemy(ent);
        if (spotted) carrier_launch_at(ent,spotted);
    }
    carrier_keep_clear(ent);
    return true;
}

/* Airfield CAP (Facp level 2 = on): stored, refuelled fighters take off and every idle fighter
 * near the field circles it; ordinary target acquisition intercepts raiders. Fighters land
 * at bingo fuel, refuel and relaunch (s_air_combat.c) until CAP is switched off. */
#define BZ_AIRFIELD_CAP MAKEFOURCC('F','a','c','p')
#define AIRFIELD_CAP_RADIUS 1800.0f
cstring_t const airfield_cap_orders[] = { "airfieldcap", NULL };
static bool airfield_fighter(edict_t const *plane) {
    static cstring_t const codes[]={"ffgt","ufig","jfig"};
    FOR_LOOP(i,sizeof(codes)/sizeof(codes[0])) if (plane->class_id==FS_SLKKey(codes[i])) return true;
    return false;
}
static bool airfield_carrier_owned(edict_t const *plane) {
    FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && S_SpellChannelTarget(f)==plane) return true;
    return false;
}
BZ_ABILITY_PROC(CAbilityAirfieldCap) {
    switch (msg) {
    case A_VALIDATE: return ent && G_UnitAbilityLevel(ent,BZ_AIRFIELD_CAP)>0;
    case A_TOGGLE_ON: return ent && G_UnitAbilityLevel(ent,BZ_AIRFIELD_CAP)==2;
    case A_EXECUTE: {
        bool const on=G_UnitAbilityLevel(ent,BZ_AIRFIELD_CAP)!=2;
        G_UnitSetAbilityLevel(ent,BZ_AIRFIELD_CAP,on ? 2 : 1);
        carrier_notice(ent,on ? "Airfield CAP ON: fighters circle the airfield." : "Airfield CAP OFF.");
        G_InvalidateCommands(G_GetPlayerClientByNumber(ent->s.player));
        return true;
    }
    case A_UPDATE: {
        if (!ent || G_UnitAbilityLevel(ent,BZ_AIRFIELD_CAP)!=2 || M_IsDead(ent) || ent->construction ||
            (G_Time()+(uint32_t)ent->s.number*53)%2000>=FRAMETIME) return false;
        for (int32_t i=ent->cargo ? (int32_t)ent->cargo->count-1 : -1; i>=0; i--) {
            edict_t *plane=S_CargoUnitAt(ent,(uint32_t)i);
            /* Only a refuelled fighter takes off (fuel is its mana bar, s_air_combat.c). */
            if (plane && airfield_fighter(plane) && plane->mana.value>=plane->mana.max_value*.9f) S_CargoUnloadAt(ent,(uint32_t)i);
        }
        FILTER_EDICTS(plane,plane->inuse && plane->s.player==ent->s.player && !M_IsDead(plane) && airfield_fighter(plane) &&
                            !(plane->s.renderfx&RF_HIDDEN) && Vector2_distance(&plane->s.origin2,&ent->s.origin2)<AIRFIELD_CAP_RADIUS) {
            if (plane->currentmove && strcmp(plane->currentmove->animation,"stand")) continue; /* busy */
            if (airfield_carrier_owned(plane)) continue;
            float const angle=(float)(plane->s.number%6)*(M_PI/3);
            unit_issueorder(plane,"patrol",&(vec2_t){ent->s.origin.x+cosf(angle)*600,ent->s.origin.y+sinf(angle)*600});
        }
        return true;
    }
    default: return msg==A_EXECUTE ? false : CAbilitySimpleSpell(ent,msg,call);
    }
}
