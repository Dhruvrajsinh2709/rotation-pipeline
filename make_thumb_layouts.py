#!/usr/bin/env python3
"""Rotation long-form thumbnails: a NEW layout every video (user 2026-10-30: "don't repeat long-form video cover design").
Same brand (cut-out subject, orange #FA4E02, cream, black, Anton/Poppins, small logo), six layouts that rotate:
  collage  cut-out over blue-duotone place photo + orange disc + props + 2-3 title-case words   (make_thumb_collage.py)
  stack    orange band left with stacked caps words (one on a black slab) + cut-out + dark line chart right ending in a value slab
  slab     cut-out on duotone left + cream panel right with a big number on a black slab and a falling/rising orange bar
  ui       cut-out left + cream panel right with a company wordmark and a search/chat box holding a provocative question
  grid     cut-out + tile grid of names (what the story touches) + stacked caps words bottom-left
  ring     dark bg, thin concentric rings around a wordmark on a white slab + cut-out + caps words
Auto-rotation: "layout": "auto" (default) picks a layout not used in the last 4 long videos (covers/cover_log.json) and
a duotone tint not used last time. Every render appends {date, title, layout, tint, out} to the log unless "log": false.
Usage: PYTHONPATH=/workspace/work/pylib python3 make_thumb_layouts.py '{json}'   (keys per layout: see SPEC_KEYS "Thumbnail layouts")
"""
import json, sys, os, random, math, datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps, ImageChops
sys.path.insert(0, "/workspace/work/yt")
W, H = 1280, 720; FD = "/workspace/work/yt/fonts/"; OR = (250, 78, 2); CR = (248, 241, 228); BK = (12, 12, 14)
LOG = "/workspace/work/yt/covers/cover_log.json"; LAYOUTS = ["stack", "slab", "ui", "grid"]  # Study 11 (2026-11-01): collage + ring dropped (abstract covers lose)
TINTS = [[10, 38, 78], [70, 20, 18], [16, 52, 40], [48, 28, 72], [60, 44, 12], [14, 46, 62]]
def F(name, sz): return ImageFont.truetype(FD + name, int(sz))
def ANTON(sz): return F("Anton-Regular.ttf", sz)
def POP(sz): return F("Poppins-ExtraBold.ttf", sz)
def POPS(sz): return F("Poppins-SemiBold.ttf", sz)

def load_log():
    try: return json.load(open(LOG))
    except Exception: return []
def pick(c):
    log = load_log(); recent = [e.get("layout") for e in log[-4:]]
    lay = c.get("layout", "auto")
    if lay == "auto":
        free = [l for l in LAYOUTS if l not in recent] or LAYOUTS
        random.seed(c.get("title", "") + str(len(log))); lay = random.choice(free)
    tint = c.get("tint")
    if not tint:
        last = log[-1].get("tint") if log else None
        opts = [t for t in TINTS if t != last]; random.seed(c.get("title", "") + "t"); tint = random.choice(opts)
    return lay, list(tint)

# ---------- shared pieces ----------
def cover(im, w, h, fx=0.5, fy=0.5):
    s = max(w/im.width, h/im.height); im = im.resize((int(im.width*s+1), int(im.height*s+1)), Image.LANCZOS)
    x = int((im.width-w)*fx); y = int((im.height-h)*fy); return im.crop((x, y, x+w, y+h))
def duotone(path, w, h, tint, fx=0.5, blur=2):
    bg = cover(Image.open(path).convert("RGB"), w, h, fx).filter(ImageFilter.GaussianBlur(blur))
    g = ImageOps.autocontrast(bg.convert("L"))
    return ImageOps.colorize(g, black=(4, 6, 10), white=tuple(min(255, v*3) for v in tint), mid=tuple(tint)).convert("RGBA")
def cutout(p):
    im = Image.open(p)
    if not (im.mode == "RGBA" and im.split()[3].getextrema()[0] < 10):
        from rembg import remove, new_session
        im = remove(im.convert("RGB"), session=new_session("isnet-general-use"))
    return im.crop(im.split()[3].getbbox())
