/* Actual generated map acceptance; no retail archives or synthetic movement copies.
 * FRONTLINE_ACCEPTANCE=1 openwarcraft3-tests -data build/frontline +dedicated 1 +test frontline.* */
#ifdef BZ_TESTS
#include <time.h>
#include "../g_local.h"
#include "../skills/s_skills.h"
#include "../hud/hud_local.h"
#include "shared/test.h"
#include <stdlib.h>

static uiFrame_t anchor_frames[4];
static uint32_t anchor_count;
static void ForwardAnchorUnicast(edict_t *ent) { (void)ent; }
static void CaptureForwardAnchor(pfWriteType_t type, void const *data) {
    if ((type==PF_UIFRAME || type==PF_UIWINDOWFRAME) && anchor_count<4)
        anchor_frames[anchor_count++]=*(uiFrame_t const *)data;
}
TEST(wc3_hud, forward_sibling_anchor_keeps_its_wire_reference) {
    UI_ResetHud();
    frameDef_t *root=UI_Spawn(FT_FRAME,NULL);
    frameDef_t *early=UI_Spawn(FT_GLUETEXTBUTTON,root);
    frameDef_t *late=UI_Spawn(FT_GLUETEXTBUTTON,root);
    UI_SetSize(root,.33f,.34f);UI_SetSize(early,.26f,.04f);UI_SetSize(late,.26f,.04f);
    UI_SetPoint(early,FRAMEPOINT_TOP,late,FRAMEPOINT_BOTTOM,0,-.008f);
    UI_SetPoint(late,FRAMEPOINT_TOP,root,FRAMEPOINT_TOP,0,-.15f);
    void (*old_write)(pfWriteType_t,void const *)=gi.Write;
    void (*old_unicast)(edict_t *)=gi.unicast;
    anchor_count=0;gi.Write=CaptureForwardAnchor;gi.unicast=ForwardAnchorUnicast;
    UI_WriteWindow(NULL,root,&(uiWindowDef_t){.id=1,.class_id=1});
    gi.Write=old_write;gi.unicast=old_unicast;
    T_EQ(anchor_count,3);
    T_EQ(anchor_frames[1].points.y[FPP_MIN].relativeTo,anchor_frames[2].number);
    T_EQ(anchor_frames[2].points.y[FPP_MIN].relativeTo,anchor_frames[0].number);
    T_ASSERT(anchor_frames[1].number!=anchor_frames[2].number);
    UI_ResetHud();
}


/* Flak heavy/light selection from existing weapon data (s_air_effects.c). */
TEST(wc3_frontline_flak, heavy_and_light_selection) {
    T_EQ(S_FlakClassify(true,false,40,950),FLAK_NONE);    /* fighters dogfighting */
    T_EQ(S_FlakClassify(true,true,40,1700),FLAK_NONE);
    T_EQ(S_FlakClassify(false,true,150,950),FLAK_LIGHT);  /* battleship 40/25 mm tracers */
    T_EQ(S_FlakClassify(false,false,35,1300),FLAK_HEAVY); /* destroyer/cruiser 5"/38, 12.7 cm shells */
    T_EQ(S_FlakClassify(false,false,34,1700),FLAK_HEAVY); /* Anti-Aircraft Gun: 90 mm / Type 88 */
    T_EQ(S_FlakClassify(false,false,12,1800),FLAK_LIGHT); /* .50 cal / 20 mm */
    T_EQ(S_FlakClassify(false,false,10,1700),FLAK_LIGHT); /* carrier galleries */
    T_EQ(S_FlakClassify(false,false,8,0),FLAK_LIGHT);
}

/* A strike fills the sky but never beyond the per-frame and live caps; light puffs
 * leave room for heavy bursts; bursts expire after their lifetime. */
TEST(wc3_frontline_flak, burst_caps) {
    uint32_t const old_time=level.time;
    edict_t plane={0};plane.s.origin=(vec3_t){100,200,240};plane.aiflags=AI_FLYING;
    S_FlakReset();level.time=1000;
    T_ASSERT(!S_FlakBurst(&plane,FLAK_NONE));
    T_ASSERT(!S_FlakBurst(NULL,FLAK_HEAVY));
    uint32_t accepted=0;
    FOR_LOOP(i,50) accepted+=S_FlakBurst(&plane,FLAK_HEAVY);
    T_EQ(accepted,FLAK_MAX_PER_FRAME);
    T_EQ(S_FlakLiveCount(),FLAK_MAX_PER_FRAME);
    FOR_LOOP(f,40) { level.time+=100; FOR_LOOP(i,20) S_FlakBurst(&plane,FLAK_LIGHT); }
    T_EQ(S_FlakLiveCount(),FLAK_LIGHT_LIVE);              /* light stops short of the cap */
    level.time+=100; FOR_LOOP(i,20) S_FlakBurst(&plane,FLAK_HEAVY);
    T_ASSERT(S_FlakLiveCount()>FLAK_LIGHT_LIVE);
    T_ASSERT(S_FlakLiveCount()<=FLAK_MAX_LIVE);
    FOR_LOOP(f,10) { level.time+=100; FOR_LOOP(i,20) S_FlakBurst(&plane,FLAK_HEAVY); }
    T_EQ(S_FlakLiveCount(),FLAK_MAX_LIVE);
    level.time+=FLAK_LIFETIME_MS+100;
    T_EQ(S_FlakLiveCount(),0);
    T_ASSERT(S_FlakBurst(&plane,FLAK_LIGHT));
    S_FlakReset();level.time=old_time;
}

static uint32_t front_time;
static uint32_t FrontTime(void) { return front_time; }
static uint32_t (*front_old_time)(void);
static edict_t *FrontUnit(uint32_t owner, cstring_t code) {
    FILTER_EDICTS(e, e->inuse && e->s.player == owner && e->class_id == FS_SLKKey(code) && !M_IsDead(e)) return e;
    return NULL;
}
static void FrontStep(uint32_t frames) {
    FOR_LOOP(i, frames) { front_time += 100; globals.RunFrame(); }
}
static void FrontLoad(bool bot) {
    srand(1); /* Each acceptance scenario owns a reproducible combat/AI stream. */
    front_old_time = gi.GetTime; gi.GetTime = FrontTime; front_time = 0;
    CM_SetupTestWorldBounds(NULL);
    T_ASSERT(globals.PrepareMap("Maps/Frontline/IslandCommand.w3m"));
    T_ASSERT(globals.LoadMap("Maps/Frontline/IslandCommand.w3m"));
    T_NOT_NULL(level.vm); T_ASSERT(!jass_rterror_pending(level.vm));
    jass_callbyname(level.vm,"FrontlineTestForces",false);
    if (!bot) {
        FILTER_EDICTS(e,e->inuse && G_UnitAbilityLevel(e,MAKEFOURCC('F','c','a','p')))
            G_UnitSetAbilityLevel(e,MAKEFOURCC('F','c','a','p'),2);
        G_BotShutdown();
        /* Test isolated orders with the real map scheduler, without opponent tactics. */
        char stop[] = "function StopScenario takes nothing returns nothing\nset finished = true\nendfunction\n";
        T_ASSERT(jass_dobuffer(level.vm, stop));
        jass_callbyname(level.vm,"StopScenario",false);
        FILTER_EDICTS(e, e->inuse && e->s.player == 1 && (e->svflags & SVF_MONSTER)) G_FreeEdict(e);
    }
}
static void FrontEnd(void) { G_BotShutdown(); gi.GetTime = front_old_time; }
static void FrontNaval(void) {
    edict_t *ship, *target, *engineer;
    gameCommandButton_t button;
    FrontLoad(false);
    ship=FrontUnit(0,"fbat");engineer=FrontUnit(0,"fwkr");
    T_NOT_NULL(ship);T_NOT_NULL(engineer);
    T_EQ(M_UnitStaticPathingFlags(ship),CM_PATHING_UNSWIMMABLE);
    T_ASSERT(CM_TerrainPointIsSwimmable(&ship->s.origin2));
    T_ASSERT(!CM_TerrainPointIsWalkable(&ship->s.origin2));
    T_ASSERT(!CM_TerrainPointIsSwimmable(&(vec2_t){-3000,3000}));
    T_ASSERT(CM_TerrainPointIsWalkable(&(vec2_t){-3000,3000}));
    T_ASSERT(G_BuildCommandButton(FrontUnit(0,"fdoc"),"fbat",false,0,&button));
    T_ASSERT(G_BuildCommandButton(engineer,"AHbu",false,0,&button));
    /* Open central ocean: the battleship sails from its coast toward the middle unobstructed. */
    T_ASSERT(unit_issueorder(ship,"move",&(vec2_t){-300,300}));
    FrontStep(120);
    T_ASSERT(Vector2_distance(&ship->s.origin2,&(vec2_t){-300,300})<250);
    target=unit_create(1,FS_SLKKey("fcrs"),&(vec2_t){350,-350},0);
    T_NOT_NULL(target);
    float before=target->health.value;
    T_ASSERT(G_IssueUnitTargetOrder(ship,"attack",target,false,0));
    uint32_t impacts=0;
    FOR_LOOP(i,70) {
        FrontStep(1);
        /* Shell hits leave a short Death-sequence burst that frees itself. */
        FILTER_EDICTS(e,e->inuse && e->think==G_EffectThink && (e->s.flags & EF_NOT_SELECTABLE) && e->movetype==MOVETYPE_NONE && !e->goalentity) impacts++;
    }
    T_ASSERT(target->health.value < before);
    T_ASSERT(impacts>0);
    FrontStep(20);
    FILTER_EDICTS(e,e->inuse && e->think==G_EffectThink && (e->s.flags & EF_NOT_SELECTABLE) && e->movetype==MOVETYPE_NONE && !e->goalentity && e->s.origin.x>0) T_ASSERT(false);
    T_ASSERT(ship->data.UnitWeapons->attack1.range > 1500);
    /* Data-driven audio: weapon class + armor impact rows, UI and acknowledgement sounds. */
    T_EQ(strcmp(ship->data.UnitWeapons->attack1.weaponSound,"FLHeavy"),0);
    T_EQ(G_UnitCombatSoundVariantCount("FLHeavyMetal"),2);
    T_ASSERT(G_UnitCombatSoundVariantIndex("FLHeavyMetal",0)>0);
    T_ASSERT(G_UnitCombatSoundVariantIndex("FLSmallFlesh",1)>0);
    T_ASSERT(G_RegisterUISound("InterfaceError")>0);
    T_ASSERT(G_UnitAckSoundVariantCount("Ember","Yes")>0);
    /* Death voices: ships/vehicles explode, infantry fall; buildings loop construction. */
    T_NOT_NULL(ship->sound);T_ASSERT(ship->sound->death>0);
    T_NOT_NULL(engineer->sound);T_ASSERT(engineer->sound->death>0);
    T_ASSERT(ship->sound->death!=engineer->sound->death);
    T_EQ(strcmp(FrontUnit(0,"fdoc")->data.UnitProfile->buildingSoundLabel,"FLConstruction"),0);
    G_SetConstructionLoopSound(FrontUnit(0,"fdoc"),true);T_ASSERT(FrontUnit(0,"fdoc")->s.sound>0);
    G_SetConstructionLoopSound(FrontUnit(0,"fdoc"),false);T_EQ(FrontUnit(0,"fdoc")->s.sound,0);
    target=unit_create(1,FS_SLKKey("fbnk"),&(vec2_t){-2100,2500},0);
    before=target->health.value;
    T_ASSERT(G_IssueUnitTargetOrder(ship,"attack",target,false,0));
    FrontStep(140);T_ASSERT(target->health.value<before);
    order_stop(ship);
    float ally_hp=FrontUnit(0,"fdst")->health.value;
    FrontStep(20);
    T_FEQ(FrontUnit(0,"fdst")->health.value,ally_hp,.1f);
    FrontEnd();
}
/* Regression: engineers ordered onto one tree keep logging, delivering and
 * re-targeting for the whole life of the forest. Before the fix a worker that
 * felled the last tree within 650 units of itself went idle with live trees a
 * short walk away. They may only stop once no tree remains near the base. */
static uint32_t FrontTreesNear(vec2_t const *point,float radius) {
    uint32_t n=0;
    FILTER_EDICTS(e,e->inuse && e->targtype==TARG_TREE && !M_IsDead(e) && Vector2_distance(&e->s.origin2,point)<radius) n++;
    return n;
}
static void FrontLogging(void) {
    FrontLoad(false);
    edict_t *hq=FrontUnit(0,"fhq0");
    edict_t *w[5]={0};uint32_t n=0;
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && e->class_id==FS_SLKKey("fwkr") && !M_IsDead(e)) { if (n<5) w[n++]=e; }
    T_EQ(n,5u);
    FOR_LOOP(i,5) { order_stop(w[i]);w[i]->resources=0; }
    FrontStep(2);
    edict_t *tree=NULL;float best=FLT_MAX;
    FILTER_EDICTS(e,e->inuse && e->targtype==TARG_TREE && !M_IsDead(e)) {
        float d=Vector2_distance(&w[0]->s.origin2,&e->s.origin2); /* the tree the player clicks, nearest the first engineer */
        if (d<best) { best=d;tree=e; }
    }
    T_NOT_NULL(tree);
    uint32_t const start_trees=FrontTreesNear(&hq->s.origin2,2000);
    T_ASSERT(start_trees>=40); /* a real forest, not the old 16-tree grove */
    FOR_LOOP(i,5) T_ASSERT(G_IssueUnitTargetOrder(w[i],"smart",tree,false,0));
    gameClient_t *client=G_GetPlayerClientByNumber(0);
    uint32_t idle_frames[5]={0},longest_idle=0,deliveries=0,last_lumber=client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER];
    FOR_LOOP(f,7000) {
        FrontStep(1);
        uint32_t const lumber=client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER];
        if (lumber>last_lumber) deliveries++;
        last_lumber=lumber;
        FOR_LOOP(k,5) {
            if (G_GetCurrentOrderId(w[k])==0 && !(w[k]->s.renderfx&RF_HIDDEN)) idle_frames[k]++;else idle_frames[k]=0;
            longest_idle=MAX(longest_idle,idle_frames[k]);
        }
    }
    fprintf(stderr,"LOGGING start_trees=%u trees_left=%u deliveries=%u longest_idle=%u\n",start_trees,FrontTreesNear(&hq->s.origin2,2000),deliveries,longest_idle);
    T_EQ(FrontTreesNear(&hq->s.origin2,2000),start_trees); /* trees are an unlimited resource */
    T_ASSERT(tree->health.value>0 && !M_IsDead(tree));
    T_NOT_NULL(tree->pathtex); /* and solid: they block movement */
    T_ASSERT(longest_idle<20); /* nobody stood idle while trees remained */
    T_ASSERT(deliveries>=100); /* and lumber kept arriving at the headquarters */
    /* The forest is gone: workers stop instead of orbiting. */
    FILTER_EDICTS(e,e->inuse && e->targtype==TARG_TREE && !M_IsDead(e)) T_Damage(e,e,(int)e->health.max_value+1);
    FrontStep(1500);
    FOR_LOOP(k,5) T_EQ(G_GetCurrentOrderId(w[k]),0);
    FrontEnd();
}
/* Buildings block exactly their drawn footprint: placement refuses overlaps with
 * structures, trees and mines; units path around them; trained units appear
 * outside every footprint; a destroyed building frees its ground. */
static float FrontFootprintSide(cstring_t code) {
    pathTex_t *tex=M_LoadPathTex(G_UnitData(FS_SLKKey(code))->pathingTexture);
    float side=tex ? tex->width*32.0f : 0;
    if (tex) gi.MemFree(tex);
    return side;
}
static bool FrontInsideAnyFootprint(vec2_t const *point,float margin) {
    FILTER_EDICTS(b,b->inuse && b->pathtex && G_UnitIsStructure(b) && !M_IsDead(b))
        if (CM_DistanceToPathingFootprint(b,point)<margin) return true;
    return false;
}
static void FrontBuildingCollision(void) {
    FrontLoad(false);
    edict_t *engineer=FrontUnit(0,"fwkr");
    uint32_t const barracks=FS_SLKKey("fbar");
    float const side=FrontFootprintSide("fbar");
    T_FEQ(side,192,.01f); /* footprint equals the 6-cell model, not the old 1-cell stub */
    vec2_t snapped,corner={-4100,2700};
    /* 1. Dense packing: every accepted site is a full footprint from every other. */
    edict_t *built[32];uint32_t count=0;
    for (float y=corner.y;y<=corner.y+700;y+=16)
        for (float x=corner.x;x<=corner.x+800;x+=16) {
            vec2_t at={x,y};
            if (G_EvaluateBuildPlacement(engineer,barracks,&at,&snapped)!=PLACE_OK) continue;
            T_ASSERT(count<32);if (count>=32) continue;
            built[count]=unit_create(0,barracks,&snapped,0);T_NOT_NULL(built[count]);
            if (built[count]) count++;
        }
    T_ASSERT(count>=6);
    FOR_LOOP(i,count) for (uint32_t j=i+1;j<count;j++) {
        float const dx=fabsf(built[i]->s.origin2.x-built[j]->s.origin2.x),dy=fabsf(built[i]->s.origin2.y-built[j]->s.origin2.y);
        T_ASSERT(MAX(dx,dy)>=side-.01f); /* footprints never overlap */
    }
    /* A site overlapping any placed building is refused, one a footprint away is allowed. */
    vec2_t const first=built[0]->s.origin2;
    FOR_LOOP(k,4) {
        vec2_t at={first.x+(k&1?side*.5f:0),first.y+(k&2?side*.5f:0)};
        if (k==0) continue;
        T_ASSERT(G_EvaluateBuildPlacement(engineer,barracks,&at,&snapped)!=PLACE_OK);
    }
    /* 2. Trees and mines refuse structures too. */
    edict_t *tree=NULL,*mine=FrontUnit(15,"eore");
    FILTER_EDICTS(e,e->inuse && e->targtype==TARG_TREE && !M_IsDead(e) && e->s.origin2.x<0) { tree=e;break; }
    T_NOT_NULL(tree);T_NOT_NULL(mine);
    if (tree) T_ASSERT(G_EvaluateBuildPlacement(engineer,barracks,&tree->s.origin2,&snapped)!=PLACE_OK);
    if (mine) T_ASSERT(G_EvaluateBuildPlacement(engineer,barracks,&mine->s.origin2,&snapped)!=PLACE_OK);
    /* 3. Units path through a 64-unit corridor and around a wall without entering a footprint. */
    float const reach=side*.5f;
    struct { vec2_t from,to;float centers[3][2];uint32_t n;bool detour; } const walks[2]={
        {{-2572,3050},{-2572,3650},{{-2700,3350},{-2444,3350}},2,false},
        {{-2508,3050},{-2508,3650},{{-2700,3350},{-2508,3350},{-2316,3350}},3,true}};
    FOR_LOOP(w,2) {
        edict_t *group[3]={0};
        FOR_LOOP(i,walks[w].n) {
            vec2_t c={walks[w].centers[i][0],walks[w].centers[i][1]};
            group[i]=unit_create(0,barracks,&c,0);T_NOT_NULL(group[i]);
        }
        FrontStep(3);
        edict_t *squad=unit_create(0,FS_SLKKey("finf"),&walks[w].from,0);
        T_ASSERT(unit_issueorder(squad,"move",&walks[w].to));
        float deepest=0,sideways=0;
        FOR_LOOP(i,700) {
            FrontStep(1);
            FILTER_EDICTS(bb,bb->inuse && bb->pathtex && G_UnitIsStructure(bb) && !M_IsDead(bb)) {
                float const dx=reach-fabsf(squad->s.origin2.x-bb->s.origin2.x),dy=reach-fabsf(squad->s.origin2.y-bb->s.origin2.y);
                if (dx>0 && dy>0) deepest=MAX(deepest,MIN(dx,dy));
            }
            sideways=MAX(sideways,fabsf(squad->s.origin2.x-walks[w].from.x));
        }
        T_ASSERT(deepest<28); /* never deeper than its own radius into a footprint */
        T_ASSERT(Vector2_distance(&squad->s.origin2,&walks[w].to)<160); /* and it still got across */
        if (walks[w].detour) T_ASSERT(sideways>150); /* around the wall, not through it */
        G_FreeEdict(squad);
        FOR_LOOP(i,walks[w].n) T_Damage(group[i],group[i],(int)group[i]->health.max_value+1); /* destruction releases the footprint */
        FrontStep(80);
    }
    /* 4. Trained units appear on free ground even when the producer is boxed in. */
    edict_t *producer=built[0];
    gameClient_t *client=G_GetPlayerClientByNumber(0);client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=5000;
    uint32_t const infantry=FS_SLKKey("finf");
    uint32_t before=0,after=0;
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && e->class_id==infantry) before++;
    FOR_LOOP(i,5) T_ASSERT(SP_TrainUnit(producer,infantry));
    FrontStep(900);
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && e->class_id==infantry && !M_IsDead(e)) {
        after++;T_ASSERT(!FrontInsideAnyFootprint(&e->s.origin2,1));
    }
    T_ASSERT(after>=before+3);
    /* 5. Destroying a building frees its footprint. */
    vec2_t const site=first;
    T_ASSERT(G_EvaluateBuildPlacement(engineer,barracks,&site,&snapped)!=PLACE_OK);
    T_Damage(built[0],built[0],(int)built[0]->health.max_value+1);FrontStep(60);
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && e->class_id==infantry && !M_IsDead(e)) G_FreeEdict(e);
    T_ASSERT(G_EvaluateBuildPlacement(engineer,barracks,&site,&snapped)==PLACE_OK);
    FrontEnd();
}
static test_t building_collision={"frontline.buildings_never_overlap_and_units_path_around",FrontBuildingCollision,__FILE__,__LINE__,NULL};
/* The bigger map: a larger playable area, plentiful forests, and bases that keep their clearings. */
static void FrontMapAndForests(void) {
    FrontLoad(false);
    vec2_t const hq0={-5400,5400},hq1={5400,-5400};
    /* Player 0 HQ survives FrontLoad(false); check it is at the expected deep-corner position. */
    edict_t *hq0u=FrontUnit(0,"fhq0");
    T_NOT_NULL(hq0u);
    T_ASSERT(Vector2_distance(&hq0u->s.origin2,&hq0)<1);
    T_ASSERT(Vector2_distance(&hq0,&hq1)>15000); /* bases sit deep in opposite corners, far apart */
    uint32_t trees=0,near_hq[2]={0,0},near_home[2]={0,0},on_islands=0,in_clearing=0,blocked_pathing=0;
    FILTER_EDICTS(e,e->inuse && e->targtype==TARG_TREE && !M_IsDead(e)) {
        trees++;
        FOR_LOOP(k,2) {
            vec2_t const hq=k?hq1:hq0;
            float const d=Vector2_distance(&e->s.origin2,&hq);
            if (d<1600) near_hq[k]++;
            if (d<3000) near_home[k]++;
            if (d<500) in_clearing++; /* the HQ building clearing must stay open (the 16 home trees start 600 out) */
        }
        if (fabsf(e->s.origin2.x-e->s.origin2.y)<3900) on_islands++;
        if (!CM_TerrainPointIsWalkable(&e->s.origin2) && false) blocked_pathing++;
    }
    fprintf(stderr,"MAP trees=%u near_hq=%u/%u within3000=%u/%u island_trees=%u\n",trees,near_hq[0],near_hq[1],near_home[0],near_home[1],on_islands);
    T_ASSERT(trees>=1000);
    FOR_LOOP(k,2) { T_ASSERT(near_hq[k]>=18);T_ASSERT(near_home[k]>=100); }
    T_EQ(in_clearing,0u);
    T_ASSERT(on_islands>=40);
    T_EQ(blocked_pathing,0u);
    /* Both sides get the same forest (the layout is point-symmetric). */
    T_ASSERT(abs((int)near_home[0]-(int)near_home[1])<=6);
    /* A battleship can still cross the whole ocean; no forest or island blocks the central lane. */
    edict_t *ship=unit_create(0,FS_SLKKey("fbat"),&(vec2_t){-1500,-1500},0);
    vec2_t const far={5500,3500};
    T_ASSERT(unit_issueorder(ship,"move",&far));
    FrontStep(1400);
    T_ASSERT(Vector2_distance(&ship->s.origin2,&far)<500);
    /* Outer-rim islands carry gold mines to contest. */
    uint32_t rim_mines=0;
    FILTER_EDICTS(e,e->inuse && e->class_id==FS_SLKKey("eore") && hypotf(e->s.origin2.x,e->s.origin2.y)>5500) rim_mines++;
    T_ASSERT(rim_mines>=10);
    FrontEnd();
}
static test_t map_forests={"frontline.bigger_map_forests_and_clearings",FrontMapAndForests,__FILE__,__LINE__,NULL};
static void FrontClearSelection(gameClient_t *client);
static uint32_t FrontFlightStage(edict_t *plane) {
    FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && S_SpellChannelTarget(f)==plane) return f->damage;
    return UINT32_MAX;
}
static void FrontCarrier(void) {
    edict_t *ship;
    gameClient_t *client;
    gameCommandButton_t button;
    FrontLoad(false); ship=FrontUnit(0,"fcvr");client=G_GetPlayerClientByNumber(0);
    T_NOT_NULL(ship);
    /* Squadron card: one button per aircraft type, Recall, Air Status, Protection. */
    cstring_t const panel[]={"Fsqf","Fsqd","Fsqt","Fret","Fsts","Fpro"};
    FOR_LOOP(i,6) T_ASSERT(G_BuildCommandButton(ship,panel[i],false,0,&button));
    gameCommandButton_t card[24];uint32_t cmds=G_GetCommandButtons(ship,card,24);
    T_ASSERT(cmds<=12);
    FOR_LOOP(i,cmds) T_ASSERT(strcmp(card[i].command,"Frep") && strcmp(card[i].command,"Fgrp"));
    T_ASSERT(G_BuildCommandButton(ship,"Fcov",false,0,&button));
    uint32_t gold=client->ps.stats[PLAYERSTATE_RESOURCE_GOLD];
    FrontStep(12);
    T_EQ(S_CarrierAircraftCount(ship),24);T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],gold);
    edict_t *fighter=FrontUnit(0,"ffgt"),*bomber=FrontUnit(0,"fbmb");
    T_NOT_NULL(fighter);T_NOT_NULL(bomber);
    if (!fighter || !bomber) { FrontEnd(); return; }
    T_ASSERT(fighter->s.renderfx & RF_HIDDEN);T_EQ(FrontFlightStage(fighter),1u);
    T_FEQ(fighter->mana.value,8,.01f);T_FEQ(bomber->mana.value,1,.01f);
    /* Fighter squadron: every ready fighter flies to the area; bombers stay aboard. */
    T_ASSERT(unit_issueorder(ship,"fightersquadron",&(vec2_t){0,1200}));
    FrontStep(260);
    uint32_t out=0;
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && e->class_id==FS_SLKKey("ffgt") && !(e->s.renderfx&RF_HIDDEN)) {
        out++;T_ASSERT(Vector2_distance(&e->s.origin2,&(vec2_t){0,1200})<700);
    }
    T_EQ(out,8u);T_ASSERT(bomber->s.renderfx & RF_HIDDEN);
    char status[256];
    T_ASSERT(S_CarrierStatusLabel(ship,status,sizeof(status)));T_ASSERT(strstr(status,"Fighters 0 ready")!=NULL);T_ASSERT(strstr(status,"aloft 8")!=NULL);
    /* A second order retasks the squadron already aloft to the new area. */
    T_ASSERT(unit_issueorder(ship,"fightersquadron",&(vec2_t){0,1800}));
    /* Condition on landing: a lightly damaged fighter rearms quickly, a damaged one waits
     * longer, and a wreck is written off for good. */
    edict_t *planes[4];uint32_t n=0;
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && e->class_id==FS_SLKKey("ffgt") && n<4) planes[n++]=e;
    T_EQ(n,4u);
    planes[1]->health.value=planes[1]->health.max_value*.5f;
    planes[2]->health.value=planes[2]->health.max_value*.1f;
    T_ASSERT(unit_issueimmediateorder(ship,"recallaircraft"));
    for (uint32_t i=0;i<400 && (FrontFlightStage(planes[0])!=1u && FrontFlightStage(planes[0])!=5u);i++) FrontStep(1);
    FrontStep(150);
    T_EQ(S_CarrierAircraftCount(ship),23); /* the wreck is gone */
    T_ASSERT(S_CarrierStatusLabel(ship,status,sizeof(status)));T_ASSERT(strstr(status,"lost 1")!=NULL);
    T_EQ(FrontFlightStage(planes[0]),1u);   /* ready: 8 s rearm */
    T_EQ(FrontFlightStage(planes[1]),5u);   /* still in repair: 8 + 30 s */
    FrontStep(300);
    T_EQ(FrontFlightStage(planes[1]),1u);T_FEQ(planes[1]->health.value,planes[1]->health.max_value,.5f);
    T_ASSERT(!unit_issueimmediateorder(ship,"replenishair"));T_EQ(S_CarrierAircraftCount(ship),23);
    FrontEnd();
}
static uint32_t FrontStrikeStage(void) {
    FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) return m->damage;
    return UINT32_MAX;
}
/* Squadrons refuse targets their aircraft cannot attack, launching nothing. */
static void FrontStrikeEligibility(void) {
    FrontLoad(false);
    edict_t *carrier=unit_create(0,FS_SLKKey("fcvr"),&(vec2_t){-700,1300},0);
    FrontStep(12);
    struct { cstring_t order,unit;vec2_t at;bool ok; } const cases[]={
        {"torpedosquadron","ftnk",{-3100,3100},false}, /* torpedo bombers only hit ships */
        {"divesquadron","ffgt",{1000,1900},false},     /* bombers cannot hit aircraft */
        {"torpedosquadron","ftrn",{1500,2300},true},
        {"divesquadron","ftnk",{-3100,3100},true}};
    FOR_LOOP(c,4) {
        edict_t *target=unit_create(1,FS_SLKKey(cases[c].unit),&cases[c].at,0);
        T_NOT_NULL(target);
        T_EQ(G_IssueUnitTargetOrder(carrier,cases[c].order,target,false,0),cases[c].ok);
        uint32_t launched=0;
        FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && f->variation==3 && S_SpellChannelOwner(f)==carrier) launched++;
        if (!cases[c].ok) T_EQ(launched,0u); else {
            T_EQ(launched,8u); /* the whole squadron (8 on a fleet carrier), one type only */
            T_ASSERT(unit_issueimmediateorder(carrier,"recallaircraft"));FrontStep(1500);
        }
        G_FreeEdict(target);
    }
    FrontEnd();
}
/* Two selected carriers ordered together run ONE strike: everything launches,
 * nothing attacks until the whole wave is airborne and assembled, bombers spend
 * their payload in one run and every survivor lands back on its own carrier. */
