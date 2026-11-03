#ifndef r_font_fallback_h
#define r_font_fallback_h

/* Base letter for a Latin Extended-A codepoint (U+0100..U+017F: ā ē ī ō ū ł ő ...), or 0.
 * The font renderer draws this letter when the loaded font has no glyph for the accented one,
 * so "Kongō" degrades to "Kongo" instead of dropping the letter. */
static inline unsigned R_FontFallbackCodepoint(unsigned codepoint) {
    static char const latin_extended_a[129] =
        "AaAaAaCcCcCcCcDdDdEeEeEeEeEeGgGgGgGgHhHhIiIiIiIiIiIiJjKkkLlLlLlLlLlNnNnNnnNnOoOoOoOoRrRrRrSsSsSsSsTtTtTtUuUuUuUuUuUuWwYyYZzZzZzs";
    return codepoint >= 0x100 && codepoint < 0x180 ? (unsigned char)latin_extended_a[codepoint - 0x100] : 0;
}

#endif
