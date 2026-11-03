/*
 * ui/screens/map_editor.c — Top-down island editor for offline packs.
 *
 * Available when the skin names an OfflineSkirmishMap. Everything is drawn and
 * hit-tested here (no FDF), so one pointer path serves mouse and touch: press
 * a tool, then drag on the map. Saves go to the writable user Maps/Custom tree
 * as one map per base start (Command USN / Command IJN).
 */

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../menu_local.h"
#include "../menu_screen.h"
#include "../menu_map_editor.h"

#define ME_UNDO 8
#define ME_LIST 10
#define ME_PREFIX "Island "
#define ME_LAST_CVAR "map_editor_last"

typedef enum { TOOL_LAND, TOOL_SEA, TOOL_FOREST, TOOL_CLEAR, TOOL_ORE, TOOL_TROOPS } meTool_t;

typedef enum {
    BTN_LAND, BTN_SEA, BTN_FOREST, BTN_CLEAR, BTN_ORE, BTN_MIRROR, BTN_TROOPS, BTN_SIDE, BTN_ROLE, BTN_BRUSH, BTN_UNDO,
    BTN_NEW, BTN_OPEN, BTN_SAVE, BTN_SAVE_NEW, BTN_PLAY, BTN_PLAY_ALT, BTN_BACK, BTN_COUNT,
    BTN_LIST = 100, BTN_LIST_CANCEL = 200,
} meButton_t;

static mapEditorLayout_t me_layout;
static mapEditorLayout_t me_undo[ME_UNDO];
static uint32_t me_undo_count;
static meTool_t me_tool = TOOL_LAND;
static uint32_t me_brush = 1;                   /* index into me_brushes */
static float const me_brushes[] = { 1.0f, 2.5f, 5.0f };  /* tiles on a 156-tile map; scaled with map size */
static cstring_t const me_brush_names[] = { "Small", "Medium", "Large" };
static bool me_mirror = true, me_painting, me_loaded, me_listing;
static uint8_t me_side, me_role;               /* troop placement: owner and map_editor_roles index */
static vec2_t me_last;
static char me_name[64];                        /* "" until first saved */
static char me_status[128];
static char me_maps[ME_LIST][64];
static uint32_t me_num_maps;

static cstring_t ME_Theme(cstring_t key) {
    cstring_t value = Theme_String(key, "Default");
    return value && *value && strcmp(value, key) ? value : NULL;
}

static void ME_Status(cstring_t fmt, cstring_t arg) {
    snprintf(me_status, sizeof(me_status), fmt, arg ? arg : "");
}

/* ---- Layout of the screen (FDF units) ---- */

/* Square on screen: FDF units are stretched differently per axis on wide windows. */
static rect_t ME_Canvas(void) {
    rect_t scene = UI_GetSceneRect();
    refExport_t *re = mi.GetRenderer();
    size2_t window = re && re->GetWindowSize ? re->GetWindowSize() : MAKE(size2_t, 0, 0);
    float h = scene.h - 0.04f, w = h;
    if (window.width && window.height) w = h * ((float)window.height / scene.h) / ((float)window.width / scene.w);
    w = MIN(w, scene.w * 0.72f);
    return MAKE(rect_t, scene.x + 0.02f, scene.y + 0.02f, w, h);
}

static rect_t ME_Panel(void) {
    rect_t scene = UI_GetSceneRect(), canvas = ME_Canvas();
    float x = canvas.x + canvas.w + 0.02f;
    return MAKE(rect_t, x, canvas.y, scene.x + scene.w - 0.02f - x, canvas.h);
}

static bool ME_Inside(rect_t r, float x, float y) {
    return x >= r.x && y >= r.y && x < r.x + r.w && y < r.y + r.h;
}

