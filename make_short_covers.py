"""Rotating Shorts covers (user 2026-10-30: "design new cover each short video").
render(frame_png, title, out_jpg, cover=None) -> layout name.
cover (spec "cover"): {"layout": "auto"|name, "words": [2-4 words, not the title], "number": "-$42.4B" (real, verified), "kicker": "AMAZON"}
Auto picks a layout not used in the last 4 Shorts (covers/short_cover_log.json). 1080x1920, orange #FA4E02 / cream / black, never yellow.
"""
import json, os, random, datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

W, H = 1080, 1920
FD = "/workspace/work/yt/fonts/"
OR = (250, 78, 2); CR = (248, 241, 228); BK = (12, 12, 14); WH = (255, 255, 255)
LOG = "/workspace/work/yt/covers/short_cover_log.json"
LAYOUTS = ["slab", "topbar", "number", "split", "frame", "bold"]

def ANTON(s): return ImageFont.truetype(FD + "Anton-Regular.ttf", int(s))
def POP(s): return ImageFont.truetype(FD + "Poppins-ExtraBold.ttf", int(s))
def POPS(s): return ImageFont.truetype(FD + "Poppins-SemiBold.ttf", int(s))

def _log():
    try: return json.load(open(LOG))
    except Exception: return []

def pick(want):
    if want and want != "auto": return want
    recent = [e["layout"] for e in _log()[-4:]]
    free = [l for l in LAYOUTS if l not in recent] or LAYOUTS
    random.seed(); return random.choice(free)

def wrap(d, text, font, maxw):
    L = [""]
    for w in text.split():
        x = (L[-1] + " " + w).strip()
        if d.textlength(x, font=font) > maxw and L[-1]: L.append(w)
        else: L[-1] = x
    return L

def fit_block(text, ffn, maxw, maxh, start, lo=50, lh=1.08):
    d = ImageDraw.Draw(Image.new("L", (1, 1))); s = start
    while True:
        f = ffn(s); L = wrap(d, text, f, maxw)
        if (len(L) * s * lh <= maxh and all(d.textlength(l, font=f) <= maxw for l in L)) or s <= lo: return f, L, s
        s -= 4

def draw_lines(im, L, f, s, x, y, fill, lh=1.08, align="l", shadow=False):
    d = ImageDraw.Draw(im)
    for l in L:
        tx = x if align == "l" else (W - d.textlength(l, font=f)) / 2
        if shadow:
            sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((tx + 4, y + 6), l, font=f, fill=(0, 0, 0, 200))
            im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8))); d = ImageDraw.Draw(im)
        d.text((tx, y), l, font=f, fill=fill); y += int(s * lh)
    return y

def logo(im, x, y, col=OR, txt=CR):
    d = ImageDraw.Draw(im); r = 26
    d.ellipse([x, y, x + 2 * r, y + 2 * r], fill=col); d.ellipse([x + 13, y + 13, x + 2 * r - 13, y + 2 * r - 13], fill=BK if col != BK else OR)
    d.text((x + 2 * r + 14, y + 2), "ROTATION", font=POP(38), fill=txt)

def grain(im, a=0.05):
    n = Image.effect_noise((W, H), 40).convert("L").point(lambda v: int(v * a))
    g = Image.new("RGBA", (W, H), (255, 255, 255, 0)); g.putalpha(n); im.alpha_composite(g)

def duo(bg, dark, light):
    g = ImageOps.grayscale(bg.convert("RGB")); g = ImageOps.autocontrast(g, cutoff=1)
    return ImageOps.colorize(g, dark, light).convert("RGBA")

def darken(bg, a):
    bg = bg.copy(); bg.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, a))); return bg

def grad(bg, y0, y1, a=235):
    m = Image.new("L", (1, H), 0)
    for y in range(H): m.putpixel((0, y), int(a * min(1, max(0, (y - y0) / max(1, y1 - y0)))))
    sh = Image.new("RGBA", (W, H), BK + (0,)); sh.putalpha(m.resize((W, H))); bg = bg.copy(); bg.alpha_composite(sh); return bg