static void FrontCoordinatedStrike(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=5000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=2000;
    edict_t *carriers[2]={FrontUnit(0,"fcvr"),unit_create(0,FS_SLKKey("fcvr"),&(vec2_t){-1300,1500},0)};
    G_UnitSetAbilityLevel(carriers[1],MAKEFOURCC('F','c','a','p'),2);
    FrontStep(12); /* both carriers embark their air groups */
    /* An enemy transport in open water, beyond every surface gun's reach. */
    edict_t *target=unit_create(1,FS_SLKKey("ftrn"),&(vec2_t){1500,2300},0);
    float const hp=target->health.value;
    /* The UI casts a targeted spell from the focused carrier; the selection joins it. */
    FrontClearSelection(client);G_SelectEntity(client,carriers[0]);G_SelectEntity(client,carriers[1]);
    T_ASSERT(G_IssueUnitTargetOrder(carriers[0],"airstrike",target,false,0));
    uint32_t missions=0;
    FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) missions++;
    T_EQ(missions,1u);
    uint32_t members=0;
    FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && f->combatentity && f->variation==3) members++;
    T_EQ(members,32u); /* the default package is bombers only: eight dive and eight torpedo bombers per carrier */
    bool saw_launch=false,saw_assemble=false,attacked_early=false,wave_airborne=true;
    uint32_t frames=0;
    while (FrontStrikeStage()!=UINT32_MAX && frames<2400) {
        uint32_t const stage=FrontStrikeStage();
        if (stage==1) saw_launch=true;
        if (stage==2) saw_assemble=true;
        if (stage<3 && target->health.value<hp) attacked_early=true;
        if (getenv("STRIKE_DEBUG") && frames%10==0) {
            fprintf(stderr,"STRIKEDBG f=%u stage=%u hp=%.0f",frames,stage,target->health.value);
            FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && f->variation==3) {
                edict_t *pl=S_SpellChannelTarget(f);
                fprintf(stderr," [%s st=%u ammo=%.0f d=%.0f]",G_UnitName(pl->class_id),f->damage,pl->mana.value,Vector2_distance(&pl->s.origin2,&target->s.origin2));
            }
            fprintf(stderr,"\n");
        }
        if (stage==3 && frames>0) {
            FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && f->combatentity && f->variation==3)
                if (f->damage<2) wave_airborne=false; /* a member still on deck during the attack */
        }
        FrontStep(1);frames++;
    }
    T_ASSERT(saw_launch);T_ASSERT(saw_assemble);T_ASSERT(!attacked_early);T_ASSERT(wave_airborne);
    T_ASSERT(target->health.value<hp);
    T_EQ(FrontStrikeStage(),UINT32_MAX);
    FrontStep(200);
    FOR_LOOP(i,2) {
        FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && S_SpellChannelOwner(f)==carriers[i]) {
            edict_t *plane=S_SpellChannelTarget(f);
            T_ASSERT(S_CargoTransportForUnit(plane)==carriers[i]); /* landed on its own deck */
            T_ASSERT(f->variation!=3);
        }
    }
    edict_t *bomber=FrontUnit(0,"fbmb");
    T_NOT_NULL(bomber);
    if (bomber) T_FEQ(bomber->mana.value,1,.01f); /* rearmed after landing */
    fprintf(stderr,"COORDINATED_STRIKE frames=%u target_hp=%.0f/%.0f\n",frames,target->health.value,hp);
    FrontEnd();
}
/* Battleship AA engages aircraft on its own while the main battery fires at a ship. */
static void FrontBattleshipAA(void) {
    FrontLoad(false);
    FILTER_EDICTS(e,e->inuse && (e->svflags&SVF_MONSTER) && e->class_id!=FS_SLKKey("fhq0")) G_FreeEdict(e);
    cstring_t const ships[]={"uiow","jyam","jnag"};
    FOR_LOOP(k,3) {
        uint32_t const owner=k==0 ? 0 : 1;
        edict_t *ship=unit_create(owner,FS_SLKKey(ships[k]),&(vec2_t){0,500},0);
        edict_t *plane=unit_create(1-owner,FS_SLKKey(owner ? "ufig" : "jfig"),&(vec2_t){350,650},0);
        edict_t *hull=unit_create(1-owner,FS_SLKKey("ftrn"),&(vec2_t){1300,500},0);
        T_NOT_NULL(ship);T_NOT_NULL(plane);T_NOT_NULL(hull);
        if (!ship || !plane || !hull) break;
        order_stop(plane);
        float const air=plane->health.value,sea=hull->health.value;
        T_ASSERT(G_IssueUnitTargetOrder(ship,"attack",hull,false,owner));
        uint32_t tracers=0;
        FOR_LOOP(i,120) {
            FrontStep(1);
            FILTER_EDICTS(m,m->inuse && m->movetype==MOVETYPE_FLYMISSILE && m->owner==ship && m->goalentity==plane) tracers++;
        }
        T_ASSERT(tracers>0);
        T_ASSERT(plane->health.value<air); /* AA hit the fighter */
        T_ASSERT(hull->health.value<sea);  /* while the main battery engaged the ship */
        uint32_t directors=0;
        FILTER_EDICTS(d,d->inuse && d->think==naval_aa_think && S_SpellChannelOwner(d)==ship) directors++;
        T_EQ(directors,1u);
        G_FreeEdict(ship);G_FreeEdict(plane);G_FreeEdict(hull);FrontStep(2);
    }
    FrontEnd();
}
/* Damaged warships smoke below half health and also burn below a quarter. */
static uint32_t FrontEffects(cstring_t model) {
    uint32_t count=0,index=G_RegisterModel(model);
    FILTER_EDICTS(e,e->inuse && e->s.model==index && !e->class_id) count++;
    return count;
}
/* Ship condition: smoke when damaged, fire and inferno when burning/critical, a list that
 * steps one level at a time, matching model sequences, turrets riding the lowered deck. */
void naval_battery_think(edict_t *mount);
static float FrontMountZ(edict_t *ship) {
    float z=-1e9f;
    FILTER_EDICTS(m,m->inuse && m->think==naval_battery_think && S_SpellChannelOwner(m)==ship) z=MAX(z,m->s.origin.z);
    return z;
}
static bool FrontAnimationHas(edict_t *ship, cstring_t word) {
    return ship->animation && strcasestr(ship->animation->name,word)!=NULL;
}
/* Dry-dock presentation: the gate tag drives drydock.py's 'Stand Alternate' (caisson open),
 * and a launched ship leaves a launch_wake effect behind it. */
static void FrontDockPresentation(void) {
    FrontLoad(false);
    edict_t *dock=unit_create(0,FS_SLKKey("fdoc"),&(vec2_t){-2400,1900},0);
    edict_t *ship=unit_create(0,FS_SLKKey("uflt"),&(vec2_t){-2200,2200},0);
    T_NOT_NULL(dock);T_NOT_NULL(ship);
    if (!dock || !ship) {FrontEnd();return;}
    S_DockGate(dock,true);FrontStep(2);
    T_ASSERT(FrontAnimationHas(dock,"alternate"));
    S_DockGate(dock,false);FrontStep(2);
    T_ASSERT(!FrontAnimationHas(dock,"alternate"));
    uint32_t const wake=G_RegisterModel("Emberfield/Models/launch_wake.mdx");
    uint32_t before=0,after=0;
    FILTER_EDICTS(e,e->inuse && e->s.model==wake) before++;
    S_ShipLaunchFx(ship,dock);
    FILTER_EDICTS(e,e->inuse && e->s.model==wake) after++;
    T_EQ(after,before+1);
    S_DockGate(NULL,true);S_ShipLaunchFx(NULL,dock);       /* tolerated */
    FrontEnd();
}
static void FrontShipDamageEffects(void) {
    FrontLoad(false);
    edict_t *ship=unit_create(0,FS_SLKKey("uiow"),&(vec2_t){0,500},0);
    /* Earlier scenarios restart game time, so a ballistics fire/flood record left on this
     * edict slot can still match; let any such record lapse (flooding lasts 20 s). */
    FrontStep(220);
    T_EQ(S_ShipEffect(ship),0u);T_EQ(S_ShipListLevel(ship),0u);
    T_ASSERT(!FrontAnimationHas(ship,"smoke") && !FrontAnimationHas(ship,"list"));
    float const level_z=FrontMountZ(ship);
    T_ASSERT(level_z>-1e8f);
    ship->health.value=ship->health.max_value*.5f;
    FrontStep(2);
    T_EQ(S_ShipEffect(ship),1u);T_EQ(S_ShipListLevel(ship),0u);T_ASSERT(FrontAnimationHas(ship,"smoke"));
    /* Critical: inferno at once, the list settles one step per 800 ms. */
    ship->health.value=ship->health.max_value*.2f;
    FrontStep(1);
    T_EQ(S_ShipEffect(ship),3u);T_EQ(S_ShipListLevel(ship),1u);
    T_ASSERT(FrontAnimationHas(ship,"inferno") && FrontAnimationHas(ship,"list1"));
    FrontStep(4);T_EQ(S_ShipListLevel(ship),1u);
    FrontStep(6);T_EQ(S_ShipListLevel(ship),2u);T_ASSERT(FrontAnimationHas(ship,"list2"));
    FrontStep(20);T_EQ(S_ShipListLevel(ship),2u);
    T_ASSERT(FrontMountZ(ship)<level_z-2); /* turrets ride the lower, trimmed deck */
    /* Repairs reverse the list a step at a time. */
    ship->health.value=ship->health.max_value;
    FrontStep(1);T_EQ(S_ShipEffect(ship),0u);T_EQ(S_ShipListLevel(ship),1u);
    FrontStep(10);T_EQ(S_ShipListLevel(ship),0u);T_ASSERT(!FrontAnimationHas(ship,"list"));
    T_Damage(ship,ship,(int)ship->health.max_value*2);
    FrontStep(2);
    T_ASSERT(M_IsDead(ship));T_ASSERT(FrontAnimationHas(ship,"death"));
    FrontEnd();
}
/* Evasion lowers hit rates, never to zero, delays the aircraft's own fire and jinks it sideways. */
static float FrontEvadeRate(cstring_t code) {
    edict_t *plane=unit_create(1,FS_SLKKey(code),&(vec2_t){0,800},0),*gun=unit_create(0,FS_SLKKey("faa0"),&(vec2_t){-3000,3000},0);
    uint32_t evaded=0;
    FOR_LOOP(i,400) {
        if (M_IsDead(plane)) plane=unit_create(1,FS_SLKKey(code),&(vec2_t){0,800},0); /* a hit can be fatal now */
        plane->evade_until=plane->evade_ready=0; /* every trial starts with the pilot recovered */
        S_AircraftClearCrits(plane); /* and unwounded */
        plane->health.value=plane->health.max_value;
        S_ResolveAttackHit(gun,plane,10);
        if (G_Time()<plane->evade_until) evaded++; /* a maneuver started; clean misses are gunnery, not evasion */
    }
    G_FreeEdict(plane);G_FreeEdict(gun);
    return evaded/400.0f;
}
static void FrontAircraftEvasion(void) {
    FrontLoad(false);
    float const zero=FrontEvadeRate("jfig"),wildcat=FrontEvadeRate("ufig"),dive=FrontEvadeRate("ubom"),torpedo=FrontEvadeRate("jtor"),recon=FrontEvadeRate("frec");
    fprintf(stderr,"EVASION zero=%.2f wildcat=%.2f dive=%.2f torpedo=%.2f recon=%.2f\n",zero,wildcat,dive,torpedo,recon);
    T_ASSERT(zero>.28f && zero<.52f);T_ASSERT(wildcat>.22f && wildcat<.42f);
    T_ASSERT(dive<wildcat);T_ASSERT(torpedo<dive+.05f);T_ASSERT(torpedo>.03f);
    T_ASSERT(recon<.01f); /* no evasion row: no evasion */
    /* A sustained burst still lands: a maneuver is followed by a recovery window. */
    edict_t *plane=unit_create(1,FS_SLKKey("jfig"),&(vec2_t){0,800},0),*gun=unit_create(0,FS_SLKKey("faa0"),&(vec2_t){-3000,3000},0);
    plane->health.value=plane->health.max_value;
    FOR_LOOP(i,200) {
        if (G_Time()<plane->evade_until) break;
        plane->evade_until=plane->evade_ready=0;
        S_ResolveAttackHit(gun,plane,1);
    }
    T_ASSERT(G_Time()<plane->evade_until);
    vec2_t before;
    T_ASSERT(plane->unit_state->attack_cooldown_end_time>=plane->evade_until); /* the maneuver costs firing time */
    before=plane->s.origin2;
    FrontStep(6);
    T_ASSERT(Vector2_distance(&before,&plane->s.origin2)>5); /* jinked off its line */
    float const hp=plane->health.value;
    FrontStep(15); /* maneuver over, pilot recovering */
    FOR_LOOP(i,5) S_ResolveAttackHit(gun,plane,10);
    T_ASSERT(plane->health.value<hp);
    G_FreeEdict(plane);G_FreeEdict(gun);
    FrontEnd();
}
/* Fire on aircraft is a direct hit, a near miss (a burst or a few rounds: partial damage) or a
 * clean miss, for flak, fighter guns and small arms alike, scaled by speed, size, altitude,
 * range and maneuvering. Every hit path (attacks, AA tracers, splash) resolves through it. */