/* Two columns of rows; slot = row * 2 + column, wide buttons take both columns. */
static rect_t ME_Slot(uint32_t row, uint32_t col, bool wide) {
    rect_t panel = ME_Panel();
    float gap = 0.006f, h = 0.03f, w = (panel.w - gap) * 0.5f;
    return MAKE(rect_t, panel.x + col * (w + gap), panel.y + 0.04f + row * (h + gap), wide ? panel.w : w, h);
}

typedef struct { meButton_t id; uint32_t row, col; bool wide; } meButtonPlace_t;
static meButtonPlace_t const me_places[] = {
    { BTN_LAND, 0, 0 }, { BTN_SEA, 0, 1 }, { BTN_FOREST, 1, 0 }, { BTN_CLEAR, 1, 1 },
    { BTN_ORE, 2, 0 }, { BTN_MIRROR, 2, 1 }, { BTN_TROOPS, 3, 0 }, { BTN_SIDE, 3, 1 }, { BTN_ROLE, 4, 0, true },
    { BTN_BRUSH, 5, 0, true }, { BTN_UNDO, 6, 0 }, { BTN_NEW, 6, 1 },
    { BTN_OPEN, 7, 0 }, { BTN_SAVE, 7, 1 }, { BTN_SAVE_NEW, 8, 0, true },
    { BTN_PLAY, 9, 0 }, { BTN_PLAY_ALT, 9, 1 }, { BTN_BACK, 13, 0, true },
};

static void ME_Label(meButton_t id, string_t out, size_t size) {
    switch (id) {
    case BTN_LAND: snprintf(out, size, "Land"); break;
    case BTN_SEA: snprintf(out, size, "Sea"); break;
    case BTN_FOREST: snprintf(out, size, "Forest"); break;
    case BTN_CLEAR: snprintf(out, size, "Clear"); break;
    case BTN_ORE: snprintf(out, size, "Ore field"); break;
    case BTN_MIRROR: snprintf(out, size, "Mirror: %s", me_mirror ? "On" : "Off"); break;
    case BTN_TROOPS: snprintf(out, size, "Troops"); break;
    case BTN_SIDE: snprintf(out, size, "Side: %s", me_side ? "Enemy" : "Allied"); break;
    case BTN_ROLE: snprintf(out, size, "Unit: %s", map_editor_roles[me_role].name); break;
    case BTN_BRUSH: snprintf(out, size, "Brush: %s", me_brush_names[me_brush]); break;
    case BTN_UNDO: snprintf(out, size, "Undo"); break;
    case BTN_NEW: snprintf(out, size, "New"); break;
    case BTN_OPEN: snprintf(out, size, "Load map"); break;
    case BTN_SAVE: snprintf(out, size, "Save"); break;
    case BTN_SAVE_NEW: snprintf(out, size, "Save as new map"); break;
    case BTN_PLAY: snprintf(out, size, "%s", ME_Theme("OfflineSkirmishLabel") ? ME_Theme("OfflineSkirmishLabel") : "Play"); break;
    case BTN_PLAY_ALT: snprintf(out, size, "%s", ME_Theme("OfflineAlternateSkirmishLabel") ? ME_Theme("OfflineAlternateSkirmishLabel") : "Play alternate"); break;
    case BTN_BACK: snprintf(out, size, "Back to menu"); break;
    default: out[0] = 0; break;
    }
}

static bool ME_ButtonActive(meButton_t id) {
    return (id == BTN_LAND && me_tool == TOOL_LAND) || (id == BTN_SEA && me_tool == TOOL_SEA) ||
           (id == BTN_FOREST && me_tool == TOOL_FOREST) || (id == BTN_CLEAR && me_tool == TOOL_CLEAR) ||
           (id == BTN_ORE && me_tool == TOOL_ORE) || (id == BTN_TROOPS && me_tool == TOOL_TROOPS) ||
           (id == BTN_MIRROR && me_mirror);
}

/* ---- Map files ---- */

/* Custom maps are "Maps\Custom\<name>.w3m" plus "<name> (alt).w3m" for the alternate start. */
static void ME_MapPath(cstring_t name, bool alternate, string_t out, size_t size) {
    snprintf(out, size, "Maps\\Custom\\%s%s.w3m", name, alternate ? " (alt)" : "");
}

