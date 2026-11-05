"""TLDR-style opener devices + running captions for make_long.py (added 2026-10-29)."""
import os
from PIL import Image, ImageDraw, ImageFilter
W, H = 1920, 1080; YEL = (240, 180, 0); WH = (255, 255, 255); BLK = (8, 8, 10)
ACC_L = YEL; QBG = (10, 12, 18); MUTE = (170, 172, 180); V8 = False
FPS = 30   # v9 long-form: 24
def set_theme(name="mono", accent=None):
    """v8 monochrome long-form look (user 2026-10-29): white accents, grey secondary, black cards."""
    global YEL, ACC_L, QBG, MUTE, V8
    if name == "mono": YEL = (255, 255, 255); ACC_L = (14, 14, 16); QBG = (8, 8, 9); MUTE = (120, 120, 124); V8 = True
    if name == "mono" and accent: YEL = tuple(accent)

def _e(p): p = max(0, min(1, p)); return 1-(1-p)**3

def sting_frames(D, d_out, MF, logo_mark, brand="ROTATION"):
    """~3 s brand hit: logo mark + wordmark centred on black, eases in, holds, quick fade out."""
    os.makedirs(d_out, exist_ok=True); n = int(D*FPS)+1; mk = logo_mark(150); f = MF(150, 800)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10))); tw = tmp.textlength(brand, font=f); gap = 40
    full = Image.new("RGBA", (int(mk.width+gap+tw+40), 220), (0, 0, 0, 0))
    full.alpha_composite(mk, (0, 35)); ImageDraw.Draw(full).text((mk.width+gap, 18), brand, font=f, fill=WH)
    for k in range(n):
        t = k/FPS; a = _e(t/0.45) * (1 if t < D-0.3 else max(0, (D-t)/0.3)); sc = 0.9+0.1*_e(t/0.6)
        im = Image.new("RGB", (W, H), BLK)
        L = full.resize((int(full.width*sc), int(full.height*sc)), Image.LANCZOS)
        L.putalpha(L.getchannel("A").point(lambda v: int(v*a)))
        im.paste(L, ((W-L.width)//2, (H-L.height)//2), L)
        bw = int(420*_e((t-0.25)/0.5)*a)
        if bw > 2: ImageDraw.Draw(im).rectangle([(W-bw)//2, H//2+150, (W+bw)//2, H//2+158], fill=YEL)
        im.save(f"{d_out}/{k:04d}.png")

def question_frames(D, d_out, MF, wrap, text):
    """Dark title card posing the video's question, centred, words settle in."""
    os.makedirs(d_out, exist_ok=True); n = int(D*FPS)+1; f = MF(92, 800)
    d0 = ImageDraw.Draw(Image.new("RGB", (10, 10))); L = wrap(d0, text, f, 1400)
    for k in range(n):
        t = k/FPS; a = _e(t/0.5); dy = int(30*(1-a))
        im = Image.new("RGB", (W, H), QBG); d = ImageDraw.Draw(im)
        y = H/2 - len(L)*58 + dy; col = tuple(int(c*a + QBG[0]*(1-a)) for c in WH)
        for l in L: d.text(((W-d.textlength(l, font=f))/2, y), l, font=f, fill=col); y += 116
        bw = int(140*_e((t-0.3)/0.4)); 
        if bw > 2: d.rectangle([(W-bw)//2, y+24, (W+bw)//2, y+32], fill=YEL)
        im.save(f"{d_out}/{k:04d}.png")

def subscribe_frames(D, d_out, MF, line="New deep dives every weekend"):
    """Full-frame black SUBSCRIBE card with an outline box and a wipe line."""
    os.makedirs(d_out, exist_ok=True); n = int(D*FPS)+1; f = MF(110, 800); lf = MF(40, 500)
    for k in range(n):
        t = k/FPS; a = _e(t/0.4); im = Image.new("RGB", (W, H), BLK); d = ImageDraw.Draw(im)
        tw = d.textlength("SUBSCRIBE", font=f); sc = 0.92+0.08*a
        bx0, by0, bx1, by1 = W/2-(tw/2+70)*sc, H/2-110*sc, W/2+(tw/2+70)*sc, H/2+90*sc
        col = tuple(int(255*a) for _ in range(3))
        d.rounded_rectangle([bx0, by0, bx1, by1], int(40*sc), outline=col, width=8)
        d.text(((W-tw)/2, H/2-78), "SUBSCRIBE", font=f, fill=col)
        lw = d.textlength(line, font=lf); d.text(((W-lw)/2, H/2+140), line, font=lf, fill=tuple(int(200*_e((t-0.3)/0.4)) for _ in range(3)))
        ww = int(W*0.42*_e((t-0.15)/0.6)); d.rectangle([60, H-120, 60+ww, H-112], fill=YEL)
        im.save(f"{d_out}/{k:04d}.png")

def stack_card(im, c, MF, wrap, shown):
    """Several real headlines with outlet tags, fanned over dimmed footage. shown = how many are visible."""
    d = ImageDraw.Draw(im); im.alpha_composite(Image.new("RGBA", im.size, (0, 0, 0, 120)))
    xs = [150, 720, 260, 820]; cw = 900; hf = MF(44, 800)
    Ls = [wrap(d, t, hf, cw-90)[:3] for _, t in c["items"]]; hs = [100+len(L)*56+30 for L in Ls]
    n = min(len(hs), 4); tot = sum(hs[:n]); gap = 24 if n < 2 else max(-30, min(24, (1000-140-tot)/(n-1)))  # stack downward; overlap only the padding
    ys = [140]
    for k in range(1, n): ys.append(ys[-1]+hs[k-1]+gap)
    for i, (outlet, text) in enumerate(c["items"][:shown][:4]):
        x0, y0 = xs[i], int(ys[i]); d = ImageDraw.Draw(im)
        L = Ls[i]; chh = hs[i]
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([x0+8, y0+12, x0+cw+8, y0+chh+12], 16, fill=(0, 0, 0, 170))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12))); d = ImageDraw.Draw(im)
        d.rounded_rectangle([x0, y0, x0+cw, y0+chh], 16, fill=(250, 250, 248)); d.rectangle([x0, y0+24, x0+10, y0+chh-24], fill=ACC_L)
        d.text((x0+45, y0+30), outlet.upper(), font=MF(28, 800), fill=(110, 110, 120)); y = y0+82
        for l in L: d.text((x0+45, y), l, font=hf, fill=(15, 15, 20)); y += 56

def doc_card(im, c, MF, wrap):
    """Primary-document page: faded text with one highlighted sentence (filings, letters, reports)."""
    d = ImageDraw.Draw(im); im.alpha_composite(Image.new("RGBA", im.size, (6, 8, 14, 225))); d = ImageDraw.Draw(im)
    x0, y0, pw, ph = 330, 90, 1260, 760
    d.rounded_rectangle([x0, y0, x0+pw, y0+ph], 10, fill=(244, 242, 236))
    d.text((x0+70, y0+55), c.get("doc", "").upper(), font=MF(26, 700), fill=(120, 120, 128))
    if c.get("heading"): d.text((x0+70, y0+100), c["heading"], font=MF(44, 800), fill=(150, 150, 155))
    bf = MF(36, 500); y = y0+190; maxw = pw-140
    for part, hi in ((c.get("before", ""), False), (c["highlight"], True), (c.get("after", ""), False)):
        if not part: continue
        for l in wrap(d, part, bf, maxw):
            if y > y0+ph-70: break
            if hi:
                tw = d.textlength(l, font=bf); d.rectangle([x0+62, y-6, x0+78+tw, y+46], fill=(18, 18, 20) if V8 else (255, 214, 90))
                d.text((x0+70, y), l, font=MF(36, 700), fill=(250, 250, 250) if V8 else (10, 10, 12))
            else: d.text((x0+70, y), l, font=bf, fill=(185, 185, 188))
            y += 58

def pills_card(im, c, MF, shown):
    """Company/brand pills on black (leaderboard motif). items: [[name, '#hex'], ...]."""
    im.alpha_composite(Image.new("RGBA", im.size, (8, 8, 10, 255))); d = ImageDraw.Draw(im)
    if c.get("title"): d.text((160, 140), c["title"], font=MF(60, 800), fill=WH)
    f = MF(54, 800); items = c["items"]; y = 270; step = min(150, 640/max(1, len(items)))
    for i, it in enumerate(items[:shown]):
        name, col = it[0], it[1]
        rgb = tuple(int(col.lstrip("#")[j:j+2], 16) for j in (0, 2, 4)); tw = d.textlength(name, font=f)
        if V8: g_ = 240 if i == 0 else max(40, 200-i*40); rgb = (g_, g_, g_)   # mono: shades of grey, leader brightest
        d.rounded_rectangle([160, y, 160+tw+110, y+step-30], (step-30)//2, fill=rgb)
        lum = 0.3*rgb[0]+0.59*rgb[1]+0.11*rgb[2]; d.text((215, y+(step-30-60)/2), name, font=f, fill=(15, 15, 15) if lum > 170 else WH)
        if len(c["items"][i]) > 2: d.text((160+tw+150, y+(step-30-50)/2), c["items"][i][2], font=MF(46, 700), fill=YEL)
        y += step

def chunks(words, maxw=6):
    """words: [(start_s, end_s, text)] -> caption phrases [(start, end, text)], break at punctuation or maxw words."""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= maxw or w[2][-1:] in ".,?!;:":
            out.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur))); cur = []
    if cur: out.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur)))
    return out