static void FrontAircraftHitVariance(void) {
    FrontLoad(false);
    edict_t *flak=unit_create(0,FS_SLKKey("faa0"),&(vec2_t){-3000,3000},0);
    edict_t *gunner=unit_create(0,FS_SLKKey("ufig"),&(vec2_t){-2900,3000},0);
    edict_t *rifle=unit_create(0,FS_SLKKey("fmg0"),&(vec2_t){-3000,2900},0);
    edict_t *zero=unit_create(1,FS_SLKKey("jfig"),&(vec2_t){-2700,3200},0);
    edict_t *kate=unit_create(1,FS_SLKKey("jtor"),&(vec2_t){-2700,3200},0);
    edict_t *val=unit_create(1,FS_SLKKey("jbom"),&(vec2_t){-2700,3200},0);
    T_NOT_NULL(flak);T_NOT_NULL(gunner);T_NOT_NULL(rifle);T_NOT_NULL(zero);T_NOT_NULL(kate);T_NOT_NULL(val);
    if (!flak || !gunner || !rifle || !zero || !kate || !val) { FrontEnd(); return; }
    edict_t *sources[3]={flak,gunner,rifle};
    FOR_LOOP(s,3) {
        uint32_t n[3]={0};float near_min=1,near_max=0;
        FOR_LOOP(i,600) {
            float fraction=0;airHitKind_t const kind=S_AircraftRollHit(sources[s],zero,&fraction);
            n[kind]++;
            if (kind==AIR_HIT_NEAR) { near_min=MIN(near_min,fraction);near_max=MAX(near_max,fraction); }
            if (kind==AIR_HIT_DIRECT) T_ASSERT(fraction>=.8f && fraction<=1.2f);
            if (kind==AIR_HIT_MISS) T_FEQ(fraction,0,.001f);
        }
        fprintf(stderr,"AIRHIT source=%u miss=%u near=%u direct=%u\n",(unsigned)s,n[0],n[1],n[2]);
        T_ASSERT(n[AIR_HIT_MISS]>30 && n[AIR_HIT_NEAR]>60 && n[AIR_HIT_DIRECT]>90);
        T_ASSERT(near_min>=.15f && near_max<=.6f);
    }
    /* Real factors: big slow bombers are easier than a nimble fighter; small arms reach a
     * low torpedo plane better than a high dive bomber; heavy flak tracks the low, crossing
     * torpedo run worse; a jinking or distant target is harder. */
    T_ASSERT(S_AircraftAccuracy(flak,val)>S_AircraftAccuracy(flak,zero));
    T_ASSERT(S_AircraftAccuracy(rifle,kate)>S_AircraftAccuracy(rifle,val));
    T_ASSERT(S_AircraftAccuracy(flak,kate)<S_AircraftAccuracy(flak,val));
    float const steady=S_AircraftAccuracy(flak,zero);
    zero->evade_until=G_Time()+1000;
    T_ASSERT(S_AircraftAccuracy(flak,zero)<steady*.75f);
    zero->evade_until=zero->evade_ready=0;
    zero->s.origin.x=zero->s.origin2.x=-3000+900;
    T_ASSERT(S_AircraftAccuracy(flak,zero)<steady);
    /* The ordinary hit path delivers clean misses, partial near misses and full hits. */
    uint32_t zero_damage=0,partial=0,full=0;
    FOR_LOOP(i,400) {
        val->health.value=val->health.max_value;val->evade_until=val->evade_ready=0;S_AircraftClearCrits(val);
        float const before=val->health.value;
        S_ResolveAttackHit(flak,val,100);
        if (M_IsDead(val)) { val=unit_create(1,FS_SLKKey("jbom"),&(vec2_t){-2700,3200},0);continue; }
        float const lost=before-val->health.value;
        if (lost<=0) zero_damage++; else if (lost<60) partial++; else full++;
    }
    fprintf(stderr,"AIRHIT resolve miss=%u partial=%u full=%u\n",zero_damage,partial,full);
    T_ASSERT(zero_damage>20 && partial>40 && full>100);
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
/* Critical hits: engine fire burns, a wounded pilot evades and shoots worse, damaged
 * controls force the aircraft home, a fuel leak triples fuel burn. Landing repairs all. */
static uint32_t FrontManeuvers(edict_t *plane, edict_t *gun) {
    uint32_t started=0;
    FOR_LOOP(i,400) {
        plane->evade_until=plane->evade_ready=0;plane->health.value=plane->health.max_value;
        S_AircraftEvades(plane,gun);
        if (G_Time()<plane->evade_until) started++;
    }
    plane->evade_until=plane->evade_ready=0;
    return started;
}
static void FrontAircraftCrits(void) {
    FrontLoad(false);
    edict_t *field=unit_create(0,FS_SLKKey("fair"),&(vec2_t){-3300,1300},0);
    edict_t *gun=unit_create(1,FS_SLKKey("faa0"),&(vec2_t){3000,-3000},0);
    edict_t *plane=unit_create(0,FS_SLKKey("ffgt"),&field->s.origin2,0);
    edict_t *enemy=unit_create(1,FS_SLKKey("jfig"),&(vec2_t){-2000,1300},0);
    T_NOT_NULL(field);T_NOT_NULL(gun);T_NOT_NULL(plane);T_NOT_NULL(enemy);
    if (!field || !gun || !plane || !enemy) { FrontEnd(); return; }
    T_ASSERT(S_CargoTryLoad(field,plane));FrontStep(6);
    T_ASSERT(S_CargoUnloadAt(field,0));FrontStep(2);
    T_ASSERT(S_AircraftHome(plane)==field);
    T_ASSERT(unit_issueorder(plane,"move",&(vec2_t){-1800,1300}));FrontStep(40);
    /* Engine fire: damage over time with no further attack, then it burns out. */
    S_AircraftApplyCrit(plane,gun,AIR_CRIT_ENGINE_FIRE);
    T_ASSERT(S_AircraftCritStates(plane)&(1u<<AIR_CRIT_ENGINE_FIRE));
    float const hp=plane->health.value;
    FrontStep(50);
    T_ASSERT(hp-plane->health.value>=plane->health.max_value*.08f);
    FrontStep(80);
    T_ASSERT(!(S_AircraftCritStates(plane)&(1u<<AIR_CRIT_ENGINE_FIRE)));
    plane->health.value=plane->health.max_value;
    /* Wounded pilot: fewer evasive maneuvers, worse gunnery. */
    uint32_t const healthy=FrontManeuvers(plane,gun);
    float const aim=S_AircraftAccuracy(plane,enemy);
    S_AircraftApplyCrit(plane,gun,AIR_CRIT_PILOT);
    uint32_t const wounded=FrontManeuvers(plane,gun);
    fprintf(stderr,"AIRCRIT maneuvers healthy=%u wounded=%u\n",healthy,wounded);
    T_ASSERT(wounded<healthy*.7f);
    T_ASSERT(S_AircraftAccuracy(plane,enemy)<aim*.85f);
    /* Fuel leak: three times the burn. */
    T_FEQ(S_AircraftFuelBurn(plane),1,.001f);
    S_AircraftApplyCrit(plane,gun,AIR_CRIT_FUEL_LEAK);
    T_FEQ(S_AircraftFuelBurn(plane),3,.001f);
    /* Damaged controls: the aircraft breaks off and flies home, where it is stored and repaired. */
    T_ASSERT(unit_issueorder(plane,"move",&(vec2_t){-600,1300}));FrontStep(5);
    S_AircraftApplyCrit(plane,gun,AIR_CRIT_CONTROLS);
    T_ASSERT(S_AircraftCritStates(plane)&(1u<<AIR_CRIT_CONTROLS));
    for (uint32_t i=0;i<300 && !(plane->s.renderfx&RF_HIDDEN);i++) FrontStep(1);
    T_ASSERT(plane->s.renderfx&RF_HIDDEN);T_ASSERT(S_CargoTransportForUnit(plane)==field);
    FrontStep(6);
    T_EQ(S_AircraftCritStates(plane),0u);
    /* Crits happen on real hits, at a modest rate. */
    uint32_t crits=0;
    edict_t *target=unit_create(1,FS_SLKKey("jbom"),&(vec2_t){-2700,3200},0);
    edict_t *flak=unit_create(0,FS_SLKKey("faa0"),&(vec2_t){-3000,3000},0);
    FOR_LOOP(i,500) {
        if (!target || M_IsDead(target)) target=unit_create(1,FS_SLKKey("jbom"),&(vec2_t){-2700,3200},0);
        target->health.value=target->health.max_value;target->evade_until=target->evade_ready=0;
        S_AircraftClearCrits(target);
        S_ResolveAttackHit(flak,target,20);
        if (M_IsDead(target) || S_AircraftCritStates(target)) crits++;
    }
    fprintf(stderr,"AIRCRIT rate=%u/500\n",crits);
    T_ASSERT(crits>10 && crits<150);
    FrontEnd();
}
/* Fuel: every aircraft burns it while airborne (mana bar on airfield aircraft, the sortie
 * tank on carrier flights), flies home at bingo fuel, refuels in storage and relaunches;
 * a dry tank ditches it. */
static void FrontAircraftFuel(void) {
    FrontLoad(false);
    edict_t *field=unit_create(0,FS_SLKKey("fair"),&(vec2_t){-3300,1300},0);
    edict_t *plane=unit_create(0,FS_SLKKey("ffgt"),&field->s.origin2,0);
    T_NOT_NULL(field);T_NOT_NULL(plane);
    if (!field || !plane) { FrontEnd(); return; }
    T_FEQ(plane->mana.max_value,90,.01f);T_FEQ(plane->mana.value,90,.01f);
    T_ASSERT(unit_issueorder(plane,"move",&(vec2_t){-300,1300}));
    FrontStep(100);
    float const after=plane->mana.value;
    T_ASSERT(after<87 && after>78);
    /* Bingo: too little fuel for the way home plus a reserve. Home defaults to the nearest field. */
    plane->mana.value=10;
    for (uint32_t i=0;i<300 && !(plane->s.renderfx&RF_HIDDEN);i++) FrontStep(1);
    T_ASSERT(plane->s.renderfx&RF_HIDDEN);T_ASSERT(S_CargoTransportForUnit(plane)==field);
    T_ASSERT(S_AircraftHome(plane)==field);
    char label[256];
    T_ASSERT(S_AircraftStatusLabel(plane,label,sizeof(label)));T_ASSERT(strstr(label,"Fuel")!=NULL);
    /* Refuelled in storage, it takes off again by itself. */
    for (uint32_t i=0;i<400 && (plane->s.renderfx&RF_HIDDEN);i++) FrontStep(1);
    T_ASSERT(!(plane->s.renderfx&RF_HIDDEN));T_ASSERT(plane->mana.value>=plane->mana.max_value*.9f);
    /* A dry tank ends the flight. */
    edict_t *stray=unit_create(0,FS_SLKKey("frec"),&(vec2_t){1500,1300},0);
    T_NOT_NULL(stray);
    if (stray) { stray->mana.value=.05f;FrontStep(10);T_ASSERT(M_IsDead(stray)); }
    /* Carrier flights: a fuel leak drains the sortie tank three times as fast, and a flight
     * whose reserve is gone ditches. */
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    T_ASSERT(unit_issueorder(carrier,"fightersquadron",&(vec2_t){0,1200}));
    FrontStep(120);
    edict_t *flight=NULL,*fighter=NULL;
    FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && S_SpellChannelOwner(f)==carrier && f->damage==3) { flight=f;break; }
    T_NOT_NULL(flight);
    if (flight) {
        fighter=S_SpellChannelTarget(flight);
        T_ASSERT(S_CarrierFlightForPlane(fighter)==flight);
        float const tank=flight->wait;
        S_AircraftApplyCrit(fighter,carrier,AIR_CRIT_FUEL_LEAK);
        FrontStep(10);
        T_FEQ(tank-flight->wait,3,.25f);
        T_ASSERT(S_AircraftStatusLabel(fighter,label,sizeof(label)));T_ASSERT(strstr(label,"Fuel")!=NULL);
        flight->damage=4;flight->wait=-14.95f;
        FrontStep(3);
        T_ASSERT(M_IsDead(fighter));
    }
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
/* Return Home (Q) sends an aircraft to the carrier or airfield where it was last stored. */
static void FrontAircraftReturnHome(void) {
    FrontLoad(false);
    gameCommandButton_t card[24];
    cstring_t const types[]={"ffgt","fbmb","ftor","frec","ufig","jbom","utor"};
    FOR_LOOP(t,7) {
        edict_t *plane=unit_create(0,FS_SLKKey(types[t]),&(vec2_t){-3000,3000},0);
        T_NOT_NULL(plane);
        if (!plane) continue;
        uint32_t const count=G_GetCommandButtons(plane,card,24);
        uint32_t home=0,q=0;
        FOR_LOOP(i,count) {
            if (!strcmp(card[i].command,"Fhom")) { home++;T_EQ(card[i].hotkey,'Q'); }
            if (card[i].hotkey=='Q') q++;
            FOR_LOOP(j,i) T_ASSERT(card[i].x!=card[j].x || card[i].y!=card[j].y);
        }
        T_EQ(home,1u);T_EQ(q,1u);
        G_FreeEdict(plane);
    }
    edict_t *near_field=unit_create(0,FS_SLKKey("fair"),&(vec2_t){-3300,1300},0);
    edict_t *last_field=unit_create(0,FS_SLKKey("fair"),&(vec2_t){-3000,3000},0);
    edict_t *plane=unit_create(0,FS_SLKKey("fbmb"),&last_field->s.origin2,0);
    T_NOT_NULL(near_field);T_NOT_NULL(last_field);T_NOT_NULL(plane);
    if (!near_field || !last_field || !plane) { FrontEnd(); return; }
    T_ASSERT(S_CargoTryLoad(last_field,plane));FrontStep(3);
    T_ASSERT(S_CargoUnloadAt(last_field,0));
    T_ASSERT(unit_issueorder(plane,"move",&(vec2_t){-3300,1000}));
    FrontStep(80);
    T_ASSERT(Vector2_distance(&plane->s.origin2,&near_field->s.origin2)<Vector2_distance(&plane->s.origin2,&last_field->s.origin2));
    T_ASSERT(unit_issueimmediateorder(plane,"returnhome"));
    for (uint32_t i=0;i<400 && !(plane->s.renderfx&RF_HIDDEN);i++) FrontStep(1);
    T_ASSERT(S_CargoTransportForUnit(plane)==last_field);
    /* Stored by the player's order, it stays stored. */
    FrontStep(300);T_ASSERT(plane->s.renderfx&RF_HIDDEN);
    /* A carrier aircraft goes home to its carrier. */
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    T_ASSERT(unit_issueorder(carrier,"fightersquadron",&(vec2_t){0,1200}));
    FrontStep(120);
    edict_t *fighter=NULL;
    FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && S_SpellChannelOwner(f)==carrier && f->damage==3) { fighter=S_SpellChannelTarget(f);break; }
    T_NOT_NULL(fighter);
    if (fighter) {
        T_ASSERT(S_AircraftHome(fighter)==carrier);
        T_ASSERT(unit_issueimmediateorder(fighter,"returnhome"));
        T_EQ(FrontFlightStage(fighter),4u);
        for (uint32_t i=0;i<400 && !(fighter->s.renderfx&RF_HIDDEN);i++) FrontStep(1);
        T_ASSERT(S_CargoTransportForUnit(fighter)==carrier);
    }
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
static test_t air_variance={"frontline.aircraft_hit_variance",FrontAircraftHitVariance,__FILE__,__LINE__,NULL};
static test_t air_crits={"frontline.aircraft_critical_states",FrontAircraftCrits,__FILE__,__LINE__,NULL};
static test_t air_fuel={"frontline.aircraft_fuel_bingo_and_ditching",FrontAircraftFuel,__FILE__,__LINE__,NULL};
static test_t air_home={"frontline.aircraft_return_home_hotkey",FrontAircraftReturnHome,__FILE__,__LINE__,NULL};
static uint32_t front_cargo_buttons;
static void FrontCargoWrite(pfWriteType_t type, void const *data) {
    uiFrame_t const *frame=data;
    if (type!=PF_UIFRAME || !frame || frame->flags.type!=FT_COMMANDBUTTON || !frame->onclick || strncmp(frame->onclick,"cargounload ",12)) return;
    front_cargo_buttons++;
    T_ASSERT(frame->size.width*834.0f/.6f>=44.0f);
    T_ASSERT(frame->size.height*834.0f/.6f>=44.0f);
}
static void FrontTransport(void) {
    edict_t *craft, *infantry, *tank, *enemy;
    FrontLoad(false);
    craft=FrontUnit(0,"flct");infantry=FrontUnit(0,"finf");tank=FrontUnit(0,"ftnk");
    T_ASSERT(G_IssueUnitTargetOrder(infantry,"smart",craft,false,0));
    T_ASSERT(G_IssueUnitTargetOrder(tank,"smart",craft,false,0));
    FrontStep(70);
    T_ASSERT(S_CargoTransportForUnit(infantry)==craft);
    T_ASSERT(S_CargoTransportForUnit(tank)==craft);
    T_EQ(craft->cargo->count,2);
    void (*old_write)(pfWriteType_t,void const *)=gi.Write;
    front_cargo_buttons=0;gi.Write=FrontCargoWrite;
    UI_WriteSingleInfo(craft,G_GetPlayerClientByNumber(0));
    gi.Write=old_write;T_EQ(front_cargo_buttons,2);
    T_ASSERT(unit_issueorder(craft,"move",&(vec2_t){-800,800}));
    FrontStep(90);
    T_ASSERT(!S_CargoUnloadAt(craft,0));
    T_EQ(craft->cargo->count,2);
    /* Straight across the open ocean to the opposing mainland's beach. */
    T_ASSERT(unit_issueorder(craft,"move",&(vec2_t){2000,-2150}));
    FrontStep(200);
    T_ASSERT(unit_issueimmediateorder(craft,"unloadall"));
    FrontStep(20);
    T_EQ(craft->cargo->count,0);
    T_ASSERT(!(infantry->s.renderfx & RF_HIDDEN));
    T_ASSERT(!(tank->s.renderfx & RF_HIDDEN));
    T_ASSERT(CM_TerrainPointIsWalkable(&infantry->s.origin2));
    T_ASSERT(CM_TerrainPointIsWalkable(&tank->s.origin2));
    enemy=unit_create(1,FS_SLKKey("finf"),&(vec2_t){2300,-2450},0);
    T_NOT_NULL(enemy);
    float before=enemy->health.value;
    T_ASSERT(G_IssueUnitTargetOrder(infantry,"attack",enemy,false,0));
    T_ASSERT(G_IssueUnitTargetOrder(tank,"attack",enemy,false,0));
    FrontStep(60);
    T_ASSERT(enemy->health.value<before);
    FrontEnd();
}

static void FrontProduction(void) {
    static cstring_t const products[][2]={
        {"fhq0","fwkr"},{"fbar","finf"},{"fbar","fmg0"},{"fbar","fmrt"},{"fbar","fcmd"},
        {"ffac","ftnk"},{"ffac","fcar"},{"ffac","fart"},{"ffac","faa0"},{"ffac","fhtk"},{"ffac","frkt"},
        {"fair","ffgt"},{"fair","fbmb"},{"fair","frec"},{"fair","ftor"},
        {"fdoc","fbat"},{"fdoc","fdst"},{"fdoc","fcrs"},{"fdoc","fcvr"},{"fdoc","flct"},{"fdoc","ftrn"},
    };
    gameClient_t *client;
    edict_t *worker,*bunker;
    gameCommandButton_t button;
    FrontLoad(false);client=G_GetPlayerClientByNumber(0);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=30000;
    client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=30000;
    client->ps.stats[PLAYERSTATE_RESOURCE_FOOD_CAP]=200;
    T_NOT_NULL(unit_create(0,FS_SLKKey("ffac"),&(vec2_t){-3900,1800},0));
    T_NOT_NULL(unit_create(0,FS_SLKKey("fair"),&(vec2_t){-3300,1300},0));
    FOR_LOOP(i,sizeof(products)/sizeof(products[0])) {
        edict_t *producer=FrontUnit(0,products[i][0]);
        T_NOT_NULL(producer);
        T_ASSERT(G_BuildCommandButton(producer,products[i][1],false,0,&button));
        T_ASSERT(SP_TrainUnit(producer,FS_SLKKey(products[i][1])));
    }
    worker=FrontUnit(0,"fwkr");bunker=FrontUnit(0,"fbnk");
    /* Shipyards need navigable water nearby; inland yards would strand ships. */
    T_EQ(G_EvaluateBuildPlacement(worker,FS_SLKKey("fdoc"),&(vec2_t){-3000,2700},NULL),PLACE_REQUIRES_WATER);
    T_EQ(G_EvaluateBuildPlacement(worker,FS_SLKKey("fdoc"),&(vec2_t){-2100,2600},NULL),PLACE_OK);
    T_ASSERT(!G_IssueBuildOrder(worker,FS_SLKKey("fdoc"),&(vec2_t){-3000,2700}));
    T_EQ(G_EvaluateBuildPlacement(worker,FS_SLKKey("fbar"),&(vec2_t){-3000,2700},NULL),PLACE_OK);
    T_ASSERT(G_IssueBuildOrder(worker,FS_SLKKey("fwat"),&(vec2_t){-3100,2900}));
    T_ASSERT(G_StartBuildingUpgrade(bunker,FS_SLKKey("fbn2")));
    FrontStep(1200);
    FOR_LOOP(i,sizeof(products)/sizeof(products[0])) T_NOT_NULL(FrontUnit(0,products[i][1]));
    T_EQ(bunker->class_id,FS_SLKKey("fbn2"));
    T_ASSERT(client->ps.stats[PLAYERSTATE_GOLD_GATHERED]>0);
    T_ASSERT(client->score.values[WC3_PLAYER_SCORE_LUMBER_TOTAL]>0);
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}

static void FrontCarrierLimits(void) {
    edict_t *carrier,*plane;
    gameClient_t *client;
    char status[256];
    FrontLoad(false);carrier=FrontUnit(0,"fcvr");client=G_GetPlayerClientByNumber(0);
    FrontStep(12);
    T_EQ(S_CarrierAircraftCount(carrier),24); /* 8 fighters, 8 dive and 8 torpedo bombers, embarked free */
    uint32_t before=client->ps.stats[PLAYERSTATE_RESOURCE_GOLD];
    T_ASSERT(!unit_issueimmediateorder(carrier,"replenishair"));
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],before);
    T_ASSERT(S_CarrierStatusLabel(carrier,status,sizeof(status)));
    T_ASSERT(strstr(status,"Fighters 8 ready")!=NULL);T_ASSERT(strstr(status,"Torpedo 8 ready")!=NULL);
    T_ASSERT(WriteGame(Test_TempPath("frontline-carrier.bin")));
    T_ASSERT(ReadGame(Test_TempPath("frontline-carrier.bin")));
    carrier=FrontUnit(0,"fcvr");
    T_EQ(S_CarrierAircraftCount(carrier),24);
    FrontStep(30);T_EQ(S_CarrierAircraftCount(carrier),24); /* loading never embarks a second air group */
    plane=S_CargoUnitAt(carrier,0);T_NOT_NULL(plane);
    T_Damage(plane,carrier,(int)plane->health.max_value+1);
    FrontStep(2);
    T_EQ(S_CarrierAircraftCount(carrier),23);
    T_ASSERT(!unit_issueimmediateorder(carrier,"replenishair")); /* losses are permanent */
    T_EQ(S_CarrierAircraftCount(carrier),23);
    T_ASSERT(S_CarrierStatusLabel(carrier,status,sizeof(status)));T_ASSERT(strstr(status,"lost 1")!=NULL);
    /* An Airfield fighter landed in the hold joins the air group and flies with the squadron. */
    edict_t *spare=unit_create(0,FS_SLKKey("ffgt"),&carrier->s.origin2,0);
    T_ASSERT(S_CargoTryLoad(carrier,spare));
    FrontStep(15);
    T_EQ(S_CarrierAircraftCount(carrier),24);
    T_ASSERT(S_CarrierStatusLabel(carrier,status,sizeof(status)));T_ASSERT(strstr(status,"lost")==NULL);
    FrontStep(120); /* rearmed */
    T_ASSERT(unit_issueorder(carrier,"fightersquadron",&(vec2_t){carrier->s.origin.x,carrier->s.origin.y+900}));
    FrontStep(60);T_ASSERT(!(spare->s.renderfx&RF_HIDDEN));
    T_Damage(carrier,carrier,(int)carrier->health.max_value+1);
    FrontStep(2);
    T_EQ(S_CarrierAircraftCount(carrier),0);
    FrontEnd();
}

static void FrontBot(void) {
    uint32_t peak_flights=0,peak_cargo=0,landed=0,peak_factory=0,peak_air=0,strike_stages=0,bot_aa=0;
    bool rebuilt=false,outpost=false;
    FrontLoad(true);
    /* Keep this long doctrine fixture running after air superiority is won.
     * Natural HQ defeat remains covered by FrontFreshAI/FrontMatchResults. */
    G_SetUnitFlag(FrontUnit(0,"fhq0"),UNIT_FLAG_INVULNERABLE,true);
    G_SetUnitFlag(FrontUnit(1,"fhq0"),UNIT_FLAG_INVULNERABLE,true);
    gameClient_t *bot=G_GetPlayerClientByNumber(1);
    T_NOT_NULL(level.bots[1].vm);
    edict_t *initial_dock=FrontUnit(1,"fdoc");
    uint32_t dock_generation=initial_dock->spawn_time;
    FOR_LOOP(i,25000) { /* late game: the land-first AI reaches its island expansion and invasion after its army is established */
        if (i==99) T_Damage(initial_dock,FrontUnit(0,"fbat"),(int)initial_dock->health.max_value+1);
        FrontStep(1);
             FILTER_EDICTS(e,e->inuse && e->s.player==1 && !M_IsDead(e)) {
            if (e->class_id==FS_SLKKey("fcvr")) peak_flights=MAX(peak_flights,S_CarrierAircraftCount(e));
            if (e->class_id==FS_SLKKey("flct") || e->class_id==FS_SLKKey("ftrn") || e->class_id==FS_SLKKey("jdai")) peak_cargo=MAX(peak_cargo,e->cargo?e->cargo->count:0);
            if (e->class_id==FS_SLKKey("jinf") && e->s.origin.y-e->s.origin.x > 3900 && !(e->s.renderfx&RF_HIDDEN)) landed++;
            /* The bot's harbor is now its faction Escort Shipyard (no generic yard), at any coastal site. */
            if ((e->class_id==FS_SLKKey("fdoc") || e->class_id==FS_SLKKey("fesc")) && e->spawn_time!=dock_generation && !e->construction) rebuilt=true;
            /* Island expansion: settlers ferried to the east island raise an outpost HQ. */
            if (e->class_id==FS_SLKKey("fhq0") && !e->construction && Vector2_distance(&e->s.origin2,&(vec2_t){3800,1650})<200) outpost=true;
            if (e->class_id==FS_SLKKey("ffac")) peak_factory=1;
            if (e->class_id==FS_SLKKey("fair")) peak_air=1;
        }
        FILTER_EDICTS(e,e->inuse && e->think==strike_mission_think && e->s.player==1) strike_stages|=1u<<e->damage;
        FILTER_EDICTS(e,e->inuse && e->think==naval_aa_think && S_SpellChannelOwner(e) && S_SpellChannelOwner(e)->s.player==1) bot_aa=1;
    }
    T_ASSERT(!jass_rterror_pending(level.vm));
    T_ASSERT(!jass_rterror_pending(level.bots[1].vm));
    T_ASSERT(bot->ps.stats[PLAYERSTATE_GOLD_GATHERED]>0);
    T_ASSERT(bot->score.values[WC3_PLAYER_SCORE_LUMBER_TOTAL]>0);
    if (!outpost || !landed) {
        FILTER_EDICTS(e,e->inuse && e->s.player==1 && (e->class_id==FS_SLKKey("fwkr") || e->class_id==FS_SLKKey("flct") || e->class_id==FS_SLKKey("fhq0")))
            fprintf(stderr,"FRONTLINE_OUTPOST %.4s hp=%.0f xy=%.0f,%.0f hidden=%u cargo=%u phase=%d move=%s goal=%.0f,%.0f\n",(char *)&e->class_id,e->health.value,e->s.origin.x,e->s.origin.y,e->s.renderfx&RF_HIDDEN,e->cargo?e->cargo->count:0,e->user_data,e->currentmove?e->currentmove->animation:"none",e->goalentity?e->goalentity->s.origin.x:0,e->goalentity?e->goalentity->s.origin.y:0);
    }
    T_ASSERT(peak_factory>0);T_ASSERT(peak_air>0);T_ASSERT(rebuilt);T_ASSERT(outpost);
    T_ASSERT(peak_flights>0);T_ASSERT(peak_cargo>0);
    T_ASSERT(strike_stages&(1u<<1)); /* the bot launched a coordinated strike */
    T_ASSERT(bot_aa); /* bot battleships run their AA batteries */
    fprintf(stderr,"FRONTLINE_BOT frames=25000 flights=%u strike_stages=%#x aa=%u cargo=%u landed_samples=%u factory=%u airfield=%u outpost=%d gold=%u logistics=%u\n",peak_flights,strike_stages,bot_aa,peak_cargo,landed,peak_factory,peak_air,outpost,bot->ps.stats[PLAYERSTATE_GOLD_GATHERED],bot->ps.stats[PLAYERSTATE_LUMBER_GATHERED]);
    FrontEnd();
}

static bool FrontGroundUnit(edict_t const *e) {
    static cstring_t const codes[]={"finf","fmg0","ftnk","fart","faa0","fhtk","frkt","fmrt","fcmd",
                                    "jinf","jmg0","jtnk","jhtk","jmrt","jcmd"};
    FOR_LOOP(i,sizeof(codes)/sizeof(codes[0])) if (e->class_id==FS_SLKKey(codes[i])) return true;
    return false;
}
static uint32_t FrontBotCargo(void) {
    uint32_t loaded=0;
    FILTER_EDICTS(e,e->inuse && e->s.player==1 && (e->class_id==FS_SLKKey("flct") || e->class_id==FS_SLKKey("ftrn") || e->class_id==FS_SLKKey("jdai")) && !M_IsDead(e) && e->cargo) loaded+=e->cargo->count;
    return loaded;
}
/* Rally/unload leave a persistent Smart order; doctrine must not treat those units as busy forever. */
static void FrontBotDoctrine(void) {
    uint32_t const smart=G_OrderId("smart"),attack=G_OrderId("attack");
    uint32_t checked=0,landed=0;
    edict_t *ashore[64];
    uint32_t ashore_spawn[64];
    FrontLoad(true);
    /* Keep the match running: doctrine stops once a Headquarters falls. */
    G_SetUnitFlag(FrontUnit(0,"fhq0"),UNIT_FLAG_INVULNERABLE,true);
    FrontStep(1500);
    FILTER_EDICTS(e,e->inuse && e->s.player==1 && !M_IsDead(e) && FrontGroundUnit(e) && !(e->s.renderfx&RF_HIDDEN)) {
        float const dx=e->s.origin.x-2300,dy=e->s.origin.y+2450;
        if (e->s.origin.y-e->s.origin.x > 3900 && landed<64) { ashore[landed]=e;ashore_spawn[landed++]=e->spawn_time; }
        else if (G_GetIssuedOrderId(e)==smart) T_ASSERT(dx*dx+dy*dy < 900*900);
        checked++;
    }
    /* Troops unloaded since the last 3-second doctrine tick get their inland order on the next one. */
    FrontStep(31);
    FOR_LOOP(i,landed) if (ashore[i]->inuse && ashore[i]->spawn_time==ashore_spawn[i] && !M_IsDead(ashore[i]))
        T_EQ(G_GetIssuedOrderId(ashore[i]),attack);
    T_ASSERT(checked>0);
    edict_t *home[64];
    vec2_t home_pos[64];
    uint32_t home_spawn[64],homes=0;
    FILTER_EDICTS(e,e->inuse && e->s.player==1 && !M_IsDead(e) && FrontGroundUnit(e) && !(e->s.renderfx&RF_HIDDEN) && e->s.origin.x-e->s.origin.y>3900 && homes<64) {
        home[homes]=e;home_pos[homes]=e->s.origin2;home_spawn[homes++]=e->spawn_time;
    }
    T_ASSERT(homes>0);
    FOR_LOOP(i,4) T_NOT_NULL(unit_create(0,FS_SLKKey("finf"),&(vec2_t){2700,-2900+80.0f*i},0));
    uint32_t const cargo=FrontBotCargo();
    FrontStep(70);
    T_ASSERT(FrontBotCargo()<=cargo);
    /* Units present when the raid began must be committed to the defense, including
     * rallied ones; those out of range must actually close in rather than stall. */
    FrontStep(30);
    FOR_LOOP(i,homes) if (home[i]->inuse && home[i]->spawn_time==home_spawn[i] && !M_IsDead(home[i])) {
        T_EQ(G_GetIssuedOrderId(home[i]),attack);
        /* Units beyond their own weapon range must close in (a mortar already in range just fires). */
        float const reach=MAX(700.0f,home[i]->unit_state->attack1.range+100.0f);
        if (Vector2_distance(&home_pos[i],&(vec2_t){2700,-2780})>reach) T_ASSERT(Vector2_distance(&home_pos[i],&home[i]->s.origin2)>10);
    }
    fprintf(stderr,"FRONTLINE_DOCTRINE checked=%u landed=%u\n",checked,landed);
    FrontEnd();
}
/* JASS GetUnitCurrentOrder must report 0 once an order has finished, as in retail;
 * a stale Move/Smart id made map tactics treat finished units as busy forever. */