static void ME_RefreshList(void) {
    static char list[16384];
    int count = mi.FS_GetFileList("Maps", ".w3m", list, sizeof(list));
    me_num_maps = 0;
    cstring_t p = list;
    for (int i = 0; i < count && *p; i++, p += strlen(p) + 1) {
        cstring_t base = NULL;
        if (!strncasecmp(p, "Maps\\Custom\\", 12) || !strncasecmp(p, "Maps/Custom/", 12)) base = p + 12;
        size_t len = base ? strlen(base) : 0;
        if (len < 5 || strstr(base, " (alt).w3m") || me_num_maps >= ME_LIST) continue;
        snprintf(me_maps[me_num_maps++], sizeof(me_maps[0]), "%.*s", (int)(len - 4), base);
    }
}

static bool ME_NameUsed(cstring_t name) {
    FOR_LOOP(i, me_num_maps) if (!strcasecmp(me_maps[i], name)) return true;
    return false;
}

static void ME_PickNewName(void) {
    ME_RefreshList();
    for (uint32_t n = 1; n < 1000; n++) {
        snprintf(me_name, sizeof(me_name), ME_PREFIX "%u", n);
        if (!ME_NameUsed(me_name)) return;
    }
}

static bool ME_SaveAs(cstring_t name) {
    cstring_t bases[2] = { ME_Theme("OfflineSkirmishMap"), ME_Theme("OfflineAlternateSkirmishMap") };
    FOR_LOOP(i, 2) {
        char rel[128], disk[MAX_PATHLEN * 2];
        if (!bases[i]) continue;
        snprintf(rel, sizeof(rel), "Maps/Custom/%s%s.w3m", name, i ? " (alt)" : "");
        mi.UserPath(rel, disk, sizeof(disk));
        if (!MapEditor_Save(&me_layout, bases[i], disk, name, i == 1)) {
            ME_Status("Could not save %s.", name);
            return false;
        }
    }
    mi.Cvar_Set(ME_LAST_CVAR, name);
    ME_Status("Saved %s. Load map reopens it any time.", name);
    return true;
}

static void ME_New(void) {
    cstring_t base = ME_Theme("OfflineSkirmishMap");
    me_undo_count = 0;
    me_name[0] = 0;
    me_loaded = base && MapEditor_Load(base, &me_layout);
    ME_Status(me_loaded ? "New map from the standard theater." : "The standard map could not be read.", NULL);
}

static void ME_Open(cstring_t name) {
    char path[160];
    ME_MapPath(name, false, path, sizeof(path));
    if (MapEditor_Load(path, &me_layout)) {
        me_undo_count = 0;
        snprintf(me_name, sizeof(me_name), "%s", name);
        mi.Cvar_Set(ME_LAST_CVAR, name);
        me_loaded = true;
        ME_Status("Opened %s.", name);
    } else ME_Status("Could not open %s.", name);
}

/* ---- Painting ---- */

static void ME_PushUndo(void) {
    if (me_undo_count == ME_UNDO) {
        memmove(me_undo, me_undo + 1, sizeof(me_undo[0]) * (ME_UNDO - 1));
        me_undo_count--;
    }
    me_undo[me_undo_count++] = me_layout;
}

static vec2_t ME_CanvasToTile(float fx, float fy) {
    rect_t c = ME_Canvas();
    float n = (float)me_layout.tiles;
    return MAKE(vec2_t, (fx - c.x) / c.w * n, (1.0f - (fy - c.y) / c.h) * n);   /* north is up */
}

