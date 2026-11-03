#include "client.h"
#include "client/map_labels.h"

/* Per-map geographic labels (client/map_labels.h). Loaded with the world, drawn as a
 * presentation overlay after the 3D frame and over the minimap. Labels are public geography:
 * they ignore fog of war and carry a dark outline so they stay readable over dimmed terrain. */

#define MAP_LABEL_FONT "Fonts\\FRIZQT__.TTF" // WC3 master font path; Frontline/Emberfield ship DejaVu here
#define MAP_LABEL_MINIMAP_FONT_SIZE 9        // renderer minimum font size
#define MAP_LABEL_SCALE_STEP 200.0f          // world units; probe distance for the projected scale

static mapLabel_t map_labels[MAX_MAP_LABELS];
static uint32_t map_label_count;
static char map_labels_map[MAX_PATHLEN];

void CL_ClearMapLabels(void) {
    map_label_count = 0;
    map_labels_map[0] = 0;
}

void CL_LoadMapLabels(cstring_t map) {
    PATHSTR path;
    void *buffer = NULL;
    int size;

    if (!map || !*map) { CL_ClearMapLabels(); return; }
    if (!strcmp(map_labels_map, map)) return;
    CL_ClearMapLabels();
    snprintf(map_labels_map, sizeof(map_labels_map), "%s", map);
    snprintf(path, sizeof(path), "%s\\war3mapLabels.txt", map);
    size = FS_ReadFileQ3(path, &buffer);
    if (size <= 0 || !buffer) {
        if (buffer) FS_FreeFile(buffer);
        return;
    }
    char *text = malloc((size_t)size + 1);
    if (text) {
        memcpy(text, buffer, (size_t)size);
        text[size] = 0;
        map_label_count = MapLabels_Parse(text, map_labels, MAX_MAP_LABELS);
        free(text);
    }
    FS_FreeFile(buffer);
}


static bool CL_MapLabelProject(vec2_t origin, vec2_t *screen, float *scale) {
    vec3_t point = { origin.x, origin.y, 0.0f };
    vec2_t probe;

    point.z = re.GetHeightAtPoint ? MAX(0.0f, re.GetHeightAtPoint(origin.x, origin.y)) : 0.0f;
    if (!SCR_ProjectWorldPoint(&point, screen)) return false;
    FOR_LOOP(side, 2) {
        vec3_t other = point;
        other.x += side ? -MAP_LABEL_SCALE_STEP : MAP_LABEL_SCALE_STEP;
        if (!SCR_ProjectWorldPoint(&other, &probe)) continue;
        *scale = hypotf(probe.x - screen->x, probe.y - screen->y) * (1000.0f / MAP_LABEL_SCALE_STEP);
        return true;
    }
    return false;
}

static void CL_DrawMapLabelText(font_t const *font, cstring_t text, rect_t rect, color32_t color,
                                bool outline, rect_t const *clip) {
    float const px = SCR_UICanvasWidth() / MAX(1.0f, (float)re.GetWindowSize().width);
    color32_t const shadow = MAKE(color32_t, 8, 12, 16, (uint8_t)(color.a * (outline ? 0.85f : 0.6f)));
    static vec2_t const offsets[] = { {1, 1}, {-1, 1}, {1, -1}, {-1, -1} };
    drawText_t dt = { .font = font, .text = text, .rect = rect, .color = shadow, .textWidth = rect.w,
                      .halign = FONT_JUSTIFYCENTER, .valign = FONT_JUSTIFYMIDDLE,
                      .flags = clip ? DRAW_CLIP : 0, .clip = clip ? *clip : MAKE(rect_t, 0, 0, 0, 0) };
    FOR_LOOP(i, outline ? 4 : 1) {
        dt.rect = MAKE(rect_t, rect.x + offsets[i].x * px, rect.y + offsets[i].y * px * UI_PIXEL_ASPECT, rect.w, rect.h);
        re.DrawText(&dt);
    }
    dt.rect = rect;
    dt.color = color;
    re.DrawText(&dt);
}

/* Centre `text` on `at`; returns the label box used for declutter. */
static rect_t CL_MapLabelRect(font_t const *font, cstring_t text, vec2_t at) {
    vec2_t size = re.GetTextSize(&MAKE(drawText_t, .font = font, .text = text,
                                       .rect = MAKE(rect_t, 0, 0, SCR_UICanvasWidth(), UI_BASE_HEIGHT),
                                       .textWidth = SCR_UICanvasWidth()));
    float const pad = 0.004f;
    return MAKE(rect_t, at.x - size.x * 0.5f - pad, at.y - size.y * 0.5f - pad * 0.5f, size.x + pad * 2, size.y + pad);
}

/* Draw world labels: background names (seas, regions) declutter among themselves, point names
 * (groups, islands, bases) among themselves, larger kinds first so they win overlaps. */
void CL_DrawMapLabels(void) {
    static rect_t placed[2][MAX_MAP_LABELS];
    uint32_t counts[2] = { 0, 0 };

    if (!map_label_count || (cl.viewDef.rdflags & RDF_NOWORLDMODEL)) return;
    FOR_LOOP(kind, MAP_LABEL_KIND_COUNT) {
        mapLabelStyle_t const *style = MapLabels_Style((mapLabelKind_t)kind);
        font_t const *font = re.LoadFont(MAP_LABEL_FONT, style->font_size);
        uint32_t const layer = style->background ? 0 : 1;
        if (!font) continue;
        FOR_LOOP(i, map_label_count) {
            mapLabel_t const *label = &map_labels[i];
            vec2_t screen;
            float scale = 0.0f, alpha;
            if (label->kind != kind || !CL_MapLabelProject(label->origin, &screen, &scale)) continue;
            alpha = MapLabels_Alpha(label->kind, scale);
            if (alpha <= 0.01f) continue;
            rect_t const box = CL_MapLabelRect(font, label->name, screen);
            if (!MapLabels_Place(&box, placed[layer], &counts[layer], MAX_MAP_LABELS)) continue;
            color32_t color = style->color;
            color.a = (uint8_t)(color.a * alpha);
            CL_DrawMapLabelText(font, label->name, box, color, !style->background, NULL);
        }
    }
}

/* Small labels for the major island groups over the minimap, kept inside its frame. */
void CL_DrawMinimapLabels(rect_t const *frame) {
    static rect_t placed[MAX_MAP_LABELS];
    uint32_t count = 0;
    font_t const *font;

    if (!map_label_count || !frame) return;
    font = re.LoadFont(MAP_LABEL_FONT, MAP_LABEL_MINIMAP_FONT_SIZE);
    if (!font) return;
    FOR_LOOP(i, map_label_count) {
        mapLabel_t const *label = &map_labels[i];
        mapLabelStyle_t const *style = MapLabels_Style(label->kind);
        vec2_t screen;
        if (!style->minimap || !re.WorldToMinimap(&label->origin, &screen)) continue;
        rect_t box = CL_MapLabelRect(font, label->name, screen);
        /* Keep edge names (Manchuria, Hawaiian Islands) whole by sliding them inside the frame. */
        box.x = MAX(frame->x, MIN(box.x, frame->x + frame->w - box.w));
        box.y = MAX(frame->y, MIN(box.y, frame->y + frame->h - box.h));
        if (!MapLabels_Place(&box, placed, &count, MAX_MAP_LABELS)) continue;
        color32_t color = style->color;
        color.a = 230;
        CL_DrawMapLabelText(font, label->name, box, color, true, frame);
    }
}
