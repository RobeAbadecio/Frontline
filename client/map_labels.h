#ifndef map_labels_h
#define map_labels_h

#include "common/shared.h"

/* Geographic place-name labels authored per map in `<map>\war3mapLabels.txt`.
 *
 * One label per line: `<kind> <x> <y> <name...>` in world units; `#` starts a comment line.
 * Kinds, from largest to smallest: sea, region, group, island, base. The kind selects the zoom
 * band, style and minimap visibility; the client never needs to know the map. Maps without the
 * file simply draw no labels. See docs/games/warcraft-3/frontline-visuals.md#place-name-labels. */

#define MAX_MAP_LABELS 256       // labels per map; bounds the static per-map table
#define MAP_LABEL_NAME_LEN 48    // bytes including terminator
#define MAP_LABEL_LINE_LEN 160   // bytes; longer lines are skipped as malformed

typedef enum {
    MAP_LABEL_SEA,
    MAP_LABEL_REGION,
    MAP_LABEL_GROUP,
    MAP_LABEL_ISLAND,
    MAP_LABEL_BASE,
    MAP_LABEL_KIND_COUNT
} mapLabelKind_t;

typedef struct {
    mapLabelKind_t kind;
    vec2_t origin;
    char name[MAP_LABEL_NAME_LEN];
} mapLabel_t;

typedef struct {
    float min_scale, max_scale; // canvas units per 1000 world units; outside the band the label is hidden
    uint32_t font_size;         // renderer font size (≈ 500 x canvas height)
    color32_t color;
    bool minimap;               // also drawn, small, on the minimap
    bool background;            // large faint water/region names: decluttered among themselves only
} mapLabelStyle_t;

bool MapLabels_ParseLine(cstring_t line, mapLabel_t *out);
uint32_t MapLabels_Parse(cstring_t text, mapLabel_t *out, uint32_t max);
mapLabelStyle_t const *MapLabels_Style(mapLabelKind_t kind);
/* 0..1 opacity for a label of this kind at a projected scale; fades in/out near the band edges. */
float MapLabels_Alpha(mapLabelKind_t kind, float scale);
/* Greedy declutter: true and appended when `rect` overlaps none of the already placed rects. */
bool MapLabels_Place(rect_t const *rect, rect_t *placed, uint32_t *count, uint32_t max);

#endif
