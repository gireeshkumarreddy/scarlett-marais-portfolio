# Regenerates script-words.js. Usage: python tools/make-script-words.py "Scarlett" "Conversion" "Heights" "unforgettable" "with love"
import urllib.request, io, json, re, sys
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/imperialscript/ImperialScript-Regular.ttf"
data = urllib.request.urlopen(URL, timeout=30).read()
font = TTFont(io.BytesIO(data))
gs = font.getGlyphSet()
upm = font["head"].unitsPerEm
hbfont = hb.Font(hb.Face(hb.Blob(data)))
order = font.getGlyphOrder()

WORDS = sys.argv[1:]
out = {"upm": upm}
for word in WORDS:
    buf = hb.Buffer(); buf.add_str(word); buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"liga": True, "calt": True, "kern": True})
    x = 0; glyphs = []; bp = BoundsPen(gs)
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        ox, oy = x + pos.x_offset, pos.y_offset
        sp = SVGPathPen(gs, ntos=lambda v: ("%.0f" % v))
        gs[name].draw(TransformPen(sp, (1, 0, 0, -1, ox, -oy)))
        gs[name].draw(TransformPen(bp, (1, 0, 0, -1, ox, -oy)))
        d = sp.getCommands()
        contours = [c.strip() for c in re.split(r"(?=M)", d) if c.strip()]
        if contours:
            glyphs.append(contours)
        x += pos.x_advance
    xmin, ymin, xmax, ymax = bp.bounds
    pad = 30
    out[word] = {"vb": [int(xmin - pad), int(ymin - pad), int(xmax - xmin + 2 * pad), int(ymax - ymin + 2 * pad)], "g": glyphs}
    print(word, out[word]["vb"], len(glyphs), "glyphs", sum(len(g) for g in glyphs), "contours", file=sys.stderr)

js = "/* Imperial Script (OFL) outlines, pre-shaped with HarfBuzz for the handwriting animation */\nwindow.SCRIPT_WORDS = " + json.dumps(out, separators=(",", ":")) + ";\n"
open("script-words.js", "w").write(js)
print(len(js), "bytes", file=sys.stderr)
