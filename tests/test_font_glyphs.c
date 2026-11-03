#include "test.h"
#include "renderer/r_local.h"

/* Production font rasteriser with the GPU upload and draw calls stubbed out: glyph metrics,
 * the lazily baked 256-codepoint sets and the missing-glyph fallback all run for real. */
#include "renderer/r_font.c"

#define SHIPPED_FONT "tools/emberfield/assets/fonts/DejaVuSans.ttf" // Emberfield\Fonts\ui.ttf and Fonts\FRIZQT__.TTF
#define LATIN1_FONT "tests/resources/dejavu-latin1.ttf"           // previous U+0020..U+00FF subset

refImport_t ri;
static texture_t test_font_texture;
static uint32_t test_font_uploads;

texture_t *R_AllocateTexture(uint32_t width, uint32_t height) {
    test_font_texture.width = width;
    test_font_texture.height = height;
    return &test_font_texture;
}
void R_LoadTextureMipLevel(texture_t *texture, texMip_t const *mip) { (void)texture; (void)mip; test_font_uploads++; }
void R_ReleaseTexture(texture_t *texture) { (void)texture; }
vertex_t *R_AddQuad(vertex_t *buffer, rect_t const *screen, rect_t const *uv, color32_t color, float z) {
    (void)screen; (void)uv; (void)color; (void)z; return buffer;
}
void R_DrawImageEx(drawImage_t const *drawImage) { (void)drawImage; }
void R_DrawImageBatch(texture_t const *texture, SHADERTYPE shaderType, BLEND_MODE alphamode, float uActiveGlow,
                      float uRadialShade, bool hasClip, rect_t const *clip, vertex_t const *vertices,
                      uint32_t num_vertices, bool repeat) {
    (void)texture; (void)shaderType; (void)alphamode; (void)uActiveGlow; (void)uRadialShade; (void)hasClip;
    (void)clip; (void)vertices; (void)num_vertices; (void)repeat;
}

static void *test_font_alloc(long size) { return calloc(1, (size_t)size); }
static void test_font_free(handle_t ptr) { free(ptr); }
static int test_font_read(cstring_t filename, void **buffer) {
    FILE *file = fopen(filename, "rb");
    long size;
    if (!file) return -1;
    fseek(file, 0, SEEK_END);
    size = ftell(file);
    fseek(file, 0, SEEK_SET);
    *buffer = malloc((size_t)size);
    if (!*buffer || fread(*buffer, 1, (size_t)size, file) != (size_t)size) { fclose(file); free(*buffer); return -1; }
    fclose(file);
    return (int)size;
}

static font_t *test_load_font(cstring_t path) {
    ri.MemAlloc = test_font_alloc;
    ri.MemFree = test_font_free;
    ri.FS_ReadFile = test_font_read;
    return R_LoadFont(path, 16);
}

/* "Kongō" lost its last letter: the shipped UI font was a Latin-1 subset with no macron glyphs. */
TEST(font_glyphs, shipped_ui_font_covers_latin_extended_a) {
    void *data = NULL;
    stbtt_fontinfo info;
    T_ASSERT(test_font_read(SHIPPED_FONT, &data) > 0);
    T_ASSERT(stbtt_InitFont(&info, data, 0));
    for (unsigned cp = 0x20; cp < 0x7f; cp++) T_ASSERT(stbtt_FindGlyphIndex(&info, (int)cp) != 0);
    for (unsigned cp = 0xa0; cp < 0x180; cp++) T_ASSERT(stbtt_FindGlyphIndex(&info, (int)cp) != 0);
    free(data);
}

TEST(font_glyphs, macron_letters_measure_and_bake_in_their_own_set) {
    font_t *font = test_load_font(SHIPPED_FONT);
    T_ASSERT(font != NULL);
    float const kong = R_GetFontWidth(font, "Kong");
    float const kongo = R_GetFontWidth(font, "Kongo");
    T_ASSERT(kongo > kong);
    T_FEQ(R_GetFontWidth(font, "Kong\xC5\x8D"), kongo, 0.0001f); /* ō has o's advance in DejaVu Sans */
    T_ASSERT(R_GetFontWidth(font, "\xC4\x81\xC4\x93\xC4\xAB\xC5\x8D\xC5\xAB") > 0.0f); /* ā ē ī ō ū */
    T_ASSERT(font->sets[1] != NULL);   /* U+0100..U+01FF baked lazily as one 256-glyph set */
    T_ASSERT(font->sets[2] == NULL);   /* untouched ranges cost nothing */
    glyphSet_t *set = font->sets[1];
    T_EQ(set->missing[0x4d / 8] & (1u << (0x4d % 8)), 0u);
    R_ReleaseFont(font);
}

/* A font without Latin Extended-A (retail FRIZQT__ or an older subset) draws the base letter. */
TEST(font_glyphs, missing_accented_letter_falls_back_to_its_base_letter) {
    font_t *font = test_load_font(LATIN1_FONT);
    T_ASSERT(font != NULL);
    T_FEQ(R_GetFontWidth(font, "Kong\xC5\x8D"), R_GetFontWidth(font, "Kongo"), 0.0001f);
    T_FEQ(R_GetFontWidth(font, "\xC5\xAA"), R_GetFontWidth(font, "U"), 0.0001f);
    T_ASSERT(R_GetFontWidth(font, "\xC5\x8D") > 0.0f);
    glyphSet_t *set = font->sets[1];
    T_ASSERT(set != NULL);
    T_ASSERT(set->missing[0x4d / 8] & (1u << (0x4d % 8)));
    R_ReleaseFont(font);
}

TEST(font_glyphs, fallback_table_maps_latin_extended_a_to_ascii_letters) {
    T_EQ(R_FontFallbackCodepoint(0x014D), (unsigned)'o'); /* ō */
    T_EQ(R_FontFallbackCodepoint(0x016A), (unsigned)'U'); /* Ū */
    T_EQ(R_FontFallbackCodepoint(0x0101), (unsigned)'a'); /* ā */
    T_EQ(R_FontFallbackCodepoint(0x0142), (unsigned)'l'); /* ł */
    T_EQ(R_FontFallbackCodepoint(0x017E), (unsigned)'z'); /* ž */
    T_EQ(R_FontFallbackCodepoint('o'), 0u);
    T_EQ(R_FontFallbackCodepoint(0x0180), 0u);
    for (unsigned cp = 0x100; cp < 0x180; cp++) {
        unsigned base = R_FontFallbackCodepoint(cp);
        T_ASSERT((base >= 'A' && base <= 'Z') || (base >= 'a' && base <= 'z'));
    }
}