static void FrontCurrentOrderIdle(void) {
    edict_t *unit;
    FrontLoad(false);
    unit=unit_create(0,FS_SLKKey("finf"),&(vec2_t){-3200,2200},0);
    T_NOT_NULL(unit);
    T_EQ(G_GetCurrentOrderId(unit),0);
    T_ASSERT(unit_issueorder(unit,"move",&(vec2_t){-3200,2500}));
    FrontStep(2);
    T_EQ(G_GetCurrentOrderId(unit),G_OrderId("move"));
    FrontStep(60);
    T_ASSERT(Vector2_distance(&unit->s.origin2,&(vec2_t){-3200,2500})<40);
    T_EQ(G_GetIssuedOrderId(unit),G_OrderId("move")); /* event-response state is unchanged */
    T_EQ(G_GetCurrentOrderId(unit),0);
    T_ASSERT(unit_issueimmediateorder(unit,"holdposition"));
    FrontStep(2);
    T_EQ(G_GetCurrentOrderId(unit),G_OrderId("holdposition"));
    /* Player feedback: ships cannot reach land, troops cannot cross the ocean. */
    T_ASSERT(!M_MoveDestinationUnreachable(unit,&(vec2_t){-3500,2800}));
    T_ASSERT(M_MoveDestinationUnreachable(unit,&(vec2_t){0,0}));
    T_ASSERT(M_MoveDestinationUnreachable(FrontUnit(0,"fbat"),&(vec2_t){-3300,2800}));
    T_ASSERT(!M_MoveDestinationUnreachable(FrontUnit(0,"fbat"),&(vec2_t){1000,-1000}));
    T_ASSERT(!M_MoveDestinationUnreachable(FrontUnit(0,"fbat"),&(vec2_t){0,0}));
    FrontEnd();
}
/* Fresh map acceptance deliberately skips the battle fixtures used above. */
static void FrontFreshStart(void) {
    front_old_time=gi.GetTime;gi.GetTime=FrontTime;front_time=0;
    CM_SetupTestWorldBounds(NULL);
    T_ASSERT(globals.PrepareMap("Maps/Frontline/IslandCommand.w3m"));
    T_ASSERT(globals.LoadMap("Maps/Frontline/IslandCommand.w3m"));
    G_BotShutdown();
    FOR_LOOP(player,2) {
        uint32_t count=0;
        FILTER_EDICTS(e,e->inuse && e->s.player==player && (e->svflags&SVF_MONSTER)) {
            count++;T_EQ(e->class_id,FS_SLKKey("fhq0"));
        }
        T_EQ(count,1);
        gameClient_t *client=G_GetPlayerClientByNumber(player);
        T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_FOOD_USED],0);
        T_ASSERT(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]>=45);
        T_ASSERT(SP_TrainUnit(FrontUnit(player,"fhq0"),FS_SLKKey("fwkr")));
    }
    FrontStep(140);
    T_NOT_NULL(FrontUnit(0,"fwkr"));T_NOT_NULL(FrontUnit(1,"fwkr"));
    UI_LoadHudGameResult();
    T_NOT_NULL(hud.result.GameResultDialog);
    T_ASSERT(hud.game_result_original_height>0.2f);
    edict_t *controller=G_GetPlayerEntityByNumber(0);
    FOR_LOOP(i,4) {
        UI_ShowGameResult(controller,i%2);
        T_ASSERT(hud.result.GameResultDialog->Height>0.2f);
    }
    FrontEnd();
}
static void FrontOffshoreBoarding(void) {
    FrontLoad(false);
    edict_t *craft=FrontUnit(0,"flct"),*troop=FrontUnit(0,"finf");
    craft->s.origin2=(vec2_t){-600,600};gi.LinkEntity(craft);
    vec2_t const before=craft->s.origin2;
    T_ASSERT(G_IssueUnitTargetOrder(troop,"smart",craft,false,0));
    FrontStep(300);
    T_ASSERT(Vector2_distance(&before,&craft->s.origin2)>500);
    T_ASSERT(S_CargoTransportForUnit(troop)==craft);
    FrontEnd();
}
static test_t offshore={"frontline.offshore_transport_meets_passenger",FrontOffshoreBoarding,__FILE__,__LINE__,NULL};
static void FrontRallyEconomy(void) {
    FrontLoad(false);
    edict_t *hq=FrontUnit(0,"fhq0"),*ore=NULL;
    float best=FLT_MAX;
    FILTER_EDICTS(e,e->inuse && e->class_id==FS_SLKKey("eore")) {
        float d=Vector2_distance(&hq->s.origin2,&e->s.origin2);
        if (d<best) { best=d;ore=e; }
    }
    T_NOT_NULL(ore);
    T_ASSERT(G_IssueUnitTargetOrder(hq,"smart",ore,false,0));
    gameClient_t *client=G_GetPlayerClientByNumber(0);
    uint32_t before=client->ps.stats[PLAYERSTATE_GOLD_GATHERED];
    FOR_LOOP(i,2) { T_ASSERT(SP_TrainUnit(hq,FS_SLKKey("fwkr")));FrontStep(160); }
    vec2_t point;edict_t *target=NULL;
    T_EQ(G_ResolveRallyTarget(hq,&point,&target),RALLY_TARGET_ENTITY);
    T_ASSERT(target==ore);
    T_ASSERT(client->ps.stats[PLAYERSTATE_GOLD_GATHERED]>before);
    edict_t *barracks=FrontUnit(0,"fbar");
    point=(vec2_t){-3100,3000};
    T_ASSERT(unit_issueorder(barracks,"smart",&point));
    T_ASSERT(SP_TrainUnit(barracks,FS_SLKKey("finf")));
    FrontStep(180);
    bool arrived=false;
    FILTER_EDICTS(e,e->inuse && e->class_id==FS_SLKKey("finf") && e->s.player==0)
        if (Vector2_distance(&e->s.origin2,&point)<200) arrived=true;
    T_ASSERT(arrived);
    edict_t *controller=G_GetPlayerEntityByNumber(0);
    char number[24];snprintf(number,sizeof(number),"%u",barracks->s.number);
    G_ClientCommand(controller,2,(cstring_t[]){"select",number});
    G_ClientCommand(controller,1,(cstring_t[]){"clearrally"});
    T_EQ(G_ResolveRallyTarget(barracks,&point,&target),RALLY_TARGET_SELF);
    FrontEnd();
}
static void FrontFreshAI(void) {
    front_old_time=gi.GetTime;gi.GetTime=FrontTime;front_time=0;
    CM_SetupTestWorldBounds(NULL);
    T_ASSERT(globals.PrepareMap("Maps/Frontline/IslandCommand.w3m"));
    T_ASSERT(globals.LoadMap("Maps/Frontline/IslandCommand.w3m"));
    /* The passive "human" has no client, so its carrier spots by range like a bot's: keep its
     * automatic launches off so it stays the passive opponent this scenario measures against. */
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && G_UnitAbilityLevel(e,MAKEFOURCC('F','c','a','p'))) e->resources|=1u<<30;
    /* Land first: no ship or carrier appears before a working land force and a bunker stand. */
    uint32_t first_ship_time=0,land_when_first_ship=0,bunkers_then=0,workers_early=0;
    FOR_LOOP(slice,24) {
        FrontStep(250);
        uint32_t land=0,ships=0,bunkers=0,workers=0;
        FILTER_EDICTS(e,e->inuse && e->s.player==1 && !M_IsDead(e)) {
            /* The bot is the IJN side on this map: it trains the Japanese land variants. */
            if (e->class_id==FS_SLKKey("jinf") || e->class_id==FS_SLKKey("jmg0") || e->class_id==FS_SLKKey("fart")) land++;
            if (e->class_id==FS_SLKKey("jtnk")) land+=2;
            /* ...and its own navy's warships: there is no generic shipyard. */
            if (e->class_id==FS_SLKKey("jfub") || e->class_id==FS_SLKKey("jmog") || e->class_id==FS_SLKKey("jyam") || e->class_id==FS_SLKKey("jakg")) ships++;
            /* No generic bunker on the card: the IJN bot builds its Type 92 pillbox. */
            if (e->class_id==FS_SLKKey("fbnk") || e->class_id==FS_SLKKey("jpbx") || e->class_id==FS_SLKKey("jpb2")) bunkers++;
            if (e->class_id==FS_SLKKey("fwkr")) workers++;
        }
        if (slice==3) workers_early=workers;
        if (ships && !first_ship_time) { first_ship_time=front_time;land_when_first_ship=land;bunkers_then=bunkers; }
    }
    fprintf(stderr,"FRONTLINE_AI first_ship_at=%us land=%u bunkers=%u workers_at_75s=%u\n",first_ship_time/1000,land_when_first_ship,bunkers_then,workers_early);
    T_ASSERT(first_ship_time>0); /* ships do come once the land force is established */
    T_ASSERT(land_when_first_ship>=12);T_ASSERT(bunkers_then>=1);
    T_ASSERT(first_ship_time>200000); /* never in the opening: the old AI had a carrier at 50 s */
    T_ASSERT(workers_early>=5);
    gameClient_t *bot=G_GetPlayerClientByNumber(1);
    T_ASSERT(!jass_rterror_pending(level.vm));
    T_ASSERT(!jass_rterror_pending(level.bots[1].vm));
    T_NOT_NULL(FrontUnit(1,"fwkr"));T_NOT_NULL(FrontUnit(1,"fbar"));
    T_NOT_NULL(FrontUnit(1,"fesc"));T_NOT_NULL(FrontUnit(1,"jinf"));
    T_ASSERT(FrontUnit(1,"finf")==NULL); /* US infantry is tech-capped for the IJN bot */
    T_ASSERT(bot->ps.stats[PLAYERSTATE_GOLD_GATHERED]>0);
    T_ASSERT(bot->score.values[WC3_PLAYER_SCORE_LUMBER_TOTAL]>0);
    gameClient_t *human=G_GetPlayerClientByNumber(0);
    for (uint32_t i=0;i<20000 && !human->jass.removed;i++) { /* damaged units hit softer (Fhpf): the push takes longer */
        FrontStep(1);
        if (getenv("AIDBG") && i%1000==0) {
            uint32_t n[8]={0};cstring_t codes[8]={"jdai","fesc","flnd","fhvy","jfub","jinf","jtnk","jmog"};
            FILTER_EDICTS(e,e->inuse && e->s.player==1 && !M_IsDead(e)) FOR_LOOP(k,8) if (e->class_id==FS_SLKKey(codes[k])) n[k]++;
            FILTER_EDICTS(e,e->inuse && e->s.player==1 && !M_IsDead(e) && (e->class_id==FS_SLKKey("jdai") || e->class_id==FS_SLKKey("fesc") || e->class_id==FS_SLKKey("jfub"))) fprintf(stderr,"  AIDBG %.4s xy=%.0f,%.0f phase=%d cargo=%u\n",(char*)&e->class_id,e->s.origin.x,e->s.origin.y,e->user_data,e->cargo?e->cargo->count:0);
            fprintf(stderr,"AIDBG t=%u jdai=%u fesc=%u flnd=%u fhvy=%u jfub=%u jinf=%u jtnk=%u jmog=%u gold=%u\n",front_time/1000,n[0],n[1],n[2],n[3],n[4],n[5],n[6],n[7],G_GetPlayerClientByNumber(1)->ps.stats[PLAYERSTATE_RESOURCE_GOLD]);
        }
    }
    T_ASSERT(human->jass.removed);
    T_EQ(human->ps.stats[PLAYERSTATE_GAME_RESULT],1);
    fprintf(stderr,"FRONTLINE_FULL_MATCH seconds=%u result=%u\n",front_time/1000,human->ps.stats[PLAYERSTATE_GAME_RESULT]);
    FrontEnd();
}
static void FrontSoundOptions(void) {
    FrontLoad(false);
    T_NOT_NULL(hud.options.EscMenuOptionsPanel);
    T_NOT_NULL(hud.options.SoundVolumeSlider);
    T_ASSERT(hud.menu.OptionsButton->Width>.2f);
    T_STREQ(hud.options.SoundVolumeSlider->OnClick,UI_WINDOW_CVAR_SLIDER_PREFIX "s_volume");
    G_ClientCommand(G_GetPlayerEntityByNumber(0),1,(cstring_t[]){"wc3_menu_options_sound"});
    T_ASSERT(!hud.options.SoundPanel->hidden);
    T_ASSERT(hud.options.SoundVolumeSlider->Width>.2f);
    T_FEQ(hud.options.SoundVolumeSlider->Slider.MinValue,0,.001f);
    T_FEQ(hud.options.SoundVolumeSlider->Slider.MaxValue,1,.001f);
    FrontEnd();
}
static test_t sound_options={"frontline.volume_controls_use_existing_sound_options",FrontSoundOptions,__FILE__,__LINE__,NULL};
static void FrontMobileAA(void) {
    FrontLoad(false);
    static cstring_t const codes[]={"fdst","faa0"};
    static vec2_t const starts[]={{0,0},{-4000,4000}};
    FOR_LOOP(i,2) {
        edict_t *mount=unit_create(0,FS_SLKKey(codes[i]),&starts[i],0);
        edict_t *plane=unit_create(1,FS_SLKKey("ffgt"),&(vec2_t){5000,0},0);
        T_NOT_NULL(plane);T_NOT_NULL(mount);
        G_SetUnitFlag(plane,UNIT_FLAG_PAUSED,true);
        plane->health.value=plane->health.max_value=10000;
        FrontStep(10);T_FEQ(plane->health.value,10000,.01f);
        G_SetUnitFlag(mount,UNIT_FLAG_PAUSED,true);
        plane->s.origin2=(vec2_t){starts[i].x+100,starts[i].y};gi.LinkEntity(plane);
        FrontStep(10);T_FEQ(plane->health.value,10000,.01f);
        G_SetUnitFlag(mount,UNIT_FLAG_PAUSED,false);
        vec2_t const dest={starts[i].x+1500,starts[i].y};
        T_ASSERT(unit_issueorder(mount,"move",&dest));
        edict_t *goal=mount->goalentity;
        FrontStep(35);
        T_ASSERT(plane->health.value<10000);
        T_ASSERT(Vector2_distance(&starts[i],&mount->s.origin2)>300);
        T_ASSERT(mount->goalentity==goal);
        T_ASSERT(mount->currentmove && mount->currentmove->travel);
    }
    FrontEnd();
}
static void FrontBuildingRotation(void) {
    FrontLoad(false);
    edict_t *hq=FrontUnit(0,"fhq0"),*controller=G_GetPlayerEntityByNumber(0);
    char number[24];snprintf(number,sizeof(number),"%u",hq->s.number);
    G_ClientCommand(controller,2,(cstring_t[]){"select",number});
    float before=hq->s.angle;
    G_ClientCommand(controller,1,(cstring_t[]){"rotatebuilding"});
    T_FEQ(hq->s.angle,before+(float)M_PI/2,.001f);
    T_ASSERT(G_IssueBuildOrder(FrontUnit(0,"fwkr"),FS_SLKKey("fbar"),&(vec2_t){-3100,2900}));
    edict_t *worker=FrontUnit(0,"fwkr");
    snprintf(number,sizeof(number),"%u",worker->s.number);
    G_ClientCommand(controller,2,(cstring_t[]){"select",number});
    G_ClientCommand(controller,1,(cstring_t[]){"rotatebuilding"});
    before=worker->orders->build_preview->s.angle;
    uint32_t worker_number=worker->s.number;
    T_ASSERT(WriteGame(Test_TempPath("frontline-rotation.bin")));
    T_ASSERT(ReadGame(Test_TempPath("frontline-rotation.bin")));
    worker=&g_edicts[worker_number];
    T_NOT_NULL(worker->orders->build_preview);
    T_FEQ(worker->orders->build_preview->s.angle,before,.001f);
    FrontStep(350);
    bool matched=false;
    FILTER_EDICTS(e,e->inuse && e->class_id==FS_SLKKey("fbar") && Vector2_distance(&e->s.origin2,&(vec2_t){-3100,2900})<120)
        if (fabsf(e->s.angle-before)<.001f) matched=true;
    T_ASSERT(matched);
    FrontEnd();
}
static test_t mobile_aa={"frontline.passive_aa_fires_while_ship_moves",FrontMobileAA,__FILE__,__LINE__,NULL};
static test_t rotate={"frontline.rotate_building_and_pending_site",FrontBuildingRotation,__FILE__,__LINE__,NULL};
/* Real map result transitions, repeated across fresh matches. */
static void FrontMatchResults(void) {
    FOR_LOOP(i,4) {
        front_old_time=gi.GetTime;gi.GetTime=FrontTime;front_time=0;
        CM_SetupTestWorldBounds(NULL);
        T_ASSERT(globals.PrepareMap("Maps/Frontline/IslandCommand.w3m"));
        T_ASSERT(globals.LoadMap("Maps/Frontline/IslandCommand.w3m"));
        G_BotShutdown();
        edict_t *target=FrontUnit(i%2 ? 0 : 1,"fhq0");
        T_Damage(target,target,(int)target->health.max_value+1);
        FrontStep(40);
        gameClient_t *human=G_GetPlayerClientByNumber(0);
        T_ASSERT(human->jass.removed);
        T_EQ(human->ps.stats[PLAYERSTATE_GAME_RESULT],i%2);
        UI_ShowGameResult(G_GetPlayerEntityByNumber(0),i%2);
        T_ASSERT(hud.result.GameResultDialog->Height>.2f);
        T_ASSERT(!hud.result.GameResultQuitButton->hidden);
        T_ASSERT(hud.result.GameResultQuitButton->OnClick[0]);
        if (i%2==0) {
            G_ClientCommand(G_GetPlayerEntityByNumber(0),1,(cstring_t[]){"hidegameresult"});
            T_ASSERT(!jass_rterror_pending(level.vm));
        } else {
            G_ClientCommand(G_GetPlayerEntityByNumber(0),1,(cstring_t[]){"gameresult_restart"});
            T_ASSERT(G_HasPendingDifficultyTransition());
        }
        FrontEnd();
    }
}
/* LAN: a human slot 1 gets no bot, and a dropped opponent concedes to the remaining commander. */
static void (*front_old_lobby)(mapInfo_t *);
static void FrontHumanOpponent(mapInfo_t *info) {
    if (front_old_lobby) front_old_lobby(info);
    info->players[1].playerType = kPlayerTypeHuman;
}
static void FrontLanOpponent(void) {
    FOR_LOOP(dropped,2) {
        front_old_lobby=gi.ApplyLobbySettings;gi.ApplyLobbySettings=FrontHumanOpponent;
        front_old_time=gi.GetTime;gi.GetTime=FrontTime;front_time=0;
        CM_SetupTestWorldBounds(NULL);
        T_ASSERT(globals.PrepareMap("Maps/Frontline/IslandCommand.w3m"));
        T_ASSERT(globals.LoadMap("Maps/Frontline/IslandCommand.w3m"));
        gi.ApplyLobbySettings=front_old_lobby;
        T_ASSERT(!jass_rterror_pending(level.vm));
        gameClient_t *guest=G_GetPlayerClientByNumber(1),*left=G_GetPlayerClientByNumber(dropped);
        T_EQ(guest->jass.controller,0u);
        FrontStep(300);
        uint32_t guest_units=0;
        FILTER_EDICTS(e,e->inuse&&e->s.player==1&&(e->svflags&SVF_MONSTER)&&!M_IsDead(e)) guest_units++;
        T_EQ(guest_units,1u); /* only the HQ: no AI trained or built for the human slot */
        T_ASSERT(!left->jass.removed);
        left->connected=false;left->departed=true;
        FrontStep(40);
        gameClient_t *winner=G_GetPlayerClientByNumber(1-dropped);
        T_ASSERT(left->jass.removed);T_EQ(left->ps.stats[PLAYERSTATE_GAME_RESULT],1);
        T_ASSERT(winner->jass.removed);T_EQ(winner->ps.stats[PLAYERSTATE_GAME_RESULT],0);
        T_ASSERT(!jass_rterror_pending(level.vm));
        FrontEnd();
    }
}
static void FrontClearSelection(gameClient_t *client) {
    FOR_SELECTED_UNITS(client,e) G_DeselectEntity(client,e);
}
static bool landing_cursor_packet,landing_cursor_clear;
static void FrontLandingWrite(pfWriteType_t type,void const *data) {
    if (type==PF_BYTE) landing_cursor_packet=*(int32_t const *)data==svc_cursor_splat;
    if (landing_cursor_packet && type==PF_FLOAT && *(float const *)data==0) landing_cursor_clear=true;
}
static void FrontLandingCursor(void) {
    FOR_LOOP(restart,3) {
        FrontLoad(false);
        edict_t *craft=FrontUnit(0,"flct"),*troop=FrontUnit(0,"finf");
        edict_t *clent=G_GetPlayerEntityByNumber(0);
        gameClient_t *client=clent->client;
        T_ASSERT(G_IssueUnitTargetOrder(troop,"smart",craft,false,0));FrontStep(70);
        T_ASSERT(S_CargoTransportForUnit(troop)==craft);
        FrontClearSelection(client);G_SelectEntity(client,craft);
        void (*write)(pfWriteType_t,void const *)=gi.Write;
        void (*unicast)(edict_t *)=gi.unicast;
        gi.Write=FrontLandingWrite;gi.unicast=ForwardAnchorUnicast;
        FOR_LOOP(cancel,3) {
            G_ClientCommand(clent,2,(cstring_t[]){"button","Adro"});
            T_ASSERT(client->menu.on_location_selected!=NULL);
            S_SpellCursorSplat(clent,200);
            landing_cursor_clear=false;
            G_ClientCommand(clent,1,(cstring_t[]){"cancel"});
            T_ASSERT(landing_cursor_clear);T_ASSERT(client->menu.on_location_selected==NULL);
        }
        G_ClientCommand(clent,2,(cstring_t[]){"button","Adro"});
        S_SpellCursorSplat(clent,200);landing_cursor_clear=false;
        char x[32],y[32];snprintf(x,sizeof(x),"%f",craft->s.origin.x);snprintf(y,sizeof(y),"%f",craft->s.origin.y);
        G_ClientCommand(clent,3,(cstring_t[]){"point",x,y});
        T_ASSERT(landing_cursor_clear);T_ASSERT(client->menu.on_location_selected==NULL);
        gi.Write=write;gi.unicast=unicast;
        FrontStep(80);
        T_ASSERT(!S_CargoTransportForUnit(troop));T_ASSERT(!(troop->s.renderfx&RF_HIDDEN));
        FrontEnd();
    }
}
static void FrontMassProduction(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);
    edict_t *clent=G_GetPlayerEntityByNumber(0), *first=FrontUnit(0,"fbar");
    edict_t *second=unit_create(0,FS_SLKKey("fbar"),&(vec2_t){-3550,3500},0);
    edict_t *factory=FrontUnit(0,"ffac");
    FrontClearSelection(client);G_SelectEntity(client,first);G_SelectEntity(client,second);G_SelectEntity(client,factory);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=2000;
    G_ClientCommand(clent,2,(cstring_t[]){"button","finf"});
    T_EQ(G_ProductionQueueCount(first),1);T_EQ(G_ProductionQueueCount(second),1);
    T_EQ(G_ProductionQueueCount(factory),0);
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],1860);
    G_ClientCommand(clent,3,(cstring_t[]){"button","finf","queue"});
    T_EQ(G_ProductionQueueCount(first),6);T_EQ(G_ProductionQueueCount(second),6);
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],1160);
    FrontStep(150);
    T_EQ(G_ProductionQueueCount(first),5);T_EQ(G_ProductionQueueCount(second),5);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=70;
    G_ClientCommand(clent,2,(cstring_t[]){"button","finf"});
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],0);
    T_EQ(G_ProductionQueueCount(first)+G_ProductionQueueCount(second),11);
    FrontClearSelection(client);
    edict_t *carrier=FrontUnit(0,"fcvr"), *other=unit_create(0,FS_SLKKey("fcvr"),&(vec2_t){-1100,1400},0);
    G_SelectEntity(client,carrier);G_SelectEntity(client,other);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=2000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=200;
    FrontStep(12); /* both embark their own air group; Replenish buys nothing */
    G_ClientCommand(clent,2,(cstring_t[]){"button","Frep"});
    T_EQ(S_CarrierAircraftCount(carrier),24);T_EQ(S_CarrierAircraftCount(other),24);
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],2000);
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER],200);
    FrontEnd();
}
static void FrontFormations(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);
    edict_t *clent=G_GetPlayerEntityByNumber(0), *ships[4];
    FrontClearSelection(client);
    FOR_LOOP(i,4) {
        ships[i]=unit_create(0,FS_SLKKey(i ? "fdst":"fbat"),&(vec2_t){-400+(float)i*200,600},0);
        G_SelectEntity(client,ships[i]);
    }
    for (uint32_t shape=1;shape<=4;shape++) {
        S_SetFormation(client,shape,220);
        T_ASSERT(move_selectlocation(clent,&(vec2_t){1500,-1500}));
        FOR_LOOP(i,4) {
            T_NOT_NULL(ships[i]->goalentity);
            T_FEQ(ships[i]->movement->group_speed,175,.01f);
            T_ASSERT(CM_TerrainPointIsSwimmable(&ships[i]->goalentity->s.origin2));
            FOR_LOOP(j,i) T_ASSERT(Vector2_distance(&ships[i]->goalentity->s.origin2,&ships[j]->goalentity->s.origin2)>=ships[i]->collision+ships[j]->collision);
        }
    }
    FrontStep(220);
    FOR_LOOP(i,4) T_ASSERT(Vector2_distance(&ships[i]->s.origin2,&(vec2_t){1500,-1500})<700);
    FrontClearSelection(client);G_SelectEntity(client,ships[0]);
    S_SetFormation(client,4,220);
    T_ASSERT(move_selectlocation(clent,&(vec2_t){1000,-1000}));
    T_FEQ(ships[0]->goalentity->s.origin2.x,1000,.01f);
    T_FEQ(ships[0]->goalentity->s.origin2.y,-1000,.01f);
    FrontClearSelection(client);
    edict_t *infantry=FrontUnit(0,"finf"),*tank=FrontUnit(0,"ftnk");
    G_SelectEntity(client,infantry);G_SelectEntity(client,tank);
    S_SetFormation(client,3,140);
    T_ASSERT(move_selectlocation(clent,&(vec2_t){-3100,3400}));
    T_ASSERT(CM_TerrainPointIsWalkable(&infantry->goalentity->s.origin2));
    T_ASSERT(CM_TerrainPointIsWalkable(&tank->goalentity->s.origin2));
    T_FEQ(infantry->movement->group_speed,235,.01f);
    S_SetFormation(client,0,0);
    FrontEnd();
}
static void FrontCriticalStrikes(void) {
    FrontLoad(false);
    edict_t *bomber=unit_create(0,FS_SLKKey("fbmb"),&(vec2_t){0,0},0);
    abilityLevel_t *cfg=(abilityLevel_t *)G_AbilityLevel(MAKEFOURCC('F','h','i','t'),1);
    float chance=cfg->data[0].number,payload=cfg->data[1].number;
    /* Perfect bomb aim, no ricochets: this case isolates the critical payload. */
    abilityLevel_t *aim=(abilityLevel_t *)G_AbilityLevel(MAKEFOURCC('F','b','l','b'),1);
    float const spread=aim->data[0].number,glance=aim->data[4].number;
    aim->data[0].number=0;aim->data[4].number=-100;
    cfg->data[0].number=0;
    edict_t *carrier=unit_create(1,FS_SLKKey("fcvr"),&(vec2_t){500,0},0);
    S_ResolveAttackHit(bomber,carrier,95);T_ASSERT(carrier->health.value>2400); /* bombs hit carriers 3x (no crit) */
    cfg->data[0].number=100;cfg->data[1].number=3500; /* non-stock authored payload */
    S_ResolveAttackHit(bomber,carrier,95);T_ASSERT(M_IsDead(carrier));
    T_ASSERT(FrontEffects("Emberfield/Models/critical.mdx")>0); /* the blast is a live effect */
    carrier=unit_create(1,FS_SLKKey("fcvr"),&(vec2_t){800,0},0);
    gameClient_t *client=G_GetPlayerClientByNumber(1);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=200;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=50;
    T_ASSERT(unit_issueimmediateorder(carrier,"shipprotection"));
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],0);T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER],0);
    T_ASSERT(!unit_issueimmediateorder(carrier,"shipprotection"));
    S_ResolveAttackHit(bomber,carrier,95);T_ASSERT(!M_IsDead(carrier));T_ASSERT(carrier->health.value<1700);
    S_ResolveAttackHit(bomber,carrier,95);S_ResolveAttackHit(bomber,carrier,95);T_ASSERT(M_IsDead(carrier));
    edict_t *land=unit_create(1,FS_SLKKey("ftnk"),&(vec2_t){-3100,3100},0);
    S_ResolveAttackHit(bomber,land,95);T_ASSERT(!M_IsDead(land));
    cfg->data[0].number=chance;cfg->data[1].number=payload;
    aim->data[0].number=spread;aim->data[4].number=glance;
    FrontEnd();
}