def place_subject(bg, c, h, cx, dy=0, shadow=True):
    sub = cutout(c["subject"]); sub = sub.resize((int(sub.width*h/sub.height), h), Image.LANCZOS)
    sub = ImageEnhance.Contrast(ImageEnhance.Color(sub).enhance(1.12)).enhance(1.08)
    if c.get("flip"): sub = ImageOps.mirror(sub)
    x = int(cx - sub.width/2); y = H - h + dy
    if shadow:
        a = sub.split()[3]; s = Image.new("RGBA", sub.size, (0, 0, 0, 0)); s.putalpha(a.point(lambda v: int(v*0.6)))
        bg.alpha_composite(s.filter(ImageFilter.GaussianBlur(14)), (x+14, y+10))
    bg.alpha_composite(sub, (x, y)); return (x, y, x+sub.width, y+h)
def logo(h, col=OR):
    src = Image.open('/workspace/work/yt/banner/logo.jpg').convert('L')
    a = src.point(lambda v: 255 if v > 200 else (0 if v < 150 else int((v-150)*255/50)))
    m = Image.new('RGBA', src.size, col + (0,)); m.putalpha(a); m = m.crop(a.getbbox())
    return m.resize((int(m.width*h/m.height), h), Image.LANCZOS)
def shadowed(bg, layer, off=(4, 6), blur=8, k=0.8):
    s = Image.new("RGBA", bg.size, (0, 0, 0, 0)); s.putalpha(layer.split()[3].point(lambda v: int(v*k)))
    bg.alpha_composite(s.filter(ImageFilter.GaussianBlur(blur)), off); bg.alpha_composite(layer)
def fit(font_fn, words, maxw, start, lo=40):
    d = ImageDraw.Draw(Image.new("L", (1, 1))); sz = start
    while max(d.textlength(w, font=font_fn(sz)) for w in words) > maxw and sz > lo: sz -= 3
    return sz
def caps_stack(bg, words, x, y_bottom, maxw, slab_i=None, slab_col=BK, fg=(255, 255, 255), start=150, kicker=None, kcol=None):
    """Stacked Anton caps words, bottom-anchored; word `slab_i` sits on a coloured slab."""
    words = [w.upper() for w in words]; sz = fit(ANTON, words, maxw, start); f = ANTON(sz); lh = int(sz*1.02)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    y0 = y_bottom - lh*len(words)
    if kicker:
        kf = POP(26); kw = d.textlength(kicker.upper(), font=kf)
        d.rectangle([x, y0-46, x+kw+24, y0-10], fill=kcol or BK); d.text((x+12, y0-45), kicker.upper(), font=kf, fill=(255, 255, 255))
    for i, w in enumerate(words):
        yy = y0 + i*lh
        if i == slab_i:
            bb = d.textbbox((x, yy), w, font=f); d.rectangle([bb[0]-14, bb[1]-10, bb[2]+14, bb[3]+12], fill=slab_col)
        d.text((x, yy), w, font=f, fill=fg)
    shadowed(bg, L, blur=6, k=0.55)
def grain(bg, amt=0.16):
    random.seed(7); n = Image.effect_noise((W, H), 28).convert("L")
    return Image.blend(bg.convert("RGB"), ImageChops.overlay(bg.convert("RGB"), Image.merge("RGB", (n, n, n))), amt).convert("RGBA")
def finish(bg, c, logo_col=OR, pos="bl"):
    bg = grain(bg, c.get("grain", 0.14)); lg = logo(c.get("logo_h", 50), logo_col)
    xy = (30, H-lg.height-26) if pos == "bl" else (W-lg.width-30, H-lg.height-26)
    bg.alpha_composite(lg, xy); return bg

# ---------- layouts ----------
def L_collage(c, tint):
    import make_thumb_collage as mc
    cc = dict(c); cc["tint"] = tint; cc.setdefault("words", c.get("words", ["Big", "Question?"])); mc.main(cc)
    return None