def caption_png(path, text, MF, shadow_text):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); f = MF(54, 700)
    if text:
        tw = ImageDraw.Draw(im).textlength(text, font=f)
        while tw > 1600: f = MF(f.size-4, 700); tw = ImageDraw.Draw(im).textlength(text, font=f)
        shadow_text(im, ((W-tw)/2, H-215), text, f, r=6)
    im.save(path)

def agenda_overlay(path, chapters, cur, prog, MF, shadow_text, logo_bug=None):
    """Study 2 chapter list (CNBC): dark scrim over moving footage, 3-4 chapters, current one in #F0B400 with a bar.
    cur: 0-based index of the current chapter. prog: seconds since the card started (items stagger in)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); a0 = _e(prog/0.25)
    im.alpha_composite(Image.new("RGBA", (W, H), ((4, 4, 5) if V8 else (4, 6, 12))+(int(185*a0),))); d = ImageDraw.Draw(im)
    n = len(chapters); step = 118; y0 = int(H/2 - n*step/2 + 30)
    hf = MF(34, 800); d.text((200, y0-95), "IN THIS VIDEO", font=hf, fill=YEL+(int(255*a0),))
    for i, name in enumerate(chapters):
        p = _e((prog-0.08-i*0.08)/0.25)
        if p <= 0: continue
        y = y0+i*step; x = 200+int(30*(1-p)); on = i == cur
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
        if on: ld.rectangle([x-40, y+6, x-28, y+82], fill=YEL)
        ld.text((x, y+18), f"{i+1:02d}", font=MF(40, 700), fill=YEL if on else MUTE)
        if on: shadow_text(L, (x+100, y), name, MF(70, 800), fill=YEL, r=4)
        else: ld.text((x+100, y+4), name, font=MF(64, 700), fill=(225, 226, 230))
        L.putalpha(L.getchannel("A").point(lambda v: int(v*p*(1.0 if on else 0.62)))); im.alpha_composite(L)
    if logo_bug: logo_bug(im)
    im.save(path)