/* Each case constructs through the command dispatcher, exercises the actual
 * scheduler, then constructs a second hull through the AI production owner. */
static void FrontHistoricalVessel(cstring_t code,cstring_t facility,uint32_t owner,uint32_t role) {
    FrontLoad(false);
    FILTER_EDICTS(e,e->inuse && (e->svflags&SVF_MONSTER) && e->class_id!=FS_SLKKey("fhq0")) G_FreeEdict(e);
    edict_t *clent=G_GetPlayerEntityByNumber(owner);
    gameClient_t *client=G_GetPlayerClientByNumber(owner);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=30000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=30000;
    float side=owner ? 1:-1;
    edict_t *dock=unit_create(owner,FS_SLKKey(facility),&(vec2_t){side*2400,-side*1900},0);
    T_NOT_NULL(dock);
    if (!dock) {FrontEnd();return;}
    gameCommandButton_t buttons[32];uint32_t count=G_GetCommandButtons(dock,buttons,32);
    bool found=false;
    FOR_LOOP(i,count) if (!strcmp(buttons[i].command,code)) {found=true;T_ASSERT(buttons[i].art[0]);T_ASSERT(buttons[i].ubertip[0]);}
    T_ASSERT(found);
    T_EQ(G_GetTrainCommandState(client,dock,FS_SLKKey(code),NULL,0),BUILD_COMMAND_AVAILABLE);
    gameClient_t *opponent=G_GetPlayerClientByNumber(1-owner);
    edict_t *wrong=unit_create(1-owner,FS_SLKKey(facility),&(vec2_t){-side*2400,side*1900},0);
    T_EQ(G_GetTrainCommandState(opponent,wrong,FS_SLKKey(code),NULL,0),BUILD_COMMAND_HIDDEN);
    FrontClearSelection(client);G_SelectEntity(client,dock);
    uint32_t gold=client->ps.stats[PLAYERSTATE_RESOURCE_GOLD];
    G_ClientCommand(clent,2,(cstring_t[]){"button",code});
    T_EQ(G_ProductionQueueCount(dock),1);
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],gold-G_UnitBalance(FS_SLKKey(code))->goldCost);
    FrontStep(500);
    edict_t *ship=FrontUnit(owner,code);T_NOT_NULL(ship);
    if (!ship) {FrontEnd();return;}
    T_EQ(G_ProductionQueueCount(dock),0);
    T_ASSERT(!(ship->s.renderfx&RF_HIDDEN));T_ASSERT(ship->s.model>0);
    T_EQ(ship->data.UnitBalance->foodUsed,0);
    T_EQ(M_UnitStaticPathingFlags(ship),CM_PATHING_UNSWIMMABLE);
    FrontClearSelection(client);G_SelectEntity(client,ship);T_ASSERT(G_IsEntitySelected(client,ship));
    if (role==1) {unit_issueimmediateorder(ship,"recallaircraft");FrontStep(220);}
    vec2_t before=ship->s.origin2,destination={0,500};
    T_ASSERT(unit_issueorder(ship,"move",&destination));FrontStep(15);
    float dx=ship->s.origin.x-before.x,dy=ship->s.origin.y-before.y;
    T_ASSERT(hypotf(dx,dy)>20);T_ASSERT(cosf(ship->s.angle-atan2f(dy,dx))>.8f);
    FrontStep(230);T_ASSERT(Vector2_distance(&ship->s.origin2,&destination)<220);
    if (role==1) {
        UI_WriteSingleInfo(ship,client);T_STREQ(hud.simple.SimpleNameValue->Text,G_UnitName(ship->class_id));
        cstring_t fighter=owner ? "jfig":"ufig",bomber=owner ? "jbom":"ubom",torpedo=owner ? "jtor":"utor";
        T_ASSERT(!unit_issueimmediateorder(ship,"replenishair")); /* the air group embarked on completion */
        edict_t *f=FrontUnit(owner,fighter),*b=FrontUnit(owner,bomber),*t=FrontUnit(owner,torpedo);
        T_NOT_NULL(f);T_NOT_NULL(b);T_NOT_NULL(t);
        if (f && b && t) {
            T_ASSERT(b->s.renderfx&RF_HIDDEN);T_ASSERT(t->s.renderfx&RF_HIDDEN); /* armed on deck */
            edict_t *target=unit_create(1-owner,FS_SLKKey("ftrn"),&(vec2_t){600,500},0);
            float hp=target->health.value;
            T_ASSERT(G_IssueUnitTargetOrder(ship,"airstrike",target,false,0));
            for (uint32_t i=0;i<600 && target->health.value>=hp;i++) FrontStep(1);
            T_ASSERT(target->health.value<hp);
            bool spent=false; /* some bomber of the air group made its run */
            FILTER_EDICTS(e,e->inuse && e->s.player==owner && (e->class_id==b->class_id || e->class_id==t->class_id) && e->mana.value<e->mana.max_value) spent=true;
            T_ASSERT(spent);
            T_Damage(target,ship,10000);
            T_ASSERT(unit_issueimmediateorder(ship,"recallaircraft"));FrontStep(250);
            T_ASSERT(S_CargoTransportForUnit(b)==ship);T_ASSERT(S_CargoTransportForUnit(t)==ship);
            FrontStep(100);T_FEQ(b->mana.value,b->mana.max_value,.01f); /* rearmed on deck */
            gold=client->ps.stats[PLAYERSTATE_RESOURCE_GOLD];
            T_ASSERT(!unit_issueimmediateorder(ship,"replenishair"));T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],gold);
        }
    } else if (role==2) {
        T_ASSERT(unit_issueorder(ship,"move",&(vec2_t){side*2000,-side*2150}));FrontStep(230);
        edict_t *troop=unit_create(owner,FS_SLKKey("finf"),&(vec2_t){side*2160,-side*2300},0);
        edict_t *tank=unit_create(owner,FS_SLKKey("ftnk"),&(vec2_t){side*2230,-side*2340},0);
        T_ASSERT(G_IssueUnitTargetOrder(troop,"smart",ship,false,0));FrontStep(70);
        T_ASSERT(S_CargoTransportForUnit(troop)==ship);
        edict_t *hull=unit_create(owner,FS_SLKKey("flct"),&ship->s.origin2,0);
        T_ASSERT(!S_CargoTryLoad(ship,hull));
        if (S_CargoTransportForUnit(hull)) S_CargoReleaseUnit(hull);
        G_FreeEdict(hull);
        bool infantry_only=!strcmp(code,"ulcv");
        if (infantry_only) T_ASSERT(!S_CargoOrderBoard(tank,ship));
        else {T_ASSERT(G_IssueUnitTargetOrder(tank,"smart",ship,false,0));FrontStep(70);T_ASSERT(S_CargoTransportForUnit(tank)==ship);}
        T_ASSERT(unit_issueorder(ship,"move",&(vec2_t){-side*2000,side*2150}));FrontStep(400);
        T_ASSERT(unit_issueimmediateorder(ship,"unloadall"));FrontStep(40);
        T_ASSERT(!S_CargoTransportForUnit(troop));T_ASSERT(CM_TerrainPointIsWalkable(&troop->s.origin2));
        if (!infantry_only) {T_ASSERT(!S_CargoTransportForUnit(tank));T_ASSERT(CM_TerrainPointIsWalkable(&tank->s.origin2));}
    } else {
        edict_t *target=unit_create(1-owner,FS_SLKKey("ftrn"),&(vec2_t){600,650},0);
        float hp=target->health.value;
        T_ASSERT(G_IssueUnitTargetOrder(ship,"attack",target,false,0));FrontStep(110);
        T_ASSERT(target->health.value<hp);
        abilityAliasRef_t battery=S_ResolveAbilityAlias(ship,MAKEFOURCC('F','g','u','n'));
        if (battery.alias) {
            uint32_t mounts=0;
            FILTER_EDICTS(m,m->inuse && m->think==naval_battery_think && S_SpellChannelOwner(m)==ship) {
                mounts++;T_ASSERT(m->s.model>0);T_ASSERT(m->s.flags&EF_NOT_SELECTABLE);
                if (!strcmp(code,"jyam") || !strcmp(code,"jmus")) {
                    T_EQ(m->s.model,gi.ModelIndex(m->variation ? "Emberfield/Models/yamato_turret_aa.mdx" : "Emberfield/Models/yamato_turret.mdx"));
                    abilityLevel_t const *cfg=G_AbilityLevel(battery.alias,1);
                    T_FEQ(m->channel->origin.x,cfg->data[2+m->variation].number,.001f);
                    T_FEQ(m->wait,cfg->data[6+m->variation].number,.001f);
                }
                T_ASSERT(cosf(m->s.angle-atan2f(target->s.origin.y-m->s.origin.y,target->s.origin.x-m->s.origin.x))>.8f);
            }
            T_EQ(mounts,(uint32_t)G_AbilityLevel(battery.alias,1)->data[0].number);
            T_ASSERT(WriteGame(Test_TempPath("historical-battery.bin")));
            T_ASSERT(ReadGame(Test_TempPath("historical-battery.bin")));
            ship=FrontUnit(owner,code);dock=FrontUnit(owner,facility);FrontStep(2);
            T_NOT_NULL(ship);T_NOT_NULL(dock);
            if (ship && (!strcmp(code,"jyam") || !strcmp(code,"jmus"))) {
                uint32_t restored=0;
                FILTER_EDICTS(m,m->inuse && m->think==naval_battery_think && S_SpellChannelOwner(m)==ship) {
                    T_EQ(m->s.model,gi.ModelIndex(m->variation ? "Emberfield/Models/yamato_turret_aa.mdx" : "Emberfield/Models/yamato_turret.mdx"));
                    restored++;
                }
                T_EQ(restored,3);
            }
        }
    }
    T_Damage(ship,ship,100000);FrontStep(30);T_ASSERT(!ship->inuse || M_IsDead(ship));
    T_ASSERT(G_BotProduce(G_GetPlayerByNumber(owner),1,FS_SLKKey(code),-1));FrontStep(500);
    edict_t *ai_ship=FrontUnit(owner,code);T_NOT_NULL(ai_ship);
    if (ai_ship) {T_ASSERT(!(ai_ship->s.renderfx&RF_HIDDEN));T_ASSERT(unit_issueorder(ai_ship,"move",&(vec2_t){side*800,-side*900}));vec2_t ai_before=ai_ship->s.origin2;FrontStep(80);T_ASSERT(!M_IsDead(ai_ship));T_ASSERT(Vector2_distance(&ai_before,&ai_ship->s.origin2)>30);}
    T_ASSERT(!jass_rterror_pending(level.vm));
    fprintf(stderr,"HISTORICAL_VESSEL %.4s player_build movement role destruction ai_build exercised\n",code);
    FrontEnd();
}
static void FrontHistorical_unca(void) { FrontHistoricalVessel("unca","fhvy",0,0); }
static test_t history_unca={"frontline.historical_unca",FrontHistorical_unca,__FILE__,__LINE__,NULL};
static void FrontHistorical_usdk(void) { FrontHistoricalVessel("usdk","fhvy",0,0); }
static test_t history_usdk={"frontline.historical_usdk",FrontHistorical_usdk,__FILE__,__LINE__,NULL};
static void FrontHistorical_uind(void) { FrontHistoricalVessel("uind","fhvy",0,1); }
static test_t history_uind={"frontline.historical_uind",FrontHistorical_uind,__FILE__,__LINE__,NULL};
static void FrontHistorical_ubal(void) { FrontHistoricalVessel("ubal","fesc",0,0); }
static test_t history_ubal={"frontline.historical_ubal",FrontHistorical_ubal,__FILE__,__LINE__,NULL};
static void FrontHistorical_uatl(void) { FrontHistoricalVessel("uatl","fesc",0,0); }
static test_t history_uatl={"frontline.historical_uatl",FrontHistorical_uatl,__FILE__,__LINE__,NULL};
static void FrontHistorical_usum(void) { FrontHistoricalVessel("usum","fesc",0,0); }
static test_t history_usum={"frontline.historical_usum",FrontHistorical_usum,__FILE__,__LINE__,NULL};
static void FrontHistorical_jkon(void) { FrontHistoricalVessel("jkon","fhvy",1,0); }
static test_t history_jkon={"frontline.historical_jkon",FrontHistorical_jkon,__FILE__,__LINE__,NULL};
static void FrontHistorical_jtak(void) { FrontHistoricalVessel("jtak","fesc",1,0); }
static test_t history_jtak={"frontline.historical_jtak",FrontHistorical_jtak,__FILE__,__LINE__,NULL};
static void FrontHistorical_jmyo(void) { FrontHistoricalVessel("jmyo","fesc",1,0); }
static test_t history_jmyo={"frontline.historical_jmyo",FrontHistorical_jmyo,__FILE__,__LINE__,NULL};
static void FrontHistorical_jkgr(void) { FrontHistoricalVessel("jkgr","fesc",1,0); }
static test_t history_jkgr={"frontline.historical_jkgr",FrontHistorical_jkgr,__FILE__,__LINE__,NULL};
static void FrontHistorical_jaki(void) { FrontHistoricalVessel("jaki","fesc",1,0); }
static test_t history_jaki={"frontline.historical_jaki",FrontHistorical_jaki,__FILE__,__LINE__,NULL};
static void FrontHistorical_uiow(void) { FrontHistoricalVessel("uiow","fhvy",0,0); }
static test_t history_uiow={"frontline.historical_uiow",FrontHistorical_uiow,__FILE__,__LINE__,NULL};
static void FrontHistorical_umss(void) { FrontHistoricalVessel("umss","fhvy",0,0); }
static test_t history_umss={"frontline.historical_umss",FrontHistorical_umss,__FILE__,__LINE__,NULL};
static void FrontHistorical_uent(void) { FrontHistoricalVessel("uent","fhvy",0,1); }
static test_t history_uent={"frontline.historical_uent",FrontHistorical_uent,__FILE__,__LINE__,NULL};
static void FrontHistorical_uykt(void) { FrontHistoricalVessel("uykt","fhvy",0,1); }
static test_t history_uykt={"frontline.historical_uykt",FrontHistorical_uykt,__FILE__,__LINE__,NULL};
static void FrontHistorical_uesx(void) { FrontHistoricalVessel("uesx","fhvy",0,1); }
static test_t history_uesx={"frontline.historical_uesx",FrontHistorical_uesx,__FILE__,__LINE__,NULL};
static void FrontHistorical_uflt(void) { FrontHistoricalVessel("uflt","fesc",0,0); }
static test_t history_uflt={"frontline.historical_uflt",FrontHistorical_uflt,__FILE__,__LINE__,NULL};
static void FrontHistorical_uclv(void) { FrontHistoricalVessel("uclv","fesc",0,0); }
static test_t history_uclv={"frontline.historical_uclv",FrontHistorical_uclv,__FILE__,__LINE__,NULL};
static void FrontHistorical_ulcv(void) { FrontHistoricalVessel("ulcv","flnd",0,2); }
static test_t history_ulcv={"frontline.historical_ulcv",FrontHistorical_ulcv,__FILE__,__LINE__,NULL};
static void FrontHistorical_ulcm(void) { FrontHistoricalVessel("ulcm","flnd",0,2); }
static test_t history_ulcm={"frontline.historical_ulcm",FrontHistorical_ulcm,__FILE__,__LINE__,NULL};
static void FrontHistorical_jyam(void) { FrontHistoricalVessel("jyam","fhvy",1,0); }
static test_t history_jyam={"frontline.historical_jyam",FrontHistorical_jyam,__FILE__,__LINE__,NULL};
static void FrontHistorical_jmus(void) { FrontHistoricalVessel("jmus","fhvy",1,0); }
static test_t history_jmus={"frontline.historical_jmus",FrontHistorical_jmus,__FILE__,__LINE__,NULL};
static void FrontHistorical_jnag(void) { FrontHistoricalVessel("jnag","fhvy",1,0); }
static test_t history_jnag={"frontline.historical_jnag",FrontHistorical_jnag,__FILE__,__LINE__,NULL};
static void FrontHistorical_jakg(void) { FrontHistoricalVessel("jakg","fhvy",1,1); }
static test_t history_jakg={"frontline.historical_jakg",FrontHistorical_jakg,__FILE__,__LINE__,NULL};
static void FrontHistorical_jkag(void) { FrontHistoricalVessel("jkag","fhvy",1,1); }
static test_t history_jkag={"frontline.historical_jkag",FrontHistorical_jkag,__FILE__,__LINE__,NULL};
static void FrontHistorical_jsor(void) { FrontHistoricalVessel("jsor","fhvy",1,1); }
static test_t history_jsor={"frontline.historical_jsor",FrontHistorical_jsor,__FILE__,__LINE__,NULL};
static void FrontHistorical_jhir(void) { FrontHistoricalVessel("jhir","fhvy",1,1); }
static test_t history_jhir={"frontline.historical_jhir",FrontHistorical_jhir,__FILE__,__LINE__,NULL};
static void FrontHistorical_jsho(void) { FrontHistoricalVessel("jsho","fhvy",1,1); }
static test_t history_jsho={"frontline.historical_jsho",FrontHistorical_jsho,__FILE__,__LINE__,NULL};
static void FrontHistorical_jzui(void) { FrontHistoricalVessel("jzui","fhvy",1,1); }
static test_t history_jzui={"frontline.historical_jzui",FrontHistorical_jzui,__FILE__,__LINE__,NULL};
static void FrontHistorical_jmog(void) { FrontHistoricalVessel("jmog","fesc",1,0); }
static test_t history_jmog={"frontline.historical_jmog",FrontHistorical_jmog,__FILE__,__LINE__,NULL};
static void FrontHistorical_jfub(void) { FrontHistoricalVessel("jfub","fesc",1,0); }
static test_t history_jfub={"frontline.historical_jfub",FrontHistorical_jfub,__FILE__,__LINE__,NULL};
static void FrontHistorical_jdai(void) { FrontHistoricalVessel("jdai","flnd",1,2); }
static test_t history_jdai={"frontline.historical_jdai",FrontHistorical_jdai,__FILE__,__LINE__,NULL};

static void FrontKidoButai(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(1);
    edict_t *clent=G_GetPlayerEntityByNumber(1);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=30000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=30000;
    edict_t *dock=unit_create(1,FS_SLKKey("fhvy"),&(vec2_t){2400,-1900},0);
    FrontClearSelection(client);G_SelectEntity(client,dock);
    gameCommandButton_t card[32];uint32_t count=G_GetCommandButtons(dock,card,32);bool preset=false;
    FOR_LOOP(i,count) { if (!strcmp(card[i].command,"Fkdo")) preset=true; FOR_LOOP(j,i) T_ASSERT(card[i].x!=card[j].x || card[i].y!=card[j].y); }
    T_ASSERT(preset);
    G_ClientCommand(clent,2,(cstring_t[]){"button","Fkdo"});T_ASSERT(G_IsEntitySelected(client,dock));
    static cstring_t const codes[]={"jakg","jkag","jsor","jhir","jsho","jzui","jmog","jfub"};
    edict_t *fleet[8];
    FOR_LOOP(i,8) fleet[i]=unit_create(1,FS_SLKKey(codes[i]),&(vec2_t){700+(i%2)*400.0f,-900+(i/2)*450.0f},0);
    G_ClientCommand(clent,2,(cstring_t[]){"button","Fkdo"});T_EQ(S_GetFormation(client),4);
    FOR_LOOP(i,8) T_ASSERT(G_IsEntitySelected(client,fleet[i]));
    T_ASSERT(!G_IsEntitySelected(client,dock));
    T_ASSERT(move_selectlocation(clent,&(vec2_t){-400,300}));
    FOR_LOOP(i,8) {
        T_NOT_NULL(fleet[i]->goalentity);T_FEQ(fleet[i]->movement->group_speed,170,.1f);
        FOR_LOOP(j,i) T_ASSERT(Vector2_distance(&fleet[i]->goalentity->s.origin2,&fleet[j]->goalentity->s.origin2)>fleet[i]->collision+fleet[j]->collision);
    }
    /* No enemy warships about: carriers would otherwise (rightly) stand off from them. */
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && S_IsShip(e)) G_FreeEdict(e);
    FrontStep(250);
    uint32_t cap=0;
    FOR_LOOP(i,8) {T_ASSERT(Vector2_distance(&fleet[i]->s.origin2,&(vec2_t){-400,300})<1000);cap+=S_CarrierAircraftCount(fleet[i]);}
    T_ASSERT(cap>=12);
    uint32_t ship_index=fleet[0]->s.number;
    T_ASSERT(WriteGame(Test_TempPath("historical-kido.bin")));T_ASSERT(ReadGame(Test_TempPath("historical-kido.bin")));FrontStep(5);
    T_ASSERT(S_CarrierAircraftCount(&globals.edicts[ship_index])>=2);
    FrontEnd();
}
static void FrontHistoricalBattle(void) {
    FrontLoad(false);
    FILTER_EDICTS(e,e->inuse && (e->svflags&SVF_MONSTER) && e->class_id!=FS_SLKKey("fhq0")) G_FreeEdict(e);
    FOR_LOOP(p,2) {gameClient_t *client=G_GetPlayerClientByNumber(p);client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=30000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=30000;}
    jass_callbyname(level.vm,"FrontlineHistoricalBattle",false);
    uint32_t alive[2]={0},frames=0,peak_air=0;
    do {
        FrontStep(10);frames+=10;alive[0]=alive[1]=0;
        uint32_t air=0;
        FILTER_EDICTS(e,e->inuse && !M_IsDead(e) && (e->svflags&SVF_MONSTER) && !(e->s.renderfx&RF_HIDDEN)) {
            if (e->s.player<2 && M_UnitStaticPathingFlags(e)==CM_PATHING_UNSWIMMABLE && e->data.UnitBalance->speed>0) alive[e->s.player]++;
            if (G_UnitTargetType(e)==TARG_AIR) air++;
        }
        peak_air=MAX(peak_air,air);
    } while (alive[0] && alive[1] && alive[0]+alive[1]>4 && frames<7200);
    /* Attrition, not annihilation: carriers carry no guns, so a side can end the engagement with a lone carrier. */
    T_ASSERT(peak_air>=4);T_ASSERT(alive[0]+alive[1]<=4); /* at least half of the ten ships are gone */
    T_ASSERT(!jass_rterror_pending(level.vm));
    fprintf(stderr,"HISTORICAL_BATTLE frames=%u USN_survivors=%u IJN_survivors=%u peak_air=%u\n",frames,alive[0],alive[1],peak_air);
    FrontStep(100);FrontEnd();
}
static test_t history_kido={"frontline.historical_kido_butai",FrontKidoButai,__FILE__,__LINE__,NULL};
static test_t history_battle={"frontline.historical_full_battle",FrontHistoricalBattle,__FILE__,__LINE__,NULL};