def L_stack(c, tint):
    bg = Image.new("RGBA", (W, H), BK + (255,))
    # right: dark chart panel
    ch = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ch)
    vals = c.get("chart", [1, 1.2, 1.1, 1.6, 1.5, 2.4, 3.1, 2.6, 3.8, 1.2]); x0, x1, yt, yb = 640, 1230, 120, 560
    mn, mx = min(vals), max(vals); pts = [(x0+(x1-x0)*i/(len(vals)-1), yb-(yb-yt)*(v-mn)/(mx-mn or 1)) for i, v in enumerate(vals)]
    for k in range(5): yy = yt+(yb-yt)*k/4; d.line([(x0, yy), (x1, yy)], fill=(40, 40, 44, 255), width=2)
    d.line(pts, fill=OR+(255,), width=9, joint="curve"); ex, ey = pts[-1]; d.ellipse([ex-13, ey-13, ex+13, ey+13], fill=OR+(255,))
    if c.get("years"): yf = POPS(22); d.text((x0, yb+14), c["years"][0], font=yf, fill=(150, 150, 154)); d.text((x1-d.textlength(c["years"][1], font=yf), yb+14), c["years"][1], font=yf, fill=(150, 150, 154))
    bg.alpha_composite(ch)
    if c.get("value"):
        vf = POP(64); L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(L); vw = ld.textlength(c["value"], font=vf)
        bx, by = (int(ex)-vw-60, int(ey)-46) if ey > 380 else (min(int(ex)-vw/2, W-vw-70), int(ey)+30)
        ld.rectangle([bx-20, by, bx+vw+20, by+92], fill=(255, 255, 255)); ld.text((bx, by+6), c["value"], font=vf, fill=BK); shadowed(bg, L)
    # left: orange band
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(band).rectangle([0, 0, 470, H], fill=OR+(255,)); bg.alpha_composite(band)
    place_subject(bg, c, c.get("subj_h", 560), c.get("subj_x", 470), c.get("subj_dy", 0))
    caps_stack(bg, c["words"], 40, H-70, 400, slab_i=len(c["words"])-1, slab_col=BK, kicker=c.get("kicker"), kcol=BK)
    return finish(bg, c, (255, 255, 255), "br")
def L_slab(c, tint):
    bg = duotone(c["bg"], W, H, tint, c.get("bgfx", 0.5)) if c.get("bg") else Image.new("RGBA", (W, H), tuple(tint)+(255,))
    pan = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pd = ImageDraw.Draw(pan); pd.rectangle([560, 0, W, H], fill=CR+(255,)); bg.alpha_composite(pan)
    d = ImageDraw.Draw(bg)
    # chip + falling/rising bar
    up = c.get("direction", "down") == "up"; bx0, bx1 = 1040, 1200
    top, bot = (170, 640) if not up else (110, 640)
    d.rectangle([bx0, top, bx1, bot], fill=OR if not up else (30, 160, 90))
    lab = c.get("bar_label", "Losses"); lf = POP(34); d.text(((bx0+bx1)/2-d.textlength(lab, font=lf)/2, bot-70), lab, font=lf, fill=(255, 255, 255))
    if c.get("chip"):
        cf = POP(32); cw = d.textlength(c["chip"], font=cf); d.rectangle([640, 130, 640+cw+36, 190], fill=OR); d.text((658, 136), c["chip"], font=cf, fill=(255, 255, 255))
        d.line([(640, 214), (bx1, 214)], fill=BK, width=5)
    place_subject(bg, c, c.get("subj_h", 640), c.get("subj_x", 330), c.get("subj_dy", 0))
    num = c.get("number", "-$9.1B"); sz = fit(POP, [num], 520, 150); nf = POP(sz)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(L); nw = ld.textlength(num, font=nf)
    nx, ny = 600, 330; ld.rectangle([nx-16, ny, nx+nw+20, ny+sz*1.12], fill=(255, 255, 255)); ld.text((nx, ny-sz*0.06), num, font=nf, fill=BK)
    shadowed(bg, L, blur=12, k=0.5)
    if c.get("words"): caps_stack(bg, c["words"], 600, 680, 440, fg=BK, start=70)
    return finish(bg, c)
def L_ui(c, tint):
    bg = Image.new("RGBA", (W, H), CR+(255,))
    left = duotone(c["bg"], 520, H, tint, c.get("bgfx", 0.5)) if c.get("bg") else Image.new("RGBA", (520, H), tuple(tint)+(255,))
    bg.alpha_composite(left, (0, 0))
    d = ImageDraw.Draw(bg); brand = c.get("brand", "Google"); bf = POP(96); bw = d.textlength(brand, font=bf)
    cx = 520 + (W-520)/2; d.text((cx-bw/2, 150), brand, font=bf, fill=BK)
    sub = c.get("ui_hint", "How can I help you?"); sf = POPS(30); d.text((cx-d.textlength(sub, font=sf)/2, 290), sub, font=sf, fill=(130, 126, 120))
    # input box
    q = c.get("question", "Can we afford this?"); qf = POPS(36); qw = d.textlength(q, font=qf)
    bw_ = max(520, qw+150); x0 = cx-bw_/2; y0 = 380
    box = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(box)
    bd.rounded_rectangle([x0, y0, x0+bw_, y0+104], 52, fill=(255, 255, 255), outline=(215, 208, 196), width=3)
    bd.text((x0+48, y0+28), q, font=qf, fill=BK)
    bd.ellipse([x0+bw_-86, y0+18, x0+bw_-18, y0+86], fill=OR); ax = x0+bw_-52
    bd.line([(ax, y0+70), (ax, y0+34)], fill=(255, 255, 255), width=7); bd.polygon([(ax-16, y0+48), (ax+16, y0+48), (ax, y0+30)], fill=(255, 255, 255))
    shadowed(bg, box, off=(0, 10), blur=18, k=0.25)
    place_subject(bg, c, c.get("subj_h", 620), c.get("subj_x", 300), c.get("subj_dy", 0))
    if c.get("words"): caps_stack(bg, c["words"], 600, 680, 620, fg=OR, start=80)
    return finish(bg, c, OR, "bl")