def render(frame, title, out, cover=None):
    c = cover or {}
    lay = pick(c.get("layout", "auto"))
    bg = ImageOps.fit(Image.open(frame).convert("RGBA"), (W, H))
    words = " ".join(c.get("words") or []) or title
    num = c.get("number"); kick = (c.get("kicker") or "").upper()
    if lay == "slab":   # orange slab bottom, cream headline (the original Short cover)
        im = bg.copy(); top = 1060; d = ImageDraw.Draw(im)
        d.rectangle([0, top, W, H], fill=OR); d.rectangle([0, top - 10, W, top], fill=CR)
        logo(im, 75, top + 50, col=CR, txt=CR)
        f, L, s = fit_block(title, lambda z: POP(z), W - 150, H - top - 260, 104, 70, 1.13)
        draw_lines(im, L, f, s, 75, top + 150, CR, 1.13)
    elif lay == "topbar":   # cream block on top, black caps words, orange rule, footage below
        im = bg.copy(); bar = 760; d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, bar], fill=CR); d.rectangle([0, bar, W, bar + 18], fill=OR)
        if kick: d.text((80, 120), kick, font=POPS(44), fill=OR)
        f, L, s = fit_block(words.upper(), ANTON, W - 160, bar - 330, 230, 90, 1.0)
        draw_lines(im, L, f, s, 80, 200, BK, 1.0)
        logo(im, W - 330, 112, col=OR, txt=BK)
    elif lay == "number":   # dark footage, huge orange number, words under it
        im = grad(darken(bg, 70), 500, 1300, 230)
        n = num or words; d = ImageDraw.Draw(im)
        f, L, s = fit_block(n, ANTON, W - 120, 520, 420, 120, 1.0)
        y = draw_lines(im, L, f, s, 0, 820, OR, 1.0, "c", True)
        f2, L2, s2 = fit_block(words.upper() if num else title.upper(), ANTON, W - 180, 330, 120, 60, 1.05)
        draw_lines(im, L2, f2, s2, 0, y + 40, WH, 1.05, "c", True)
        if kick: ImageDraw.Draw(im).text(((W - ImageDraw.Draw(im).textlength(kick, font=POPS(44))) / 2, 700), kick, font=POPS(44), fill=CR)
        logo(im, (W - 300) // 2, 1740, col=OR, txt=CR)
    elif lay == "split":   # duotone footage top 58 %, black bottom, orange words + white number
        cut = 1110; im = Image.new("RGBA", (W, H), BK + (255,))
        top = duo(ImageOps.fit(bg, (W, cut)), (20, 20, 24), CR); im.alpha_composite(top)
        d = ImageDraw.Draw(im); d.rectangle([0, cut, W, cut + 14], fill=OR)
        if num:
            pf = POP(110); pw = d.textlength(num, font=pf)
            d.rounded_rectangle([70, cut - 90, 70 + pw + 70, cut + 90], 20, fill=OR); d.text((105, cut - 78), num, font=pf, fill=WH)
        f, L, s = fit_block(words.upper(), ANTON, W - 150, 470, 210, 80, 1.02)
        draw_lines(im, L, f, s, 75, cut + 160, OR if num else WH, 1.02)
        logo(im, 75, 1760, col=OR, txt=CR)
    elif lay == "frame":   # cream border frame, footage window, black headline on cream foot, orange pill
        im = Image.new("RGBA", (W, H), CR + (255,)); m = 54; win_h = 1180
        im.alpha_composite(ImageOps.fit(bg, (W - 2 * m, win_h)), (m, m))
        d = ImageDraw.Draw(im)
        pill = kick or (num or "")
        if pill:
            pf = POP(54); pw = d.textlength(pill, font=pf)
            d.rounded_rectangle([m + 30, m + win_h - 110, m + 30 + pw + 60, m + win_h - 20], 45, fill=OR); d.text((m + 60, m + win_h - 105), pill, font=pf, fill=WH)
        f, L, s = fit_block(title, POP, W - 2 * m - 40, H - win_h - m - 260, 100, 60, 1.12)
        draw_lines(im, L, f, s, m + 20, win_h + m + 60, BK, 1.12)
        logo(im, m + 20, H - 130, col=OR, txt=BK)
    else:   # bold: orange duotone full bleed, giant white stacked caps
        im = duo(bg, (40, 10, 0), OR); im = grad(im, 900, 1500, 120)
        f, L, s = fit_block(words.upper(), ANTON, W - 140, 900, 300, 100, 0.98)
        y0 = (H - len(L) * int(s * 0.98)) // 2
        draw_lines(im, L, f, s, 0, y0, WH, 0.98, "c", True)
        if num:
            d = ImageDraw.Draw(im); pf = POP(90); pw = d.textlength(num, font=pf)
            d.rounded_rectangle([(W - pw) / 2 - 40, y0 - 190, (W + pw) / 2 + 40, y0 - 50], 24, fill=BK); d.text(((W - pw) / 2, y0 - 180), num, font=pf, fill=OR)
        logo(im, (W - 300) // 2, 1740, col=BK, txt=WH)
    grain(im)
    os.makedirs(os.path.dirname(out), exist_ok=True); im.convert("RGB").save(out, quality=92)
    if c.get("log", True):
        lg = _log(); lg.append({"date": str(datetime.date.today()), "title": title, "layout": lay, "out": out}); json.dump(lg, open(LOG, "w"), indent=1)
    return lay

if __name__ == "__main__":
    import sys
    a = json.loads(sys.argv[1]); print(render(a["frame"], a["title"], a["out"], a.get("cover")))