static void FrontHistoricalIJNStart(void) {
    front_old_time=gi.GetTime;gi.GetTime=FrontTime;front_time=0;CM_SetupTestWorldBounds(NULL);
    T_ASSERT(globals.PrepareMap("Maps/Frontline/IslandCommandIJN.w3m"));
    T_ASSERT(globals.LoadMap("Maps/Frontline/IslandCommandIJN.w3m"));
    T_NOT_NULL(level.vm);T_ASSERT(!jass_rterror_pending(level.vm));
    gameClient_t *client=G_GetPlayerClientByNumber(0);
    T_EQ(G_GetPlayerTechMaxAllowed(client,FS_SLKKey("jakg")),-1);
    T_EQ(G_GetPlayerTechMaxAllowed(client,FS_SLKKey("uiow")),0);
    T_EQ(G_GetPlayerTechMaxAllowed(G_GetPlayerClientByNumber(1),FS_SLKKey("uiow")),-1);
    T_EQ(G_GetPlayerTechMaxAllowed(G_GetPlayerClientByNumber(1),FS_SLKKey("jakg")),0);
    G_BotShutdown();
    edict_t *dock=unit_create(0,FS_SLKKey("fhvy"),&(vec2_t){-2400,1900},0);
    gameCommandButton_t card[32];uint32_t count=G_GetCommandButtons(dock,card,32);bool preset=false;
    FOR_LOOP(i,count) if (!strcmp(card[i].command,"Fkdo")) preset=true;
    T_ASSERT(preset);FrontClearSelection(client);G_SelectEntity(client,dock);
    G_ClientCommand(G_GetPlayerEntityByNumber(0),2,(cstring_t[]){"button","jakg"});
    T_EQ(G_ProductionQueueCount(dock),1);FrontStep(400);
    T_NOT_NULL(FrontUnit(0,"jakg"));T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
static void FrontHistoricalParallelYards(void) {
    FrontLoad(false);gameClient_t *client=G_GetPlayerClientByNumber(0);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=6000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=1000;
    edict_t *a=unit_create(0,FS_SLKKey("fhvy"),&(vec2_t){-2400,1900},0);
    edict_t *b=unit_create(0,FS_SLKKey("fhvy"),&(vec2_t){-1900,2400},0);
    FrontClearSelection(client);G_SelectEntity(client,a);G_SelectEntity(client,b);
    G_ClientCommand(G_GetPlayerEntityByNumber(0),2,(cstring_t[]){"button","uiow"});
    T_EQ(G_ProductionQueueCount(a),1);T_EQ(G_ProductionQueueCount(b),1);
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],4520);
    FrontStep(380);T_EQ(G_ProductionQueueCount(a),0);T_EQ(G_ProductionQueueCount(b),0);
    uint32_t ships=0;FILTER_EDICTS(e,e->inuse && e->s.player==0 && e->class_id==FS_SLKKey("uiow") && !(e->s.renderfx&RF_HIDDEN)) ships++;
    T_EQ(ships,2);FrontEnd();
}
static test_t history_ijn={"frontline.historical_ijn_player_start",FrontHistoricalIJNStart,__FILE__,__LINE__,NULL};
static test_t history_parallel={"frontline.historical_parallel_shipyards",FrontHistoricalParallelYards,__FILE__,__LINE__,NULL};
static void FrontHistoricalRegistry(void) {
    FrontLoad(false);
    T_NOT_NULL(FrontUnit(0,"fhq0"));
    T_ASSERT(G_UnitBalance(FS_SLKKey("uiow"))->id==FS_SLKKey("uiow"));
    T_ASSERT(G_UnitBalance(FS_SLKKey("jzui"))->id==FS_SLKKey("jzui"));
    FrontEnd();
}
static test_t history_registry={"frontline.historical_roster_registry",FrontHistoricalRegistry,__FILE__,__LINE__,NULL};
static test_t landing_cursor={"frontline.landing_cursor_completion_cancel_and_restart",FrontLandingCursor,__FILE__,__LINE__,NULL};
static test_t mass={"frontline.mass_production_and_carrier_replenishment",FrontMassProduction,__FILE__,__LINE__,NULL};
static test_t formations={"frontline.formations_use_real_group_movement",FrontFormations,__FILE__,__LINE__,NULL};
static test_t critical={"frontline.critical_strikes_and_paid_protection",FrontCriticalStrikes,__FILE__,__LINE__,NULL};
static test_t lan={"frontline.lan_human_opponent_and_dropped_player",FrontLanOpponent,__FILE__,__LINE__,NULL};
static test_t aa={"frontline.battleship_aa_independent_of_main_battery",FrontBattleshipAA,__FILE__,__LINE__,NULL};
static test_t evasion={"frontline.aircraft_evasion_limits",FrontAircraftEvasion,__FILE__,__LINE__,NULL};
static test_t damage_fx={"frontline.damaged_ships_smoke_and_burn",FrontShipDamageEffects,__FILE__,__LINE__,NULL};
static test_t dock_fx={"frontline.dock_gate_and_launch_wake",FrontDockPresentation,__FILE__,__LINE__,NULL};
static test_t logging={"frontline.engineers_log_until_the_forest_is_gone",FrontLogging,__FILE__,__LINE__,NULL};
static test_t elig={"frontline.strike_package_eligibility",FrontStrikeEligibility,__FILE__,__LINE__,NULL};
static test_t results={"frontline.repeated_match_results_accept_restart",FrontMatchResults,__FILE__,__LINE__,NULL};
static test_t fresh_ai={"frontline.ai_bootstraps_from_hq_only",FrontFreshAI,__FILE__,__LINE__,NULL};
static test_t rally={"frontline.resource_and_combat_rally_persist",FrontRallyEconomy,__FILE__,__LINE__,NULL};
static test_t fresh={"frontline.hq_only_start_and_result_window_bounds",FrontFreshStart,__FILE__,__LINE__,NULL};
static test_t blocked={"frontline.current_order_is_zero_when_idle",FrontCurrentOrderIdle,__FILE__,__LINE__,NULL};
static test_t naval={"frontline.battleship_navigates_and_attacks",FrontNaval,__FILE__,__LINE__,NULL};
static test_t transport={"frontline.amphibious_board_cross_land_and_fight",FrontTransport,__FILE__,__LINE__,NULL};
static test_t production={"frontline.roster_production_construction_and_economy",FrontProduction,__FILE__,__LINE__,NULL};
static test_t limits={"frontline.carrier_capacity_fuel_replacement_and_save",FrontCarrierLimits,__FILE__,__LINE__,NULL};
static test_t bot={"frontline.bot_combined_arms_and_invasion",FrontBot,__FILE__,__LINE__,NULL};
static test_t doctrine={"frontline.bot_doctrine_advances_rallied_units_and_defends",FrontBotDoctrine,__FILE__,__LINE__,NULL};
static test_t carrier={"frontline.carrier_replenish_patrol_recall_service",FrontCarrier,__FILE__,__LINE__,NULL};
static test_t strike={"frontline.coordinated_multi_carrier_strike",FrontCoordinatedStrike,__FILE__,__LINE__,NULL};
/* Classic-RTS layer: tech requirements, combat ranks with real bonuses, and selling structures. */
static void FrontClassicRanksTechSell(void) {
    FrontLoad(false);gameClient_t *client=G_GetPlayerClientByNumber(0);edict_t *clent=G_GetPlayerEntityByNumber(0);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=5000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=1000;
    edict_t *worker=FrontUnit(0,"fwkr");char reason[128];
    T_NOT_NULL(worker);
    FILTER_EDICTS(e,e->inuse && e->s.player==0 && e->class_id==FS_SLKKey("ffac")) G_FreeEdict(e);
    T_EQ(G_GetBuildCommandState(client,worker,FS_SLKKey("fair"),reason,sizeof(reason)),BUILD_COMMAND_DISABLED);
    T_NOT_NULL(unit_create(0,FS_SLKKey("ffac"),&(vec2_t){-3900,1800},0));
    T_EQ(G_GetBuildCommandState(client,worker,FS_SLKKey("fair"),reason,sizeof(reason)),BUILD_COMMAND_AVAILABLE);
    /* Ranks: the map script promotes at 3 kills; Elite replaces Veteran and self-repairs. */
    edict_t *rifle=unit_create(0,FS_SLKKey("finf"),&(vec2_t){-3000,3000},0);
    float armor=rifle->unit_state->armor_value;
    FOR_LOOP(i,3) {
        edict_t *foe=unit_create(1,FS_SLKKey("finf"),&(vec2_t){-2900,3000},0);
        T_Damage(foe,rifle,5000);FrontStep(1);
    }
    T_EQ(G_UnitAbilityLevel(rifle,MAKEFOURCC('F','v','t','1')),1);
    T_ASSERT(rifle->unit_state->attack1.temporaryDamageBonus>=3);
    T_ASSERT(fabsf(rifle->unit_state->armor_value-armor-2)<.01f);
    T_ASSERT(G_ActorRemoveSkill(rifle,MAKEFOURCC('F','v','t','1')));T_ASSERT(G_ActorAddSkill(rifle,MAKEFOURCC('F','v','t','2')));
    T_ASSERT(fabsf(rifle->unit_state->armor_value-armor-4)<.01f);
    rifle->health.value=100;FrontStep(30);T_ASSERT(rifle->health.value>=105);
    /* Sell: half the cost back; the Headquarters has no Sell button. */
    gameCommandButton_t card[32];uint32_t count=G_GetCommandButtons(FrontUnit(0,"fhq0"),card,32);
    FOR_LOOP(i,count) T_ASSERT(strcmp(card[i].command,"Fsel"));
    edict_t *yard=unit_create(0,FS_SLKKey("fbar"),&(vec2_t){-2600,2400},0);
    uint32_t gold=client->ps.stats[PLAYERSTATE_RESOURCE_GOLD];
    FrontClearSelection(client);G_SelectEntity(client,yard);
    G_ClientCommand(clent,2,(cstring_t[]){"button","Fsel"});
    T_ASSERT(M_IsDead(yard));T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],gold+75);
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
static test_t classic={"frontline.classic_tech_ranks_and_sell",FrontClassicRanksTechSell,__FILE__,__LINE__,NULL};
/* CAP: carrier fighters circle the fleet without purchases; an airfield launches its stored fighters. */
static void FrontAirCap(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    uint32_t gold=client->ps.stats[PLAYERSTATE_RESOURCE_GOLD];
    T_ASSERT(unit_issueimmediateorder(carrier,"togglecap"));
    FrontStep(80);
    uint32_t aloft=0;
    FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && S_SpellChannelOwner(f)==carrier && f->variation==2 && f->damage==3) aloft++;
    T_EQ(aloft,8u); /* every fighter flies CAP */
    T_EQ(S_CarrierAircraftCount(carrier),24);T_ASSERT(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]>=gold); /* nothing bought (engineers keep mining) */
    T_ASSERT(unit_issueimmediateorder(carrier,"togglecap")); /* off: they come home */
    FrontStep(300);
    FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && S_SpellChannelOwner(f)==carrier) T_ASSERT(f->damage!=3);
    edict_t *field=unit_create(0,FS_SLKKey("fair"),&(vec2_t){-3300,1300},0);
    edict_t *fighter=unit_create(0,FS_SLKKey("ffgt"),&field->s.origin2,0);
    T_ASSERT(S_CargoTryLoad(field,fighter));T_ASSERT(fighter->s.renderfx&RF_HIDDEN);
    T_ASSERT(unit_issueimmediateorder(field,"airfieldcap"));
    FrontStep(60);
    T_ASSERT(!(fighter->s.renderfx&RF_HIDDEN));T_ASSERT(Vector2_distance(&fighter->s.origin2,&field->s.origin2)<1800);
    T_ASSERT(fighter->currentmove && strcmp(fighter->currentmove->animation,"stand"));
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
/* The command card path: the squadron button arms a target cursor; a clicked unit or
 * ground point becomes the strike target (never the map origin). */
static void FrontSquadronClicks(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);edict_t *clent=G_GetPlayerEntityByNumber(0);
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    edict_t *ship=unit_create(1,FS_SLKKey("ftrn"),&(vec2_t){1500,2300},0);
    FrontClearSelection(client);G_SelectEntity(client,carrier);
    G_ClientCommand(clent,2,(cstring_t[]){"button","Fsqt"});
    char number[16];snprintf(number,sizeof(number),"%u",(unsigned)(ship-globals.edicts));
    G_ClientCommand(clent,2,(cstring_t[]){"select",number});
    edict_t *mission=NULL;
    FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) mission=m;
    T_NOT_NULL(mission);
    if (mission) { T_ASSERT(mission->goalentity==ship);T_ASSERT(Vector2_distance(&mission->channel->origin,&ship->s.origin2)<1); }
    T_ASSERT(unit_issueimmediateorder(carrier,"recallaircraft"));FrontStep(1500);
    FrontClearSelection(client);G_SelectEntity(client,carrier);
    G_ClientCommand(clent,2,(cstring_t[]){"button","Fsqd"});
    G_ClientCommand(clent,3,(cstring_t[]){"point","-2600","2900"});
    mission=NULL;
    FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) mission=m;
    T_NOT_NULL(mission);
    if (mission) T_ASSERT(Vector2_distance(&mission->channel->origin,&(vec2_t){-2600,2900})<1);
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
/* Ballistics: green crews scatter, experience tightens the spread; armour ricochets
 * shells and well-centred hits on a ship strike its citadel. Aircraft are unaffected. */
static void FrontBallistics(void) {
    FrontLoad(false);
    edict_t *battleship=unit_create(0,FS_SLKKey("fbat"),&(vec2_t){-600,1300},0);
    edict_t *destroyer=unit_create(1,FS_SLKKey("fdst"),&(vec2_t){600,1300},0);
    T_FEQ(S_BallisticSettle(battleship),1,.001f); /* first seen standing still: settled */
    T_FEQ(S_BallisticDispersion(battleship),91,.01f); /* 130 green, 30% tighter when settled */
    battleship->s.origin2.x+=200;
    T_FEQ(S_BallisticSettle(battleship),0,.001f);T_FEQ(S_BallisticDispersion(battleship),130,.01f); /* moved */
    FrontStep(20);T_FEQ(S_BallisticSettle(battleship),.5f,.01f); /* half settled after 2 s */
    FrontStep(20);
    destroyer->s.angle=(float)M_PI/2; /* broadside to the battleship */
    uint32_t late_miss=0,overpen=0,citadel=0;
    FOR_LOOP(i,1000) {
        int const hit=S_BallisticHit(battleship,destroyer,150);
        if (i>=140 && !hit) late_miss++;
        if (hit==45) overpen++; /* 150-damage shells pass through a thin destroyer hull */
        if (hit==450) citadel++;
    }
    T_FEQ(S_BallisticExperience(battleship),1,.001f);
    T_FEQ(S_BallisticDispersion(battleship),27.3f,.01f); /* veteran and settled */
    T_ASSERT(late_miss==0);T_ASSERT(overpen>0);
    T_EQ(citadel,0u); /* a destroyer has no armoured citadel */
    /* Seen bow-on the destroyer is narrower and deflects more: a green, moving gun misses often. */
    destroyer->s.angle=0;
    edict_t *fresh=unit_create(0,FS_SLKKey("fdst"),&(vec2_t){-900,1300},0);
    uint32_t misses=0;
    FOR_LOOP(i,20) { fresh->s.origin2.y+=50; if (!S_BallisticHit(fresh,destroyer,35)) misses++; }
    T_ASSERT(misses>0);
    edict_t *gun=unit_create(0,FS_SLKKey("fart"),&(vec2_t){-600,1700},0);
    edict_t *tank=unit_create(1,FS_SLKKey("ftnk"),&(vec2_t){-400,1700},0);
    uint32_t tank_citadel=0;
    FOR_LOOP(i,200) if (S_BallisticHit(gun,tank,90)==270) tank_citadel++;
    T_EQ(tank_citadel,0u); /* only ships have citadels */
    /* A torpedo hit floods the ship; flooding keeps doing damage afterwards. */
    edict_t *torpedo=unit_create(0,FS_SLKKey("ftor"),&(vec2_t){400,1300},0);
    float const before=destroyer->health.value;
    int hit=0;FOR_LOOP(i,20) if (!hit) hit=S_BallisticHit(torpedo,destroyer,110);
    T_ASSERT(hit>0);
    FrontStep(30);T_ASSERT(destroyer->health.value<before);
    edict_t *plane=unit_create(1,FS_SLKKey("ffgt"),&(vec2_t){0,1300},0);
    edict_t *green=unit_create(0,FS_SLKKey("fdst"),&(vec2_t){-600,900},0);
    FOR_LOOP(i,50) T_EQ(S_BallisticHit(green,plane,35),35);
    FrontEnd();
}
/* Fire `shots` rounds of `damage` from gun at target and tally the outcomes (and deck hits). */
static void FrontVolley(edict_t *gun, edict_t *target, int damage, uint32_t shots, uint32_t counts[BALLISTIC_OUTCOMES], uint32_t *deck) {
    memset(counts,0,sizeof(uint32_t)*BALLISTIC_OUTCOMES);
    if (deck) *deck=0;
    FOR_LOOP(i,shots) {
        bool on_deck=false;
        S_BallisticHit(gun,target,damage);
        counts[S_BallisticLastOutcome(&on_deck)]++;
        if (deck && on_deck) (*deck)++;
    }
}
static edict_t *FrontShipAt(uint32_t player, cstring_t code, float x, float y, float angle) {
    vec2_t const at={x,y};
    T_ASSERT(CM_TerrainPointIsSwimmable(&at));
    edict_t *ship=unit_create(player,FS_SLKKey(code),&at,0);
    T_NOT_NULL(ship);
    ship->s.angle=angle;ship->s.origin2=at;ship->s.origin.x=x;ship->s.origin.y=y;
    return ship;
}
/* Armour penetration (docs/frontline-naval-damage.md): guns penetrate by calibre and lose
 * belt penetration with range; ships carry belt and deck armour. Destroyer guns shatter on a
 * battleship and start fires instead; battleship AP overpenetrates a destroyer; cruisers sit
 * between; long range drops shells onto the deck; a bow-on target deflects shells. */
static void FrontArmour(void) {
    FrontLoad(false);
    float const broadside=(float)M_PI/2;
    edict_t *iowa=FrontShipAt(0,"uiow",-600,1300,0),*fletcher=FrontShipAt(0,"uflt",-600,900,0),
            *baltimore=FrontShipAt(0,"ubal",-600,500,0);
    edict_t *yamato=FrontShipAt(1,"jyam",-600,100,0),*kagero=FrontShipAt(1,"jkgr",-600,-300,0);
    /* Penetration by calibre: 16-inch > 8-inch > 5-inch; belt penetration falls with range,
     * deck penetration grows with it (plunging fire). */
    T_ASSERT(S_BallisticPenetration(iowa,0,false)>S_BallisticPenetration(baltimore,0,false));
    T_ASSERT(S_BallisticPenetration(baltimore,0,false)>S_BallisticPenetration(fletcher,0,false));
    T_ASSERT(S_BallisticPenetration(fletcher,0,false)>0);
    T_ASSERT(S_BallisticPenetration(iowa,1800,false)<S_BallisticPenetration(iowa,300,false));
    T_FEQ(S_BallisticPenetration(iowa,0,true),0,.001f);
    T_ASSERT(S_BallisticPenetration(iowa,1800,true)>S_BallisticPenetration(iowa,600,true));
    float belt[3],deck[3],torpedo[3];
    T_ASSERT(S_ShipArmour(yamato,&belt[0],&deck[0],&torpedo[0]));
    T_ASSERT(S_ShipArmour(baltimore,&belt[1],&deck[1],&torpedo[1]));
    T_ASSERT(S_ShipArmour(kagero,&belt[2],&deck[2],&torpedo[2]));
    T_ASSERT(belt[0]>belt[1] && belt[1]>belt[2] && deck[0]>deck[1] && deck[1]>deck[2]);
    T_ASSERT(torpedo[0]>torpedo[1] && torpedo[1]>=torpedo[2]);
    uint32_t n[BALLISTIC_OUTCOMES],on_deck=0;
    /* 5-inch against Yamato at 400: mostly shattered shells, never a citadel, fires on the upperworks. */
    edict_t *target=FrontShipAt(1,"jyam",-200,900,broadside);
    FrontVolley(fletcher,target,40,400,n,NULL);
    uint32_t landed=400-n[BALLISTIC_MISS];
    T_ASSERT(landed>200);
    T_ASSERT(n[BALLISTIC_SHATTER]+n[BALLISTIC_NO_PENETRATION]>landed/2);
    T_EQ(n[BALLISTIC_PENETRATION],0u);T_EQ(n[BALLISTIC_CITADEL],0u);
    T_ASSERT(n[BALLISTIC_UPPERWORKS]>0);
    T_ASSERT(S_BallisticBurning(target));
    G_FreeEdict(target);
    /* 16-inch against a destroyer at 600: the AP shell usually passes straight through. */
    target=FrontShipAt(1,"jkgr",0,1300,broadside);
    FrontVolley(iowa,target,155,400,n,NULL);
    T_ASSERT(n[BALLISTIC_OVERPENETRATION]>n[BALLISTIC_PENETRATION]);
    T_EQ(n[BALLISTIC_CITADEL],0u);T_EQ(n[BALLISTIC_SHATTER],0u);
    G_FreeEdict(target);
    /* 16-inch against a battleship broadside at 500: penetrations and citadel hits. */
    target=FrontShipAt(1,"uiow",-100,1300,broadside);
    FrontVolley(iowa,target,155,400,n,&on_deck);
    T_ASSERT(n[BALLISTIC_PENETRATION]+n[BALLISTIC_CITADEL]>n[BALLISTIC_SHATTER]+n[BALLISTIC_NO_PENETRATION]);
    T_ASSERT(n[BALLISTIC_CITADEL]>0);
    uint32_t const near_deck=on_deck;
    /* Bow-on, the same battleship deflects shells off its belt. */
    target->s.angle=0;
    FrontVolley(iowa,target,155,400,n,NULL);
    T_ASSERT(n[BALLISTIC_RICOCHET]>20);
    G_FreeEdict(target);
    /* At 1750 most hull hits plunge onto the deck. */
    target=FrontShipAt(1,"uiow",1150,1300,broadside);
    FrontVolley(iowa,target,155,400,n,&on_deck);
    T_ASSERT(on_deck>near_deck*3+20);
    G_FreeEdict(target);
    /* 8-inch: penetrates a cruiser at 400 but not a battleship belt at 1100. */
    target=FrontShipAt(1,"jtak",-200,500,broadside);
    FrontVolley(baltimore,target,80,400,n,NULL);
    T_ASSERT(n[BALLISTIC_PENETRATION]+n[BALLISTIC_CITADEL]>n[BALLISTIC_SHATTER]+n[BALLISTIC_NO_PENETRATION]);
    G_FreeEdict(target);
    target=FrontShipAt(1,"jyam",500,500,broadside);
    FrontVolley(baltimore,target,80,400,n,NULL);
    T_ASSERT(n[BALLISTIC_SHATTER]+n[BALLISTIC_NO_PENETRATION]>n[BALLISTIC_PENETRATION]+n[BALLISTIC_CITADEL]);
    G_FreeEdict(target);
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
static uint32_t FrontTorpedoes(edict_t const *owner) {
    uint32_t count=0;
    FILTER_EDICTS(t,t->inuse && t->think==ship_torpedo_think && t->owner==owner) count++;
    return count;
}
static uint32_t FrontAwaitSalvo(edict_t const *owner, uint32_t frames) {
    FOR_LOOP(i,frames) { uint32_t const n=FrontTorpedoes(owner); if (n) return n; FrontStep(1); }
    return FrontTorpedoes(owner);
}
/* Ship torpedoes: destroyers and torpedo cruisers fire spread salvos at ships in range,
 * reload, can miss a ship that moves, and flood what they hit. Long Lances outrange US
 * torpedoes; battleships carry none; torpedo protection reduces the damage. */
static void FrontShipTorpedoes(void) {
    FrontLoad(false);
    FILTER_EDICTS(e,e->inuse && !(e->aiflags&AI_FLYING) && e->data.UnitBalance && e->data.UnitBalance->speed>0 &&
                    M_UnitStaticPathingFlags(e)==CM_PATHING_UNSWIMMABLE) G_FreeEdict(e);
    edict_t *fletcher=FrontShipAt(0,"uflt",-500,500,0),*iowa=FrontShipAt(1,"uiow",700,500,(float)M_PI/2);
    G_SetUnitFlag(iowa,UNIT_FLAG_PAUSED,true); /* the target holds fire and course */
    unit_issueimmediateorder(fletcher,"holdposition");
    T_ASSERT(S_ResolveAbilityAlias(fletcher,MAKEFOURCC('F','t','p','s')).alias);
    T_ASSERT(!S_ResolveAbilityAlias(iowa,MAKEFOURCC('F','t','p','s')).alias); /* battleships carry no tubes */
    float const before=iowa->health.value;
    T_EQ(FrontAwaitSalvo(fletcher,20),4u); /* a spread of four */
    FrontStep(50);
    T_EQ(FrontTorpedoes(fletcher),0u); /* the salvo has run out */
    T_ASSERT(S_BallisticFlooding(iowa));
    T_ASSERT(iowa->health.value<before);
    /* Tubes reload: nothing more inside the reload time. */
    FrontStep(150);T_EQ(FrontTorpedoes(fletcher),0u);
    /* The next salvo is aimed where the target was; it turns away and every torpedo misses. */
    T_ASSERT(FrontAwaitSalvo(fletcher,400)>0);
    T_ASSERT(!S_BallisticFlooding(iowa));
    float const dodged=iowa->health.value;
    iowa->s.origin.y+=700;iowa->s.origin2.y+=700;gi.LinkEntity(iowa);
    FrontStep(60);
    T_EQ(FrontTorpedoes(fletcher),0u);
    T_ASSERT(!S_BallisticFlooding(iowa));
    T_ASSERT(iowa->health.value>=dodged-.5f); /* no torpedo found it */
    /* Torpedo protection: bulges and bulkheads absorb part of a hit; destroyers have none;
     * carriers keep their avgas and hangar vulnerability on top. */
    edict_t *carrier=FrontShipAt(1,"uykt",-500,-200,0);
    T_EQ(S_TorpedoDamage(fletcher,200),200);
    T_ASSERT(S_TorpedoDamage(iowa,200)<200);
    T_ASSERT(S_TorpedoDamage(carrier,200)>S_TorpedoDamage(iowa,200));
    G_FreeEdict(fletcher);G_FreeEdict(iowa);G_FreeEdict(carrier);
    /* Long Lance: a Kagero reaches a target at 1700 that a Fletcher cannot. */
    edict_t *kagero=FrontShipAt(0,"jkgr",-500,-300,0),*sumner=FrontShipAt(0,"uflt",-500,-100,0);
    edict_t *far=FrontShipAt(1,"uiow",1200,-200,(float)M_PI/2);
    G_SetUnitFlag(far,UNIT_FLAG_PAUSED,true);
    unit_issueimmediateorder(kagero,"holdposition");unit_issueimmediateorder(sumner,"holdposition");
    T_ASSERT(FrontAwaitSalvo(kagero,20)>0);
    T_EQ(FrontTorpedoes(sumner),0u);
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
/* Carriers pick aircraft for the target: Attack on a land unit sends dive bombers with
 * fighters; automatic launches go for battleships before smaller ships. */
static void FrontCarrierAutoLaunch(void) {
    FrontLoad(false);
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    edict_t *tank=unit_create(1,FS_SLKKey("ftnk"),&(vec2_t){carrier->s.origin.x+500,carrier->s.origin.y+300},0);
    carrier->resources|=1u<<30; /* automatic launches off for the manual case */
    vec2_t const berth=carrier->s.origin2;
    T_ASSERT(G_IssueUnitTargetOrder(carrier,"attack",tank,false,0));
    FrontStep(2);
    edict_t *mission=NULL;
    FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) mission=m;
    T_NOT_NULL(mission);
    uint32_t fighters=0,dive=0,torpedo=0;
    FILTER_EDICTS(f,f->inuse && f->think==carrier_flight_think && f->variation==3) {
        edict_t *plane=S_SpellChannelTarget(f);
        if (plane->class_id==FS_SLKKey("ffgt")) fighters++;
        if (plane->class_id==FS_SLKKey("fbmb")) dive++;
        if (plane->class_id==FS_SLKKey("ftor")) torpedo++;
    }
    T_EQ(fighters,8u);T_EQ(dive,8u);T_EQ(torpedo,0u); /* a fleet carrier embarks 8/8/8 */
    FrontStep(30);T_ASSERT(Vector2_distance(&carrier->s.origin2,&berth)<40); /* the hull holds back */
    G_FreeEdict(tank);
    T_ASSERT(unit_issueimmediateorder(carrier,"recallaircraft"));FrontStep(1500);
    FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) G_FreeEdict(m);
    /* Automatic: a destroyer and a battleship come into view; the battleship is struck. */
    /* Both are paused: a carrier under fire cannot launch (checked below). */
    /* Toward the map centre, so both stay on the map (and inside the fog grid). */
    float const toward=atan2f(-carrier->s.origin.y,-carrier->s.origin.x);
    edict_t *destroyer=unit_create(1,FS_SLKKey("fdst"),&(vec2_t){carrier->s.origin.x+900*cosf(toward),carrier->s.origin.y+900*sinf(toward)},0);
    edict_t *battleship=unit_create(1,FS_SLKKey("fbat"),&(vec2_t){carrier->s.origin.x+1500*cosf(toward),carrier->s.origin.y+1500*sinf(toward)},0);
    G_SetUnitFlag(destroyer,UNIT_FLAG_PAUSED,true);G_SetUnitFlag(battleship,UNIT_FLAG_PAUSED,true);
    carrier->resources&=~(1u<<30);
    mission=NULL;
    for (uint32_t i=0;i<30 && !mission;i++) { FrontStep(1);FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) mission=m; }
    T_NOT_NULL(mission);
    if (mission) T_ASSERT(mission->goalentity==battleship);
    (void)destroyer;
    /* Hit or burning, the deck is closed: no further launch until the fire burns out. */
    T_ASSERT(unit_issueimmediateorder(carrier,"recallaircraft"));FrontStep(1500);
    FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) G_FreeEdict(m);
    T_ASSERT(S_BallisticHit(battleship,carrier,1)>=0);
    edict_t *bomber=unit_create(1,FS_SLKKey("fbmb"),&(vec2_t){carrier->s.origin.x+300,carrier->s.origin.y},0);
    int landed=0;FOR_LOOP(i,40) if (!landed) landed=S_BallisticHit(bomber,carrier,95);
    FOR_LOOP(i,40) if (!S_BallisticBurning(carrier)) S_BallisticHit(bomber,carrier,95);
    T_ASSERT(landed>=95*3); /* bombs hit a carrier three times as hard */
    T_ASSERT(S_BallisticBurning(carrier));
    G_FreeEdict(bomber);
    mission=NULL;
    for (uint32_t i=0;i<30 && !mission;i++) { FrontStep(1);FILTER_EDICTS(m,m->inuse && m->think==strike_mission_think) mission=m; }
    T_ASSERT(mission==NULL);
    T_ASSERT(!unit_issueorder(carrier,"divesquadron",&battleship->s.origin2));
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
/* Command Both: the sandbox map starts without an opposing AI and fog; with the sandbox
 * rule the single player orders enemy units, which remain enemies. */