static void ME_PaintTile(uint32_t x, uint32_t y) {
    vec2_t c = MapEditor_TileCenter(&me_layout, x, y);
    switch (me_tool) {
    case TOOL_LAND: me_layout.land[y][x] = 1; break;
    case TOOL_SEA:
        if (MapEditor_TileLocked(&me_layout, x, y)) break;
        me_layout.land[y][x] = 0;
        me_layout.trees[y][x] = 0;
        /* fall through: drowned ore fields go too */
    case TOOL_CLEAR:
        me_layout.trees[y][x] = 0;
        for (uint32_t i = 0; i < me_layout.num_units;) {
            if (fabsf(me_layout.units[i].pos.x - c.x) <= MAP_EDITOR_TILE * 0.5f &&
                fabsf(me_layout.units[i].pos.y - c.y) <= MAP_EDITOR_TILE * 0.5f)
                me_layout.units[i] = me_layout.units[--me_layout.num_units];
            else i++;
        }
        for (uint32_t i = 0; i < me_layout.num_mines;) {
            if (fabsf(me_layout.mines[i].x - c.x) <= MAP_EDITOR_TILE * 0.5f &&
                fabsf(me_layout.mines[i].y - c.y) <= MAP_EDITOR_TILE * 0.5f)
                me_layout.mines[i] = me_layout.mines[--me_layout.num_mines];
            else i++;
        }
        break;
    case TOOL_FOREST:
        if (MapEditor_TileForestable(&me_layout, x, y) && MapEditor_TreeCount(&me_layout) +
            MAP_EDITOR_TREES_PER_TILE - me_layout.trees[y][x] <= MAP_EDITOR_MAX_TREES)
            me_layout.trees[y][x] = MAP_EDITOR_TREES_PER_TILE;
        break;
    case TOOL_ORE: case TOOL_TROOPS: break;
    }
}

/* Brushes cover the same share of the canvas on every map size. */
static float ME_BrushRadius(void) {
    return me_brushes[me_brush] * MAX(1.0f, (float)me_layout.tiles / 156.0f);
}

static void ME_Brush(vec2_t at) {
    float r = ME_BrushRadius();
    int32_t n = (int32_t)me_layout.tiles;
    for (int32_t y = (int32_t)floorf(at.y - r); y <= (int32_t)(at.y + r); y++)
        for (int32_t x = (int32_t)floorf(at.x - r); x <= (int32_t)(at.x + r); x++) {
            if (x < 0 || y < 0 || x >= n || y >= n || hypotf(x + 0.5f - at.x, y + 0.5f - at.y) > r) continue;
            ME_PaintTile((uint32_t)x, (uint32_t)y);
            if (me_mirror) ME_PaintTile((uint32_t)(n - 1 - x), (uint32_t)(n - 1 - y));
        }
}

/* Interpolate fast drags so a stroke never leaves gaps. */
static void ME_Stroke(vec2_t to) {
    float step = MAX(0.5f, ME_BrushRadius() * 0.5f);
    float len = hypotf(to.x - me_last.x, to.y - me_last.y);
    uint32_t steps = (uint32_t)(len / step) + 1;
    FOR_LOOP(i, steps) {
        float t = (float)(i + 1) / (float)steps;
        ME_Brush(MAKE(vec2_t, me_last.x + (to.x - me_last.x) * t, me_last.y + (to.y - me_last.y) * t));
    }
    me_last = to;
}

static void ME_AddMine(vec2_t tile) {
    uint32_t x = (uint32_t)tile.x, y = (uint32_t)tile.y;
    if (tile.x < 0 || tile.y < 0 || x >= me_layout.tiles || y >= me_layout.tiles) return;
    if (!me_layout.land[y][x]) { ME_Status("Ore fields need land.", NULL); return; }
    vec2_t c = MapEditor_TileCenter(&me_layout, x, y);
    vec2_t spots[2] = { c, MAKE(vec2_t, -c.x, -c.y) };
    ME_PushUndo();
    FOR_LOOP(s, me_mirror ? 2 : 1) {
        bool crowded = me_layout.num_mines >= MAP_EDITOR_MAX_MINES;
        FOR_LOOP(i, me_layout.num_sites) crowded |= hypotf(spots[s].x - me_layout.sites[i].x, spots[s].y - me_layout.sites[i].y) < 900;
        FOR_LOOP(i, me_layout.num_mines) crowded |= hypotf(spots[s].x - me_layout.mines[i].x, spots[s].y - me_layout.mines[i].y) < 900;
        if (crowded) { ME_Status("Too close to another ore field.", NULL); continue; }
        me_layout.mines[me_layout.num_mines++] = spots[s];
        /* Engineers need room around the field. */
        FOR_LOOP(ty, me_layout.tiles) FOR_LOOP(tx, me_layout.tiles)
            if (me_layout.trees[ty][tx] && !MapEditor_TileForestable(&me_layout, tx, ty)) me_layout.trees[ty][tx] = 0;
    }
}

