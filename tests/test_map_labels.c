#include "test.h"
#include "client/map_labels.h"

TEST(map_labels, parses_kinds_positions_and_multiword_names) {
    static char const text[] =
        "# Frontline Pacific place names\n"
        "\n"
        "sea -3000 -9000 Coral Sea\r\n"
        "group 8000 1200 Marshall Islands  \n"
        "  island 16700 4300 Oahu\n"
        "BASE 16700.5 4300.25 Pearl Harbor\n"
        "region -12000 15000 Japan\n";
    mapLabel_t labels[8];
    T_EQ(MapLabels_Parse(text, labels, 8), 5u);
    T_EQ(labels[0].kind, MAP_LABEL_SEA);
    T_STREQ(labels[0].name, "Coral Sea");
    T_FEQ(labels[0].origin.x, -3000.0f, 0.001f);
    T_FEQ(labels[0].origin.y, -9000.0f, 0.001f);
    T_EQ(labels[1].kind, MAP_LABEL_GROUP);
    T_STREQ(labels[1].name, "Marshall Islands");
    T_EQ(labels[2].kind, MAP_LABEL_ISLAND);
    T_EQ(labels[3].kind, MAP_LABEL_BASE);
    T_FEQ(labels[3].origin.y, 4300.25f, 0.001f);
    T_STREQ(labels[3].name, "Pearl Harbor");
    T_EQ(labels[4].kind, MAP_LABEL_REGION);
}

TEST(map_labels, rejects_malformed_lines_and_bounds_output) {
    mapLabel_t label, labels[2];
    T_ASSERT(!MapLabels_ParseLine("volcano 0 0 Fuji", &label));
    T_ASSERT(!MapLabels_ParseLine("island 0 Midway", &label));
    T_ASSERT(!MapLabels_ParseLine("island 0 0", &label));
    T_ASSERT(!MapLabels_ParseLine("island 0 0    ", &label));
    T_ASSERT(!MapLabels_ParseLine("# island 0 0 Midway", &label));
    T_ASSERT(!MapLabels_ParseLine("island nan 0 Midway", &label));
    T_EQ(MapLabels_Parse("island 1 1 A\nisland 2 2 B\nisland 3 3 C\n", labels, 2), 2u);
    T_STREQ(labels[1].name, "B");
    T_EQ(MapLabels_Parse("", labels, 2), 0u);
    T_EQ(MapLabels_Parse(NULL, labels, 2), 0u);
}

TEST(map_labels, long_names_truncate_with_sentinel_intact) {
    struct { mapLabel_t label; char sentinel; } probe;
    char line[MAP_LABEL_LINE_LEN];
    char longline[MAP_LABEL_LINE_LEN + 40];
    probe.sentinel = 0x5a;
    snprintf(line, sizeof(line), "island 0 0 %s", "Abcdefghijklmnopqrstuvwxyz Abcdefghijklmnopqrstuvwxyz Abcdefghij");
    T_ASSERT(MapLabels_ParseLine(line, &probe.label));
    T_EQ(strlen(probe.label.name), (size_t)MAP_LABEL_NAME_LEN - 1);
    T_EQ(probe.sentinel, 0x5a);
    memset(longline, 'x', sizeof(longline) - 1);
    longline[sizeof(longline) - 1] = 0;
    memcpy(longline, "island 0 0 ", 11);
    mapLabel_t labels[2];
    T_EQ(MapLabels_Parse(longline, labels, 2), 0u); /* over-long lines are skipped, not split */
}

/* Seas fade out as the camera closes in; bases only appear close; islands own the middle band. */
TEST(map_labels, zoom_bands_order_seas_islands_and_bases) {
    float const far = 0.10f, medium = 0.21f, close = 0.40f;
    T_ASSERT(MapLabels_Alpha(MAP_LABEL_SEA, far) > 0.5f);
    T_FEQ(MapLabels_Alpha(MAP_LABEL_SEA, close), 0.0f, 0.0001f);
    T_ASSERT(MapLabels_Alpha(MAP_LABEL_SEA, medium) < 0.75f); /* fading out */
    T_ASSERT(MapLabels_Alpha(MAP_LABEL_ISLAND, medium) > 0.9f);
    T_ASSERT(MapLabels_Alpha(MAP_LABEL_ISLAND, close) > 0.9f);
    T_FEQ(MapLabels_Alpha(MAP_LABEL_ISLAND, 0.02f), 0.0f, 0.0001f);
    T_FEQ(MapLabels_Alpha(MAP_LABEL_BASE, far), 0.0f, 0.0001f);
    T_FEQ(MapLabels_Alpha(MAP_LABEL_BASE, medium), 0.0f, 0.0001f);
    T_ASSERT(MapLabels_Alpha(MAP_LABEL_BASE, close) > 0.9f);
    T_ASSERT(MapLabels_Alpha(MAP_LABEL_GROUP, far) > 0.9f);
    T_FEQ(MapLabels_Alpha(MAP_LABEL_GROUP, close), 0.0f, 0.0001f);
    /* fades are continuous near a band edge */
    mapLabelStyle_t const *island = MapLabels_Style(MAP_LABEL_ISLAND);
    float const edge = MapLabels_Alpha(MAP_LABEL_ISLAND, island->min_scale * 1.1f);
    T_ASSERT(edge > 0.0f && edge < 1.0f);
    T_FEQ(MapLabels_Alpha(MAP_LABEL_ISLAND, 0.0f), 0.0f, 0.0001f);
    T_FEQ(MapLabels_Alpha(MAP_LABEL_KIND_COUNT, medium), 0.0f, 0.0001f);
}

TEST(map_labels, styles_put_groups_on_the_minimap_and_seas_in_the_background) {
    T_ASSERT(MapLabels_Style(MAP_LABEL_GROUP)->minimap);
    T_ASSERT(!MapLabels_Style(MAP_LABEL_BASE)->minimap);
    T_ASSERT(!MapLabels_Style(MAP_LABEL_REGION)->minimap);
    T_ASSERT(!MapLabels_Style(MAP_LABEL_ISLAND)->minimap);
    T_ASSERT(MapLabels_Style(MAP_LABEL_SEA)->background);
    T_ASSERT(!MapLabels_Style(MAP_LABEL_ISLAND)->background);
    T_ASSERT(MapLabels_Style(MAP_LABEL_SEA)->font_size > MapLabels_Style(MAP_LABEL_ISLAND)->font_size);
    T_ASSERT(MapLabels_Style(MAP_LABEL_SEA)->color.a < MapLabels_Style(MAP_LABEL_ISLAND)->color.a);
    T_ASSERT(MapLabels_Style(MAP_LABEL_KIND_COUNT) == NULL);
}

TEST(map_labels, declutter_drops_overlapping_labels_first_come_first_kept) {
    rect_t placed[2];
    uint32_t count = 0;
    rect_t const a = { 0.10f, 0.10f, 0.05f, 0.02f };
    rect_t const overlap = { 0.12f, 0.11f, 0.05f, 0.02f };
    rect_t const touching = { 0.15f, 0.10f, 0.05f, 0.02f };
    rect_t const far = { 0.50f, 0.40f, 0.05f, 0.02f };
    T_ASSERT(MapLabels_Place(&a, placed, &count, 2));
    T_ASSERT(!MapLabels_Place(&overlap, placed, &count, 2));
    T_ASSERT(MapLabels_Place(&touching, placed, &count, 2));
    T_EQ(count, 2u);
    T_ASSERT(!MapLabels_Place(&far, placed, &count, 2)); /* capacity */
    T_EQ(count, 2u);
}
