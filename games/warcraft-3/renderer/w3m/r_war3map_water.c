#include "r_war3map.h"

static vertex_t water_vertex_buffer[(SEGMENT_SIZE+1)*(SEGMENT_SIZE+1)*6];
static vertex_t *water_current_vertex = NULL;

// FUNCTIONS

static void R_MakeWaterTile(war3map_t const *map, uint32_t x, uint32_t y) {
    struct War3MapVertex tile[4];
    GetTileVertices(x, y, tr.world, tile);

    if (!IsTileWater(tile))
        return;

    vec2_t const pos[] = {
        { tr.world->center.x + x * TILE_SIZE, tr.world->center.y + y * TILE_SIZE },
        { tr.world->center.x + (x + 1) * TILE_SIZE, tr.world->center.y + y * TILE_SIZE },
        { tr.world->center.x + (x + 1) * TILE_SIZE, tr.world->center.y + (y + 1) * TILE_SIZE },
        { tr.world->center.x + x * TILE_SIZE, tr.world->center.y + (y + 1) * TILE_SIZE },
    };

    float const waterlevel[] = {
        GetWar3MapVertexWaterLevel(&tile[3]),
        GetWar3MapVertexWaterLevel(&tile[2]),
        GetWar3MapVertexWaterLevel(&tile[0]),
        GetWar3MapVertexWaterLevel(&tile[1]),
    };

    float const height[] = {
        GetWar3MapVertexHeight(&tile[3]),
        GetWar3MapVertexHeight(&tile[2]),
        GetWar3MapVertexHeight(&tile[0]),
        GetWar3MapVertexHeight(&tile[1]),
    };

    wc3WaterStyle_t const *style = R_WaterStyle();
    struct color32 const color[] = {
        R_WaterDepthColor(style, (waterlevel[0] - height[0]) / TILE_SIZE),
        R_WaterDepthColor(style, (waterlevel[1] - height[1]) / TILE_SIZE),
        R_WaterDepthColor(style, (waterlevel[2] - height[2]) / TILE_SIZE),
        R_WaterDepthColor(style, (waterlevel[3] - height[3]) / TILE_SIZE),
    };
    
#define WATER_SCALE(x,y) (((x%3)+y)/3.0)
    
    vec2_t const tc[] = {
        { WATER_SCALE(x, 0),  WATER_SCALE(y, 0) },
        { WATER_SCALE(x, 1),  WATER_SCALE(y, 0) },
        { WATER_SCALE(x, 1),  WATER_SCALE(y, 1) },
        { WATER_SCALE(x, 0),  WATER_SCALE(y, 1) },
    };

    struct vertex geom[] = {
        {
            .position = { pos[0].x, pos[0].y, waterlevel[0] },
            .texcoord = tc[0],
            .normal = { 0, 0, 1 },
            .color = color[0],
        },
        {
            .position = { pos[1].x, pos[1].y, waterlevel[1] },
            .texcoord = tc[1],
            .normal = { 0, 0, 1 },
            .color = color[1],
        },
        {
            .position = { pos[2].x, pos[2].y, waterlevel[2] },
            .texcoord = tc[2],
            .normal = { 0, 0, 1 },
            .color = color[2],
        },
        {
            .position = { pos[0].x, pos[0].y, waterlevel[0] },
            .texcoord = tc[0],
            .normal = { 0, 0, 1 },
            .color = color[0],
        },
        {
            .position = { pos[2].x, pos[2].y, waterlevel[2] },
            .texcoord = tc[2],
            .normal = { 0, 0, 1 },
            .color = color[2],
        },
        {
            .position = { pos[3].x, pos[3].y, waterlevel[3] },
            .texcoord = tc[3],
            .normal = { 0, 0, 1 },
            .color = color[3],
        },
    };

    memcpy(water_current_vertex, geom, sizeof(geom));
    water_current_vertex += sizeof(geom) / sizeof(vertex_t);
}