static vec2_t ME_TileToWorld(vec2_t tile) {
    return MAKE(vec2_t, me_layout.origin + tile.x * MAP_EDITOR_TILE, me_layout.origin + tile.y * MAP_EDITOR_TILE);
}

static void ME_AddTroop(vec2_t tile) {
    uint32_t x = (uint32_t)tile.x, y = (uint32_t)tile.y;
    if (tile.x < 0 || tile.y < 0 || x >= me_layout.tiles || y >= me_layout.tiles) return;
    if (!me_layout.land[y][x]) { ME_Status("Troops start on land; ships come from the shipyard.", NULL); return; }
    vec2_t at = ME_TileToWorld(tile);
    mapEditorUnit_t placed[2] = { { me_side, me_role, at }, { (uint8_t)!me_side, me_role, { -at.x, -at.y } } };
    ME_PushUndo();
    FOR_LOOP(s, me_mirror ? 2 : 1) {
        bool crowded = me_layout.num_units >= MAP_EDITOR_MAX_UNITS;
        FOR_LOOP(i, me_layout.num_units)
            crowded |= hypotf(placed[s].pos.x - me_layout.units[i].pos.x, placed[s].pos.y - me_layout.units[i].pos.y) < 64;
        if (crowded) {
            ME_Status(me_layout.num_units >= MAP_EDITOR_MAX_UNITS ? "Troop limit reached." : "Too close to another unit.", NULL);
            continue;
        }
        me_layout.units[me_layout.num_units++] = placed[s];
    }
}

static void ME_Play(bool alternate) {
    char path[160], command[192];
    if (!me_name[0]) ME_PickNewName();
    if (!ME_SaveAs(me_name)) return;
    ME_MapPath(me_name, alternate, path, sizeof(path));
    snprintf(command, sizeof(command), "map \"%s\"", path);
    UI_QueueCommand(command);
}

static void ME_Press(meButton_t id) {
    if (id >= BTN_LIST_CANCEL) { me_listing = false; return; }
    if (id >= BTN_LIST) { me_listing = false; ME_Open(me_maps[id - BTN_LIST]); return; }
    switch (id) {
    case BTN_LAND: me_tool = TOOL_LAND; break;
    case BTN_SEA: me_tool = TOOL_SEA; break;
    case BTN_FOREST: me_tool = TOOL_FOREST; break;
    case BTN_CLEAR: me_tool = TOOL_CLEAR; break;
    case BTN_ORE: me_tool = TOOL_ORE; break;
    case BTN_TROOPS: me_tool = TOOL_TROOPS; break;
    case BTN_SIDE: me_side = !me_side; me_tool = TOOL_TROOPS; break;
    case BTN_ROLE: me_role = (uint8_t)((me_role + 1) % map_editor_num_roles); me_tool = TOOL_TROOPS; break;
    case BTN_MIRROR: me_mirror = !me_mirror; break;
    case BTN_BRUSH: me_brush = (me_brush + 1) % 3; break;
    case BTN_UNDO:
        if (me_undo_count) me_layout = me_undo[--me_undo_count];
        else ME_Status("Nothing to undo.", NULL);
        break;
    case BTN_NEW: ME_New(); break;
    case BTN_OPEN:
        ME_RefreshList();
        if (me_num_maps) me_listing = true;
        else ME_Status("No saved maps yet.", NULL);
        break;
    case BTN_SAVE:
        if (!me_name[0]) ME_PickNewName();
        ME_SaveAs(me_name);
        break;
    case BTN_SAVE_NEW: ME_PickNewName(); ME_SaveAs(me_name); break;
    case BTN_PLAY: ME_Play(false); break;
    case BTN_PLAY_ALT: ME_Play(true); break;
    case BTN_BACK: UI_QueueCommand("menu_main"); break;
    default: break;
    }
}

