/*
 * menu_map_editor.c — Read and write island layouts (see menu_map_editor.h).
 *
 * The terrain rules mirror tools/frontline/generate.py map_data(): pathing in
 * 32-unit cells, a signed chamfer distance to the coast, and vertex heights that
 * slope through the waterline so the water plane cuts a curved shore.
 */

#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "menu_local.h"
#include "menu_map_editor.h"
#include "common/mpq.h"


/* tools/frontline/catalog.py LAND_IJN; artillery is shared by both navies. */
mapEditorRole_t const map_editor_roles[] = {
    { "Rifle Squad", { "finf", "jinf" } }, { "MG Squad", { "fmg0", "jmg0" } },
    { "Mortar Team", { "fmrt", "jmrt" } }, { "Medium Tank", { "ftnk", "jtnk" } },
    { "Heavy Tank", { "fhtk", "jhtk" } }, { "Field Artillery", { "fart", "fart" } },
};
uint32_t const map_editor_num_roles = sizeof(map_editor_roles) / sizeof(map_editor_roles[0]);

#define ME_CELLS_PER_TILE 4
#define ME_CELL 32
#define ME_HQ_CLEAR 1000.0f
#define ME_MINE_CLEAR 420.0f
#define ME_MINIMAP 256
#define ME_BLP_HEADER 148

static cstring_t const me_forest_start = "function FrontlineForest0 takes";
static cstring_t const me_forest_end = "function main takes nothing returns nothing";
static cstring_t const me_calls_start = "    call FrontlineForest0()\n";
static cstring_t const me_calls_end = "    call FrontlineRimMines()\n";

vec2_t MapEditor_TileCenter(mapEditorLayout_t const *layout, uint32_t x, uint32_t y) {
    return MAKE(vec2_t, layout->origin + ((float)x + 0.5f) * MAP_EDITOR_TILE,
                layout->origin + ((float)y + 0.5f) * MAP_EDITOR_TILE);
}

bool MapEditor_TileLocked(mapEditorLayout_t const *layout, uint32_t x, uint32_t y) {
    vec2_t c = MapEditor_TileCenter(layout, x, y);
    FOR_LOOP(i, layout->num_sites) {
        mapEditorSite_t const *s = &layout->sites[i];
        if (hypotf(c.x - s->x, c.y - s->y) < s->radius) return true;
    }
    return false;
}

bool MapEditor_TileForestable(mapEditorLayout_t const *layout, uint32_t x, uint32_t y) {
    vec2_t c = MapEditor_TileCenter(layout, x, y);
    float half = layout->playable - 250.0f;
    if (!layout->land[y][x] || fabsf(c.x) > half || fabsf(c.y) > half) return false;
    FOR_LOOP(i, layout->num_sites) {
        mapEditorSite_t const *s = &layout->sites[i];
        float clear = s->kind == MAP_SITE_ORE ? ME_MINE_CLEAR : s->kind == MAP_SITE_LAND ? s->radius : ME_HQ_CLEAR;
        if (hypotf(c.x - s->x, c.y - s->y) < clear) return false;
    }
    FOR_LOOP(i, layout->num_mines) {
        if (hypotf(c.x - layout->mines[i].x, c.y - layout->mines[i].y) < ME_MINE_CLEAR) return false;
    }
    return true;
}

uint32_t MapEditor_TreeCount(mapEditorLayout_t const *layout) {
    uint32_t count = 0;
    FOR_LOOP(y, layout->tiles) FOR_LOOP(x, layout->tiles) count += layout->trees[y][x];
    return count;
}

