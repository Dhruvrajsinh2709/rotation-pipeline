"""Rotation long-form v9 overlays (Study 5: CNBC + WSJ vs ours, user approved all 12 fixes 2026-10-30).
All drawn at 1920x1080 RGBA (make_long lanczos-scales to the output size). Black-and-white look, no yellow, no top-left logo.
- dateline(): WSJ-style place + date tag (open_place, inset footage)
- title_card_png(): series title card "ROTATION | episode title" over footage (replaces the logo-only sting)
- quote_png(): speaker card for real, sourced quotes read by a second AI voice (voice2)
- lower_third_png(): name / role tabs for public-domain actuality audio or video
- inset_decor_png(): thin frame + dateline + credit around footage shown in a framed inset (low-res / archival / PD)
- fallback_plate(): designed plate used instead of a random clip when nothing in the library matches the scene
- credits_png(): tall credits column (rolled by ffmpeg in the closer) ; endcard_frames(): v9 end card (RGBA, over the opening place)"""
import os, math
from PIL import Image, ImageDraw, ImageFilter
import gfx

W, H = 1920, 1080
WH = (244, 244, 244); GREY = (150, 150, 154); DARK = (10, 10, 11)
MF = gfx.MF

def ease(p): p = max(0.0, min(1.0, p)); return 1-(1-p)**4

def _shadow_text(im, xy, t, f, fill=WH, r=4, a=255):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0]+2, xy[1]+3), t, font=f, fill=(0, 0, 0, int(200*a/255)))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(r))); ImageDraw.Draw(im).text(xy, t, font=f, fill=fill[:3]+(a,))

def _fit(d, text, wg, size, maxw, minsize=40):
    f = MF(size, wg)
    while d.textlength(text, font=f) > maxw and size > minsize: size -= 4; f = MF(size, wg)
    return f

def dateline(im, place, date=None, x=72, y=64, a=1.0, big=40):
    """Place (bold caps) over date (grey), thin white bar on the left. a = 0..1 fade/slide."""
    if not place: return
    d = ImageDraw.Draw(im); al = int(255*a); dx = int(-18*(1-a))
    pf = MF(big, 800); df = MF(int(big*0.72), 500); P = place.upper()
    hh = big+8 + (int(big*0.72)+10 if date else 0)
    sc = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sc).rounded_rectangle([x-24+dx, y-16, x+max(d.textlength(P, font=pf), d.textlength(date or "", font=df))+40+dx, y+hh+12], 14, fill=(0, 0, 0, int(110*a)))
    im.alpha_composite(sc.filter(ImageFilter.GaussianBlur(10)))
    d.rectangle([x+dx, y+2, x+4+dx, y+hh-4], fill=(255, 255, 255, al))
    _shadow_text(im, (x+20+dx, y-4), P, pf, a=al)
    if date: _shadow_text(im, (x+20+dx, y+big+8), date, df, fill=(205, 205, 208), a=al)

