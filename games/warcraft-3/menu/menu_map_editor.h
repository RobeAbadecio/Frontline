/*
 * menu_map_editor.h — Island map layouts for the offline pack's map editor.
 *
 * A layout is a coarse land/sea tile grid (128 world units per tile, one tile
 * per W3E cell), a per-tile tree count and extra ore fields. It is read back
 * from a shipped or saved map (WPM pathing + JASS forest calls) and written by
 * patching that map: terrain, pathing, minimap and the script's forest/rim-mine/
 * starting-troop section change; the scenario (HQs, fixed mines, AI) stays authoritative.
 */
#ifndef menu_map_editor_h
#define menu_map_editor_h

#include "common/shared.h"

#define MAP_EDITOR_MAX_TILES 512
#define MAP_EDITOR_MAX_SITES 64
#define MAP_EDITOR_MAX_MINES 32
#define MAP_EDITOR_MAX_TREES 4000
#define MAP_EDITOR_MAX_UNITS 64
#define MAP_EDITOR_TILE 128.0f
#define MAP_EDITOR_TREES_PER_TILE 2
/* Terrain extends this far beyond the playable bounds unless war3mapSites.txt says "playable <half>". */
#define MAP_EDITOR_TERRAIN_MARGIN 1792.0f

/* Starting troops are stored by role so each saved start map gets its own navy's models. */
typedef struct { cstring_t name; char code[2][5]; } mapEditorRole_t;   /* code[0] USN, code[1] IJN */
extern mapEditorRole_t const map_editor_roles[];
extern uint32_t const map_editor_num_roles;

typedef struct { uint8_t side, role; vec2_t pos; } mapEditorUnit_t;     /* side 0 = Player(0) */

typedef enum { MAP_SITE_HQ_ALLIED, MAP_SITE_HQ_ENEMY, MAP_SITE_ORE, MAP_SITE_LAND } mapEditorSiteKind_t;

/* Scenario-owned positions, read from the map's war3mapSites.txt: always land, never forested. */
typedef struct { float x, y, radius; mapEditorSiteKind_t kind; } mapEditorSite_t;

typedef struct {
    uint32_t tiles;                 /* tiles per side (W3E vertices - 1) */
    float origin;                   /* world coordinate of tile 0's lower edge */
    uint8_t land[MAP_EDITOR_MAX_TILES][MAP_EDITOR_MAX_TILES];  /* [y][x], y grows north */
    uint8_t trees[MAP_EDITOR_MAX_TILES][MAP_EDITOR_MAX_TILES];
    uint32_t num_mines;
    vec2_t mines[MAP_EDITOR_MAX_MINES];
    uint32_t num_units;
    mapEditorUnit_t units[MAP_EDITOR_MAX_UNITS];
    uint32_t num_sites;
    mapEditorSite_t sites[MAP_EDITOR_MAX_SITES];
    float playable;                 /* playable half-size in world units */
} mapEditorLayout_t;


vec2_t MapEditor_TileCenter(mapEditorLayout_t const *layout, uint32_t x, uint32_t y);
bool MapEditor_TileLocked(mapEditorLayout_t const *layout, uint32_t x, uint32_t y);
bool MapEditor_TileForestable(mapEditorLayout_t const *layout, uint32_t x, uint32_t y);
uint32_t MapEditor_TreeCount(mapEditorLayout_t const *layout);

/* Pure codecs (no file system); returned buffers are malloc'd. */
bool MapEditor_ReadTerrainHeader(uint8_t const *w3e, uint32_t size, uint32_t *header_size,
                                 uint32_t *vertices, float *origin);
bool MapEditor_DecodePathing(uint8_t const *wpm, uint32_t size, mapEditorLayout_t *layout);
void MapEditor_ParseScript(cstring_t script, mapEditorLayout_t *layout);
/* Lines "hq0|hq1|ore|land x y radius" (tools/frontline/generate.py); hq0 is Player(0)'s. */
void MapEditor_ParseSites(cstring_t text, mapEditorLayout_t *layout);
bool MapEditor_Encode(mapEditorLayout_t const *layout, uint8_t const *base_w3e, uint32_t header_size,
                      uint8_t **w3e, uint32_t *w3e_size, uint8_t **wpm, uint32_t *wpm_size,
                      uint8_t **blp, uint32_t *blp_size);
/* alternate: the start map where Player(0) commands the second navy (IJN). */
string_t MapEditor_PatchScript(cstring_t script, mapEditorLayout_t const *layout, bool alternate);

/* Archive I/O through the menu imports. */
bool MapEditor_Load(cstring_t map_path, mapEditorLayout_t *layout);
bool MapEditor_Save(mapEditorLayout_t const *layout, cstring_t base_map, cstring_t disk_path, cstring_t title,
                    bool alternate);

#endif
