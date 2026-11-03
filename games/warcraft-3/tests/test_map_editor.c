#include <stdlib.h>
#include <string.h>

#include "test.h"
#include "../menu/menu_map_editor.h"

static uint8_t *test_w3e(uint32_t tiles, float origin, uint32_t *size) {
    uint32_t v = tiles + 1, header = 45;
    uint8_t *w3e = calloc(1, header + v * v * 7);
    uint32_t fields[] = { v, v };
    memcpy(w3e, "W3E!", 4);
    w3e[4] = 11; w3e[8] = 'L'; w3e[13] = 2;
    memcpy(w3e + 17, "EgrsEsnd", 8);
    memcpy(w3e + 29, fields, 8);
    memcpy(w3e + 37, &origin, 4);
    memcpy(w3e + 41, &origin, 4);
    *size = header + v * v * 7;
    return w3e;
}

TEST(map_editor, terrain_round_trip_keeps_the_painted_coast) {
    static mapEditorLayout_t layout, decoded;
    uint32_t size, header, verts, w3e_size, wpm_size, blp_size;
    float origin;
    uint8_t *w3e, *wpm, *blp, *base = test_w3e(24, -1536.0f, &size);

    T_ASSERT(MapEditor_ReadTerrainHeader(base, size, &header, &verts, &origin));
    T_EQ(header, 45u);
    T_EQ(verts, 25u);
    T_FEQ(origin, -1536.0f, 0.001f);
    layout.tiles = 24;
    layout.origin = origin;
    for (uint32_t y = 4; y < 14; y++) for (uint32_t x = 6; x < 20; x++) layout.land[y][x] = 1;
    layout.land[18][3] = 1;                                  /* a one-tile islet survives smoothing */
    T_ASSERT(MapEditor_Encode(&layout, base, header, &w3e, &w3e_size, &wpm, &wpm_size, &blp, &blp_size));
    T_EQ(w3e_size, size);
    T_EQ(wpm_size, 16u + 96u * 96u);
    T_EQ(blp_size, 148u + 256u * 256u * 4u);
    T_ASSERT(!memcmp(blp, "BLP2", 4));
    decoded.tiles = 24;
    decoded.origin = origin;
    T_ASSERT(MapEditor_DecodePathing(wpm, wpm_size, &decoded));
    T_ASSERT(!memcmp(layout.land, decoded.land, sizeof(layout.land)));
    /* Inland vertices rise above the water plane, open sea sinks below it. */
    uint8_t const *inland = w3e + header + (9 * 25 + 13) * 7, *sea = w3e + header + (22 * 25 + 22) * 7;
    T_ASSERT((inland[0] | inland[1] << 8) > 8192);
    T_ASSERT((sea[0] | sea[1] << 8) < 8192);
    free(base); free(w3e); free(wpm); free(blp);
}