def L_grid(c, tint):
    bg = Image.new("RGBA", (W, H), tuple(tint)+(255,))
    names = c.get("tiles", ["Search", "YouTube", "Cloud", "Gemini", "Android", "Waymo", "Chrome", "Maps", "Pixel"])
    cols = 3; tw, th, gap = 230, 150, 14; gx = W - cols*(tw+gap) - 20; gy = 30
    d = ImageDraw.Draw(bg)
    for i, nm in enumerate(names[:12]):
        r, k = divmod(i, cols); x, y = gx+k*(tw+gap), gy+r*(th+gap)
        if y+th > H-10: break
        fill = [CR, (255, 255, 255), BK, OR][(i*7) % 4]; tc = BK if fill in (CR, (255, 255, 255)) else (255, 255, 255)
        d.rectangle([x, y, x+tw, y+th], fill=fill); sz = fit(POP, [nm], tw-30, 40, 18); f = POP(sz)
        d.text((x+tw/2-d.textlength(nm, font=f)/2, y+th/2-sz*0.62), nm, font=f, fill=tc)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
    for xx in range(0, 620): sd.line([(xx, 0), (xx, H)], fill=tuple(tint)+(int(255*max(0, 1-xx/620)**0.8),))
    bg.alpha_composite(shade)
    place_subject(bg, c, c.get("subj_h", 620), c.get("subj_x", 420), c.get("subj_dy", 0))
    caps_stack(bg, c["words"], 40, H-50, 470, slab_i=c.get("slab_i", 1), slab_col=OR, kicker=c.get("kicker"), kcol=BK)
    return finish(bg, c, (255, 255, 255), "br")
def L_ring(c, tint):
    bg = Image.new("RGBA", (W, H), (16, 16, 18, 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse([560, 40, 1240, 720], fill=tuple(tint)+(255,))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(bg); cx, cy = 900, 360
    for r, w in [(330, 4), (250, 3), (170, 2)]: d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(235, 235, 235), width=w)
    for a in (40, 160, 290): d.ellipse([cx+330*math.cos(math.radians(a))-9, cy+330*math.sin(math.radians(a))-9, cx+330*math.cos(math.radians(a))+9, cy+330*math.sin(math.radians(a))+9], fill=OR)
    brand = c.get("brand", "GOOGLE").upper(); sz = fit(POP, [brand], 460, 90); f = POP(sz); bw = d.textlength(brand, font=f)
    d.rectangle([cx-bw/2-30, cy-sz*0.75, cx+bw/2+30, cy+sz*0.75], fill=(255, 255, 255)); d.text((cx-bw/2, cy-sz*0.7), brand, font=f, fill=BK)
    place_subject(bg, c, c.get("subj_h", 600), c.get("subj_x", 330), c.get("subj_dy", 0))
    caps_stack(bg, c["words"], 40, H-50, 520, slab_i=c.get("slab_i", len(c["words"])-1), slab_col=OR, kicker=c.get("kicker"), kcol=OR)
    return finish(bg, c, OR, "br")

def main(c):
    lay, tint = pick(c); out = c["out"]; os.makedirs(os.path.dirname(out), exist_ok=True)
    im = {"collage": L_collage, "stack": L_stack, "slab": L_slab, "ui": L_ui, "grid": L_grid, "ring": L_ring}[lay](c, tint)
    if im is not None: im.convert("RGB").save(out, quality=92)
    if c.get("log", True):
        log = load_log(); log.append({"date": str(datetime.date.today()), "title": c.get("title", ""), "layout": lay, "tint": tint, "out": out})
        json.dump(log, open(LOG, "w"), indent=1)
    print("thumb", lay, tint, out)
if __name__ == "__main__": main(json.loads(sys.argv[1]))
