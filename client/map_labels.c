#include <math.h>
#include "client/map_labels.h"

static cstring_t const map_label_kind_names[MAP_LABEL_KIND_COUNT] = { "sea", "region", "group", "island", "base" };

/* Scale = canvas units per 1000 world units at the label: WC3's default 1650 zoom is about 0.33,
 * the 3000 zoom-out limit about 0.11 and the 1250 close limit about 0.43.
 * Seas and regions are faint and only read when zoomed out; island names take the middle band;
 * bases need a close view. Only groups label the small minimap. */
static mapLabelStyle_t const map_label_styles[MAP_LABEL_KIND_COUNT] = {
    [MAP_LABEL_SEA]    = { 0.0f,  0.24f, 15, { 168, 206, 232, 150 }, false, true },
    [MAP_LABEL_REGION] = { 0.0f,  0.24f, 15, { 226, 214, 170, 150 }, false, true },
    [MAP_LABEL_GROUP]  = { 0.0f,  0.28f, 11, { 240, 232, 200, 225 }, true,  false },
    [MAP_LABEL_ISLAND] = { 0.05f, 0.80f, 10, { 250, 246, 228, 235 }, false, false },
    [MAP_LABEL_BASE]   = { 0.22f, 9.0f,  9,  { 255, 214, 120, 240 }, false, false },
};

bool MapLabels_ParseLine(cstring_t line, mapLabel_t *out) {
    char kind[16], name[MAP_LABEL_NAME_LEN];
    float x, y;

    if (!line || !out) return false;
    while (*line == ' ' || *line == '\t') line++;
    if (!*line || *line == '#' || *line == '\r' || *line == '\n') return false;
    if (sscanf(line, "%15s %f %f %47[^\r\n]", kind, &x, &y, name) != 4) return false;
    if (!isfinite(x) || !isfinite(y)) return false;
    for (size_t n = strlen(name); n && (name[n - 1] == ' ' || name[n - 1] == '\t'); n--) name[n - 1] = 0;
    if (!*name) return false;
    FOR_LOOP(i, MAP_LABEL_KIND_COUNT) {
        if (strcasecmp(kind, map_label_kind_names[i])) continue;
        out->kind = (mapLabelKind_t)i;
        out->origin = MAKE(vec2_t, x, y);
        snprintf(out->name, sizeof(out->name), "%s", name);
        return true;
    }
    return false;
}

uint32_t MapLabels_Parse(cstring_t text, mapLabel_t *out, uint32_t max) {
    uint32_t count = 0;

    if (!text || !out) return 0;
    while (*text && count < max) {
        cstring_t end = strchr(text, '\n');
        size_t len = end ? (size_t)(end - text) : strlen(text);
        if (len < MAP_LABEL_LINE_LEN) {
            char line[MAP_LABEL_LINE_LEN];
            memcpy(line, text, len);
            line[len] = 0;
            if (MapLabels_ParseLine(line, &out[count])) count++;
        }
        if (!end) break;
        text = end + 1;
    }
    return count;
}

mapLabelStyle_t const *MapLabels_Style(mapLabelKind_t kind) {
    return kind < MAP_LABEL_KIND_COUNT ? &map_label_styles[kind] : NULL;
}

float MapLabels_Alpha(mapLabelKind_t kind, float scale) {
    mapLabelStyle_t const *style = MapLabels_Style(kind);
    float alpha = 1.0f;

    if (!style || !isfinite(scale) || scale <= 0.0f) return 0.0f;
    if (scale < style->min_scale || scale > style->max_scale) return 0.0f;
    /* Fade over the outer quarter (in ratio terms) of each finite band edge. */
    if (style->min_scale > 0.0f) alpha = MIN(alpha, (scale / style->min_scale - 1.0f) / 0.25f);
    alpha = MIN(alpha, (style->max_scale / scale - 1.0f) / 0.25f);
    return MAX(0.0f, MIN(1.0f, alpha));
}

bool MapLabels_Place(rect_t const *rect, rect_t *placed, uint32_t *count, uint32_t max) {
    if (!rect || !placed || !count) return false;
    FOR_LOOP(i, *count) {
        rect_t const *o = &placed[i];
        if (rect->x < o->x + o->w && o->x < rect->x + rect->w &&
            rect->y < o->y + o->h && o->y < rect->y + rect->h) return false;
    }
    if (*count >= max) return false;
    placed[(*count)++] = *rect;
    return true;
}