def title_card_png(path, series, title, prog, out_a=1.0, logo=None, sub=None):
    """Series title card over footage: darkened frame, centred logo mark + letter-spaced series name, thin rule, big
    episode title (Montserrat 900, <= 2 lines). prog = seconds since start; out_a fades everything at the end."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, int(150*min(1, prog/0.3)*out_a))); d = ImageDraw.Draw(im)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for k in range(40): gd.rectangle([0, H/2-260+k*13, W, H/2-260+(k+1)*13], fill=(0, 0, 0, int(70*math.sin(math.pi*k/40)*out_a)))
    im.alpha_composite(g)
    a1 = ease(prog/0.5)*out_a; a2 = ease((prog-0.25)/0.6)*out_a; a3 = ease((prog-0.45)/0.6)*out_a
    sf = MF(40, 800); S = "  ".join(series.upper()) if len(series) <= 12 else series.upper()
    sw = d.textlength(S, font=sf); lw = 0
    if logo is not None: lw = logo.width+20
    x0 = (W-(sw+lw))/2; y0 = 330-int(14*(1-a1))
    if logo is not None:
        lg = logo.copy(); lg.putalpha(lg.getchannel("A").point(lambda v: int(v*a1))); im.alpha_composite(lg, (int(x0), int(y0+2)))
    _shadow_text(im, (x0+lw, y0), S, sf, a=int(255*a1))
    rw = int(260*a2); d.rectangle([(W-rw)//2, 410, (W+rw)//2, 412], fill=(255, 255, 255, int(220*a2)))
    tf = MF(96, 900); L = gfx.wrap(d, title, tf, 1560)
    while len(L) > 2 and tf.size > 60: tf = MF(tf.size-6, 900); L = gfx.wrap(d, title, tf, 1560)
    if len(L) == 2:   # balance the two lines (no single-word orphan)
        ws = title.split(); best = None
        for k in range(1, len(ws)):
            a_, b_ = " ".join(ws[:k]), " ".join(ws[k:]); m_ = max(d.textlength(a_, font=tf), d.textlength(b_, font=tf))
            if m_ <= 1560 and (best is None or m_ < best[0]): best = (m_, [a_, b_])
        if best: L = best[1]
    y = 460+int(24*(1-a3))
    for l in L[:3]: _shadow_text(im, ((W-d.textlength(l, font=tf))/2, y), l, tf, a=int(255*a3), r=6); y += int(tf.size*1.12)
    if sub: sbf = MF(34, 500); _shadow_text(im, ((W-d.textlength(sub, font=sbf))/2, y+18), sub, sbf, fill=(205, 205, 208), a=int(255*a3))
    im.save(path)

def quote_png(path, q, prog, voice_note=True):
    """Speaker card for a REAL sourced quote read by a second AI voice: dimmed footage, left gradient, big quote,
    rule, speaker name / role, source bottom-left, small 'Quote read by AI voice' note."""
    a = ease(prog/0.45)
    im = Image.new("RGBA", (W, H), (0, 0, 0, int(105*a))); g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for x in range(0, W, 16): gd.rectangle([x, 0, x+16, H], fill=(0, 0, 0, int(120*a*max(0, 1-x/1500))))
    im.alpha_composite(g); d = ImageDraw.Draw(im)
    qf = MF(60, 700); L = gfx.wrap(d, q["text"], qf, 1250)
    while len(L) > 5 and qf.size > 40: qf = MF(qf.size-4, 700); L = gfx.wrap(d, q["text"], qf, 1250)
    lh = int(qf.size*1.3); blk = len(L)*lh + 190; y = max(150, (H-blk)/2-20); x = 210; dy = int(16*(1-a)); al = int(255*a)
    d.text((x-16, y-150+dy), "\u201C", font=MF(210, 900), fill=(255, 255, 255, int(al*0.9)))
    for l in L: _shadow_text(im, (x, y+dy), l, qf, a=al); y += lh
    d.rectangle([x, y+28, x+80, y+31], fill=(255, 255, 255, al))
    _shadow_text(im, (x, y+52), q.get("who", ""), MF(44, 800), a=al)
    if q.get("role"): _shadow_text(im, (x, y+108), q["role"], MF(32, 500), fill=(205, 205, 208), a=al)
    if voice_note:
        nf = MF(22, 600); t = "QUOTE READ BY AI VOICE"; d.text((W-90-d.textlength(t, font=nf), H-66), t, font=nf, fill=(170, 170, 174, int(al*0.9)))
    if q.get("source"): _shadow_text(im, (60, H-70), "Source: " + q["source"], MF(26, 500), fill=(225, 225, 228), r=3, a=al)
    im.save(path)

def lower_third_png(path, who, role, credit=None, prog=1.0, source=None):
    """WSJ-style name/role tabs bottom-left: white tab with dark name, dark tab with white role; credit line under it."""
    a = ease(prog/0.4); al = int(255*a); dx = int(-30*(1-a))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    nf = MF(42, 800); rf = MF(30, 500); x = 96+dx; y = 818
    nw = d.textlength(who, font=nf); d.rectangle([x, y, x+nw+52, y+70], fill=(246, 246, 246, al)); d.text((x+26, y+10), who, font=nf, fill=(12, 12, 14, al))
    if role:
        rw = d.textlength(role, font=rf); d.rectangle([x, y+70, x+rw+52, y+122], fill=(14, 14, 16, int(al*0.92))); d.text((x+26, y+78), role, font=rf, fill=(232, 232, 234, al))
    if credit: cf = MF(22, 600); _shadow_text(im, (x+2, y+136), credit.upper(), cf, fill=(190, 190, 194), r=3, a=al)
    if source: _shadow_text(im, (60, H-70), "Source: " + source, MF(26, 500), fill=(225, 225, 228), r=3, a=al)
    im.save(path)

INSET = dict(w=0.70, dy=-10)    # inset footage = 70 % of the frame width, centred, 10 px above centre (at 1920 scale)
def inset_geom(OW=W, OH=H):
    iw = int(OW*INSET["w"])//2*2; ih = int(iw*9/16)//2*2; x = (OW-iw)//2; y = (OH-ih)//2 + int(INSET["dy"]*OH/H)
    return x, y, iw, ih

def inset_decor_png(path, place=None, date=None, credit=None, prog=1.0):
    """Frame + provenance around the inset: thin white outline, dateline above the top-left corner, credit under the right corner."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x, y, iw, ih = inset_geom()
    a = ease(prog/0.4); al = int(255*a)
    d.rectangle([x-3, y-3, x+iw+2, y+ih+2], outline=(255, 255, 255, int(al*0.85)), width=3)
    if place:
        pf = MF(34, 800); df = MF(26, 500); d.text((x, y-92), place.upper(), font=pf, fill=(246, 246, 246, al))
        if date: d.text((x, y-48), date, font=df, fill=(185, 185, 190, al))
    if credit:
        cf = MF(22, 600); t = credit.upper(); d.text((x+iw-d.textlength(t, font=cf), y+ih+16), t, font=cf, fill=(170, 170, 174, al))
    im.save(path)

