/* Optional real-map acceptance; run only with the generated original pack.
 * EMBERFIELD_ACCEPTANCE=1 openwarcraft3-tests -data build/emberfield +dedicated 1 +test 'emberfield.*'
 * It is intentionally not registered in the retail-shaped fixture suites. */
#ifdef BZ_TESTS
#include "../g_local.h"
#include "shared/test.h"
#include "../hud/hud_local.h"
#include "../skills/s_skills.h"
#include <stdlib.h>

static uint32_t ember_time;
static uint32_t EmberTime(void) { return ember_time; }
static edict_t *EmberUnit(uint32_t owner, uint32_t type) {
    for (uint32_t i = game.max_clients; i < globals.num_edicts; i++) {
        edict_t *e = globals.edicts + i;
        if (e->inuse && e->s.player == owner && e->class_id == type && e->health.value > 0) return e;
    }
    return NULL;
}
static uint32_t EmberCount(uint32_t owner, uint32_t type) {
    uint32_t count = 0;
    for (uint32_t i = game.max_clients; i < globals.num_edicts; i++) {
        edict_t *e = globals.edicts + i;
        if (e->inuse && e->s.player == owner && e->class_id == type && e->health.value > 0 && !e->build) count++;
    }
    return count;
}
static void EmberfieldMatch(void) {
    uint32_t (*old_time)(void) = gi.GetTime;
    uint32_t peak = 0, peak_bow = 0, peak_medic = 0, peak_ram = 0, peak_wing = 0, peak_seer = 0;
    uint32_t peak_roost = 0, peak_workshop = 0, peak_sanctum = 0, peak_tower = 0;
    edict_t *base;
    gameCommandButton_t button;
    gameClient_t *human, *bot;
    gi.GetTime = EmberTime; ember_time = 0;
    CM_SetupTestWorldBounds(NULL);
    T_ASSERT(globals.PrepareMap("Maps/Emberfield/FirstLight.w3m"));
    T_ASSERT(globals.LoadMap("Maps/Emberfield/FirstLight.w3m"));
    T_NOT_NULL(level.vm);
    T_ASSERT(!jass_rterror_pending(level.vm));
    T_NOT_NULL(level.bots[1].vm);
    human = G_GetPlayerClientByNumber(0);
    bot = G_GetPlayerClientByNumber(1);
    base = EmberUnit(0, MAKEFOURCC('e','h','u','b'));
    T_NOT_NULL(base);
    T_ASSERT(G_BuildCommandButton(EmberUnit(0, MAKEFOURCC('e','w','r','k')), "AHbu", false, 0, &button));
    T_ASSERT(G_BuildCommandButton(EmberUnit(0, MAKEFOURCC('e','f','a','b')), "egrd", false, 0, &button));
    /* Exercise the same commands sent by native HUD/touch hit testing. */
    {
        edict_t *controller = G_GetPlayerEntityByNumber(0);
        edict_t *forge = EmberUnit(0, MAKEFOURCC('e','f','a','b'));
        edict_t *guard = EmberUnit(0, MAKEFOURCC('e','g','r','d'));
        char number[16];
        uint32_t gold = human->ps.stats[PLAYERSTATE_RESOURCE_GOLD];
        fprintf(stderr, "EMBERFIELD_HUD forge=%u guard=%u\n", forge->s.number, guard->s.number);
        T_NOT_NULL(hud.menu.ReturnButton);
        T_NOT_NULL(hud.menu.EscMenuBackdrop);
        T_ASSERT(hud.menu.ReturnButton->Height * 834.0f / 0.6f >= 44.0f);
        T_ASSERT(hud.res.ResourceBarGoldText->Font.Color.a == 255);
        T_ASSERT(hud.res.ResourceBarLumberText->Font.Color.a == 255);
        T_NOT_NULL(hud.unit.NameValue);
        T_NOT_NULL(hud.simple.SimpleNameValue);
        T_ASSERT(!strcmp(hud.simple.SimpleNameValue->Font.Name, "MasterFont"));
        T_NOT_NULL(hud.simple.SimpleBuildingNameValue);
        T_ASSERT(!strcmp(hud.simple.SimpleBuildingNameValue->Font.Name, "MasterFont"));
        T_NOT_NULL(UI_FindFrame("ControlGroup1Recall"));
        T_NOT_NULL(UI_FindFrame("ControlGroup1Assign"));
        T_ASSERT(!strcmp(UI_FindFrame("ControlGroup1Recall")->OnClick, "group 1"));
        T_ASSERT(!strcmp(UI_FindFrame("ControlGroup1Assign")->OnClick, "group assign 1"));
        T_ASSERT(UI_FindFrame("ControlGroupBarFrame")->Parent == hud.console.ConsoleUI);
        T_ASSERT(G_BuildCommandButton(guard, "CmdAttack", false, 0, &button));
        T_EQ(button.x, 3); T_EQ(button.y, 0);
        snprintf(number, sizeof(number), "%u", forge->s.number);
        G_ClientCommand(controller, 2, (cstring_t[]){ "select", number });
        T_ASSERT(G_GetMainSelectedUnit(human) == forge);
        G_ClientCommand(controller, 2, (cstring_t[]){ "button", "egrd" });
        T_EQ(G_ProductionQueueCount(forge), 1);
        T_EQ(human->ps.stats[PLAYERSTATE_RESOURCE_GOLD], gold - 65);
        G_ClientCommand(controller, 2, (cstring_t[]){ "canceltrain", "0" });
        T_EQ(G_ProductionQueueCount(forge), 0);
        T_EQ(human->ps.stats[PLAYERSTATE_RESOURCE_GOLD], gold);
        /* Resource rejection stays authoritative even when the command is visible. */
        human->ps.stats[PLAYERSTATE_RESOURCE_GOLD] = 0;
        T_ASSERT(G_BuildCommandButton(forge, "egrd", false, 0, &button));
        G_ClientCommand(controller, 2, (cstring_t[]){ "button", "egrd" });
        T_EQ(G_ProductionQueueCount(forge), 0);
        human->ps.stats[PLAYERSTATE_RESOURCE_GOLD] = gold;
        snprintf(number, sizeof(number), "%u", guard->s.number);
        G_ClientCommand(controller, 2, (cstring_t[]){ "select", number });
        G_ClientCommand(controller, 2, (cstring_t[]){ "button", "CmdStop" });
        T_ASSERT(G_GetMainSelectedUnit(human) == guard);
        /* Leave the opening battle unchanged for the bot completion test. */
    }
    for (uint32_t i = 0; i < 6000 && !human->jass.removed; i++) {
        ember_time += 100;
        globals.RunFrame();
        peak = MAX(peak, EmberCount(1, MAKEFOURCC('e','g','r','d')));
        peak_bow = MAX(peak_bow, EmberCount(1, MAKEFOURCC('e','b','o','w')));
        peak_medic = MAX(peak_medic, EmberCount(1, MAKEFOURCC('e','m','e','d')));
        peak_ram = MAX(peak_ram, EmberCount(1, MAKEFOURCC('e','r','a','m')));
        peak_wing = MAX(peak_wing, EmberCount(1, MAKEFOURCC('e','w','n','g')));
        peak_seer = MAX(peak_seer, EmberCount(1, MAKEFOURCC('E','s','e','e')));
        peak_roost = MAX(peak_roost, EmberCount(1, MAKEFOURCC('e','a','e','r')));
        peak_workshop = MAX(peak_workshop, EmberCount(1, MAKEFOURCC('e','w','s','p')));
        peak_sanctum = MAX(peak_sanctum, EmberCount(1, MAKEFOURCC('e','s','n','c')));
        peak_tower = MAX(peak_tower, EmberCount(1, MAKEFOURCC('e','t','w','r')));
    }
    T_ASSERT(!jass_rterror_pending(level.vm));
    T_ASSERT(bot->ps.stats[PLAYERSTATE_GOLD_GATHERED] > 0);
    T_ASSERT(peak > 3);
    T_ASSERT(peak_bow > 0);
    T_ASSERT(peak_tower > 1);
    T_ASSERT(peak_medic > 0);
    T_ASSERT(peak_ram > 0);
    T_ASSERT(peak_wing > 0);
    T_ASSERT(peak_seer > 0);
    T_ASSERT(bot->ps.stats[PLAYERSTATE_LUMBER_GATHERED] > 0);
    T_ASSERT(!base || base->health.value < 1600);
    T_ASSERT(human->jass.removed);
    T_EQ(human->ps.stats[PLAYERSTATE_GAME_RESULT], 1);
    fprintf(stderr, "EMBERFIELD_ACCEPTANCE time=%u bot_gold=%u peak_guards=%u base_hp=%.1f removed=%u result=%u\n",
        ember_time, bot->ps.stats[PLAYERSTATE_GOLD_GATHERED], peak,
        base ? base->health.value : -1.0f, human->jass.removed,
        human->ps.stats[PLAYERSTATE_GAME_RESULT]);
    fprintf(stderr,"EMBERFIELD_AI lumber=%u bows=%u medics=%u siege=%u flyers=%u seers=%u roosts=%u workshops=%u sanctums=%u towers=%u\n",bot->ps.stats[PLAYERSTATE_LUMBER_GATHERED],peak_bow,peak_medic,peak_ram,peak_wing,peak_seer,peak_roost,peak_workshop,peak_sanctum,peak_tower);
    gi.GetTime = old_time;
    G_BotShutdown();
}
static void EmberfieldEconomy(void) {
    uint32_t (*old_time)(void) = gi.GetTime;
    edict_t *worker, *building, *tree = NULL;
    gi.GetTime = EmberTime; ember_time = 0;
    CM_SetupTestWorldBounds(NULL);
    T_ASSERT(globals.PrepareMap("Maps/Emberfield/FirstLight.w3m"));
    T_ASSERT(globals.LoadMap("Maps/Emberfield/FirstLight.w3m"));
    G_BotShutdown();
    worker = EmberUnit(0, MAKEFOURCC('e','w','r','k'));
    T_NOT_NULL(worker);
    T_ASSERT(G_IssueBuildOrder(worker, MAKEFOURCC('e','h','o','m'), &(vec2_t){-1050,-700}));
    for (uint32_t i = 0; i < 400; i++) { ember_time += 100; globals.RunFrame(); }
    building = EmberUnit(0, MAKEFOURCC('e','h','o','m'));
    T_NOT_NULL(building);
    if (building) {
        fprintf(stderr,"EMBERFIELD_BUILD complete=%u hp=%.1f progress=%.1f worker_move=%s\n",!building->construction,building->health.value,building->construction?building->construction->progress:0,worker->currentmove?worker->currentmove->animation:"none");
        T_ASSERT(!building->construction);
        T_FEQ(building->health.value,building->health.max_value,.1f);
    }
    for (uint32_t i=game.max_clients;i<globals.num_edicts;i++)
        if (g_edicts[i].inuse && g_edicts[i].targtype == TARG_TREE) { tree=g_edicts+i; break; }
    T_NOT_NULL(tree);
    if (tree) {
        uint32_t before=G_GetPlayerClientByNumber(0)->ps.stats[PLAYERSTATE_RESOURCE_LUMBER];
        T_ASSERT(S_HarvestCanLumber(worker));
        T_ASSERT(G_IssueUnitTargetOrder(worker,"harvest",tree,false,0));
        for (uint32_t i=0;i<600;i++) { ember_time+=100;globals.RunFrame(); }
        T_ASSERT(G_GetPlayerClientByNumber(0)->ps.stats[PLAYERSTATE_RESOURCE_LUMBER]>before);
    }
    gi.GetTime = old_time;
}
static void EmberfieldRoster(void) {
    uint32_t (*old_time)(void) = gi.GetTime;
    gameClient_t *human;
    edict_t *forge, *roost, *workshop, *sanctum, *tower, *hero, *seer_unit, *enemy, *ally;
    uint32_t bow = MAKEFOURCC('e','b','o','w'), wing = MAKEFOURCC('e','w','n','g');
    uint32_t ram = MAKEFOURCC('e','r','a','m'), medic = MAKEFOURCC('e','m','e','d');
    uint32_t bastion = MAKEFOURCC('e','b','s','t'), seer = MAKEFOURCC('E','s','e','e');
    gameCommandButton_t button;
    gi.GetTime = EmberTime; ember_time = 0;
    CM_SetupTestWorldBounds(NULL);
    T_ASSERT(globals.PrepareMap("Maps/Emberfield/FirstLight.w3m"));
    T_ASSERT(globals.LoadMap("Maps/Emberfield/FirstLight.w3m"));
    G_BotShutdown();
    human = G_GetPlayerClientByNumber(0);
    human->ps.stats[PLAYERSTATE_RESOURCE_GOLD] = 10000;
    human->ps.stats[PLAYERSTATE_RESOURCE_LUMBER] = 10000;
    human->ps.stats[PLAYERSTATE_RESOURCE_FOOD_CAP] = 1000;
    forge = EmberUnit(0, MAKEFOURCC('e','f','a','b'));
    tower = EmberUnit(0, MAKEFOURCC('e','t','w','r'));
    hero = EmberUnit(0, MAKEFOURCC('E','w','a','r'));
    T_NOT_NULL(forge); T_NOT_NULL(tower); T_NOT_NULL(hero);
    T_NOT_NULL(hud.simple.InfoPanelIconHeroStrengthLabel);
    T_ASSERT(hud.simple.InfoPanelIconHeroStrengthLabel->Width > 0);
    T_ASSERT(G_BuildCommandButton(hero,"AHtb",false,0,&button));
    T_EQ(button.x,0); T_EQ(button.y,2);
    T_ASSERT(G_WorkerCanBuild(EmberUnit(0,MAKEFOURCC('e','w','r','k')),MAKEFOURCC('e','t','w','r')));
    T_ASSERT(G_WorkerCanBuild(EmberUnit(0,MAKEFOURCC('e','w','r','k')),MAKEFOURCC('e','s','n','c')));
    T_ASSERT(G_BuildCommandButton(forge, "ebow", false, 0, &button));
    T_ASSERT(SP_TrainUnit(forge, bow));
    roost = unit_create(0, MAKEFOURCC('e','a','e','r'), &(vec2_t){-1900,-300}, 0);
    workshop = unit_create(0, MAKEFOURCC('e','w','s','p'), &(vec2_t){-1900,-550}, 0);
    sanctum = unit_create(0, MAKEFOURCC('e','s','n','c'), &(vec2_t){-1900,550}, 0);
    T_NOT_NULL(roost); T_NOT_NULL(workshop); T_NOT_NULL(sanctum);
    T_ASSERT(SP_TrainUnit(roost, wing));
    T_ASSERT(SP_TrainUnit(workshop, ram));
    T_ASSERT(SP_TrainUnit(sanctum, medic));
    T_ASSERT(SP_TrainUnit(sanctum, seer));
    for (uint32_t i=0; i<360; i++) { ember_time+=100; globals.RunFrame(); }
    T_ASSERT(EmberCount(0,bow)>0);
    T_ASSERT(EmberCount(0,wing)>0);
    T_ASSERT(EmberCount(0,ram)>0);
    T_ASSERT(EmberCount(0,medic)>0);
    T_ASSERT(EmberCount(0,seer)>0);
    T_EQ(EmberUnit(0,wing)->targtype,TARG_AIR);
    T_EQ(G_UnitAbilityLevel(EmberUnit(0,medic),MAKEFOURCC('A','h','e','a')),1);
    T_ASSERT(hero->unit_state->hero.level>=1);
    T_EQ(G_HeroSkillLevel(hero,MAKEFOURCC('A','H','t','b')),1);
    T_ASSERT(hero->unit_state->hero.str>=22);
    G_HeroSetXP(hero,G_HeroXPForLevel(3));
    T_ASSERT(hero->unit_state->hero.level>=3);
    T_ASSERT(G_HeroLearnSkill(hero,MAKEFOURCC('A','H','t','c')));
    enemy = unit_create(1,MAKEFOURCC('e','g','r','d'),&(vec2_t){-1200,450},0);
    T_NOT_NULL(enemy);
    if (enemy) {
        float mana_start=hero->mana.value;
        T_ASSERT(S_CastUnitTargetSpell(hero,MAKEFOURCC('A','H','t','b'),enemy));
        for (uint32_t i=0; i<20; i++) { ember_time+=100; globals.RunFrame(); }
        T_ASSERT(hero->mana.value<mana_start);
        T_ASSERT(!S_SpellCooldownReady(hero,MAKEFOURCC('A','H','t','b')));
    }
    seer_unit=EmberUnit(0,seer);
    ally=unit_create(0,MAKEFOURCC('e','g','r','d'),&(vec2_t){-1700,550},0);
    T_NOT_NULL(seer_unit); T_NOT_NULL(ally);
    if (seer_unit && ally) {
        ally->health.value=ally->health.max_value-160;
        T_ASSERT(G_HeroLearnSkill(seer_unit,MAKEFOURCC('A','H','h','b')));
        T_ASSERT(G_BuildCommandButton(seer_unit,"AHhb",false,0,&button));
        T_ASSERT(S_CastUnitTargetSpell(seer_unit,MAKEFOURCC('A','H','h','b'),ally));
        for (uint32_t i=0; i<12; i++) { ember_time+=100; globals.RunFrame(); }
        T_ASSERT(ally->health.value>ally->health.max_value-160);
        ally->health.value=ally->health.max_value-60;
        T_ASSERT(S_CastUnitTargetSpell(EmberUnit(0,medic),MAKEFOURCC('A','h','e','a'),ally));
        for (uint32_t i=0; i<12; i++) { ember_time+=100; globals.RunFrame(); }
        T_ASSERT(ally->health.value>ally->health.max_value-60);
    }
    T_ASSERT(G_BuildCommandButton(tower,"ebst",false,0,&button));
    T_ASSERT(G_StartBuildingUpgrade(tower,bastion));
    for (uint32_t i=0; i<300; i++) { ember_time+=100; globals.RunFrame(); }
    T_EQ(tower->class_id,bastion);
    ally = unit_create(0,MAKEFOURCC('e','g','r','d'),&(vec2_t){-550,-550},0);
    T_NOT_NULL(ally);
    if (ally) {
        float ally_start=ally->health.value;
        for (uint32_t i=0; i<40; i++) { ember_time+=100; globals.RunFrame(); }
        T_FEQ(ally->health.value,ally_start,.1f);
    }
    enemy = unit_create(1,MAKEFOURCC('e','g','r','d'),&(vec2_t){-450,-350},0);
    T_NOT_NULL(enemy);
    if (enemy) {
        float enemy_start=enemy->health.value;
        bool tower_acquired=false;
        for (uint32_t i=0; i<80; i++) {
            ember_time+=100; globals.RunFrame();
            tower_acquired |= tower->goalentity == enemy || tower->combatentity == enemy;
        }
        T_ASSERT(enemy->health.value<enemy_start);
        T_ASSERT(tower_acquired);
    }
    T_ASSERT(!jass_rterror_pending(level.vm));
    fprintf(stderr,"EMBERFIELD_ROSTER bow=%u wing=%u ram=%u medic=%u seer=%u tower=%c%c%c%c\n",EmberCount(0,bow),EmberCount(0,wing),EmberCount(0,ram),EmberCount(0,medic),EmberCount(0,seer),tower->class_id&255,(tower->class_id>>8)&255,(tower->class_id>>16)&255,(tower->class_id>>24)&255);
    gi.GetTime = old_time;
}
static test_t emberfield_economy = { "emberfield.worker_builds_and_returns_lumber", EmberfieldEconomy, __FILE__, __LINE__, NULL };
static test_t emberfield_roster = { "emberfield.roster_trains_upgrades_and_defends", EmberfieldRoster, __FILE__, __LINE__, NULL };
static test_t emberfield_match = { "emberfield.original_map_bot_completes_match", EmberfieldMatch, __FILE__, __LINE__, NULL };
__attribute__((constructor)) static void EmberRegister(void) {
    if (getenv("EMBERFIELD_ACCEPTANCE")) { Test_Register(&emberfield_match); Test_Register(&emberfield_economy); Test_Register(&emberfield_roster); }
}
#endif