static bool ME_HitButton(float x, float y, meButton_t *out) {
    if (me_listing) {
        FOR_LOOP(i, me_num_maps) if (ME_Inside(ME_Slot(i, 0, true), x, y)) { *out = (meButton_t)(BTN_LIST + i); return true; }
        if (ME_Inside(ME_Slot(me_num_maps + 1, 0, true), x, y)) { *out = BTN_LIST_CANCEL; return true; }
        return false;
    }
    FOR_LOOP(i, sizeof(me_places) / sizeof(me_places[0])) {
        meButtonPlace_t const *b = &me_places[i];
        if ((b->id != BTN_PLAY_ALT || ME_Theme("OfflineAlternateSkirmishMap")) &&
            ME_Inside(ME_Slot(b->row, b->col, b->wide), x, y)) { *out = b->id; return true; }
    }
    return false;
}

/* The screen draws no FDF frames, so it owns every pointer event: stale layouts never receive clicks. */
static bool ME_Pointer(menuMouseEvent_t event, float x, float y, int32_t param) {
    meButton_t id;
    if (!me_loaded) {
        if (event == MENU_MOUSE_DOWN) UI_QueueCommand("menu_main");
        return true;
    }
    if (event == MENU_MOUSE_DOWN && param == 1) {
        if (ME_HitButton(x, y, &id)) ME_Press(id);
        else if (!me_listing && ME_Inside(ME_Canvas(), x, y)) {
            vec2_t tile = ME_CanvasToTile(x, y);
            if (me_tool == TOOL_ORE) ME_AddMine(tile);
            else if (me_tool == TOOL_TROOPS) ME_AddTroop(tile);
            else {
                ME_PushUndo();
                me_painting = true;
                me_last = tile;
                ME_Brush(tile);
            }
        }
    } else if (event == MENU_MOUSE_MOVE && me_painting) {
        ME_Stroke(ME_CanvasToTile(x, y));
    } else if (event == MENU_MOUSE_UP) {
        me_painting = false;
    }
    return true;
}

/* ---- Drawing ---- */

static void ME_Fill(refExport_t *re, rect_t r, uint8_t red, uint8_t green, uint8_t blue, uint8_t alpha) {
    re->DrawFill(&r, MAKE(color32_t, red, green, blue, alpha));
}

static void ME_Text(refExport_t *re, rect_t r, cstring_t text, uiFontJustificationH_t align, color32_t color, bool wrap) {
    font_t const *font = re->LoadFont ? re->LoadFont(Theme_String("MasterFont", "Default"), 12) : NULL;
    if (!font || !re->DrawText) return;
    drawText_t dt = { .font = font, .text = text, .rect = r, .color = color, .textWidth = r.w,
                      .lineHeight = 1.0f, .flags = wrap ? DRAW_WORD_WRAP : 0, .halign = align,
                      .valign = wrap ? FONT_JUSTIFYTOP : FONT_JUSTIFYMIDDLE };
    re->DrawText(&dt);
}

static void ME_DrawButton(refExport_t *re, rect_t r, cstring_t label, bool active) {
    ME_Fill(re, r, active ? 120 : 48, active ? 104 : 54, active ? 58 : 46, 235);
    ME_Fill(re, MAKE(rect_t, r.x, r.y + r.h - 0.002f, r.w, 0.002f), 20, 22, 18, 255);
    ME_Text(re, r, label, FONT_JUSTIFYCENTER, MAKE(color32_t, 237, 227, 199, 255), false);
}