TEST(map_editor, script_patch_round_trips_forests_and_ore) {
    static mapEditorLayout_t layout, parsed;
    cstring_t script =
        "globals\nendglobals\n"
        "function FrontlineForest0 takes nothing returns nothing\n"
        "    call CreateDestructable('epin', 100.0, 100.0, 0.0, 1.00, 0)\n"
        "endfunction\n"
        "function FrontlineRimMines takes nothing returns nothing\n    local unit ore\nendfunction\n"
        "function main takes nothing returns nothing\n"
        "    set ore = CreateUnit(Player(15), 'eore', -side*2550.0, -side*3300.0, 0.0)\n"
        "    call FrontlineForest0()\n"
        "    call FrontlineRimMines()\n"
        "    call SetCameraPosition(-4800.0, 4700.0)\nendfunction\n";

    layout.tiles = parsed.tiles = 160;
    layout.origin = parsed.origin = -10240.0f;
    MapEditor_ParseScript(script, &parsed);
    T_EQ(MapEditor_TreeCount(&parsed), 1u);
    T_EQ(parsed.num_mines, 0u);                            /* scenario ore in main is not editor-owned */
    for (uint32_t x = 0; x < 70; x++) layout.trees[10][x] = 2;   /* 140 trees: three chunks */
    layout.num_mines = 2;
    layout.mines[0] = MAKE(vec2_t, 7200, 7200);
    layout.mines[1] = MAKE(vec2_t, -7200, -7200);
    layout.num_units = 2;
    layout.units[0] = (mapEditorUnit_t){ 0, 3, { -4000, 5000 } };     /* Medium Tank */
    layout.units[1] = (mapEditorUnit_t){ 1, 0, { 4000, -5000 } };     /* Rifle Squad */
    string_t alternate = MapEditor_PatchScript(script, &layout, true);
    T_NOT_NULL(strstr(alternate, "call CreateUnit(Player(0), 'jtnk', -4000.0, 5000.0"));   /* Player(0) is IJN there */
    T_NOT_NULL(strstr(alternate, "call CreateUnit(Player(1), 'finf', 4000.0, -5000.0"));
    free(alternate);
    string_t patched = MapEditor_PatchScript(script, &layout, false);
    T_NOT_NULL(patched);
    T_NOT_NULL(strstr(patched, "    call FrontlineForest2()\n    call FrontlineRimMines()\n    call SetCameraPosition"));
    T_NULL(strstr(patched, "FrontlineForest3"));
    T_NOT_NULL(strstr(patched, "-side*2550.0"));
    MapEditor_ParseScript(patched, &parsed);
    T_EQ(MapEditor_TreeCount(&parsed), 140u);
    T_EQ(parsed.trees[10][69], 2u);
    T_EQ(parsed.num_mines, 2u);
    T_FEQ(parsed.mines[1].x, -7200.0f, 0.5f);
    T_NOT_NULL(strstr(patched, "call CreateUnit(Player(0), 'ftnk', -4000.0, 5000.0"));
    T_EQ(parsed.num_units, 2u);
    T_EQ(parsed.units[0].role, 3u);
    T_EQ(parsed.units[1].side, 1u);
    T_FEQ(parsed.units[1].pos.y, -5000.0f, 0.5f);
    free(patched);
    T_NULL(MapEditor_PatchScript("function main takes nothing returns nothing\n", &layout, false));
}

TEST(map_editor, scenario_sites_come_from_the_map_and_stay_land_and_clear) {
    static mapEditorLayout_t layout;
    uint32_t hx, hy;
    layout.tiles = 156;
    layout.origin = -9984.0f;
    memset(layout.land, 1, sizeof(layout.land));
    MapEditor_ParseSites("hq0 -5400 5400 700\nhq1 5400 -5400 700\nore -6000 6000 450\nbogus 1 2 3\nland 3800 1650 450\n", &layout);
    T_EQ(layout.num_sites, 4u);
    T_EQ(layout.sites[1].kind, MAP_SITE_HQ_ENEMY);
    T_EQ(layout.sites[3].kind, MAP_SITE_LAND);
    T_FEQ(layout.playable, 9984.0f - 1792.0f, 0.5f);                  /* default margin */
    MapEditor_ParseSites("playable 8000 0 0\nhq0 -5400 5400 700\n", &layout);
    T_FEQ(layout.playable, 8000.0f, 0.5f);
    MapEditor_ParseSites("hq0 -5400 5400 700\nhq1 5400 -5400 700\nore -6000 6000 450\nland 3800 1650 450\n", &layout);
    hx = (uint32_t)((-5400.0f + 9984.0f) / 128.0f);
    hy = (uint32_t)((5400.0f + 9984.0f) / 128.0f);
    T_ASSERT(MapEditor_TileLocked(&layout, hx, hy));
    T_ASSERT(!MapEditor_TileForestable(&layout, hx + 6, hy));   /* inside the 1000-unit building clearing */
    T_ASSERT(MapEditor_TileForestable(&layout, hx + 12, hy + 12));
    T_ASSERT(!MapEditor_TileLocked(&layout, 78, 78));           /* open ocean centre */
}