def fallback_plate(path_png, text, sub=None, place=None, texture=None):
    """Designed plate (no footage matched): textured near-black panel, big white phrase, thin rule, optional subline/dateline."""
    im = Image.new("RGBA", (W, H), (9, 9, 10, 255))
    if texture and os.path.exists(texture): im.alpha_composite(Image.open(texture).convert("RGBA").resize((W, H)))
    d = ImageDraw.Draw(im); tf = MF(118, 900); L = gfx.wrap(d, text, tf, 1500) if text else []
    if not L: im.convert("RGB").save(path_png); return
    while len(L) > 2 and tf.size > 64: tf = MF(tf.size-8, 900); L = gfx.wrap(d, text, tf, 1500)
    y = H/2 - len(L)*tf.size*0.62 - (30 if sub else 0)
    for l in L: d.text(((W-d.textlength(l, font=tf))/2, y), l, font=tf, fill=WH); y += tf.size*1.12
    d.rectangle([W/2-70, y+26, W/2+70, y+29], fill=(255, 255, 255))
    if sub: sf = MF(40, 500); d.text(((W-d.textlength(sub, font=sf))/2, y+58), sub, font=sf, fill=(170, 170, 174))
    if place: dateline(im, place, None, 72, 64)
    im.convert("RGB").save(path_png)

def credits_png(path, sections, width=620):
    """Tall credits column: [(HEADING, [lines])] -> RGBA PNG (white headings, grey lines). Returns its height."""
    hf = MF(26, 800); lf = MF(25, 500); tmp = ImageDraw.Draw(Image.new("RGB", (8, 8))); rows = []
    for hd, lines in sections:
        rows.append(("h", hd.upper()))
        for l in lines:
            for w_ in gfx.wrap(tmp, l, lf, width-20): rows.append(("l", w_))
        rows.append(("g", ""))
    hgt = sum(44 if k == "h" else 36 if k == "l" else 30 for k, _ in rows) + 20
    im = Image.new("RGBA", (width, hgt), (0, 0, 0, 0)); d = ImageDraw.Draw(im); y = 0
    for k, t in rows:
        if k == "h": d.text((0, y), t, font=hf, fill=(246, 246, 246, 255)); y += 44
        elif k == "l": d.text((0, y), t, font=lf, fill=(178, 178, 182, 255)); y += 36
        else: y += 30
    im.save(path); return hgt

def side_gradient_png(path, x0=1100):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for x in range(x0, W, 4): u = min(1, (x-x0)/620); d.rectangle([x, 0, x+4, H], fill=(0, 0, 0, int(175*(u*u*(3-2*u)))))
    im.save(path); return path