static void ME_TileColor(uint32_t x, uint32_t y, uint8_t rgb[3]) {
    vec2_t c = MapEditor_TileCenter(&me_layout, x, y);
    float half = me_layout.playable;
    bool outside = fabsf(c.x) > half || fabsf(c.y) > half;
    if (!me_layout.land[y][x]) rgb[0] = 45, rgb[1] = 81, rgb[2] = 108;
    else if (me_layout.trees[y][x]) rgb[0] = 52, rgb[1] = 78, rgb[2] = 44;
    else rgb[0] = 103, rgb[1] = 116, rgb[2] = 73;
    if (outside) FOR_LOOP(i, 3) rgb[i] = (uint8_t)(rgb[i] * 3 / 5);
}

/* Run-length rows keep the canvas to a few hundred fills on every device. */
static void ME_DrawCanvas(refExport_t *re) {
    rect_t c = ME_Canvas();
    float cw = c.w / (float)me_layout.tiles, ch = c.h / (float)me_layout.tiles;
    FOR_LOOP(y, me_layout.tiles) {
        uint32_t start = 0;
        uint8_t run[3], rgb[3];
        ME_TileColor(0, y, run);
        for (uint32_t x = 1; x <= me_layout.tiles; x++) {
            if (x < me_layout.tiles) ME_TileColor(x, y, rgb);
            if (x < me_layout.tiles && !memcmp(rgb, run, 3)) continue;
            ME_Fill(re, MAKE(rect_t, c.x + start * cw, c.y + c.h - (y + 1) * ch, (x - start) * cw + 0.0005f, ch + 0.0005f),
                    run[0], run[1], run[2], 255);
            start = x;
            memcpy(run, rgb, 3);
        }
    }
    float sx = c.w / (2.0f * -me_layout.origin), sy = c.h / (2.0f * -me_layout.origin);
    FOR_LOOP(i, me_layout.num_sites + me_layout.num_mines) {
        bool fixed = i < me_layout.num_sites;
        vec2_t p = fixed ? MAKE(vec2_t, me_layout.sites[i].x, me_layout.sites[i].y) : me_layout.mines[i - me_layout.num_sites];
        mapEditorSiteKind_t kind = fixed ? me_layout.sites[i].kind : MAP_SITE_ORE;
        float size = kind == MAP_SITE_HQ_ALLIED || kind == MAP_SITE_HQ_ENEMY ? 0.016f : 0.010f, sw = size * c.w / c.h;
        float px = c.x + (p.x - me_layout.origin) * sx, py = c.y + c.h - (p.y - me_layout.origin) * sy;
        if (kind == MAP_SITE_LAND) continue;
        rect_t r = { px - sw * 0.5f, py - size * 0.5f, sw, size };
        ME_Fill(re, MAKE(rect_t, r.x - 0.002f * c.w / c.h, r.y - 0.002f, r.w + 0.004f * c.w / c.h, r.h + 0.004f), fixed ? 240 : 20, fixed ? 240 : 20, fixed ? 240 : 20, 255);
        if (kind == MAP_SITE_HQ_ALLIED) ME_Fill(re, r, 70, 120, 220, 255);
        else if (kind == MAP_SITE_HQ_ENEMY) ME_Fill(re, r, 210, 60, 50, 255);
        else ME_Fill(re, r, 222, 184, 72, 255);
    }
    FOR_LOOP(i, me_layout.num_units) {
        mapEditorUnit_t const *u = &me_layout.units[i];
        float size = u->role >= 3 ? 0.008f : 0.006f, sw = size * c.w / c.h;   /* vehicles draw larger */
        float px = c.x + (u->pos.x - me_layout.origin) * sx, py = c.y + c.h - (u->pos.y - me_layout.origin) * sy;
        ME_Fill(re, MAKE(rect_t, px - sw * 0.5f - 0.001f, py - size * 0.5f - 0.001f, sw + 0.002f, size + 0.002f), 15, 15, 15, 255);
        if (u->side) ME_Fill(re, MAKE(rect_t, px - sw * 0.5f, py - size * 0.5f, sw, size), 235, 95, 80, 255);
        else ME_Fill(re, MAKE(rect_t, px - sw * 0.5f, py - size * 0.5f, sw, size), 110, 160, 245, 255);
    }
}