static uint32_t ME_Read32(uint8_t const *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void ME_Write32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

bool MapEditor_ReadTerrainHeader(uint8_t const *w3e, uint32_t size, uint32_t *header_size,
                                 uint32_t *vertices, float *origin) {
    uint32_t at = 13, count;
    float ox, oy;

    if (!w3e || size < 17 || memcmp(w3e, "W3E!", 4)) return false;
    count = ME_Read32(w3e + at); at += 4 + count * 4;        /* ground tilesets */
    if (at + 4 > size) return false;
    count = ME_Read32(w3e + at); at += 4 + count * 4;        /* cliff tilesets */
    if (at + 16 > size) return false;
    uint32_t w = ME_Read32(w3e + at), h = ME_Read32(w3e + at + 4);
    memcpy(&ox, w3e + at + 8, 4);
    memcpy(&oy, w3e + at + 12, 4);
    at += 16;
    /* Editor layouts are square and centred, as every Frontline map is. */
    if (w != h || w < 2 || w - 1 > MAP_EDITOR_MAX_TILES || ox != oy || at + w * h * 7 > size) return false;
    *header_size = at;
    *vertices = w;
    *origin = ox;
    return true;
}

bool MapEditor_DecodePathing(uint8_t const *wpm, uint32_t size, mapEditorLayout_t *layout) {
    uint32_t cells = layout->tiles * ME_CELLS_PER_TILE;

    if (!wpm || size < 16 || memcmp(wpm, "MP3W", 4) || ME_Read32(wpm + 8) != cells ||
        ME_Read32(wpm + 12) != cells || size < 16 + cells * cells) return false;
    FOR_LOOP(ty, layout->tiles) FOR_LOOP(tx, layout->tiles) {
        uint32_t dry = 0;
        FOR_LOOP(dy, ME_CELLS_PER_TILE) FOR_LOOP(dx, ME_CELLS_PER_TILE) {
            uint32_t cx = tx * ME_CELLS_PER_TILE + dx, cy = ty * ME_CELLS_PER_TILE + dy;
            dry += !(wpm[16 + cy * cells + cx] & 2);
        }
        layout->land[ty][tx] = dry * 2 >= ME_CELLS_PER_TILE * ME_CELLS_PER_TILE;
    }
    return true;
}

static bool ME_WorldTile(mapEditorLayout_t const *layout, float wx, float wy, uint32_t *x, uint32_t *y) {
    float fx = floorf((wx - layout->origin) / MAP_EDITOR_TILE), fy = floorf((wy - layout->origin) / MAP_EDITOR_TILE);
    if (fx < 0 || fy < 0 || fx >= (float)layout->tiles || fy >= (float)layout->tiles) return false;
    *x = (uint32_t)fx;
    *y = (uint32_t)fy;
    return true;
}

/* Only the generated forest section is editor-owned; scenario trees and mines stay in main. */
void MapEditor_ParseScript(cstring_t script, mapEditorLayout_t *layout) {
    static cstring_t const tree = "CreateDestructable('epin', ";
    static cstring_t const ore = "CreateUnit(Player(15), 'eore', ";
    static cstring_t const troop = "    call CreateUnit(Player(";
    cstring_t start = script ? strstr(script, me_forest_start) : NULL;
    cstring_t end = start ? strstr(start, me_forest_end) : NULL;
    float wx, wy;
    uint32_t x, y;

    memset(layout->trees, 0, sizeof(layout->trees));
    layout->num_mines = 0;
    if (!end) return;
    for (cstring_t p = strstr(start, tree); p && p < end; p = strstr(p + 1, tree)) {
        if (sscanf(p + strlen(tree), "%f , %f", &wx, &wy) == 2 && ME_WorldTile(layout, wx, wy, &x, &y) &&
            layout->trees[y][x] < MAP_EDITOR_TREES_PER_TILE) layout->trees[y][x]++;
    }
    for (cstring_t p = strstr(start, ore); p && p < end; p = strstr(p + 1, ore)) {
        if (layout->num_mines < MAP_EDITOR_MAX_MINES && sscanf(p + strlen(ore), "%f , %f", &wx, &wy) == 2)
            layout->mines[layout->num_mines++] = MAKE(vec2_t, wx, wy);
    }
    layout->num_units = 0;
    for (cstring_t p = strstr(start, troop); p && p < end; p = strstr(p + 1, troop)) {
        unsigned player;
        char code[5];
        if (layout->num_units >= MAP_EDITOR_MAX_UNITS ||
            sscanf(p + strlen(troop), "%u), '%4[a-z0-9]', %f , %f", &player, code, &wx, &wy) != 4 || player > 1) continue;
        FOR_LOOP(r, map_editor_num_roles) {
            if (strcmp(code, map_editor_roles[r].code[0]) && strcmp(code, map_editor_roles[r].code[1])) continue;
            layout->units[layout->num_units++] = (mapEditorUnit_t){ (uint8_t)player, (uint8_t)r, { wx, wy } };
            break;
        }
    }
}

void MapEditor_ParseSites(cstring_t text, mapEditorLayout_t *layout) {
    static cstring_t const kinds[] = { "hq0", "hq1", "ore", "land" };
    layout->num_sites = 0;
    layout->playable = -layout->origin - MAP_EDITOR_TERRAIN_MARGIN;
    for (cstring_t line = text; line && *line && layout->num_sites < MAP_EDITOR_MAX_SITES;) {
        char kind[8];
        mapEditorSite_t site;
        if (sscanf(line, "playable %f", &site.x) == 1) layout->playable = site.x;
        else if (sscanf(line, "%7s %f %f %f", kind, &site.x, &site.y, &site.radius) == 4) {
            FOR_LOOP(k, 4) if (!strcmp(kind, kinds[k])) {
                site.kind = (mapEditorSiteKind_t)k;
                layout->sites[layout->num_sites++] = site;
            }
        }
        line = strchr(line, '\n');
        if (line) line++;
    }
}

/* Smooth the tile grid to 32-unit cells so diagonal coasts are not 128-unit stairs. */
static uint8_t *ME_SeaCells(mapEditorLayout_t const *layout, uint32_t cells) {
    uint8_t *sea = malloc((size_t)cells * cells);
    int32_t last = (int32_t)layout->tiles - 1;

    if (!sea) return NULL;
    FOR_LOOP(cy, cells) {
        float ty = ((float)cy + 0.5f) / ME_CELLS_PER_TILE - 0.5f;
        int32_t y0 = (int32_t)floorf(ty);
        float fy = ty - (float)y0;
        int32_t ya = MAX(0, MIN(last, y0)), yb = MAX(0, MIN(last, y0 + 1));
        FOR_LOOP(cx, cells) {
            float tx = ((float)cx + 0.5f) / ME_CELLS_PER_TILE - 0.5f;
            int32_t x0 = (int32_t)floorf(tx);
            float fx = tx - (float)x0;
            int32_t xa = MAX(0, MIN(last, x0)), xb = MAX(0, MIN(last, x0 + 1));
            float v = (layout->land[ya][xa] * (1 - fx) + layout->land[ya][xb] * fx) * (1 - fy) +
                      (layout->land[yb][xa] * (1 - fx) + layout->land[yb][xb] * fx) * fy;
            sea[cy * cells + cx] = v < 0.5f;
        }
    }
    return sea;
}

/* Two-pass chamfer distance to the nearest cell whose sea flag equals target. */
static void ME_Chamfer(uint8_t const *sea, uint8_t target, int32_t n, int32_t *d) {
    int32_t const big = 1000000000;
    FOR_LOOP(i, n * n) d[i] = sea[i] == target ? 0 : big;
    for (int32_t y = 0; y < n; y++) for (int32_t x = 0; x < n; x++) {
        int32_t *v = &d[y * n + x];
        if (!*v) continue;
        if (x) *v = MIN(*v, v[-1] + 32);
        if (y) {
            int32_t const *up = &d[(y - 1) * n + x];
            *v = MIN(*v, up[0] + 32);
            if (x) *v = MIN(*v, up[-1] + 45);
            if (x + 1 < n) *v = MIN(*v, up[1] + 45);
        }
    }
    for (int32_t y = n - 1; y >= 0; y--) for (int32_t x = n - 1; x >= 0; x--) {
        int32_t *v = &d[y * n + x];
        if (!*v) continue;
        if (x + 1 < n) *v = MIN(*v, v[1] + 32);
        if (y + 1 < n) {
            int32_t const *down = &d[(y + 1) * n + x];
            *v = MIN(*v, down[0] + 32);
            if (x + 1 < n) *v = MIN(*v, down[1] + 45);
            if (x) *v = MIN(*v, down[-1] + 45);
        }
    }
}

static bool ME_SeaAt(uint8_t const *sea, uint32_t cells, float origin, float wx, float wy) {
    int32_t cx = (int32_t)floorf((wx - origin) / ME_CELL), cy = (int32_t)floorf((wy - origin) / ME_CELL);
    cx = MAX(0, MIN((int32_t)cells - 1, cx));
    cy = MAX(0, MIN((int32_t)cells - 1, cy));
    return sea[cy * cells + cx];
}

bool MapEditor_Encode(mapEditorLayout_t const *layout, uint8_t const *base_w3e, uint32_t header_size,
                      uint8_t **w3e, uint32_t *w3e_size, uint8_t **wpm, uint32_t *wpm_size,
                      uint8_t **blp, uint32_t *blp_size) {
    uint32_t const cells = layout->tiles * ME_CELLS_PER_TILE, verts = layout->tiles + 1;
    uint8_t *sea = ME_SeaCells(layout, cells);
    int32_t *to_sea = malloc(sizeof(int32_t) * cells * cells);
    int32_t *to_land = malloc(sizeof(int32_t) * cells * cells);
    bool ok = false;

    *w3e = *wpm = *blp = NULL;
    *w3e_size = header_size + verts * verts * 7;
    *wpm_size = 16 + cells * cells;
    *blp_size = ME_BLP_HEADER + ME_MINIMAP * ME_MINIMAP * 4;
    *w3e = malloc(*w3e_size);
    *wpm = malloc(*wpm_size);
    *blp = calloc(1, *blp_size);
    if (!sea || !to_sea || !to_land || !*w3e || !*wpm || !*blp) goto done;

    ME_Chamfer(sea, 1, (int32_t)cells, to_sea);
    ME_Chamfer(sea, 0, (int32_t)cells, to_land);
    memcpy(*w3e, base_w3e, header_size);
    uint8_t *out = *w3e + header_size;
    FOR_LOOP(y, verts) FOR_LOOP(x, verts) {
        float sum = 0;
        uint32_t n = 0;
        for (int32_t cy = 4 * (int32_t)y - 1; cy <= 4 * (int32_t)y; cy++)
            for (int32_t cx = 4 * (int32_t)x - 1; cx <= 4 * (int32_t)x; cx++) {
                if (cx < 0 || cy < 0 || cx >= (int32_t)cells || cy >= (int32_t)cells) continue;
                uint32_t i = (uint32_t)cy * cells + (uint32_t)cx;
                sum += sea[i] ? -(float)(to_land[i] - 16) : (float)(to_sea[i] - 16);
                n++;
            }
        float d = sum / (float)n;
        float z = d < 0 ? MAX(-128.0f, MIN(10.0f, d * 0.42f)) : MIN(10.0f, d * 0.12f);
        uint16_t height = (uint16_t)(8192 + lroundf(z * 4));
        /* Water is flagged a little inland too: the plane is hidden under raised ground. */
        out[0] = (uint8_t)height; out[1] = (uint8_t)(height >> 8);
        out[2] = 0x00; out[3] = 0x20;                                   /* water level 8192 */
        out[4] = (uint8_t)((d < 200 ? 64 : 0) | (d < 210 ? 1 : 0));
        out[5] = (uint8_t)(x % 4 + 4 * (3 - y % 4));                    /* one 4x4 seamless texture */
        out[6] = 2;
        out += 7;
    }

    memcpy(*wpm, "MP3W", 4);
    ME_Write32(*wpm + 4, 0);
    ME_Write32(*wpm + 8, cells);
    ME_Write32(*wpm + 12, cells);
    FOR_LOOP(i, cells * cells) (*wpm)[16 + i] = sea[i] ? (2 | 8) : 64;

    /* Minimap: uncompressed BLP2 BGRA, top row is north (tools/emberfield/art.py blp_bytes). */
    memcpy(*blp, "BLP2", 4);
    ME_Write32(*blp + 4, 1);
    (*blp)[8] = 3; (*blp)[9] = 8;
    ME_Write32(*blp + 12, ME_MINIMAP);
    ME_Write32(*blp + 16, ME_MINIMAP);
    ME_Write32(*blp + 20, ME_BLP_HEADER);
    ME_Write32(*blp + 84, ME_MINIMAP * ME_MINIMAP * 4);
    float half = -layout->origin;
    FOR_LOOP(py, ME_MINIMAP) FOR_LOOP(px, ME_MINIMAP) {
        float wx = (float)px / ME_MINIMAP * 2 * half - half, wy = half - (float)py / ME_MINIMAP * 2 * half;
        uint8_t *p = *blp + ME_BLP_HEADER + (py * ME_MINIMAP + px) * 4;
        uint8_t r = 103, g = 116, b = 73;
        if (ME_SeaAt(sea, cells, layout->origin, wx, wy)) r = 45, g = 81, b = 108;
        else if (ME_SeaAt(sea, cells, layout->origin, wx + 200, wy) || ME_SeaAt(sea, cells, layout->origin, wx - 200, wy) ||
                 ME_SeaAt(sea, cells, layout->origin, wx, wy + 200) || ME_SeaAt(sea, cells, layout->origin, wx, wy - 200))
            r = 156, g = 148, b = 118;                                  /* beach sand */
        p[0] = b; p[1] = g; p[2] = r; p[3] = 255;
    }
    ok = true;
done:
    free(sea);
    free(to_sea);
    free(to_land);
    if (!ok) {
        free(*w3e); free(*wpm); free(*blp);
        *w3e = *wpm = *blp = NULL;
    }
    return ok;
}

static uint32_t ME_Hash(uint32_t x, uint32_t y, uint32_t k) {
    uint32_t h = x * 73856093u ^ y * 19349663u ^ k * 83492791u;
    h ^= h >> 13; h *= 0x5bd1e995u; h ^= h >> 15;
    return h;
}

typedef struct { string_t data; size_t len, cap; bool failed; } meText_t;

static void ME_Append(meText_t *t, cstring_t fmt, ...) {
    va_list args;
    for (;;) {
        size_t room = t->cap - t->len;
        va_start(args, fmt);
        int n = t->data ? vsnprintf(t->data + t->len, room, fmt, args) : -1;
        va_end(args);
        if (n >= 0 && (size_t)n < room) { t->len += (size_t)n; return; }
        size_t cap = t->cap ? t->cap * 2 : 65536;
        string_t grown = realloc(t->data, cap);
        if (!grown) { t->failed = true; return; }
        t->data = grown;
        t->cap = cap;
    }
}

static void ME_AppendSpan(meText_t *t, cstring_t start, cstring_t end) {
    ME_Append(t, "%.*s", (int)(end - start), start);
}

/* Replace the generated forest and rim-mine functions plus their calls in main. */
string_t MapEditor_PatchScript(cstring_t script, mapEditorLayout_t const *layout, bool alternate) {
    cstring_t forest = script ? strstr(script, me_forest_start) : NULL;
    cstring_t forest_end = forest ? strstr(forest, me_forest_end) : NULL;
    cstring_t calls = forest_end ? strstr(forest_end, me_calls_start) : NULL;
    cstring_t calls_end = calls ? strstr(calls, me_calls_end) : NULL;
    meText_t t = { 0 };
    uint32_t placed = 0, chunks = 0;

    if (!calls_end) return NULL;
    calls_end += strlen(me_calls_end);
    ME_AppendSpan(&t, script, forest);
    FOR_LOOP(y, layout->tiles) FOR_LOOP(x, layout->tiles) FOR_LOOP(k, layout->trees[y][x]) {
        if (placed >= MAP_EDITOR_MAX_TREES) break;
        uint32_t h = ME_Hash(x, y, k);
        vec2_t c = MapEditor_TileCenter(layout, x, y);
        float jx = (float)(h & 31) - 15.5f, jy = (float)((h >> 5) & 31) - 15.5f;
        float ox = k ? 30.0f : -30.0f, oy = k ? 30.0f : -28.0f;
        if (placed % 60 == 0) {
            if (placed) ME_Append(&t, "endfunction\n");
            ME_Append(&t, "function FrontlineForest%u takes nothing returns nothing\n", chunks++);
        }
        ME_Append(&t, "    call CreateDestructable('epin', %.0f.0, %.0f.0, %u.0, %.2f, 0)\n",
                  c.x + ox + jx, c.y + oy + jy, (h >> 10) % 360, 0.85 + (double)((h >> 19) % 46) / 100.0);
        placed++;
    }
    if (placed) ME_Append(&t, "endfunction\n");
    ME_Append(&t, "function FrontlineRimMines takes nothing returns nothing\n    local unit ore\n");
    FOR_LOOP(i, layout->num_mines)
        ME_Append(&t, "    set ore = CreateUnit(Player(15), 'eore', %.0f.0, %.0f.0, 0.0)\n    call SetResourceAmount(ore, 20000)\n",
                  layout->mines[i].x, layout->mines[i].y);
    /* Starting troops ride along in the rim-mine function, so the scenario's call list is unchanged. */
    FOR_LOOP(i, layout->num_units) {
        mapEditorUnit_t const *u = &layout->units[i];
        uint32_t navy = (uint32_t)(u->side ^ (alternate ? 1 : 0));
        ME_Append(&t, "    call CreateUnit(Player(%u), '%s', %.0f.0, %.0f.0, %u.0)\n", u->side,
                  map_editor_roles[u->role].code[navy], u->pos.x, u->pos.y, u->side ? 225u : 45u);
    }
    ME_Append(&t, "endfunction\n");
    ME_AppendSpan(&t, forest_end, calls);
    FOR_LOOP(i, chunks) ME_Append(&t, "    call FrontlineForest%u()\n", i);
    ME_Append(&t, "%s%s", me_calls_end, calls_end);
    if (t.failed) { free(t.data); return NULL; }
    return t.data;
}

/* ---- Archive I/O ---- */

static uint8_t *ME_ReadArchiveFile(handle_t archive, cstring_t name, uint32_t *size) {
    handle_t file;
    uint8_t *data = NULL;
    uint32_t got = 0;

    if (!SFileOpenFileEx(archive, name, SFILE_OPEN_FROM_MPQ, &file)) return NULL;
    *size = SFileGetFileSize(file, NULL);
    data = malloc(*size + 1);
    if (data && (!SFileReadFile(file, data, *size, &got, NULL) || got != *size)) {
        free(data);
        data = NULL;
    }
    if (data) data[*size] = 0;
    SFileCloseFile(file);
    return data;
}

static bool ME_OpenMap(cstring_t map_path, handle_t *archive, void **buffer) {
    int size = mi.FS_ReadFile(map_path, buffer);
    if (!*buffer || size <= 0) return false;
    if (SFileOpenArchiveFromMemory(*buffer, (uint32_t)size, 0, archive)) return true;
    mi.FS_FreeFile(*buffer);
    *buffer = NULL;
    return false;
}

bool MapEditor_Load(cstring_t map_path, mapEditorLayout_t *layout) {
    handle_t archive;
    void *buffer = NULL;
    uint32_t w3e_size = 0, wpm_size = 0, j_size = 0, header, verts;
    bool ok = false;

    if (!ME_OpenMap(map_path, &archive, &buffer)) return false;
    uint8_t *w3e = ME_ReadArchiveFile(archive, "war3map.w3e", &w3e_size);
    uint8_t *wpm = ME_ReadArchiveFile(archive, "war3map.wpm", &wpm_size);
    uint8_t *script = ME_ReadArchiveFile(archive, "war3map.j", &j_size);
    uint32_t sites_size = 0;
    uint8_t *sites = ME_ReadArchiveFile(archive, "war3mapSites.txt", &sites_size);
    if (script && strstr((cstring_t)script, me_forest_start) &&
        MapEditor_ReadTerrainHeader(w3e, w3e_size, &header, &verts, &layout->origin)) {
        layout->tiles = verts - 1;
        ok = MapEditor_DecodePathing(wpm, wpm_size, layout);
        if (ok) MapEditor_ParseScript((cstring_t)script, layout);
        MapEditor_ParseSites((cstring_t)sites, layout);
    }
    free(w3e); free(wpm); free(script); free(sites);
    SFileCloseArchive(archive);
    mi.FS_FreeFile(buffer);
    return ok;
}

/* Keep the base name's " - <navy>" suffix so both generated starts stay distinguishable. */
static uint8_t *ME_RenameInfo(uint8_t const *w3i, uint32_t size, cstring_t title, uint32_t *out_size) {
    uint32_t at = 12, version = size >= 4 ? ME_Read32(w3i) : 0;
    if (version >= 28) at += 16;
    if (at >= size || !memchr(w3i + at, 0, size - at)) return NULL;
    cstring_t name = (cstring_t)w3i + at;
    cstring_t suffix = strstr(name, " - ");
    size_t old_len = strlen(name) + 1;
    char renamed[256];
    snprintf(renamed, sizeof(renamed), "%s%s", title, suffix ? suffix : "");
    size_t new_len = strlen(renamed) + 1;
    uint8_t *out = malloc(size - old_len + new_len);
    if (!out) return NULL;
    memcpy(out, w3i, at);
    memcpy(out + at, renamed, new_len);
    memcpy(out + at + new_len, w3i + at + old_len, size - at - old_len);
    *out_size = (uint32_t)(size - old_len + new_len);
    return out;
}

bool MapEditor_Save(mapEditorLayout_t const *layout, cstring_t base_map, cstring_t disk_path, cstring_t title,
                    bool alternate) {
    handle_t base, out = NULL, find;
    void *buffer = NULL;
    sfileFindData_t fd;
    uint32_t w3e_size = 0, header, verts, new_w3e_size, wpm_size, blp_size, count = 0;
    uint8_t *new_w3e = NULL, *wpm = NULL, *blp = NULL;
    float origin;
    bool ok = false;

    if (!ME_OpenMap(base_map, &base, &buffer)) return false;
    uint8_t *w3e = ME_ReadArchiveFile(base, "war3map.w3e", &w3e_size);
    if (!MapEditor_ReadTerrainHeader(w3e, w3e_size, &header, &verts, &origin) || verts - 1 != layout->tiles ||
        origin != layout->origin ||
        !MapEditor_Encode(layout, w3e, header, &new_w3e, &new_w3e_size, &wpm, &wpm_size, &blp, &blp_size))
        goto done;
    find = SFileFindFirstFile(base, "*", &fd, NULL);
    for (bool more = find != NULL; more; more = SFileFindNextFile(find, &fd)) count++;
    if (find) SFileFindClose(find);
    if (!count || !SFileCreateArchive(disk_path, 0, count + 4, &out)) goto done;
    ok = true;
    find = SFileFindFirstFile(base, "*", &fd, NULL);
    for (bool more = find != NULL; more && ok; more = SFileFindNextFile(find, &fd)) {
        cstring_t name = fd.cFileName;
        uint32_t size = 0;
        uint8_t *data = NULL, *owned = NULL;
        if (name[0] == '(') continue;                         /* the writer emits its own listfile */
        if (!strcasecmp(name, "war3map.w3e")) data = new_w3e, size = new_w3e_size;
        else if (!strcasecmp(name, "war3map.wpm")) data = wpm, size = wpm_size;
        else if (!strcasecmp(name, "war3mapMap.blp")) data = blp, size = blp_size;
        else {
            uint8_t *raw = ME_ReadArchiveFile(base, name, &size);
            if (raw && !strcasecmp(name, "war3map.j")) {
                owned = (uint8_t *)MapEditor_PatchScript((cstring_t)raw, layout, alternate);
                size = owned ? (uint32_t)strlen((cstring_t)owned) : 0;
                free(raw);
            } else if (raw && !strcasecmp(name, "war3map.w3i")) {
                owned = ME_RenameInfo(raw, size, title, &size);
                free(raw);
            } else owned = raw;
            data = owned;
        }
        ok = data && SFileAddFileFromBuffer(out, name, data, size);
        free(owned);
    }
    if (find) SFileFindClose(find);
    ok = SFileCloseArchive(out) && ok;
done:
    free(w3e); free(new_w3e); free(wpm); free(blp);
    SFileCloseArchive(base);
    mi.FS_FreeFile(buffer);
    if (!ok && out) remove(disk_path);
    return ok;
}