def endcard_frames(c, D, d_out, logo=None, fps=24, credits_line=None, comments="Tell us what you think in the comments"):
    """v9 end card, RGBA frames to lay over the dimmed opening-place footage (endcard.bg_clip). Same two YouTube end-screen
    slots as v8 (video x 250-1050 / y 400-850, subscribe circle centre 1470,625 r 150) + a comments line + a compact credits band."""
    os.makedirs(d_out, exist_ok=True); n = int(D*fps)+1; brand = c.get("brand", "ROTATION")
    f = MF(64, 800); lf = MF(26, 700); cmf = MF(30, 600); bf = MF(20, 500); bh = MF(20, 800)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(base)
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bdd = ImageDraw.Draw(band)
    if credits_line:   # 3 compact columns: [(heading, text)]
        cw = (W-200)/len(credits_line)
        for k, (hd, txt) in enumerate(credits_line):
            x = 100+k*cw; bdd.text((x, 912), hd.upper(), font=bh, fill=(220, 220, 224, 255)); yy = 942
            for l in gfx.wrap(bdd, txt, bf, cw-40)[:4]: bdd.text((x, yy), l, font=bf, fill=(160, 160, 164, 255)); yy += 27
    last = None
    for k in range(n):
        t = k/fps; a0 = ease(t/0.6); a1 = ease((t-0.1)/0.7); a2 = ease((t-0.45)/0.7); a3 = ease((t-0.8)/0.7); a4 = ease((t-1.2)/0.8)
        key = tuple(round(x, 3) for x in (a0, a1, a2, a3, a4))
        p = f"{d_out}/{k:04d}.png"
        if key == last: os.link(f"{d_out}/{k-1:04d}.png", p); continue
        last = key
        im = Image.new("RGBA", (W, H), (4, 4, 5, int(196*a0))); d = ImageDraw.Draw(im)
        tw = d.textlength(brand, font=f); lw = logo.width if logo is not None else 0; gap = 22; x0 = (W-(lw+gap+tw))/2; y0 = 128+int(18*(1-a1))
        if logo is not None:
            lg = logo.copy(); lg.putalpha(lg.getchannel("A").point(lambda v: int(v*a1))); im.alpha_composite(lg, (int(x0), int(y0+6)))
        d.text((x0+lw+gap, y0), brand, font=f, fill=(255, 255, 255, int(255*a1)))
        rw = int(560*a2); d.rectangle([(W-rw)//2, 250, (W+rw)//2, 251], fill=(255, 255, 255, int(200*a2)))
        if comments: ct = comments; d.text(((W-d.textlength(ct, font=cmf))/2, 282), ct, font=cmf, fill=(225, 225, 228, int(255*a2)))
        al = int(255*a3); off = int(26*(1-a3)); vx0, vy0, vx1, vy1 = 250, 400+off, 1050, 850+off
        d.rounded_rectangle([vx0, vy0, vx1, vy1], 10, outline=(255, 255, 255, int(al*0.85)), width=2, fill=(16, 16, 18, int(al*0.9)))
        d.text((vx0, vy0-40), c.get("line", "Watch next").upper(), font=lf, fill=(170, 170, 174, al))
        if c.get("thumb") and os.path.exists(c["thumb"]):   # fix19: fill the watch-next slot with the real thumbnail + title under it
            if "_th" not in c: c["_th"] = Image.open(c["thumb"]).convert("RGBA").resize((vx1-vx0-8, vy1-vy0-8), Image.LANCZOS)
            th_ = c["_th"].copy(); th_.putalpha(int(al)); im.alpha_composite(th_, (vx0+4, vy0+4))
            if c.get("video"):
                tl_ = gfx.wrap(d, c["video"], MF(28, 700), vx1-vx0)[:1]
                if tl_: d.text((vx0, vy1+14), tl_[0], font=MF(28, 700), fill=(235, 235, 238, al))
        elif c.get("video"):
            L = gfx.wrap(d, c["video"], MF(40, 800), 680)[:3]; yy = (vy0+vy1)/2-len(L)*26
            for l_ in L: d.text(((vx0+vx1)/2-d.textlength(l_, font=MF(40, 800))/2, yy), l_, font=MF(40, 800), fill=(235, 235, 238, al)); yy += 52
        cx, cy, rr = 1470, 625+off, 150
        d.ellipse([cx-rr, cy-rr, cx+rr, cy+rr], outline=(255, 255, 255, int(al*0.85)), width=2, fill=(16, 16, 18, int(al*0.9)))
        if logo is not None:
            sl = logo.resize((int(logo.width*1.5), int(logo.height*1.5)), Image.LANCZOS); sl.putalpha(sl.getchannel("A").point(lambda v: int(v*a3))); im.alpha_composite(sl, (int(cx-sl.width/2), int(cy-sl.height/2)))
        d.text((cx-d.textlength("SUBSCRIBE", font=lf)/2, cy+rr+22), "SUBSCRIBE", font=lf, fill=(170, 170, 174, al))
        if credits_line and a4 > 0:
            b2 = band.copy(); b2.putalpha(b2.getchannel("A").point(lambda v: int(v*a4))); im.alpha_composite(b2)
        im.save(p)
    return [0.0, 0.45, 0.8, 1.2]

# ---------------- Shorts v9 (user 2026-10-30 08:56 IST: "yes same extra voice and background in the short too") ----------------
# Shared voice pool for quote voices (make_long + make_story): each quoted speaker gets their own voice, never the narrator's.
NARRATOR = "en-US-AndrewMultilingualNeural"
VOICE2 = ["en-GB-SoniaNeural", "en-GB-RyanNeural", "en-US-EmmaNeural", "en-AU-NatashaNeural"]

class QuoteVoices:
    """who -> distinct edge-tts voice (first = spec voice2 if given). Same speaker always gets the same voice."""
    def __init__(self, first=None): self.pool = list(dict.fromkeys(([first] if first else []) + VOICE2)); self.m = {}
    def __call__(self, who, want=None):
        if want: return want
        if who not in self.m: self.m[who] = self.pool[len(self.m) % len(self.pool)]
        return self.m[who]

SW, SH = 1080, 1920   # Shorts canvas
BAND_Y0, BAND_Y1 = 626, 1294   # gfx.blur_fill_vf sharp band (1188 px wide scaled 16:9, cropped to 1080) on the 1080x1920 frame

def quote_png_v(path, q, prog, voice_note=True):
    """Shorts speaker card for a REAL sourced quote read by a second AI voice (vertical, B/W). The quote words run in the
    captions (y 1360), so the card carries the speaker: big quote mark, name, role, rule, source, 'QUOTE READ BY AI VOICE'.
    Dims the footage behind it; block sits between y ~520 and ~1250 so it clears captions and the Shorts side rail."""
    a = ease(prog/0.45); al = int(255*a); dy = int(22*(1-a))
    im = Image.new("RGBA", (SW, SH), (0, 0, 0, int(95*a))); g = Image.new("RGBA", (SW, SH), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for y in range(380, 1420, 10):
        u = 1-abs((y-900)/520); gd.rectangle([0, y, SW, y+10], fill=(0, 0, 0, int(105*a*max(0, u)**0.7)))
    im.alpha_composite(g); d = ImageDraw.Draw(im); x = 96
    d.text((x-12, 470+dy), "\u201C", font=MF(250, 900), fill=(255, 255, 255, int(al*0.92)))
    who = q.get("who", ""); nf = _fit(d, who, 800, 76, SW-2*x-20, 48)
    _shadow_text(im, (x, 760+dy), who, nf, a=al, r=5)
    y = 760+dy+int(nf.size*1.22)
    if q.get("role"):
        rf = MF(40, 500)
        for l in gfx.wrap(d, q["role"], rf, SW-2*x-40)[:2]: _shadow_text(im, (x, y), l, rf, fill=(212, 212, 215), a=al); y += 52
    d.rectangle([x, y+26, x+110, y+31], fill=(255, 255, 255, al)); y += 64
    if q.get("source"):
        sf = MF(34, 600)
        for l in gfx.wrap(d, "Source: " + q["source"], sf, SW-2*x-40)[:2]: _shadow_text(im, (x, y), l, sf, fill=(230, 230, 233), a=al, r=3); y += 46
    if voice_note:
        nf2 = MF(26, 700); t = "QUOTE READ BY AI VOICE"
        d.rounded_rectangle([x-2, y+22, x+d.textlength(t, font=nf2)+30, y+70], 8, outline=(190, 190, 194, int(al*0.9)), width=2)
        d.text((x+14, y+32), t, font=nf2, fill=(200, 200, 204, int(al*0.95)))
    im.save(path)

def lower_third_png_v(path, who, role, credit=None, prog=1.0, source=None):
    """Shorts lower third for public-domain actuality shown in the blur-fill band (y 626-1294): white name tab + dark role
    tab inside the band's bottom-left (ends above the y 1360 captions); provenance (source + credit) sits above the band."""
    a = ease(prog/0.4); al = int(255*a); dx = int(-34*(1-a))
    im = Image.new("RGBA", (SW, SH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    nf = _fit(d, who, 800, 50, SW-200, 36); rf = _fit(d, role or "", 500, 34, SW-200, 26); x = 60+dx
    y = BAND_Y1-24-(78+(58 if role else 0))
    nw = d.textlength(who, font=nf); d.rectangle([x, y, x+nw+56, y+78], fill=(246, 246, 246, al)); d.text((x+28, y+12), who, font=nf, fill=(12, 12, 14, al))
    if role:
        rw = d.textlength(role, font=rf); d.rectangle([x, y+78, x+rw+56, y+136], fill=(14, 14, 16, int(al*0.92))); d.text((x+28, y+88), role, font=rf, fill=(232, 232, 234, al))
    ty = BAND_Y0-24
    if credit:
        cf = MF(24, 700); _shadow_text(im, (60, ty-30), credit.upper(), cf, fill=(196, 196, 200), r=3, a=al); ty -= 40
    if source:
        sf = _fit(d, source, 700, 36, SW-120, 26); _shadow_text(im, (60, ty-44), source, sf, a=al, r=4)
    im.save(path)