maplayer_t *R_BuildMapSegmentWater(war3map_t const *map, uint32_t sx, uint32_t sy) {
    /* R_LoadWaterStyle already reported a missing Water.slk row or texture for this tileset. */
    if (!R_WaterStyle()->num_frames) return NULL;
    maplayer_t *mapLayer = ri.MemAlloc(sizeof(maplayer_t));
    mapLayer->type = MAPLAYERTYPE_WATER;
    mapLayer->texture = R_WaterStyle()->frames[0]; /* _W3M_DrawAlphaSurfaces selects the animated frame. */
    water_current_vertex = water_vertex_buffer;
    for (uint32_t x = sx * SEGMENT_SIZE; x < W3_SegmentEnd(sx, map->width - 1); x++) {
        for (uint32_t y = sy * SEGMENT_SIZE; y < W3_SegmentEnd(sy, map->height - 1); y++) {
            R_MakeWaterTile(map, x, y);
        }
    }
    mapLayer->num_vertices = (uint32_t)(water_current_vertex - water_vertex_buffer);
    mapLayer->buffer = R_MakeVertexArrayObject(water_vertex_buffer, mapLayer->num_vertices);
    return mapLayer;
}

/* A full zoom-out at the playable edge sees past the terrain. When the map's border is sea, an
 * opaque ring of open water at the border's water level continues it (instead of black void);
 * it uses the deep-water colour and the same world-continuous texture repeat as the tiles. */
uint32_t R_WaterSkirtVertices(war3map_t const *map, vertex_t *out) {
    war3mapVertex_t const *border = NULL;
    float const x0 = map->center.x, y0 = map->center.y;
    float const x1 = x0 + (map->width - 1) * TILE_SIZE, y1 = y0 + (map->height - 1) * TILE_SIZE;
    float const w = WATER_SKIRT_WIDTH;
    for (uint32_t i = 0; i < map->width && !border; i++)
        FOR_LOOP(k, 4) {
            uint32_t const x = k < 2 ? i : (k == 2 ? 0 : map->width - 1);
            uint32_t const y = k < 2 ? (k == 0 ? 0 : map->height - 1) : MIN(i, map->height - 1);
            war3mapVertex_t const *v = GetWar3MapVertex(map, x, y);
            if (v->water && !v->mapedge) { border = v; break; }
        }
    if (!border || !R_WaterStyle()->num_frames) return 0;
    float const z = GetWar3MapVertexWaterLevel(border);
    color32_t color = R_WaterDepthColor(R_WaterStyle(), 1.0f);
    color.a = 255;
    /* Outer and inner rings, counter-clockwise from the south-west corner. */
    vec2_t const outer[4] = { { x0 - w, y0 - w }, { x1 + w, y0 - w }, { x1 + w, y1 + w }, { x0 - w, y1 + w } };
    vec2_t const inner[4] = { { x0, y0 }, { x1, y0 }, { x1, y1 }, { x0, y1 } };
    uint32_t n = 0;
    FOR_LOOP(side, 4) {
        uint32_t const next = (side + 1) % 4;
        vec2_t const quad[4] = { outer[side], outer[next], inner[next], inner[side] };
        uint32_t const order[6] = { 0, 1, 2, 0, 2, 3 };
        FOR_LOOP(k, 6) {
            vec2_t const p = quad[order[k]];
            out[n++] = (vertex_t){
                .position = { p.x, p.y, z },
                .texcoord = { (p.x - x0) / (3 * TILE_SIZE), (p.y - y0) / (3 * TILE_SIZE) },
                .normal = { 0, 0, 1 },
                .color = color,
            };
        }
    }
    return n;
}

maplayer_t *R_BuildWaterSkirt(war3map_t const *map) {
    vertex_t vertices[WATER_SKIRT_VERTICES];
    uint32_t const count = R_WaterSkirtVertices(map, vertices);
    maplayer_t *mapLayer;
    if (!count) return NULL;
    mapLayer = ri.MemAlloc(sizeof(maplayer_t));
    mapLayer->type = MAPLAYERTYPE_WATER;
    mapLayer->texture = R_WaterStyle()->frames[0];
    mapLayer->num_vertices = count;
    mapLayer->buffer = R_MakeVertexArrayObject(vertices, count);
    return mapLayer;
}