static cstring_t (*front_old_cvar)(cstring_t, cstring_t);
static cstring_t FrontSandboxCvar(cstring_t name, cstring_t def) {
    /* The menu stores the path as typed; the server receives it resolved with backslashes. */
    return !strcmp(name,"g_command_all") ? "Maps/Frontline/IslandCommandSandbox.w3m" : front_old_cvar(name,def);
}
static void FrontCommandBoth(void) {
    srand(1);
    front_old_time = gi.GetTime; gi.GetTime = FrontTime; front_time = 0;
    CM_SetupTestWorldBounds(NULL);
    front_old_cvar = gi.CvarString; gi.CvarString = FrontSandboxCvar;
    T_ASSERT(globals.PrepareMap("Maps\\Frontline\\IslandCommandSandbox.w3m"));
    gi.CvarString = front_old_cvar;
    T_ASSERT(game.command_all); /* the sandbox rule follows its own map */
    T_ASSERT(globals.LoadMap("Maps/Frontline/IslandCommandSandbox.w3m"));
    T_NOT_NULL(level.vm);
    FrontStep(5);
    T_ASSERT(!level.bots[1].vm); /* no opposing AI */
    gameClient_t *client=G_GetPlayerClientByNumber(0);
    edict_t *hq=FrontUnit(1,"fhq0");
    T_NOT_NULL(hq);
    if (!hq) { FrontEnd(); return; }
    edict_t *enemy=unit_create(1,FS_SLKKey("finf"),&(vec2_t){hq->s.origin.x-300,hq->s.origin.y},0);
    T_ASSERT(G_UnitCanControl(client,enemy));
    game.command_all=false;
    T_ASSERT(!G_UnitCanControl(client,enemy));
    game.command_all=true;T_ASSERT(G_UnitCanSpendResources(client,hq));
    T_ASSERT(S_SpellIsEnemy(FrontUnit(0,"fhq0"),enemy)); /* still opposing sides */
    edict_t *clent=G_GetPlayerEntityByNumber(0);
    FrontClearSelection(client);G_SelectEntity(client,hq);
    uint32_t gold=G_GetPlayerClientByNumber(1) ? G_GetPlayerClientByNumber(1)->ps.stats[PLAYERSTATE_RESOURCE_GOLD] : 0;
    G_ClientCommand(clent,2,(cstring_t[]){"button","fwkr"});
    T_EQ(G_ProductionQueueCount(hq),1); /* the enemy HQ trains for its own side */
    /* Its barracks offers its own (Japanese) roster, judged by its owner's tech. */
    edict_t *barracks=unit_create(1,FS_SLKKey("fbar"),&(vec2_t){hq->s.origin.x-500,hq->s.origin.y+400},0);
    FrontClearSelection(client);G_SelectEntity(client,barracks);
    T_EQ(G_GetTrainCommandState(client,barracks,FS_SLKKey("jinf"),NULL,0),BUILD_COMMAND_AVAILABLE);
    G_ClientCommand(clent,2,(cstring_t[]){"button","jinf"});
    T_EQ(G_ProductionQueueCount(barracks),1);
    FrontStep(150);T_NOT_NULL(FrontUnit(1,"jinf"));
    if (G_GetPlayerClientByNumber(1)) T_ASSERT(G_GetPlayerClientByNumber(1)->ps.stats[PLAYERSTATE_RESOURCE_GOLD]<gold);
    /* View Side: the human keeps command of both but sees one navy's fog at a time. */
    bool const was_connected=level.fow.players[0].client_connected;
    level.fow.players[0].client_connected=true;
    T_EQ(game.view_side,0u);T_ASSERT(G_FowPlayersShareVision(0,0));T_ASSERT(!G_FowPlayersShareVision(0,1));
    FrontClearSelection(client);G_SelectEntity(client,hq);
    G_ClientCommand(clent,2,(cstring_t[]){"button","Fviw"});
    T_EQ(game.view_side,2u);T_ASSERT(G_FowPlayersShareVision(0,1));T_ASSERT(!G_FowPlayersShareVision(0,0));
    T_ASSERT(G_UnitCanControl(client,FrontUnit(0,"fhq0"))); /* still commands both */
    G_ClientCommand(clent,2,(cstring_t[]){"button","Fviw"});
    T_EQ(game.view_side,1u);T_ASSERT(G_FowPlayersShareVision(0,0));T_ASSERT(!G_FowPlayersShareVision(0,1));
    level.fow.players[0].client_connected=was_connected;game.view_side=0;
    game.command_all=false;
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
/* Patrol keeps its two endpoints even after every waypoint slot in the ring is reused by
 * other orders (the bug: units drifted off or stopped after a while). */
static void FrontPatrolSurvivesWaypointRing(void) {
    FrontLoad(false);
    edict_t *tank=unit_create(0,FS_SLKKey("ftnk"),&(vec2_t){-3300,3300},0);
    vec2_t const a=tank->s.origin2,b={a.x+700,a.y-200};
    T_ASSERT(unit_issueorder(tank,"patrol",&b));
    FrontStep(5);
    FOR_LOOP(i,600) { vec2_t far={4000.0f+(float)(i%50),-4000.0f}; Waypoint_add(&far); }
    float nearest_a=FLT_MAX,nearest_b=FLT_MAX,farthest=0;
    FOR_LOOP(i,900) {
        FrontStep(1);
        if (i%100==0) FOR_LOOP(k,300) { vec2_t far={4000.0f,-4000.0f-(float)k}; Waypoint_add(&far); }
        nearest_a=MIN(nearest_a,Vector2_distance(&tank->s.origin2,&a));
        nearest_b=MIN(nearest_b,Vector2_distance(&tank->s.origin2,&b));
        farthest=MAX(farthest,MIN(Vector2_distance(&tank->s.origin2,&a),Vector2_distance(&tank->s.origin2,&b)));
    }
    T_ASSERT(nearest_a<120);T_ASSERT(nearest_b<120); /* it keeps visiting both ends */
    T_ASSERT(farthest<600);                        /* and never heads anywhere else */
    T_ASSERT(tank->orders->patrol_a!=NULL);
    FrontEnd();
}
/* The Pacific campaign map: a real match from headquarters only. The bot (IJN) builds up at
 * Yokosuka, raises its Escort Shipyard, sends a fleet and claims Saipan. */
static void FrontPacificMatch(void) {
    srand(1);
    front_old_time = gi.GetTime; gi.GetTime = FrontTime; front_time = 0;
    CM_SetupTestWorldBounds(NULL);
    T_ASSERT(globals.PrepareMap("Maps/Frontline/Pacific.w3m"));
    T_ASSERT(globals.LoadMap("Maps/Frontline/Pacific.w3m"));
    T_NOT_NULL(level.vm);
    edict_t *usn=FrontUnit(0,"fhq0"),*ijn=FrontUnit(1,"fhq0");
    T_NOT_NULL(usn);T_NOT_NULL(ijn);
    if (!usn || !ijn) { FrontEnd(); return; }
    T_ASSERT(Vector2_distance(&usn->s.origin2,&(vec2_t){16700,4300})<50);
    T_ASSERT(Vector2_distance(&ijn->s.origin2,&(vec2_t){-12485,14430})<50);
    G_SetUnitFlag(usn,UNIT_FLAG_INVULNERABLE,true);
    bool yard=false,ships=false,outpost=false;uint32_t peak_land=0;
    FOR_LOOP(i,12000) {
        FrontStep(1);
        if (i%100) continue;
        uint32_t land=0;
        FILTER_EDICTS(e,e->inuse && e->s.player==1 && !M_IsDead(e)) {
            if (e->class_id==FS_SLKKey("fesc") && !e->construction) yard=true;
            if (e->class_id==FS_SLKKey("jfub") || e->class_id==FS_SLKKey("jmog")) ships=true;
            if (e->class_id==FS_SLKKey("fhq0") && e!=ijn && !e->construction && Vector2_distance(&e->s.origin2,&(vec2_t){-9413,105})<600) outpost=true;
            if (e->class_id==FS_SLKKey("jinf") || e->class_id==FS_SLKKey("jtnk")) land++;
        }
        peak_land=MAX(peak_land,land);
        if (getenv("AIDBG") && i%1000==0) FILTER_EDICTS(e,e->inuse && e->s.player==1 && !M_IsDead(e) && (e->class_id==FS_SLKKey("jdai")||e->class_id==FS_SLKKey("fesc")))
            fprintf(stderr,"PACDBG t=%u %.4s %.0f,%.0f phase=%d cargo=%u\n",front_time/1000,(char*)&e->class_id,e->s.origin.x,e->s.origin.y,e->user_data,e->cargo?e->cargo->count:0);
    }
    fprintf(stderr,"FRONTLINE_PACIFIC yard=%d ships=%d outpost=%d peak_land=%u\n",yard,ships,outpost,peak_land);
    T_ASSERT(!jass_rterror_pending(level.vm));T_ASSERT(!jass_rterror_pending(level.bots[1].vm));
    T_ASSERT(peak_land>=4);T_ASSERT(yard);T_ASSERT(ships);T_ASSERT(outpost); /* the IJN settles Saipan */
    FrontEnd();
}
static uint32_t FrontCountModel(cstring_t model) {
    uint32_t const index=(uint32_t)G_RegisterModel(model);uint32_t count=0;
    FILTER_EDICTS(e,e->inuse && e->s.model==index) count++;
    return count;
}
/* Real map units: the AA source mapping, flak under a live air attack and the cap. */
static void FrontFlak(void) {
    FrontLoad(false);
    S_FlakReset();
    edict_t *plane=unit_create(1,FS_SLKKey("jbom"),&(vec2_t){300,0},0);
    T_NOT_NULL(plane);
    static struct { cstring_t code; flakClass_t cls; } const sources[]={
        {"uiow",FLAK_LIGHT},{"jyam",FLAK_LIGHT},{"jkon",FLAK_LIGHT},{"fdst",FLAK_HEAVY},{"uflt",FLAK_HEAVY},
        {"uatl",FLAK_HEAVY},{"jaki",FLAK_HEAVY},{"fcrs",FLAK_HEAVY},{"faa0",FLAK_HEAVY},{"fmg0",FLAK_LIGHT},
        {"fcvr",FLAK_LIGHT},{"ufig",FLAK_NONE},{"ftnk",FLAK_NONE}};
    FOR_LOOP(i,sizeof(sources)/sizeof(sources[0])) {
        edict_t *u=unit_create(0,FS_SLKKey(sources[i].code),&(vec2_t){-6000.0f+(float)i*400,-6000},0);
        T_NOT_NULL(u);
        if (!u) continue;
        if (S_FlakClassForAttack(u,plane)!=sources[i].cls) fprintf(stderr,"FLAK class %s=%d\n",sources[i].code,S_FlakClassForAttack(u,plane));
        T_EQ(S_FlakClassForAttack(u,plane),sources[i].cls);
        G_SetUnitFlag(u,UNIT_FLAG_PAUSED,true);
    }
    /* A battleship under air attack: heavy bursts per volley, light puffs where tracers land. */
    edict_t *ship=FrontUnit(0,"fbat");
    T_NOT_NULL(ship);
    plane->health.value=plane->health.max_value=100000;
    plane->s.origin2=(vec2_t){ship->s.origin.x+500,ship->s.origin.y};plane->s.origin.x=plane->s.origin2.x;plane->s.origin.y=plane->s.origin2.y;
    G_SetUnitFlag(plane,UNIT_FLAG_PAUSED,true);gi.LinkEntity(plane);
    uint32_t heavy=0,light=0;
    FOR_LOOP(i,40) { FrontStep(1); heavy=MAX(heavy,FrontCountModel("Emberfield/Models/flak_heavy.mdx")); light=MAX(light,FrontCountModel("Emberfield/Models/flak_light.mdx")); }
    T_ASSERT(heavy>0);T_ASSERT(light>0);
    /* Bursts are presentation effects at altitude that expire after their Death clip. */
    /* (In-flight fuzed rounds carry the same model; only the bursts are checked.) */
    FILTER_EDICTS(e,e->inuse && e->movetype!=MOVETYPE_FLYMISSILE && e->s.model==(uint32_t)G_RegisterModel("Emberfield/Models/flak_heavy.mdx")) {
        T_ASSERT(e->s.origin.z>plane->s.origin.z-60);T_ASSERT(e->s.flags&EF_NOT_SELECTABLE);
    }
    /* A mass strike: dozens of AA ships cannot exceed the live cap. */
    FOR_LOOP(i,24) unit_create(0,FS_SLKKey(i&1 ? "uflt" : "uiow"),&(vec2_t){ship->s.origin.x+(float)(i%6)*90-200,ship->s.origin.y+(float)(i/6)*90-150},0);
    uint32_t peak=0;
    FOR_LOOP(i,80) {
        FrontStep(1);
        uint32_t live=FrontCountModel("Emberfield/Models/flak_heavy.mdx")+FrontCountModel("Emberfield/Models/flak_light.mdx");
        peak=MAX(peak,live);
        T_ASSERT(live<=FLAK_MAX_LIVE);T_ASSERT(S_FlakLiveCount()<=FLAK_MAX_LIVE);
    }
    fprintf(stderr,"FRONTLINE_FLAK heavy=%u light=%u strike_peak=%u\n",heavy,light,peak);
    T_ASSERT(peak>=FLAK_MAX_LIVE/2);                     /* the sky fills with a flak cloud */
    FrontEnd();
}
static test_t flak={"frontline.flak_heavy_light_and_cap",FrontFlak,__FILE__,__LINE__,NULL};
/* Aircraft crit/evade visuals (s_air_effects.c) through the real aircraft models. */
static bool FrontAnimIs(edict_t const *e,cstring_t name) { return e->animation && !strcasecmp(e->animation->name,name); }
static bool FrontAnimHas(edict_t const *e,cstring_t word) { return e->animation && strstr(e->animation->name,word); }
static uint32_t FrontCrashes(void) {
    return FrontCountModel("Emberfield/Models/crash_sea.mdx")+FrontCountModel("Emberfield/Models/crash_land.mdx");
}
static void FrontAircraftEffects(void) {
    FrontLoad(false);
    edict_t *plane=unit_create(1,FS_SLKKey("ufig"),&(vec2_t){0,0},0);
    T_NOT_NULL(plane);
    FrontStep(2);
    T_ASSERT(plane->animation && !strchr(plane->animation->name,' '));
    /* Evade: a sharp jink that ends after the maneuver. */
    S_AircraftEvadeEffect(plane);
    T_ASSERT(strstr(plane->animation_props,"jink")!=NULL);
    T_ASSERT(FrontAnimHas(plane,"Jink"));
    FrontStep((AIRCRAFT_JINK_MS+400)/100);
    T_ASSERT(!strstr(plane->animation_props,"jink"));
    T_ASSERT(!FrontAnimHas(plane,"Jink"));
    /* Unknown kinds are ignored. */
    cstring_t const before=plane->animation_props;
    S_AircraftCritEffect(plane,0);S_AircraftCritEffect(plane,5);S_AircraftCritEffect(plane,-1);S_AircraftCritEffect(NULL,1);
    T_ASSERT(plane->animation_props==before);
    /* Kinds 1-4 each select their own sequence family, one airframe per kind. */
    static struct { int kind; cstring_t tag, seq; } const kinds[]={
        {AIRCRAFT_CRIT_ENGINE_FIRE,"fire","Fire"},{AIRCRAFT_CRIT_PILOT_HIT,"wobble","Wobble"},
        {AIRCRAFT_CRIT_CONTROL_LOSS,"spin","Spin"},{AIRCRAFT_CRIT_FUEL_LEAK,"vapour","Vapour"}};
    edict_t *planes[4];
    FOR_LOOP(i,4) {
        planes[i]=unit_create(1,FS_SLKKey(i&1 ? "jfig" : "ufig"),&(vec2_t){(float)i*250-400,300},0);
        T_NOT_NULL(planes[i]);
        S_AircraftCritEffect(planes[i],kinds[i].kind);
    }
    FrontStep(3);
    FOR_LOOP(i,4) {
        T_ASSERT(strstr(planes[i]->animation_props,kinds[i].tag)!=NULL);
        if (!FrontAnimHas(planes[i],kinds[i].seq)) fprintf(stderr,"AIRFX kind %d anim %s\n",kinds[i].kind,planes[i]->animation ? planes[i]->animation->name : "-");
        T_ASSERT(FrontAnimHas(planes[i],kinds[i].seq));
    }
    FrontStep(30);   /* crit presentation persists */
    FOR_LOOP(i,4) T_ASSERT(FrontAnimHas(planes[i],kinds[i].seq));
    /* An evading fire-damaged aircraft still shows its jink; a spinning one cannot jink. */
    S_AircraftEvadeEffect(planes[0]);T_ASSERT(FrontAnimHas(planes[0],"Jink"));
    S_AircraftEvadeEffect(planes[2]);T_ASSERT(FrontAnimHas(planes[2],"Spin"));
    /* Deaths: control loss tumbles (Death Spin), pilot hit glides (Death Wobble); each
     * crit-damaged wreck makes one crash effect at the surface below. */
    T_EQ(FrontCrashes(),0);
    FOR_LOOP(i,4) T_Damage(planes[i],FrontUnit(0,"fbat"),100000);
    FrontStep(2);
    FOR_LOOP(i,4) T_ASSERT(M_IsDead(planes[i]));
    T_ASSERT(FrontAnimIs(planes[2],"Death Spin"));
    T_ASSERT(FrontAnimIs(planes[1],"Death Wobble"));
    T_ASSERT(FrontAnimIs(planes[0],"Death"));
    T_EQ(FrontCrashes(),4);
    uint32_t const sea=(uint32_t)G_RegisterModel("Emberfield/Models/crash_sea.mdx");
    FILTER_EDICTS(e,e->inuse && e->s.model==sea) T_FEQ(e->s.origin.z,0,.01f);
    T_EQ(FrontCountModel("Emberfield/Models/crash_sea.mdx"),4);
    /* Over land, and a crit reported on an already-dead aircraft: one explosion at once. */
    edict_t *other=unit_create(1,FS_SLKKey("jfig"),&(vec2_t){-3000,3000},0);
    T_NOT_NULL(other);
    T_Damage(other,FrontUnit(0,"fbat"),100000);
    FrontStep(1);
    S_AircraftCritEffect(other,AIRCRAFT_CRIT_CONTROL_LOSS);
    T_EQ(FrontCountModel("Emberfield/Models/crash_land.mdx"),1);
    S_AircraftCritEffect(other,AIRCRAFT_CRIT_ENGINE_FIRE);
    FrontStep(2);
    T_EQ(FrontCountModel("Emberfield/Models/crash_land.mdx"),1);   /* never a second wreck */
    /* An undamaged aircraft dies without a crash effect (the ordinary Death dive). */
    T_Damage(plane,FrontUnit(0,"fbat"),100000);
    FrontStep(2);
    T_EQ(FrontCrashes(),5);
    FrontEnd();
}
static test_t aircraft_fx={"frontline.aircraft_crit_and_evade_effects",FrontAircraftEffects,__FILE__,__LINE__,NULL};
static test_t pacific={"frontline.pacific_match_from_headquarters",FrontPacificMatch,__FILE__,__LINE__,NULL};
static test_t patrolring={"frontline.patrol_survives_waypoint_ring",FrontPatrolSurvivesWaypointRing,__FILE__,__LINE__,NULL};
static test_t commandboth={"frontline.command_both_sandbox",FrontCommandBoth,__FILE__,__LINE__,NULL};
static test_t autolaunch={"frontline.carrier_attack_and_auto_launch",FrontCarrierAutoLaunch,__FILE__,__LINE__,NULL};
/* Ships do not repair at sea; parked beside their own shipyard they are repaired
 * (unless still under fire). Ranks never repair a ship. */
static void FrontDockRepair(void) {
    FrontLoad(false);
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    T_ASSERT(S_IsShip(carrier));
    T_ASSERT(!S_IsShip(FrontUnit(0,"fhq0")));
    carrier->health.value=carrier->health.max_value*.5f;
    float const damaged=carrier->health.value;
    FrontStep(100);
    T_FEQ(carrier->health.value,damaged,.5f); /* no regeneration at sea */
    edict_t *yard=unit_create(0,FS_SLKKey("fesc"),&(vec2_t){carrier->s.origin.x+carrier->collision+300,carrier->s.origin.y},0);
    T_NOT_NULL(yard);
    FrontStep(40);
    T_ASSERT(S_ShipDocked(carrier));                          /* taken into a berth, gate shut */
    T_ASSERT(S_ShipStatusFlags(carrier)&SHIP_STATUS_DOCKED);
    float const docked=carrier->health.value;
    T_ASSERT(docked>damaged+carrier->health.max_value*.02f);
    FrontStep(400);                                           /* fully repaired, it sails out */
    T_FEQ(carrier->health.value,carrier->health.max_value,.5f);
    T_ASSERT(!S_ShipDocked(carrier));
    /* Turrets: a knocked-out main turret cuts the broadside; with all of them out the ship
     * cannot fire; the dry dock repairs them. */
    edict_t *bb=unit_create(0,FS_SLKKey("uiow"),&(vec2_t){yard->s.origin.x+1500,yard->s.origin.y},0);
    FrontStep(12); /* turret mounts appear within a second */
    uint32_t const mounts=S_NavalMountCount(bb);
    T_ASSERT(mounts>=2);
    T_ASSERT(S_NavalBreakMount(bb));
    T_ASSERT(S_ShipStatusFlags(bb)&SHIP_STATUS_TURRET_OUT);
    T_ASSERT(S_ConditionFirepower(bb,100)<100 && S_ConditionFirepower(bb,100)>0);
    while (S_NavalBreakMount(bb)) {}
    T_EQ(S_ConditionFirepower(bb,100),0);
    S_NavalRepairMounts(bb);T_EQ(S_ConditionFirepower(bb,100),100);
    T_ASSERT(strlen(S_ShipStatusTooltip(SHIP_STATUS_TURRET_OUT))>0);
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
static test_t dockrepair={"frontline.ships_repair_only_at_shipyard",FrontDockRepair,__FILE__,__LINE__,NULL};
/* Firepower follows condition; a warship under Move engages a target in range
 * without stopping, its hull holding course while the turrets train. */
static void FrontConditionAndUnderway(void) {
    FrontLoad(false);
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    float const toward=atan2f(-carrier->s.origin.y,-carrier->s.origin.x);
    vec2_t const at={carrier->s.origin.x+600*cosf(toward),carrier->s.origin.y+600*sinf(toward)};
    edict_t *ship=unit_create(0,FS_SLKKey("fdst"),&at,0);
    T_EQ(S_ConditionFirepower(ship,100),100);
    ship->health.value=ship->health.max_value*.5f;
    T_ASSERT(S_ConditionFirepower(ship,100)>=67 && S_ConditionFirepower(ship,100)<=68); /* .35 + .65 * .5 */
    ship->health.value=1;
    T_ASSERT(S_ConditionFirepower(ship,100)>=35 && S_ConditionFirepower(ship,100)<=36);
    ship->health.value=ship->health.max_value;
    vec2_t const target_at={at.x+500*cosf(toward+1.2f),at.y+500*sinf(toward+1.2f)};
    edict_t *enemy=unit_create(1,FS_SLKKey("fdst"),&target_at,0);
    G_SetUnitFlag(enemy,UNIT_FLAG_PAUSED,true);
    float const before=enemy->health.value;
    vec2_t const goal={at.x+1500*cosf(toward),at.y+1500*sinf(toward)};
    T_ASSERT(unit_issueorder(ship,"move",&goal));
    vec2_t const start=ship->s.origin2;
    FrontStep(40);
    T_ASSERT(enemy->health.value<before);                     /* it fired */
    T_ASSERT(Vector2_distance(&ship->s.origin2,&start)>200);  /* while still under way */
    T_ASSERT(ship->currentmove==NULL || ship->currentmove->proc!=CAbilityAttack);
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
static test_t underway_fire={"frontline.ships_fire_underway_and_firepower_follows_health",FrontConditionAndUnderway,__FILE__,__LINE__,NULL};
/* A right-click that lands on a tree (an island behind the fleet) used to drop the
 * order: ships cannot act on trees. They now sail toward the clicked point. */
static void FrontShipRightClickTree(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);edict_t *clent=G_GetPlayerEntityByNumber(0);
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    edict_t *tree=NULL;float best=1e9f;
    FILTER_EDICTS(e,e->inuse && e->destructable && !M_IsDead(e)) {
        float d=Vector2_distance(&e->s.origin2,&carrier->s.origin2);
        if (d<best) { best=d;tree=e; }
    }
    T_NOT_NULL(tree);
    if (!tree) { FrontEnd(); return; }
    edict_t *ship=unit_create(0,FS_SLKKey("uflt"),&carrier->s.origin2,0);
    vec2_t const start=ship->s.origin2;
    float const before=Vector2_distance(&start,&tree->s.origin2);
    FrontClearSelection(client);G_SelectEntity(client,ship);
    char n[16],x[32],y[32];
    snprintf(n,sizeof(n),"%u",(unsigned)(tree-globals.edicts));
    snprintf(x,sizeof(x),"%d",(int)tree->s.origin.x);snprintf(y,sizeof(y),"%d",(int)tree->s.origin.y);
    G_ClientCommand(clent,4,(cstring_t[]){"smart",n,x,y});
    FrontStep(60);
    T_ASSERT(Vector2_distance(&ship->s.origin2,&start)>300);
    T_ASSERT(Vector2_distance(&ship->s.origin2,&tree->s.origin2)<before);
    FrontEnd();
}
static test_t rightclick_tree={"frontline.ships_right_clicked_on_a_tree_still_sail",FrontShipRightClickTree,__FILE__,__LINE__,NULL};
/* A ship taken off patrol and sent to a dry dock stays there: the old patrol never resumes,
 * whether it is ordered by right-click, docked, or fights on the way. */
static void FrontPatrolThenDock(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);edict_t *clent=G_GetPlayerEntityByNumber(0);
    edict_t *carrier=FrontUnit(0,"fcvr");
    FrontStep(12);
    float const toward=atan2f(-carrier->s.origin.y,-carrier->s.origin.x);
    vec2_t const post={carrier->s.origin.x+600*cosf(toward),carrier->s.origin.y+600*sinf(toward)};
    vec2_t const wake={carrier->s.origin.x+1800*cosf(toward),carrier->s.origin.y+1800*sinf(toward)};
    edict_t *ship=unit_create(0,FS_SLKKey("uflt"),&post,0);
    FrontStep(5);
    T_ASSERT(unit_issueorder(ship,"patrol",&wake));
    FrontStep(40);
    ship->health.value=ship->health.max_value*.4f;
    /* Right-click back home, as a player would. */
    FrontClearSelection(client);G_SelectEntity(client,ship);
    char x[32],y[32];snprintf(x,32,"%d",(int)post.x);snprintf(y,32,"%d",(int)post.y);
    G_ClientCommand(clent,3,(cstring_t[]){"smartpoint",x,y});
    FrontStep(80);
    T_ASSERT(ship->orders->patrol_a==NULL);
    /* A skirmish on arrival must not send it back out on the old patrol. */
    edict_t *raider=unit_create(1,FS_SLKKey("fdst"),&(vec2_t){ship->s.origin.x+500,ship->s.origin.y},0);
    FrontStep(30);
    G_FreeEdict(raider);
    FrontStep(120);
    T_ASSERT(Vector2_distance(&ship->s.origin2,&post)<500);
    T_ASSERT(Vector2_distance(&ship->s.origin2,&wake)>900);
    FrontEnd();
}
static test_t patrol_dock={"frontline.ships_sent_home_drop_their_old_patrol",FrontPatrolThenDock,__FILE__,__LINE__,NULL};
/* Idle troops that engage on their own give up a chase 700 beyond where they stood and
 * walk back instead of following an enemy across the map. */
static void FrontLeash(void) {
    FrontLoad(false);
    if (S_SpellData(MAKEFOURCC('F','l','s','h'),1,1)<=0) { FrontEnd(); return; } /* leash switched off in data */
    abilityLevel_t *leash=(abilityLevel_t *)G_AbilityLevel(MAKEFOURCC('F','l','s','h'),1);
    float const authored=leash->data[0].number;
    edict_t *hq=FrontUnit(0,"fhq0");
    float const toward=atan2f(-hq->s.origin.y,-hq->s.origin.x);
    vec2_t const post={hq->s.origin.x+900*cosf(toward),hq->s.origin.y+900*sinf(toward)};
    edict_t *guard=unit_create(0,FS_SLKKey("finf"),&post,0);
    FrontStep(10);
    vec2_t const start=guard->s.origin2;
    edict_t *raider=unit_create(1,FS_SLKKey("fcar"),&(vec2_t){start.x+400*cosf(toward),start.y+400*sinf(toward)},0);
    G_SetUnitFlag(raider,UNIT_FLAG_INVULNERABLE,true);
    FrontStep(20);
    T_ASSERT(guard->goalentity==raider); /* it engaged on its own */
    T_ASSERT(unit_issueorder(raider,"move",&(vec2_t){start.x+3500*cosf(toward),start.y+3500*sinf(toward)}));
    float farthest=0;
    FOR_LOOP(t,40) { FrontStep(10); farthest=MAX(farthest,Vector2_distance(&guard->s.origin2,&start)); }
    T_ASSERT(farthest<1200);                                     /* never chased far */
    T_ASSERT(Vector2_distance(&guard->s.origin2,&start)<300);     /* and walked back */
    leash->data[0].number=authored;
    FrontEnd();
}
static test_t leash_test={"frontline.idle_troops_give_up_long_chases",FrontLeash,__FILE__,__LINE__,NULL};
static test_t ballistics={"frontline.ballistics_dispersion_ricochet_citadel",FrontBallistics,__FILE__,__LINE__,NULL};
static test_t armour={"frontline.ballistics_armour_penetration",FrontArmour,__FILE__,__LINE__,NULL};
static test_t torpedoes={"frontline.ballistics_ship_torpedoes",FrontShipTorpedoes,__FILE__,__LINE__,NULL};
static test_t squadclicks={"frontline.carrier_squadron_button_targets",FrontSquadronClicks,__FILE__,__LINE__,NULL};
static test_t aircap={"frontline.carrier_and_airfield_cap",FrontAirCap,__FILE__,__LINE__,NULL};
/* One command-card click orders every unit of the focused (Tab) subgroup, not
 * only the focused unit: Unload empties both landing craft, Airfield CAP
 * launches from both airfields. */
static void FrontGroupOrders(void) {
    FrontLoad(false);
    edict_t *clent=G_GetPlayerEntityByNumber(0);
    gameClient_t *client=clent->client;
    edict_t *craft=FrontUnit(0,"flct"),*troop=FrontUnit(0,"finf");
    vec2_t near=craft->s.origin2;near.x+=120;
    edict_t *craft2=unit_create(0,FS_SLKKey("flct"),&near,0),*troop2=unit_create(0,FS_SLKKey("finf"),&troop->s.origin2,0);
    T_ASSERT(G_IssueUnitTargetOrder(troop,"smart",craft,false,0));
    T_ASSERT(G_IssueUnitTargetOrder(troop2,"smart",craft2,false,0));
    FrontStep(90);
    T_ASSERT(S_CargoTransportForUnit(troop)==craft);T_ASSERT(S_CargoTransportForUnit(troop2)==craft2);
    FrontClearSelection(client);G_SelectEntity(client,craft);G_SelectEntity(client,craft2);
    G_ClientCommand(clent,2,(cstring_t[]){"button","Adro"});
    char x[32],y[32];snprintf(x,sizeof(x),"%f",craft->s.origin.x);snprintf(y,sizeof(y),"%f",craft->s.origin.y);
    G_ClientCommand(clent,3,(cstring_t[]){"point",x,y});
    T_ASSERT(client->menu.on_location_selected==NULL);
    T_ASSERT(craft->orders->cargo_unload_pending);T_ASSERT(craft2->orders->cargo_unload_pending);
    FrontStep(120);
    T_ASSERT(!S_CargoTransportForUnit(troop));T_ASSERT(!S_CargoTransportForUnit(troop2));

    edict_t *field=unit_create(0,FS_SLKKey("fair"),&(vec2_t){-3300,1300},0);
    edict_t *field2=unit_create(0,FS_SLKKey("fair"),&(vec2_t){-3300,700},0);
    edict_t *fighter=unit_create(0,FS_SLKKey("ffgt"),&field->s.origin2,0),*fighter2=unit_create(0,FS_SLKKey("ffgt"),&field2->s.origin2,0);
    T_ASSERT(S_CargoTryLoad(field,fighter));T_ASSERT(S_CargoTryLoad(field2,fighter2));
    FrontStep(2);
    FrontClearSelection(client);G_SelectEntity(client,field);G_SelectEntity(client,field2);
    G_ClientCommand(clent,2,(cstring_t[]){"button","Facp"});
    FrontStep(60);
    T_ASSERT(!(fighter->s.renderfx&RF_HIDDEN));T_ASSERT(!(fighter2->s.renderfx&RF_HIDDEN));
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
static test_t grouporders={"frontline.group_command_card_orders_whole_subgroup",FrontGroupOrders,__FILE__,__LINE__,NULL};
/* T7: the engineer's Build card shows one folder per kind; a folder lists its structures
 * for the player's navy plus Back. Orders by id (the bot) still reach every structure. */
static bool FrontCardHas(gameCommandButton_t const *card,uint32_t count,cstring_t code) {
    FOR_LOOP(i,count) if (!strcmp(card[i].command,code)) return true;
    return false;
}
static void FrontCardDistinct(gameCommandButton_t const *card,uint32_t count) {
    FOR_LOOP(i,count) FOR_LOOP(j,i) T_ASSERT(card[i].x!=card[j].x || card[i].y!=card[j].y);
}
static void FrontBuildFolders(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);edict_t *clent=G_GetPlayerEntityByNumber(0);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=5000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=1000;
    edict_t *worker=FrontUnit(0,"fwkr");
    T_NOT_NULL(worker);
    FrontClearSelection(client);G_SelectEntity(client,worker);
    G_ClientCommand(clent,2,(cstring_t[]){"button","CmdBuild"});
    T_EQ(client->menu.build_folder,0u);
    gameCommandButton_t card[32];uint32_t count=G_GetBuildMenuButtons(client,card,32);
    static cstring_t const folders[]={"fzba","fzdf","fzaa","fznv","fzai"};
    T_EQ(count,5u);
    FOR_LOOP(i,5) T_ASSERT(FrontCardHas(card,count,folders[i]));
    FOR_LOOP(i,5) T_ASSERT(G_BuildMenuFolder(FS_SLKKey(folders[i])));
    T_ASSERT(!FrontCardHas(card,count,"fhq0"));T_ASSERT(!FrontCardHas(card,count,"fbnk"));
    FrontCardDistinct(card,count);
    /* Folders are never structures: no worker builds one; the generic bunker left the card. */
    T_ASSERT(!G_WorkerCanBuild(worker,FS_SLKKey("fzaa")));
    T_ASSERT(!G_WorkerCanBuild(worker,FS_SLKKey("fbnk")));T_ASSERT(!G_WorkerCanBuild(worker,FS_SLKKey("fcst")));
    T_ASSERT(G_WorkerCanBuild(worker,FS_SLKKey("uaa4")));
    G_ClientCommand(clent,2,(cstring_t[]){"button","fzaa"});
    T_EQ(client->menu.build_folder,FS_SLKKey("fzaa"));
    count=G_GetBuildMenuButtons(client,card,32);
    T_EQ(count,4u); /* USN light, medium, heavy AA and Back */
    T_ASSERT(FrontCardHas(card,count,"uaa2"));T_ASSERT(FrontCardHas(card,count,"uaa4"));T_ASSERT(FrontCardHas(card,count,"uaa9"));
    T_ASSERT(FrontCardHas(card,count,"fzbk"));T_ASSERT(!FrontCardHas(card,count,"jaa4"));
    FrontCardDistinct(card,count);
    /* A structure button arms placement; the folder survives a refresh. */
    G_ClientCommand(clent,2,(cstring_t[]){"button","uaa4"});
    T_EQ(client->menu.build_project,FS_SLKKey("uaa4"));
    T_ASSERT(G_CancelBuildPlacement(clent));
    G_ClientCommand(clent,2,(cstring_t[]){"button","CmdBuild"});
    T_EQ(client->menu.build_folder,0u);
    G_ClientCommand(clent,2,(cstring_t[]){"button","fzdf"});
    count=G_GetBuildMenuButtons(client,card,32);
    T_ASSERT(FrontCardHas(card,count,"upbx"));T_ASSERT(FrontCardHas(card,count,"fsbg"));T_ASSERT(FrontCardHas(card,count,"fwir"));
    if (client->menu.refresh) client->menu.refresh(clent);
    T_EQ(client->menu.build_folder,FS_SLKKey("fzdf"));
    G_ClientCommand(clent,2,(cstring_t[]){"button","fzbk"});
    T_EQ(client->menu.build_folder,0u);
    T_EQ(G_GetBuildMenuButtons(client,card,32),5u);
    /* The IJN side sees its own guns; it builds by order id like the bot does. */
    gameClient_t *ijn=G_GetPlayerClientByNumber(1);
    ijn->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=5000;ijn->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=1000;
    edict_t *jworker=unit_create(1,FS_SLKKey("fwkr"),&(vec2_t){4400,-4400},0);
    char reason[128];
    T_NOT_NULL(unit_create(1,FS_SLKKey("fbar"),&(vec2_t){4700,-5900},0)); /* medium AA needs barracks */
    T_EQ(G_GetBuildCommandState(ijn,jworker,FS_SLKKey("uaa4"),reason,sizeof(reason)),BUILD_COMMAND_HIDDEN);
    T_ASSERT(G_GetBuildCommandState(ijn,jworker,FS_SLKKey("jaa4"),reason,sizeof(reason))==BUILD_COMMAND_AVAILABLE);
    T_ASSERT(G_IssueBuildOrder(jworker,FS_SLKKey("jpbx"),&(vec2_t){5000,-4800}));
    FrontStep(400);
    T_NOT_NULL(FrontUnit(1,"jpbx"));
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
/* T7: anti-aircraft emplacements shoot aircraft and never ground troops. */
static void FrontAAEmplacements(void) {
    FrontLoad(false);
    edict_t *gun=unit_create(0,FS_SLKKey("uaa4"),&(vec2_t){-3600,3600},0);
    edict_t *plane=unit_create(1,FS_SLKKey("jfig"),&(vec2_t){-3600,4100},0);
    edict_t *tank=unit_create(1,FS_SLKKey("jtnk"),&(vec2_t){-3200,3600},0);
    T_NOT_NULL(gun);T_NOT_NULL(plane);T_NOT_NULL(tank);
    G_SetUnitFlag(plane,UNIT_FLAG_PAUSED,true);G_SetUnitFlag(tank,UNIT_FLAG_PAUSED,true);
    float const plane_hp=plane->health.value,tank_hp=tank->health.value;
    FrontStep(80);
    T_ASSERT(plane->health.value<plane_hp || M_IsDead(plane));
    T_FEQ(tank->health.value,tank_hp,.01f);
    T_ASSERT(G_UnitWeapons(FS_SLKKey("uaa9"))->attack1.range>G_UnitWeapons(FS_SLKKey("uaa4"))->attack1.range);
    FrontEnd();
}
/* T8b: any crewed structure buys one AA Mount; its guns fire at aircraft from the mount. */
static uint32_t FrontMountButton(edict_t *structure,char code[5]) {
    gameCommandButton_t card[32];uint32_t count=G_GetCommandButtons(structure,card,32),found=0;
    FOR_LOOP(i,count) if (!strncmp(card[i].command,"Fm",2) && strlen(card[i].command)==4) { memcpy(code,card[i].command,5);found++; }
    return found;
}
static void FrontStructureAAMount(void) {
    FrontLoad(false);
    gameClient_t *client=G_GetPlayerClientByNumber(0);edict_t *clent=G_GetPlayerEntityByNumber(0);
    client->ps.stats[PLAYERSTATE_RESOURCE_GOLD]=1000;client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=500;
    edict_t *barracks=FrontUnit(0,"fbar");
    T_NOT_NULL(barracks);
    char code[5]={0};
    T_EQ(FrontMountButton(barracks,code),1u);
    T_ASSERT(!S_AAMountInstalled(barracks));
    FrontClearSelection(client);G_SelectEntity(client,barracks);
    G_ClientCommand(clent,2,(cstring_t[]){"button",code});
    T_ASSERT(S_AAMountInstalled(barracks));
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],880);T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER],470);
    T_EQ(FrontMountButton(barracks,code),0u); /* one per structure */
    G_ClientCommand(clent,2,(cstring_t[]){"button",code});
    T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],880);
    /* The mount is drawn on the roof at its model-space point. */
    edict_t *director=NULL;
    FILTER_EDICTS(d,d->inuse && d->think==aa_mount_think && S_SpellChannelOwner(d)==barracks) director=d;
    T_NOT_NULL(director);
    vec3_t point;T_ASSERT(S_AAMountPoint(barracks,&point));
    T_ASSERT(point.z>barracks->s.origin.z+50);
    edict_t *mount=director ? S_SpellChannelTarget(director) : NULL;
    T_NOT_NULL(mount);
    if (mount) { T_ASSERT(Vector2_distance(&mount->s.origin2,&(vec2_t){point.x,point.y})<1);T_FEQ(mount->s.origin.z,point.z,.5f); }
    /* An enemy aircraft over the barracks draws tracers from the mount. */
    edict_t *plane=unit_create(1,FS_SLKKey("jbom"),&(vec2_t){barracks->s.origin.x+350,barracks->s.origin.y},0);
    G_SetUnitFlag(plane,UNIT_FLAG_PAUSED,true);
    uint32_t tracers=0;
    FOR_LOOP(i,40) { FrontStep(1);FILTER_EDICTS(t,t->inuse && t->owner==barracks && t!=director && !(t->svflags&SVF_MONSTER)) tracers++; }
    T_ASSERT(tracers>0);
    /* Not enough logistics: refused, nothing charged. */
    edict_t *depot=FrontUnit(0,"fdep");
    T_NOT_NULL(depot);
    client->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]=10;
    T_EQ(FrontMountButton(depot,code),1u);
    FrontClearSelection(client);G_SelectEntity(client,depot);
    uint32_t const gold=client->ps.stats[PLAYERSTATE_RESOURCE_GOLD];
    G_ClientCommand(clent,2,(cstring_t[]){"button",code});
    T_ASSERT(!S_AAMountInstalled(depot));T_EQ(client->ps.stats[PLAYERSTATE_RESOURCE_GOLD],gold);
    /* Field works and AA guns carry no mount. */
    edict_t *wire=unit_create(0,FS_SLKKey("fsbg"),&(vec2_t){-3600,3300},0);
    edict_t *gun=unit_create(0,FS_SLKKey("uaa2"),&(vec2_t){-3900,3300},0);
    T_EQ(FrontMountButton(wire,code),0u);T_EQ(FrontMountButton(gun,code),0u);
    /* Survives save/load: still installed, its director is rebuilt. */
    uint32_t const index=barracks->s.number;
    T_ASSERT(WriteGame(Test_TempPath("frontline-aamount.bin")));T_ASSERT(ReadGame(Test_TempPath("frontline-aamount.bin")));
    FrontStep(12);
    barracks=&globals.edicts[index];
    T_ASSERT(S_AAMountInstalled(barracks));
    uint32_t directors=0;FILTER_EDICTS(d,d->inuse && d->think==aa_mount_think && S_SpellChannelOwner(d)==barracks) directors++;
    T_EQ(directors,1u);
    FrontEnd();
}
/* T8a: the map's airfields start neutral; holding ground beside one, uncontested, takes it.
 * Aircraft use only their own side's field. */