static void ME_Draw(void) {
    refExport_t *re = mi.GetRenderer();
    rect_t scene = UI_GetSceneRect(), panel = ME_Panel();
    color32_t ink = { 237, 227, 199, 255 }, dim = { 180, 172, 150, 255 };
    char label[64], stats[96];

    if (!re || !re->DrawFill) return;
    ME_Fill(re, scene, 22, 30, 31, 255);
    if (!me_loaded) {
        ME_Text(re, scene, "The map editor needs the standard Frontline map. Click to return.", FONT_JUSTIFYCENTER, ink, false);
        return;
    }
    ME_DrawCanvas(re);
    ME_Text(re, MAKE(rect_t, panel.x, panel.y, panel.w, 0.032f), me_name[0] ? me_name : "New map (unsaved)", FONT_JUSTIFYLEFT, ink, false);
    if (me_listing) {
        FOR_LOOP(i, me_num_maps) ME_DrawButton(re, ME_Slot(i, 0, true), me_maps[i], false);
        ME_DrawButton(re, ME_Slot(me_num_maps + 1, 0, true), "Cancel", false);
    } else {
        FOR_LOOP(i, sizeof(me_places) / sizeof(me_places[0])) {
            meButtonPlace_t const *b = &me_places[i];
            if (b->id == BTN_PLAY_ALT && !ME_Theme("OfflineAlternateSkirmishMap")) continue;
            ME_Label(b->id, label, sizeof(label));
            ME_DrawButton(re, ME_Slot(b->row, b->col, b->wide), label, ME_ButtonActive(b->id));
        }
    }
    snprintf(stats, sizeof(stats), "Trees %u   Ore %u   Troops %u/%u", MapEditor_TreeCount(&me_layout),
             me_layout.num_mines, me_layout.num_units, MAP_EDITOR_MAX_UNITS);
    rect_t row = ME_Slot(10, 0, true);
    ME_Text(re, row, stats, FONT_JUSTIFYLEFT, dim, false);
    row.y += row.h + 0.006f;
    row.h *= 2;
    ME_Text(re, row, me_status, FONT_JUSTIFYLEFT, ink, true);
}

static bool ME_LoadScreen(void) {
    if (mi.Cvar_Register) mi.Cvar_Register(ME_LAST_CVAR, "", CVAR_ARCHIVE);
    return ME_Theme("OfflineSkirmishMap") != NULL;
}

static void ME_Init(void) {
    me_painting = me_listing = false;
    if (!me_loaded) {
        char last[64];
        snprintf(last, sizeof(last), "%s", mi.Cvar_String(ME_LAST_CVAR, ""));
        if (*last) ME_Open(last);
        if (!me_loaded) ME_New();
    }
    else ME_Status("Blue/red: headquarters. Gold: ore. Mirror keeps both sides fair.", NULL);
}

static void ME_Shutdown(void) {
    me_painting = me_listing = false;
}

static void ME_Refresh(int msec) { (void)msec; }

static void ME_KeyEvent(int key, bool down) {
    (void)key;
    (void)down;
}

uiScreen_t mapEditorScreen = {
    .name = "map-editor",
    .glue = { .panel = UI_GLUE_MAIN_MENU },
    .load = ME_LoadScreen,
    .init = ME_Init,
    .shutdown = ME_Shutdown,
    .refresh = ME_Refresh,
    .draw = ME_Draw,
    .key_event = ME_KeyEvent,
    .pointer = ME_Pointer,
};