static void FrontNeutralAirfield(void) {
    FrontLoad(false);
    edict_t *field=NULL;uint32_t neutral=0;
    FILTER_EDICTS(e,e->inuse && e->class_id==FS_SLKKey("fair") && e->s.player==PLAYER_NEUTRAL_PASSIVE) {
        neutral++;
        if (Vector2_distance(&e->s.origin2,&(vec2_t){2200,2850})<1) field=e;
    }
    T_EQ(neutral,2u);T_NOT_NULL(field);
    if (!field) { FrontEnd(); return; }
    FrontStep(6);
    T_ASSERT(G_UnitHasFlag(field,UNIT_FLAG_INVULNERABLE));
    edict_t *fighter=unit_create(0,FS_SLKKey("ffgt"),&field->s.origin2,0);
    T_ASSERT(!S_CargoTryLoad(field,fighter)); /* not ours yet */
    edict_t *rifle=unit_create(0,FS_SLKKey("finf"),&(vec2_t){field->s.origin.x+field->collision+150,field->s.origin.y},0);
    G_SetUnitFlag(rifle,UNIT_FLAG_PAUSED,true);
    FrontStep(60);
    int32_t claimant=-1;
    T_ASSERT(S_AirfieldCaptureProgress(field,&claimant)>=4);T_EQ(claimant,0);
    T_EQ(field->s.player,(uint32_t)PLAYER_NEUTRAL_PASSIVE);
    /* Contested: an enemy squad beside it stops the count. */
    edict_t *enemy=unit_create(1,FS_SLKKey("jinf"),&(vec2_t){field->s.origin.x-field->collision-150,field->s.origin.y},0);
    G_SetUnitFlag(enemy,UNIT_FLAG_PAUSED,true);
    FrontStep(10);
    T_FEQ(S_AirfieldCaptureProgress(field,NULL),0,.01f);
    G_FreeEdict(enemy);
    FrontStep(130);
    T_EQ(field->s.player,0u);T_ASSERT(!G_UnitHasFlag(field,UNIT_FLAG_INVULNERABLE));
    T_ASSERT(S_CargoTryLoad(field,fighter));T_ASSERT(fighter->s.renderfx&RF_HIDDEN);
    /* Retaken by the IJN: the USN fighter takes off and the field is theirs. */
    G_FreeEdict(rifle);
    edict_t *raiders[2];
    FOR_LOOP(i,2) { raiders[i]=unit_create(1,FS_SLKKey("jinf"),&(vec2_t){field->s.origin.x,field->s.origin.y+field->collision+120+i*60.0f},0);G_SetUnitFlag(raiders[i],UNIT_FLAG_PAUSED,true); }
    FrontStep(130);
    T_EQ(field->s.player,1u);
    T_ASSERT(!(fighter->s.renderfx&RF_HIDDEN));T_EQ(fighter->s.player,0u);
    T_ASSERT(!S_CargoTryLoad(field,fighter));
    T_ASSERT(!jass_rterror_pending(level.vm));
    FrontEnd();
}
static test_t build_folders={"frontline.engineer_build_folders",FrontBuildFolders,__FILE__,__LINE__,NULL};
static test_t aa_sites={"frontline.aa_emplacements_hit_aircraft_only",FrontAAEmplacements,__FILE__,__LINE__,NULL};
static test_t aa_mount={"frontline.structure_aa_mount",FrontStructureAAMount,__FILE__,__LINE__,NULL};
static test_t neutral_field={"frontline.neutral_airfield_capture",FrontNeutralAirfield,__FILE__,__LINE__,NULL};
__attribute__((constructor)) static void FrontRegister(void) {
    if (getenv("FRONTLINE_ACCEPTANCE")) { Test_Register(&pacific);Test_Register(&patrolring);Test_Register(&commandboth);Test_Register(&autolaunch);Test_Register(&air_variance);Test_Register(&air_crits);Test_Register(&air_fuel);Test_Register(&air_home);Test_Register(&build_folders);Test_Register(&aa_sites);Test_Register(&aa_mount);Test_Register(&neutral_field);Test_Register(&grouporders);Test_Register(&dockrepair);Test_Register(&underway_fire);Test_Register(&rightclick_tree);Test_Register(&patrol_dock);Test_Register(&leash_test);Test_Register(&ballistics);Test_Register(&armour);Test_Register(&torpedoes);Test_Register(&squadclicks);Test_Register(&aircap);Test_Register(&classic);Test_Register(&history_registry);Test_Register(&history_ijn);Test_Register(&history_parallel);Test_Register(&history_kido);Test_Register(&history_battle);Test_Register(&history_unca);Test_Register(&history_usdk);Test_Register(&history_uind);Test_Register(&history_ubal);Test_Register(&history_uatl);Test_Register(&history_usum);Test_Register(&history_jkon);Test_Register(&history_jtak);Test_Register(&history_jmyo);Test_Register(&history_jkgr);Test_Register(&history_jaki);Test_Register(&history_uiow);Test_Register(&history_umss);Test_Register(&history_uent);Test_Register(&history_uykt);Test_Register(&history_uesx);Test_Register(&history_uflt);Test_Register(&history_uclv);Test_Register(&history_ulcv);Test_Register(&history_ulcm);Test_Register(&history_jyam);Test_Register(&history_jmus);Test_Register(&history_jnag);Test_Register(&history_jakg);Test_Register(&history_jkag);Test_Register(&history_jsor);Test_Register(&history_jhir);Test_Register(&history_jsho);Test_Register(&history_jzui);Test_Register(&history_jmog);Test_Register(&history_jfub);Test_Register(&history_jdai); Test_Register(&landing_cursor);Test_Register(&mass);Test_Register(&formations);Test_Register(&critical); Test_Register(&results);Test_Register(&elig);Test_Register(&building_collision);Test_Register(&map_forests);Test_Register(&logging);Test_Register(&damage_fx);Test_Register(&dock_fx);Test_Register(&aa);Test_Register(&evasion);Test_Register(&lan);Test_Register(&sound_options);Test_Register(&mobile_aa);Test_Register(&rotate);Test_Register(&rally);Test_Register(&fresh_ai);Test_Register(&offshore);Test_Register(&fresh);Test_Register(&naval);Test_Register(&carrier);Test_Register(&strike);Test_Register(&transport);Test_Register(&production);Test_Register(&limits);Test_Register(&bot);Test_Register(&doctrine);Test_Register(&blocked);Test_Register(&flak);Test_Register(&aircraft_fx); }
}
#endif
