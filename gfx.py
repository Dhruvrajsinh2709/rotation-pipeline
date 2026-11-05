"""Shared Rotation graphics (CNBC/Bloomberg-study devices) for Shorts (1080x1920) and long-form (1920x1080).
Full-screen animated charts: line, bar, dots.   Overlays on B-roll: compare, quote, headline, location tag.
Data-driven: every chart/card is a dict in the video spec. See rotation-video-craft skill."""
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

YEL = (240, 180, 0); WH = (245, 247, 250); BG = (6, 12, 28); GRID = (30, 42, 70); GR = (140, 150, 175)
PAL = [YEL, (110, 190, 255), (255, 120, 170), (255, 150, 60), (90, 210, 140), (200, 200, 210)]
# v8 theme hooks (defaults = the v7 look, still used by Shorts). make_long.py calls set_theme("mono").
FILL = YEL; AREA = (60, 48, 10); AXIS = (90, 100, 130); MUTED = (150, 160, 185); TILT_EDGE = (60, 70, 95); DOWN = (255, 120, 120)
ACC_L = YEL            # accent drawn on light cards (headline/quote cards)
NODE_DARK = False      # flow nodes: False = cream boxes with dark text (v7); True = near-black boxes, white text, active = white box
V8 = False             # v8 animation upgrades (map camera tour, travelling dots, flow particles, timeline playhead)
THEME = "v7"
FPS = 30             # v9: long-form sets gfx.FPS = 24 (film cadence); Shorts keep 30
PICTO_DEFAULT = False  # v9: long-form flow nodes become pictogram circles (icon auto-picked from the label)
AXIS_DEFAULT = False # v9: long-form turns on full axes for line/bar charts
HLC = None           # highlighted-bar colour (None = WH); orange accent sets it
OV = (244, 244, 244)   # text drawn over footage (always light)
HI = (255, 255, 255)   # moving highlights (particles, playhead, rings); light theme -> cobalt
TL_DIM = (210, 214, 224); PIC_ON = ((244, 244, 244), (12, 12, 14)); PIC_OFF = ((22, 22, 24), (238, 238, 240))
BOX = (8, 8, 10); MAPSRC = (225, 228, 235)
BAR = None             # light theme: non-highlighted bars (cobalt) when a bar is highlighted
HL_GREY = False      # v8 Shorts: in mono, non-highlighted bars go mid-grey so the highlighted (white) bar reads
def set_theme(name="mono", accent=None):
    """v8 monochrome look for long-form (user 2026-10-29: 'remove this yellow color use black and white').
    White = primary/accent, greys = secondary series, near-black panels. Brand logo unchanged."""
    global YEL, WH, BG, GRID, GR, PAL, FILL, AREA, AXIS, MUTED, TILT_EDGE, DOWN, ACC_L, NODE_DARK, V8, THEME
    global ORG, CREAM, LAND, LAND_HI, BORDER, SEA, HLC, HI, TL_DIM, PIC_ON, PIC_OFF, BAR, BOX, MAPSRC
    if name == "light":   # user 2026-10-30 "use c": cream panels, brand orange lead + cobalt partner, ink text
        a = tuple(accent or (250, 78, 2)); bl = (31, 79, 216); THEME = "light"; V8 = True
        YEL = a; ORG = a; FILL = a; HLC = a; BAR = bl; HI = bl
        WH = (17, 17, 17); BG = (248, 241, 228); GRID = (226, 216, 198); GR = (110, 103, 92)
        PAL = [a, bl, (150, 140, 125), (90, 84, 76), (190, 180, 165), (60, 60, 60)]
        AREA = (250, 222, 204); AXIS = (160, 150, 135); MUTED = (190, 180, 165); TILT_EDGE = (200, 190, 175); DOWN = bl
        ACC_L = a; NODE_DARK = True; CREAM = (255, 252, 246); LAND = (226, 218, 204); LAND_HI = (214, 205, 189); BORDER = (248, 241, 228); SEA = BG
        BOX = (255, 252, 246); MAPSRC = (90, 84, 76)
        TL_DIM = (150, 140, 125); PIC_ON = (bl, (248, 241, 228)); PIC_OFF = ((232, 224, 210), (17, 17, 17))
        return
    if name != "mono": return
    THEME = "mono"; V8 = True
    YEL = (255, 255, 255); WH = (244, 244, 244); BG = (9, 9, 10); GRID = (40, 40, 42); GR = (150, 150, 152)
    PAL = [(255, 255, 255), (165, 165, 168), (105, 105, 108), (210, 210, 212), (70, 70, 72), (190, 190, 192)]
    FILL = (205, 205, 208); AREA = (30, 30, 32); AXIS = (92, 92, 96); MUTED = (92, 92, 96); TILT_EDGE = (70, 70, 72); DOWN = (120, 120, 124)
    ACC_L = (14, 14, 16); NODE_DARK = True
    ORG = (255, 255, 255); CREAM = (236, 236, 238); LAND = (40, 40, 43); LAND_HI = (50, 50, 53); BORDER = (78, 78, 82); SEA = (8, 8, 9)
    if accent:   # user 2026-10-30: "yeah orange accents there too" -> mono + one brand-orange accent
        YEL = tuple(accent); ORG = tuple(accent); FILL = tuple(accent); HLC = tuple(accent)
        PAL = [tuple(accent)] + PAL[1:]   # first line series in orange, others stay grey
FONT = "/workspace/work/yt/fonts/Montserrat-VF.ttf"
_mf = {}
def MF(sz, wg=700):
    k = (int(sz), wg)
    if k not in _mf:
        f = ImageFont.truetype(FONT, int(sz)); f.set_variation_by_axes([wg]); _mf[k] = f
    return _mf[k]

def shadow(im, xy, t, font, fill=WH, r=5):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0]+3, xy[1]+4), t, font=font, fill=(0, 0, 0, 220))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(r))); ImageDraw.Draw(im).text(xy, t, font=font, fill=fill)

def wrap(d, text, font, maxw):
    L = [""]
    for w in text.split():
        x = (L[-1]+" "+w).strip()
        if d.textlength(x, font=font) > maxw and L[-1]: L.append(w)
        else: L[-1] = x
    return L

def ease(p):
    p = max(0, min(1, p))
    return 1-(1-p)**4 if V8 else 1-(1-p)**3   # v8: quartic ease-out, softer landing

def fmt(v, c):
    dec = c.get("decimals", 0 if abs(v) >= 100 or float(v).is_integer() else 1)
    return f"{c.get('prefix','')}{v:,.{dec}f}{c.get('suffix','')}"

# ---------------- full-screen charts ----------------
def _head(d, c, W, H, v):
    s = 1.0 if not v else 1.0
    if v:
        tf, sf, x, ty, sy = MF(80, 900), MF(42, 500), 80, 230, 345
        title = c["title"].upper()
    else:
        tf, sf, x, ty, sy = MF(64, 800), MF(36, 500), 120, 100, 185
        title = c["title"]
    L = wrap(d, title, tf, W-2*x); y = ty
    for l in L: d.text((x, y), l, font=tf, fill=WH); y += tf.size*1.15
    if c.get("subtitle"): d.text((x, y+8), c["subtitle"], font=sf, fill=GR); y += sf.size*1.4
    return y + 10

def _src(d, c, W, H, v):
    if c.get("source"):
        f = MF(30 if v else 26, 500)
        d.text((80 if v else 60, (1250 if v else H-60)), "Source: " + c["source"], font=f, fill=GR)

def chart_frame(c, W, H, e, rawp, badge_a=None, hl=None):
    v = H > W; im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    top = _head(d, c, W, H, v); t = c["type"]; c = {**c, "_hl": hl}
    if t == "line": _line(d, c, W, H, v, top, e)
    elif t == "bar": _bar(d, c, W, H, v, top, e)
    elif t == "dots": _dots(d, c, W, H, v, top, e)
    if badge_a is None: badge_a = ease((rawp-0.8)/0.2) if rawp > 0.8 else 0
    if c.get("badge") and badge_a > 0:
        a = badge_a; bf = MF(58 if v else 54, 900); tw = d.textlength(c["badge"], font=bf)
        bx, by = (80, 1120) if v else (W-tw-200, 100)
        d.rounded_rectangle([bx, by, bx+tw+56, by+86], 16, fill=tuple(int(BG[i]+(YEL[i]-BG[i])*a) for i in range(3)))
        d.text((bx+28, by+8), c["badge"], font=bf, fill=BG)
        if v and c.get("badge_label"): d.text((bx+tw+90, by+20), c["badge_label"], font=MF(42, 500), fill=WH)
    _src(d, c, W, H, v)
    return im

def _line(d, c, W, H, v, top, e):
    S = c["series"]; X = c["x"]; n = len(X)
    allv = [y for s in S for y in s["values"] if y is not None]
    lo, hi = c.get("min"), c.get("max")
    if lo is None: lo = min(allv); lo = lo - (max(allv)-lo)*0.15
    if hi is None: hi = max(allv) + (max(allv)-min(allv))*0.2
    if len(S) > 1:  # legend
        lx, ly = (80 if v else 120), top; lf = MF(36 if v else 32, 600)
        for k, s in enumerate(S):
            col = tuple(s.get("color") or PAL[k % len(PAL)]); d.rectangle([lx, ly+12, lx+36, ly+24], fill=col)
            d.text((lx+48, ly), s["name"], font=lf, fill=WH); lx += 48 + d.textlength(s["name"], font=lf) + 50
            if lx > W-300: lx = 80 if v else 120; ly += 52
        top = ly + 70
    x0, x1 = (130, W-200) if v else (200, W-260)
    if len(S) > 1: x1 = W - (190 if v else 230)
    if len(S) > 1: x0 += 40
    yt, yb = (top+60, 1020) if v else (top+40, H-190)
    gf = MF(30, 500)
    ax = c.get("axis", AXIS_DEFAULT) and not v   # v9: full axes (left y labels, gridlines, ticks, baseline) - newsroom style
    if ax:
        x0 = max(x0, 150 + max(d.textlength(fmt(t_, {**c, "decimals": c.get("axis_decimals", 1)}), font=gf) for t_ in (lo, hi)) + 40)
        if c.get("y_label"): d.text((120, yt-56), c["y_label"], font=MF(28, 600), fill=GR)
    raw = (hi-lo)/4; mag = 10**math.floor(math.log10(raw)); stp = min([1, 2, 2.5, 5, 10], key=lambda m: abs(m*mag-raw))*mag
    ticks = [math.ceil(lo/stp)*stp + stp*k for k in range(8)]; ticks = [t for t in ticks if t <= hi]
    adec = c.get("axis_decimals", 0 if stp >= 1 else (1 if stp >= 0.1 else 2))   # 2026-10-30: vertical axes kept decimals too (was 4%,4%,4%)
    if adec and all(abs(t_*10**(adec-1) - round(t_*10**(adec-1))) < 1e-6 for t_ in ticks): adec -= 1   # 4.0 -> 4 when every tick is whole
    for val in ticks:
        y = yb-(val-lo)/(hi-lo)*(yb-yt)
        tl = fmt(val, {**c, "decimals": adec})
        if ax:
            d.line([(x0, y), (x1+20, y)], fill=GRID, width=2); d.line([(x0-12, y), (x0, y)], fill=AXIS, width=3)
            d.text((x0-24-d.textlength(tl, font=gf), y-18), tl, font=gf, fill=GR)
        elif len(S) > 1:
            d.line([(x0-10, y), (x1, y)], fill=GRID, width=2); d.text((x0-24-d.textlength(tl, font=gf), y-18), tl, font=gf, fill=GR)
        else:
            d.line([(x0-30, y), (x1+40, y)], fill=GRID, width=2); d.text((x1+60, y-18), tl, font=gf, fill=GR)
    xs = [x0 + (x1-x0)*i/max(1, n-1) for i in range(n)]
    step = max(1, math.ceil(n/(5 if v else 8)))
    last = -1e9; idx = [i for i in range(n) if i % step == 0]
    if n-1 not in idx:
        if xs[n-1]-xs[idx[-1]] < 110: idx[-1] = n-1
        else: idx.append(n-1)
    if ax:
        d.line([(x0, yt-20), (x0, yb)], fill=AXIS, width=3); d.line([(x0, yb), (x1+20, yb)], fill=AXIS, width=3)
        for i in idx: d.line([(xs[i], yb), (xs[i], yb+12)], fill=AXIS, width=3)
    for i in idx:
        lab = str(X[i]); tw = d.textlength(lab, font=gf); d.text((xs[i]-tw/2, yb+(28 if ax else 22)), lab, font=gf, fill=GR)
    seg = e*(n-1); used = []
    for k, s in reversed(list(enumerate(S))):
        col = tuple(s.get("color") or PAL[k % len(PAL)]); ys = [yb-(y-lo)/(hi-lo)*(yb-yt) for y in s["values"]]
        poly = [(xs[0], ys[0])]
        for i in range(n-1):
            if seg > i:
                t = min(1, seg-i); poly.append((xs[i]+(xs[i+1]-xs[i])*t, ys[i]+(ys[i+1]-ys[i])*t))
        if k == 0 and len(S) == 1 and len(poly) > 1:
            d.polygon(poly+[(poly[-1][0], yb), (xs[0], yb)], fill=AREA)
        if len(poly) > 1: d.line(poly, fill=col, width=(12 if v else 10) if k == 0 else 7, joint="curve")
        ex, ey = poly[-1]; d.ellipse([ex-13, ey-13, ex+13, ey+13], fill=col)
        cur = s["values"][min(n-1, int(seg+0.999))] if e < 1 else s["values"][-1]
        if k == 0 or e >= 1:
            lab = fmt(cur, c); lf = MF(50 if v else 44, 800); tw = d.textlength(lab, font=lf); ly = ey-90
            for u in used:
                if abs(ly-u) < 60: ly = u+60 if ey > u else u-60
            if len(S) > 1: ly = ey-lf.size/2-6; lx = ex+24
            else: lx = min(ex-tw/2, x1-tw+10)
            for u in used:
                if abs(ly-u) < lf.size*1.1: ly = u + (lf.size*1.1 if ly >= u else -lf.size*1.1)
            used.append(ly); d.text((lx, ly), lab, font=lf, fill=col if k else WH)
        if k == 0 and c.get("_hl") is not None and e >= 1:
            h = c["_hl"] % n; hx, hy = xs[h], ys[h]; rr = 30
            d.ellipse([hx-rr, hy-rr, hx+rr, hy+rr], outline=WH, width=6); d.ellipse([hx-13, hy-13, hx+13, hy+13], fill=col)
            hv = fmt(s["values"][h], c); hf = MF(46 if v else 42, 800); htw = d.textlength(hv, font=hf)
            if h != n-1: d.text((hx-htw/2, hy-rr-hf.size-14), hv, font=hf, fill=WH)

def _bar(d, c, W, H, v, top, e):
    B = c["bars"]; mx = max(b[1] for b in B); hl = c.get("highlight")
    lf = MF(40 if v else 38, 600); vf = MF(52 if v else 50, 800)
    lw = max(d.textlength(b[0], font=lf) for b in B)
    if v:
        gap = min(190, (1050-top)/len(B)); y = top+40
        vlw = max(d.textlength(fmt(b[1], c), font=vf) for b in B); bmax = min(W-300, W-80-20-vlw-40)   # keep value labels inside the frame
        for i, (lab, val) in enumerate(B):
            pe = ease(max(0, min(1, e*len(B)-i))); w = int(bmax*val/mx*pe); col = (HLC or WH) if (hl is not None and i == hl) else ((BAR if hl is not None else (YEL if i == len(B)-1 else BAR)) if BAR else ((118, 118, 122) if (HL_GREY and hl is not None) else YEL))
            d.text((80, y), lab, font=lf, fill=GR); d.rounded_rectangle([80, y+58, 80+max(w, 20), y+126], 14, fill=col)
            if c.get("_hl") is not None and c["_hl"] % len(B) == i: d.rounded_rectangle([72, y+50, 88+max(w, 20), y+134], 18, outline=WH, width=5)
            d.text((100+max(w, 20), y+58), fmt(val*pe, c), font=vf, fill=WH); y += gap
    else:
        x0 = 140+lw; gap = min(165, (H-200-top)/len(B)); y = top+30
        if c.get("axis", AXIS_DEFAULT):   # v9: value axis with vertical gridlines + tick labels under the bars
            raw = mx/4; mag = 10**math.floor(math.log10(raw)); stp = min([1, 2, 2.5, 5, 10], key=lambda m: abs(m*mag-raw))*mag
            mx = math.ceil(mx/stp-1e-9)*stp; yend = top+30+gap*len(B)-gap+95; gf = MF(28, 500)
            for k_ in range(int(round(mx/stp))+1):
                xv = x0+(W-x0-330)*k_*stp/mx; d.line([(xv, top+10), (xv, yend)], fill=GRID, width=2)
                tl = fmt(k_*stp, {**c, "decimals": c.get("axis_decimals", 0)}); d.text((xv-d.textlength(tl, font=gf)/2, yend+14), tl, font=gf, fill=GR)
            d.line([(x0, top+10), (x0, yend)], fill=AXIS, width=3); d.line([(x0, yend), (W-310, yend)], fill=AXIS, width=3)
        for i, (lab, val, *_) in enumerate(B):
            pe = ease(max(0, min(1, e*len(B)-i))); w = int((W-x0-330)*val/mx*pe); col = (HLC or WH) if (hl is not None and i == hl) else ((BAR if hl is not None else (YEL if i == len(B)-1 else BAR)) if BAR else ((118, 118, 122) if (HL_GREY and hl is not None) else YEL))
            d.text((120, y+18), lab, font=lf, fill=GR); d.rectangle([x0, y, x0+max(w, 16), y+85], fill=col)
            if c.get("_hl") is not None and c["_hl"] % len(B) == i: d.rectangle([x0-8, y-8, x0+max(w, 16)+8, y+93], outline=WH, width=5)
            d.text((x0+25+max(w, 16), y+14), (B[i][2] if len(B[i]) > 2 and pe >= 0.999 else fmt(val*pe, c)), font=vf, fill=WH); y += gap

def _dots(d, c, W, H, v, top, e):
    G = c["groups"]; tot = sum(g[1] for g in G); per = c.get("per", 1)
    nd = int(round(tot/per)); cols = c.get("cols", 12 if v else 26)
    hf = MF(150 if v else 120, 900); ht = c.get("headline", fmt(tot, c))
    d.text((80 if v else 120, top), ht, font=hf, fill=YEL); top += hf.size*1.15
    if c.get("headline_label"): d.text((80 if v else 120, top), c["headline_label"], font=MF(42 if v else 38, 500), fill=WH); top += 70
    gx0 = 80 if v else 120; gw = (W-160) if v else 1100
    avail = ((1240 - top) - 70*len(G) - 40) if v else (H-170-top)
    while True:
        r = gw/cols
        if math.ceil(nd/cols)*r <= avail or cols > 60: break
        cols += 1
    sizes = [int(round(g[1]/per)) for g in G]; ge = e*len(G); gi_ = min(int(ge), len(G)); shown = sum(sizes[:gi_]) + (int(sizes[gi_]*(ge-gi_)) if gi_ < len(G) else 0)
    k = 0; colors = []
    for gi, g in enumerate(G): colors += [tuple(g[2]) if len(g) > 2 else PAL[gi % len(PAL)]]*int(round(g[1]/per))
    for i in range(nd):
        row, col = divmod(i, cols); x = gx0+col*r; y = top+20+row*r
        d.ellipse([x+r*0.15, y+r*0.15, x+r*0.85, y+r*0.85], fill=colors[i] if i < shown and i < len(colors) else GRID)
    by = top+40+math.ceil(nd/cols)*r if v else top+20
    bx = 80 if v else 1320
    for gi, g in enumerate(G):
        col = tuple(g[2]) if len(g) > 2 else PAL[gi % len(PAL)]
        d.rounded_rectangle([bx, by, bx+24, by+24], 5, fill=col)
        d.text((bx+44, by-10), f"{g[0]}  {fmt(g[1]*e, c)}", font=MF(42 if v else 40, 700), fill=WH); by += 70

def chart_steps(c, D, hold_max=3.0, lead=0.3, anim=0.6):
    """Stepped build (Study 2): one new element every 1-3 s (point/segment, bar, dot group), then highlight moves
    every ~2.5 s if time is left, then the badge; finished chart holds <= hold_max s."""
    t = c["type"]; E = max(1, len(c["x"])-1 if t == "line" else len(c["bars"]) if t == "bar" else len(c["groups"]))
    nb = 1 if c.get("badge") else 0; hold = min(hold_max, max(1.0, D*0.2)); m = E+nb
    S = max(0.5, D-hold-anim-lead)               # time from first to last event start
    nh = 0; iv = S/max(1, m-1)
    if iv > 3.0 and t in ("line", "bar"): nh = math.ceil(S/3.0)-(m-1); iv = S/(m-1+nh)
    iv = max(0.8, iv); anim = min(anim, iv*0.8)
    ev = []; tt = lead
    for k in range(E): ev.append(("el", k, tt)); tt += iv
    for k in range(nh): ev.append(("hl", k, tt)); tt += iv
    if nb: ev.append(("badge", 0, tt))
    return ev, E, anim

def chart_state(c, ev, E, anim, tm):
    done = 0.0; hl = None; ba = 0.0; npts = len(c["x"]) if c["type"] == "line" else len(c.get("bars", [])) or 1
    for kind, k, t0 in ev:
        if tm < t0: break
        p = ease((tm-t0)/anim)
        if kind == "el": done = k + p
        elif kind == "hl": hl = (npts-1-k) if c["type"] == "line" else k   # line: walk back from the latest point
        else: ba = p; hl = None
    return min(1.0, done/E), ba, hl

def chart_frames(c, D, d_out, W, H):
    os.makedirs(d_out, exist_ok=True); n = int(D*FPS)+1; ev, E, anim = chart_steps(c, D); last = None
    for k in range(n):
        st = chart_state(c, ev, E, anim, k/FPS); key = (round(st[0], 4), round(st[1], 3), st[2])
        if key == last: os.link(f"{d_out}/{k-1:04d}.png", f"{d_out}/{k:04d}.png"); continue
        chart_frame(c, W, H, st[0], 1.0, badge_a=st[1], hl=st[2]).save(f"{d_out}/{k:04d}.png"); last = key

# ---------------- overlays on B-roll ----------------
def loc_tag(im, text, x, y, v):
    d = ImageDraw.Draw(im); f = MF(40 if v else 34, 600); tw = d.textlength(text, font=f); h = 66 if v else 58
    pill = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(pill).rounded_rectangle([x, y, x+tw+100, y+h], h//2, fill=(0, 0, 0, 150))
    im.alpha_composite(pill); cx, cy, r = x+36, y+h*0.42, h*0.2
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=YEL); d.polygon([(cx-r*0.85, cy+r*0.5), (cx+r*0.85, cy+r*0.5), (cx, cy+r*2.3)], fill=YEL)
    d.ellipse([cx-r*0.38, cy-r*0.38, cx+r*0.38, cy+r*0.38], fill=(0, 0, 0))
    d.text((x+66, y+(h-f.size)/2-4), text, font=f, fill=OV)

def card(im, c, v):
    """Draw an overlay card dict onto RGBA im (already transparent). Darkens the frame for readability."""
    W, H = im.size; d = ImageDraw.Draw(im); t = c["type"]
    dim = Image.new("RGBA", im.size, (0, 0, 0, 120 if t != "headline" else 100)); im.alpha_composite(dim); d = ImageDraw.Draw(im)
    if t == "compare":
        tf = MF(54 if v else 50, 800); title = c.get("title", "")
        tw = d.textlength(title, font=tf); ty = 470 if v else 170
        d.rectangle([(W-tw)/2-40, ty, (W+tw)/2+40, ty+92], fill=YEL); d.text(((W-tw)/2, ty+14), title, font=tf, fill=BG)
        items = c["items"]; nf = MF(150 if v else 140, 900); lf = MF(48 if v else 44, 600)
        for i, it in enumerate(items):
            lab, val = it[0], it[1]
            if v: cx, cy = W/2, 680+i*330
            else: cx, cy = W*(i+1)/(len(items)+1), 420
            col = YEL if i == 0 else OV
            vw = d.textlength(val, font=nf); shadow(im, (cx-vw/2, cy), val, nf, fill=col)
            lw = d.textlength(lab, font=lf); shadow(im, (cx-lw/2, cy+nf.size*1.15), lab, lf)
        if not v and len(items) == 2: d.line([(W/2, 400), (W/2, 700)], fill=(255, 255, 255, 120), width=3)
        if v and len(items) == 2:
            vs = MF(44, 800); d.text((W/2-d.textlength("vs", font=vs)/2, 920), "vs", font=vs, fill=YEL)
    elif t == "quote":
        qf = MF(66 if v else 64, 700); mw = (W-200) if v else 1350; x = 100 if v else 285
        L = wrap(d, c["text"], qf, mw); y = (560 if v else (H/2 - len(L)*42 - 60))
        d.text((x-10, y-150 if v else y-140), "\u201C", font=MF(220, 900), fill=YEL)
        for l in L: shadow(im, (x, y), l, qf); y += qf.size*1.3
        d.rectangle([x, y+30, x+70, y+38], fill=YEL)
        shadow(im, (x, y+60), c.get("who", ""), MF(46 if v else 42, 800))
        if c.get("role"): shadow(im, (x, y+60+62), c["role"], MF(38 if v else 34, 500), fill=(220, 220, 220))
    elif t == "headline":
        cw = (W-140) if v else 1300; x0 = (W-cw)/2; hf = MF(60 if v else 58, 800)
        L = wrap(d, c["text"], hf, cw-120); chh = 150 + len(L)*hf.size*1.25 + 70; y0 = (620 if v else (H-chh)/2)
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([x0+8, y0+14, x0+cw+8, y0+chh+14], 18, fill=(0, 0, 0, 160))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14))); d = ImageDraw.Draw(im)
        d.rounded_rectangle([x0, y0, x0+cw, y0+chh], 18, fill=(250, 250, 248)); d.rectangle([x0, y0+30, x0+14, y0+chh-30], fill=ACC_L)
        d.text((x0+60, y0+48), c["outlet"].upper(), font=MF(36, 800), fill=(110, 110, 120))
        if c.get("date"): d.text((x0+cw-60-d.textlength(c["date"], font=MF(32, 500)), y0+52), c["date"], font=MF(32, 500), fill=(140, 140, 150))
        y = y0+130
        for l in L: d.text((x0+60, y), l, font=hf, fill=(15, 15, 20)); y += hf.size*1.25
    if c.get("source"):
        shadow(im, (80 if v else 60, (1260 if v else H-70)), "Source: " + c["source"], MF(30 if v else 26, 500), fill=(235, 235, 235), r=3)

# ---------------- blurred-fill for wide clips in Shorts ----------------
def blur_fill_vf(inp, D, out="bg"):
    """ffmpeg filter: sharp 16:9 band centred over a blurred, zoomed copy (Bloomberg Shorts device)."""
    return (f"[{inp}]fps=30,split[a{out}][b{out}];[a{out}]scale=-2:1920,crop=1080:1920,boxblur=30:3,eq=brightness=-0.12[bb{out}];"
            f"[b{out}]scale=1188:-2:flags=lanczos,crop=1080:ih:'(iw-ow)/2*(1-t/{D:.2f})':0[fg{out}];"
            f"[bb{out}][fg{out}]overlay=0:(H-h)/2,setsar=1[{out}]")


# ---------------- Study 2 devices (2026-10-29) ----------------
def tl_track(D, bps, anims, state, render, fps=None):
    """Generic overlay timeline -> ffmpeg concat list text. bps: times where the overlay changes; anims: [(a, b)]
    windows rendered frame by frame; state(t) -> hashable key; render(key) -> png path (cached per key)."""
    fps = fps or FPS
    pts = sorted(set([b for b in bps if 0 < b < D] + [D])); t = 0.0; seq = []
    while t < D-1e-6:
        if any(a <= t+1e-6 < b for a, b in anims): nt = min(t+1/fps, D)
        else: nt = min([p for p in pts if p > t+1e-6] + [a for a, b in anims if a > t+1e-6] + [D])
        k = state(t)
        if seq and seq[-1][0] == k: seq[-1][1] += nt-t
        else: seq.append([k, nt-t])
        t = nt
    cache = {}; lines = []
    for k, d in seq:
        if k not in cache: cache[k] = render(k)
        lines.append(f"file '{cache[k]}'\nduration {d:.4f}")
    lines.append(f"file '{cache[seq[-1][0]]}'")
    return "\n".join(lines)

def stat_window(D, start=0.0, first_shot=None, count=0.7, fade=0.3, hold=(2.5, 4.0)):
    """Count-up 0.7 s, hold 2.5-4 s, 0.3 s fade; must end inside the first shot. -> (start, count_end, hold_end, end)"""
    lim = min(D, first_shot or D) - 0.1
    h = max(min(hold[1], lim-start-count-fade), min(hold[0], max(0.5, lim-start-count-fade)))
    return start, start+count, start+count+h, start+count+h+fade

def _pop(p): p = max(0, min(1, p)); return 1+2.2*(p-1)**3+1.2*(p-1)**2 if p < 1 else 1.0   # easeOutBack

def hook_card(im, text, loc=None, v=True):
    """Shorts 0-3 s headline: 2-3 lines of white Montserrat 800, sentence case, over a dark gradient; optional pin."""
    W, H = im.size; d = ImageDraw.Draw(im); x = 90; maxw = 860
    for sz in (92, 86, 80, 74, 68):
        f = MF(sz, 800); L = wrap(d, text, f, maxw)
        if len(L) <= 3: break
    lh = int(f.size*1.16); bottom = 1300; top = bottom-len(L)*lh
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g); g0 = top-330
    for y in range(max(0, g0), H):
        a = int(185*min(1, (y-g0)/260)) if y < top else 185
        gd.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    im.alpha_composite(g)
    if loc: loc_tag(im, loc, x-6, top-100, True)
    y = top
    for l in L: shadow(im, (x, y), l, f, r=6); y += lh

def pills_row(im, items, prog, v=True, y=None):
    """TLDR/EE-style company pills (text, no logos). items: ["Alphabet", ["Microsoft", "#00A4EF"], ...]. prog: seconds since start."""
    W, H = im.size; d = ImageDraw.Draw(im); f = MF(44 if v else 40, 800); ph = 84 if v else 76; pad = 34; gap = 22
    its = [(it, None) if isinstance(it, str) else (it[0], it[1] if len(it) > 1 else None) for it in items]
    if THEME == "mono": its = [(n, None) for n, _ in its]   # v8 Shorts (2026-10-30): no brand colours, white pills only
    ws = [d.textlength(n, font=f)+2*pad+(30 if not col else 0) for n, col in its]
    rows = [[]]; rw = 0; maxw = 900 if v else 1500
    for i, w in enumerate(ws):
        if rows[-1] and rw+gap+w > maxw: rows.append([]); rw = 0
        rows[-1].append(i); rw += (gap if rw else 0)+w
    yb = y if y is not None else (1250 if v else H-200)
    for r, row in enumerate(reversed(rows)):
        yy = yb-(r+1)*ph-r*16; tw = sum(ws[i] for i in row)+gap*(len(row)-1); xx = (W-tw)/2 if v else 120
        for i in row:
            p = max(0, min(1, (prog-i*0.12)/0.25))
            if p > 0:
                n, col = its[i]; sc = 0.7+0.3*_pop(p); w = ws[i]
                rgb = tuple(int(col.lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) if col else (250, 250, 248)
                L = Image.new("RGBA", (int(w)+20, ph+20), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
                ld.rounded_rectangle([10, 10, 10+w, 10+ph], ph//2, fill=rgb+(255,))
                lum = 0.3*rgb[0]+0.59*rgb[1]+0.11*rgb[2]; tc = (15, 15, 18) if lum > 160 else OV
                tx = 10+pad
                if not col: ld.ellipse([tx, 10+ph/2-9, tx+18, 10+ph/2+9], fill=(14, 14, 16) if THEME == "mono" else YEL); tx += 30
                ld.text((tx, 10+(ph-f.size)/2-5), n, font=f, fill=tc)
                L = L.resize((max(1, int(L.width*sc)), max(1, int(L.height*sc))), Image.LANCZOS)
                L.putalpha(L.getchannel("A").point(lambda a_: int(a_*min(1, p*1.6))))
                sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); cx, cy = xx+w/2, yy+ph/2
                sh.alpha_composite(L, (int(cx-L.width/2), int(cy-L.height/2))); im.alpha_composite(sh)
            xx += ws[i]+gap

def sticker(im, s, prog, v=True):
    """Sticker label with a drawn arrow (EE/TLDR). s: "text" or {"text", "x", "y", "to": [x, y], "angle"}. prog: seconds since start."""
    W, H = im.size; s = {"text": s} if isinstance(s, str) else dict(s)
    f = MF(48 if v else 44, 800); d = ImageDraw.Draw(im); tw = d.textlength(s["text"], font=f)
    bx, by = s.get("x", 470 if v else 1180), s.get("y", 420 if v else 230); ang = s.get("angle", -5)
    tx, ty = s.get("to", [bx-60, by+330] if v else [bx-260, by+300])
    p = max(0, min(1, prog/0.3)); pa = max(0, min(1, (prog-0.15)/0.4))
    if p <= 0: return
    L = Image.new("RGBA", (int(tw)+80, f.size+70), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
    ld.rounded_rectangle([8, 8, tw+64, f.size+52], 14, fill=YEL); ld.text((36, 20), s["text"], font=f, fill=(12, 12, 14))
    L = L.rotate(ang, expand=True, resample=Image.BICUBIC); sc = 0.5+0.5*_pop(p)
    L = L.resize((max(1, int(L.width*sc)), max(1, int(L.height*sc))), Image.LANCZOS)
    cx, cy = bx+tw/2+36, by+f.size/2+30
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    S = Image.new("RGBA", L.size, (0, 0, 0, 0)); S.putalpha(L.getchannel("A").point(lambda a_: int(a_*0.55)))
    sh.alpha_composite(S, (int(cx-L.width/2)+6, int(cy-L.height/2)+10)); im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    im.alpha_composite(L, (int(cx-L.width/2), int(cy-L.height/2)))
    if pa > 0:  # arrow: quadratic curve from label to target, drawn progressively, white with dark edge
        sx, sy = bx+30, by+f.size+50; mx, my = (sx+tx)/2-90, (sy+ty)/2; pts = []
        for i in range(41):
            u = i/40*ease(pa); pts.append(((1-u)**2*sx+2*(1-u)*u*mx+u*u*tx, (1-u)**2*sy+2*(1-u)*u*my+u*u*ty))
        A = Image.new("RGBA", im.size, (0, 0, 0, 0)); ad = ImageDraw.Draw(A)
        ad.line(pts, fill=(0, 0, 0, 160), width=16, joint="curve"); ad.line(pts, fill=OV+(255,), width=9, joint="curve")
        if pa >= 1:
            (x1, y1), (x2, y2) = pts[-4], pts[-1]; ang2 = math.atan2(y2-y1, x2-x1); hl = 38
            hd = [(x2+8*math.cos(ang2), y2+8*math.sin(ang2)), (x2-hl*math.cos(ang2-0.5), y2-hl*math.sin(ang2-0.5)), (x2-hl*math.cos(ang2+0.5), y2-hl*math.sin(ang2+0.5))]
            ad.polygon(hd, fill=OV+(255,), outline=(0, 0, 0, 160))
        im.alpha_composite(A)

_MONTHS = "January February March April May June July August September October November December".split()
_GENERIC = set("India Indian China Chinese US U.S. America American Europe European Japan Japanese UK Britain British Germany German Asia Wall Street".split())  # filler as a pop
_STOP = set("No Not Every Each All Some Many Most For From With As At By To Of Even Just Still Yet After Before Over Under So Then That This It The And But If Let's Only On In Its Now Why How What When Who Which Number First Second Third Here There They We You Our A An Or Also Because Big One Two Three".split())
def auto_keywords(text, k=2):
    """1-4 word keyword pops from narration: numbers with their unit first, then proper-noun runs."""
    import re
    toks = text.replace("\u2019", "'").split(); nums = []; names = []; i = 0
    def clean(w): return w.strip(".,;:!?\"()")
    while i < len(toks):
        w = clean(toks[i])
        if re.match(r"^[\u20b9$]?-?[0-9][0-9,]*(\.[0-9]+)?(st|nd|rd|th|%)?$", w):
            nxt = [clean(x).lower() for x in toks[i+1:i+3]]; val = w; cur = ""
            if i > 0 and clean(toks[i-1]) in _MONTHS: val = clean(toks[i-1])[:3]+" "+re.sub(r"(st|nd|rd|th)$", "", w)
            elif nxt[:1] == ["percent"]: val = w+"%"
            elif nxt[:1] and nxt[0] in ("billion", "million", "trillion"):
                val = w+nxt[0][0].upper(); cur = "$" if nxt[1:2] == ["dollars"] else ""
            elif nxt[:1] and nxt[0] in ("crore", "lakh"):
                val = w+" "+nxt[0]+("" if len(nxt) < 2 else ""); cur = "\u20b9" if nxt[1:2] == ["rupees"] else ""
            elif nxt[:1] == ["rupees"]: cur = "\u20b9"
            elif nxt[:1] == ["dollars"]: cur = "$"
            if i > 0 and clean(toks[i-1]).lower() == "minus": val = "-"+val
            if not (re.match(r"^[0-9]$", w) and not cur and "%" not in val): nums.append(((cur+val if not val.startswith("-") else "-"+cur+val[1:]), i))
            i += 1; continue
        if w[:1].isupper() and w not in _STOP and not (i == 0 or toks[i-1][-1:] in ".?!") or (w[:1].isupper() and w not in _STOP and i+1 < len(toks) and clean(toks[i+1])[:1].isupper() and clean(toks[i+1]) not in _STOP):
            run = [w]; j = i+1
            while j < len(toks) and clean(toks[j])[:1].isupper() and clean(toks[j]) not in _STOP and len(run) < 3 and toks[j-1][-1:] not in ".,?!;:" and not run[-1].endswith("'s") and not clean(toks[j]).endswith("'s"):
                run.append(clean(toks[j])); j += 1
            nm_ = " ".join(run); nm_ = nm_[:-2] if nm_.endswith("'s") else nm_
            if w not in _MONTHS and nm_ not in _STOP and nm_ not in _GENERIC: names.append((nm_, i))
            i = j; continue
        i += 1
    seen = set(); out = []
    for kw, pos in nums+names:
        if kw.lower() not in seen: seen.add(kw.lower()); out.append((kw, pos))
    return sorted(out[:k], key=lambda x: x[1])

def keyword_png(path, text, prog, W=1920, H=1080):
    """Long-form keyword pop: white Montserrat 800 with yellow bar accent (numbers in yellow), lower third left."""
    import re
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if text:
        p = ease(prog/0.22); f = MF(78, 800); x = 150-int(40*(1-p)); y = H-300; d = ImageDraw.Draw(im)
        parts = re.split(r"(\S*[0-9]\S*)", text); tw = sum(d.textlength(q, font=f) for q in parts)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
        sc_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sc_).rounded_rectangle([x-60, y-40, x+tw+120, y+f.size+50], 40, fill=(0, 0, 0, 110))
        L.alpha_composite(sc_.filter(ImageFilter.GaussianBlur(30)))
        ld.rectangle([x, y+6, x+14, y+f.size+12], fill=YEL); xx = x+44
        for q in parts:
            if not q: continue
            shadow(L, (xx, y-6), q, f, fill=YEL if re.search(r"[0-9]", q) else OV, r=5); xx += ImageDraw.Draw(L).textlength(q, font=f)
        L.putalpha(L.getchannel("A").point(lambda a_: int(a_*p))); im.alpha_composite(L)
    im.save(path)

def plan_shots(shots, D, target, maxlen, cuts_pref=(), cuts_any=(), first_min=0.0, durs=None, pool=(), min_shot=1.1):
    """Split a scene of D s into shots: n = max(len(shots), ceil(D/target)), each <= maxlen; cuts snap to sentence/
    comma ends (cuts_pref) or word starts (cuts_any). Extra shots alternate the scene's clips (new in-points), or the
    scene clip with pool clips. Returns [(clip_id, in_point, dur)]. Clip ids may carry an in-point: "hd_4308@3.5"."""
    n = max(len(shots), math.ceil(D/target - 0.15))
    while D/n > maxlen: n += 1
    while n > 1 and D/n < min_shot: n -= 1
    cuts = []; t0 = 0.0
    for k in range(1, n):
        rem = n-k+1; ideal = t0+(D-t0)/rem
        if k == 1 and first_min > ideal: ideal = first_min
        lo = t0+min_shot; hi = D-(n-k)*min_shot
        cand = [c for c in cuts_pref if abs(c-ideal) <= 0.9 and lo <= c <= hi and (k > 1 or c >= first_min)]
        if not cand: cand = [c for c in cuts_any if abs(c-ideal) <= 0.6 and lo <= c <= hi and (k > 1 or c >= first_min)]
        c = min(cand, key=lambda c: abs(c-ideal)) if cand else max(lo, min(hi, ideal))
        cuts.append(c); t0 = c
    edges = [0.0]+cuts+[D]; lens = [edges[k+1]-edges[k] for k in range(n)]
    base = [(s.split("@")[0], float(s.split("@")[1]) if "@" in s else 0.0) for s in shots]
    seq = list(base)
    if len(seq) < n:
        alt = base if len(base) > 1 else [x for b in [base[0]] for x in [b]]
        extra_pool = [(p, 0.0) for p in pool if p not in [b[0] for b in base]]
        k = 0; used = {}
        while len(seq) < n:
            if len(base) == 1 and extra_pool and len(seq) % 2 == 1: cid, ss = extra_pool[(len(seq)//2) % len(extra_pool)]
            else: cid, ss = alt[k % len(alt)]; k += 1
            m = used.get(cid, 0)+1; used[cid] = m
            seq.append((cid, ss+m*0.37*(durs.get(cid, 10) if durs else 10)))
    out = []
    for (cid, ss), L in zip(seq[:n], lens):
        dd = durs.get(cid) if durs else None
        if dd: ss = ss % max(0.5, dd) if ss + L <= dd - 0.1 or ss < dd else 0.0
        if dd and ss + L > dd - 0.1: ss = max(0.0, dd - L - 0.15)
        out.append((cid, round(ss, 2), L))
    return out


# ================= v7 (Study 3) animated devices, 2026-10-29 =================
# map, flow, timeline, icons, morph bars, tilt post-process, punch word, end screen, luma check.
# Every *_frames(spec, D, d_out, W, H, ...) writes %04d.png at 30 fps and returns the list of visible-change times (s).
import json as _json
ORG = (250, 78, 2); CREAM = (248, 241, 228); LAND = (24, 34, 56); LAND_HI = (34, 46, 74); BORDER = (52, 66, 98); SEA = (6, 12, 28)
DATA = "/workspace/work/yt/data"

def _ev_times(n, D, start=0.4, end_frac=0.78, max_gap=2.6, min_gap=0.35):
    """n event start times spread over [start, D*end_frac], gaps clamped to [min_gap, max_gap]."""
    if n <= 0: return []
    if n == 1: return [start]
    span = max(0.5, D*end_frac-start); g = max(min_gap, min(max_gap, span/(n-1)))
    return [start+i*g for i in range(n)]

def _linked_save(im, d_out, k, key, last):
    p = f"{d_out}/{k:04d}.png"
    if key is not None and key == last[0] and k > 0: os.link(f"{d_out}/{k-1:04d}.png", p)
    else: im.save(p)
    last[0] = key

def _fill_blend(a, b, t): return tuple(int(a[i]+(b[i]-a[i])*max(0, min(1, t))) for i in range(3))

# ---------------- map ----------------
_GEO = {}
def _geo(res="50m"):
    if res not in _GEO:
        fc = _json.load(open(f"{DATA}/ne_{res}.geojson")); out = {}
        for f in fc["features"]:
            p = f["properties"]; code = p.get("ADM0_A3") or p.get("ISO_A3")
            g = f["geometry"]; polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            out.setdefault(code, {"name": p.get("NAME"), "polys": [], "lx": p.get("LABEL_X"), "ly": p.get("LABEL_Y")})["polys"] += polys
            for alt in ("ISO_A3", "ISO_A3_EH", "ADM0_ISO"):
                if p.get(alt) and p[alt] != "-99" and p[alt] not in out: out[p[alt]] = out[code]
        _GEO[res] = out
    return _GEO[res]

VIEWS = {"world": [-170, -56, 190, 76], "asia": [28, -12, 150, 58], "india": [64, 5, 100, 37.5], "south_asia": [58, 2, 102, 40],
         "europe": [-25, 34, 45, 71], "us": [-128, 22, -64, 52], "north_america": [-170, 7, -50, 75], "china": [72, 17, 136, 54],
         "middle_east": [24, 10, 64, 42], "east_asia": [95, 0, 150, 50], "africa": [-20, -36, 54, 38], "latam": [-120, -56, -30, 33]}

def _merc_y(lat): lat = max(-85, min(85, lat)); return math.degrees(math.log(math.tan(math.pi/4+math.radians(lat)/2)))

def _bbox_of(code, geo):
    xs, ys = [], []
    for poly in geo[code]["polys"]:
        ring = poly[0]
        if len(ring) < 8 and len(geo[code]["polys"]) > 3: continue
        xs += [p[0] for p in ring]; ys += [p[1] for p in ring]
    return [min(xs), min(ys), max(xs), max(ys)]

def _centroid(code, geo):
    g = geo[code]
    if g.get("lx") is not None: return g["lx"], g["ly"]
    b = _bbox_of(code, geo); return (b[0]+b[2])/2, (b[1]+b[3])/2

def _view_rect(v, W, H, geo, pad=0.35):
    """-> mercator rect [x0, y0, x1, y1] (x=lon, y=merc lat) fitted to W:H."""
    if isinstance(v, str) and v in VIEWS: b = VIEWS[v]
    elif isinstance(v, str): b = _bbox_of(v, geo); dx, dy = (b[2]-b[0])*pad, (b[3]-b[1])*pad; b = [b[0]-dx, b[1]-dy, b[2]+dx, b[3]+dy]
    else: b = v
    x0, x1, y0, y1 = b[0], b[2], _merc_y(b[1]), _merc_y(b[3]); cx, cy = (x0+x1)/2, (y0+y1)/2
    w, h = x1-x0, y1-y0; ar = W/H
    if w/h < ar: w = h*ar
    else: h = w/ar
    return [cx-w/2, cy-h/2, cx+w/2, cy+h/2]

def _lerp_rect(a, b, t): return [a[i]+(b[i]-a[i])*t for i in range(4)]

def _ease_io(p): p = max(0, min(1, p)); return 0.5-0.5*math.cos(math.pi*p)

def map_frames(m, D, d_out, W=1920, H=1080, sync=None):
    """Animated map. m = {"view", "fill":[ISO3..], "pins":[[label, lon, lat]..], "routes":[[from, to, label]..],
    "zoom_to": ISO3|view, "push": 0.15, "counter": [value, label], "title", "subtitle", "source", "res": "50m"|"110m"}.
    Fills light one after another, then pins drop, then routes draw on (0.8 s), then the counter counts up."""
    os.makedirs(d_out, exist_ok=True); geo = _geo(m.get("res", "50m")); n = int(D*FPS)+1
    S = 1.15  # supersample for the base layer: drawn once at S x (W, H) of the *start* view, cropped per frame
    r0 = _view_rect(m.get("view", "world"), W, H, geo)
    if m.get("zoom_to"): r1 = _view_rect(m["zoom_to"], W, H, geo, pad=m.get("zoom_pad", 0.18))
    else:
        z = 1+m.get("push", 0.15); cx, cy = (r0[0]+r0[2])/2, (r0[1]+r0[3])/2
        if m.get("fill"):
            fx, fy = _centroid(m["fill"][0], geo); cx, cy = cx+(fx-cx)*0.25, cy+(_merc_y(fy)-cy)*0.25
        w, h = (r0[2]-r0[0])/z, (r0[3]-r0[1])/z; r1 = [cx-w/2, cy-h/2, cx+w/2, cy+h/2]
    if m.get("zoom_to") and (m.get("title") or m.get("counter")):   # keep the country clear of the title/counter band
        hh = r1[3]-r1[1]; cx = (r1[0]+r1[2])/2; top, bot = r1[3]+0.42*hh, r1[1]-0.08*hh; w = (top-bot)*W/H
        r1 = [cx-w/2, bot, cx+w/2, top]
    # ---- v8 camera tour: frame each pin / route as it appears, then pull back for the counter ----
    _fills0 = [c for c in m.get("fill", []) if c in geo]; _pins0 = m.get("pins", []); _routes0 = m.get("routes", [])
    _ne0 = len(_fills0) + len(_pins0) + len(_routes0) + (1 if m.get("counter") else 0)
    if sync and len(sync) >= _ne0: _T0 = list(sync[:_ne0])
    else: _T0 = _ev_times(_ne0, D, 0.5, 0.8, 2.6)
    KF = []   # (move start, move duration, target rect)
    if V8 and m.get("tour", True):
        r1w = r1[2]-r1[0]
        def _rect(cx, cy, w): h = w*H/W; return [cx-w/2, cy-h/2, cx+w/2, cy+h/2]
        def _loc0(x):
            if isinstance(x, str):
                if x in geo: return _centroid(x, geo)
                for p_ in _pins0:
                    if p_[0] == x: return p_[1], p_[2]
            return x[0], x[1]
        KF.append((0.0, min(1.8, max(0.8, (_T0[0] if _T0 else 1.0)+0.6)), r1))
        tz = m.get("tour_zoom", 0.62)
        tpp = _T0[len(_fills0):len(_fills0)+len(_pins0)]; trr = _T0[len(_fills0)+len(_pins0):len(_fills0)+len(_pins0)+len(_routes0)]
        if len(_pins0) >= 2:
            for (lab, lon, lat, *_), t0 in zip(_pins0, tpp):
                w_ = r1w*tz; h_ = w_*H/W; KF.append((max(0.2, t0-0.45), 1.0, _rect(lon, _merc_y(lat)+0.10*h_, w_)))
        for rt_, t0 in zip(_routes0, trr):
            ptl = rt_["path"] if isinstance(rt_, dict) else [_loc0(rt_[0]), _loc0(rt_[1])]
            xs_ = [q[0] for q in ptl]; ys_ = [q[1] for q in ptl]
            rr_ = _view_rect([min(xs_), min(ys_), max(xs_), max(ys_)], W, H, geo)
            cx_, cy_ = (rr_[0]+rr_[2])/2, (rr_[1]+rr_[3])/2; w_ = min(r0[2]-r0[0], max(r1w*0.75, (rr_[2]-rr_[0])*1.5))
            KF.append((max(0.2, t0-0.3), 1.2, _rect(cx_, cy_+0.06*w_*H/W, w_)))
        if m.get("counter") or KF[-1][2] is not r1:
            tcc = _T0[-1] if m.get("counter") else max(KF[-1][0]+2.2, D-3.0)
            allp = [(q[1], q[2]) for q in _pins0] + [tuple(q) for rt_ in _routes0 for q in (rt_["path"] if isinstance(rt_, dict) else [_loc0(rt_[0]), _loc0(rt_[1])])]
            if allp:   # final pull-back frames everything that was drawn, content kept below the title band
                bx0_, bx1_ = min(q[0] for q in allp), max(q[0] for q in allp); by0_, by1_ = _merc_y(min(q[1] for q in allp)), _merc_y(max(q[1] for q in allp))
                tb_, bb_ = (0.30 if m.get("title") else 0.10), 0.92          # content between 30 % and 92 % of the frame height
                fh = (by1_-by0_)/(bb_-tb_); fw = max(fh*W/H, (bx1_-bx0_)*1.10); fh = fw*H/W; fcx = (bx0_+bx1_)/2
                top_ = by1_ + tb_*fh + ((fh*(bb_-tb_))-(by1_-by0_))/2
                tgt = [fcx-fw/2, top_-fh, fcx+fw/2, top_]
            else: tgt = _rect((r1[0]+r1[2])/2, (r1[1]+r1[3])/2, r1w*1.04)
            KF.append((max(KF[-1][0]+1.0, tcc-0.4), 1.3, tgt))
        KF.sort(key=lambda x: x[0])
    def cam(t):
        if not KF: return _lerp_rect(r0, r1, _ease_io(t/D))
        cur = r0; arr = 0.0
        for (ts, dd, tg) in KF:
            if t < ts: break
            if t < ts+dd: return _lerp_rect(cur, tg, _ease_io((t-ts)/dd))
            cur = tg; arr = ts+dd
        z_ = min(0.06, 0.012*(t-arr)); cx_, cy_ = (cur[0]+cur[2])/2, (cur[1]+cur[3])/2; w_ = (cur[2]-cur[0])*(1-z_); h_ = (cur[3]-cur[1])*(1-z_)
        return [cx_-w_/2, cy_-h_/2, cx_+w_/2, cy_+h_/2]   # slow push while holding
    # union rect drawn once
    _R = [r0, r1] + [x[2] for x in KF]
    U = [min(r[0] for r in _R), min(r[1] for r in _R), max(r[2] for r in _R), max(r[3] for r in _R)]
    uw, uh = U[2]-U[0], U[3]-U[1]; scale = S*W/min(r[2]-r[0] for r in _R)            # px per degree at the tightest view
    if uw*uh*scale*scale > 64e6: scale = math.sqrt(64e6/(uw*uh))                        # memory cap (~64 MP base)
    BW, BH = int(uw*scale)+4, int(uh*scale)+4
    def P(lon, lat, mercy=False):
        y = lat if mercy else _merc_y(lat); return ((lon-U[0])*scale, (U[3]-y)*scale)
    base = Image.new("RGB", (BW, BH), SEA); bd = ImageDraw.Draw(base)
    fills = [c for c in m.get("fill", []) if c in geo]
    def rings(code):
        out = []
        for poly in geo[code]["polys"]:
            pts = [P(x, y) for x, y in poly[0]]
            if max(p[0] for p in pts) < -50 or min(p[0] for p in pts) > BW+50 or max(p[1] for p in pts) < -50 or min(p[1] for p in pts) > BH+50: continue
            out.append(pts)
        return out
    seen = set()
    for code, g in geo.items():
        if id(g) in seen: continue
        seen.add(id(g))
        for pts in rings(code):
            if len(pts) > 2: bd.polygon(pts, fill=LAND, outline=BORDER)
    masks = {}
    for code in fills:
        mk = Image.new("L", (BW, BH), 0); md = ImageDraw.Draw(mk)
        for pts in rings(code):
            if len(pts) > 2: md.polygon(pts, fill=255)
        masks[code] = mk
    # graticule-free flat style; subtle vignette later
    pins = m.get("pins", []); routes = m.get("routes", [])
    def loc(x):
        if isinstance(x, str):
            if x in geo: return _centroid(x, geo)
            for p in pins:
                if p[0] == x: return p[1], p[2]
        return x[0], x[1]
    ne = len(fills) + len(pins) + len(routes) + (1 if m.get("counter") else 0)
    if sync and len(sync) >= ne: T = list(sync[:ne])
    else: T = _ev_times(ne, D, 0.5, 0.8, 2.6)
    tf = T[:len(fills)]; tp = T[len(fills):len(fills)+len(pins)]; tr = T[len(fills)+len(pins):len(fills)+len(pins)+len(routes)]
    tc = T[-1] if m.get("counter") else None
    title_f, sub_f = MF(58, 800), MF(34, 500); lab_f = MF(34, 700); rl_f = MF(36, 800)
    vig = Image.new("L", (W, H), 0); vd = ImageDraw.Draw(vig)
    for k in range(40): vd.rectangle([k*6, k*4, W-k*6, H-k*4], outline=int(150*(1-k/40)))
    vig = vig.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v*0.55)); dark = Image.new("RGB", (W, H), (0, 0, 0))
    tlayer = None
    last = [None]; events = sorted(T)
    for k in range(n):
        t = k/FPS; r = cam(t); z = round(r[0], 5)+round(r[2], 5)*1e-3+(k if V8 else 0)
        # fill state
        fa = {c: ease((t-tt)/0.6) for c, tt in zip(fills, tf)}
        key = (round(z, 4), tuple(round(v, 2) for v in fa.values()), tuple(round(min(1, max(0, (t-x)/0.4)), 2) for x in tp),
               tuple(round(min(1, max(0, (t-x)/0.9)), 2) for x in tr), round(min(1, max(0, (t-tc)/0.9)), 2) if tc is not None else 0)
        if key == last[0]: os.link(f"{d_out}/{k-1:04d}.png", f"{d_out}/{k:04d}.png"); continue
        # crop to current view first (fast), then light the fills inside the crop
        x0, y0 = (r[0]-U[0])*scale, (U[3]-r[3])*scale; x1, y1 = (r[2]-U[0])*scale, (U[3]-r[1])*scale
        cb = (max(0, int(x0)-2), max(0, int(y0)-2), min(BW, int(x1)+3), min(BH, int(y1)+3)); im = base.crop(cb)
        for c in fills:
            if fa[c] > 0: im.paste(_fill_blend(LAND, FILL, fa[c]), (0, 0), masks[c].crop(cb))
        im = im.resize((W, H), Image.BICUBIC, box=(x0-cb[0], y0-cb[1], x1-cb[0], y1-cb[1]))
        im = (Image.composite(dark, im, vig) if THEME != "light" else im).convert("RGBA")
        sx = W/(r[2]-r[0])
        def SP(lon, lat): return ((lon-r[0])*sx, (r[3]-_merc_y(lat))*sx)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        rlabels = []
        # routes: quadratic arcs, orange, draw on over 0.9 s, label at apex
        for rt, t0 in zip(routes, tr):
            if isinstance(rt, dict):   # {"path": [[lon, lat], ...], "label": str, "dur": 1.8, "dash": false}
                pdur = rt.get("dur", 1.8); p = _ease_io((t-t0)/pdur)
                if p <= 0: continue
                P_ = [SP(*q) for q in rt["path"]]; P_ = [P_[0]] + P_ + [P_[-1]]; dense = []
                for i_ in range(1, len(P_)-2):
                    p0, p1, p2, p3 = P_[i_-1], P_[i_], P_[i_+1], P_[i_+2]
                    for j_ in range(16):
                        u_ = j_/16; u2, u3 = u_*u_, u_*u_*u_
                        dense.append(tuple(0.5*((2*p1[c_]) + (-p0[c_]+p2[c_])*u_ + (2*p0[c_]-5*p1[c_]+4*p2[c_]-p3[c_])*u2 + (-p0[c_]+3*p1[c_]-3*p2[c_]+p3[c_])*u3) for c_ in (0, 1)))
                dense.append(P_[-2]); cum = [0.0]
                for i_ in range(1, len(dense)): cum.append(cum[-1]+math.hypot(dense[i_][0]-dense[i_-1][0], dense[i_][1]-dense[i_-1][1]))
                def at(f_):
                    L_ = f_*cum[-1]; i_ = max(1, min(len(cum)-1, next((q for q in range(1, len(cum)) if cum[q] >= L_), len(cum)-1)))
                    w_ = (L_-cum[i_-1])/max(1e-6, cum[i_]-cum[i_-1]); return (dense[i_-1][0]+(dense[i_][0]-dense[i_-1][0])*w_, dense[i_-1][1]+(dense[i_][1]-dense[i_-1][1])*w_), i_
                hp, hi_ = at(p); pts = dense[:hi_]+[hp]
                rc = tuple(rt.get("color", ORG)); wd = rt.get("width", 7)
                if len(pts) > 1:
                    od.line(pts, fill=(0, 0, 0, 120), width=wd+5, joint="curve"); od.line(pts, fill=rc+(255,), width=wd, joint="curve")
                od.ellipse([pts[0][0]-8, pts[0][1]-8, pts[0][0]+8, pts[0][1]+8], fill=WH+(255,))
                if p < 1: od.ellipse([hp[0]-11, hp[1]-11, hp[0]+11, hp[1]+11], fill=HI+(255,))
                elif V8:
                    for q in range(6):
                        (qx, qy), _ = at(((t-t0-pdur)/max(2.6, pdur*1.6) - q*0.012) % 1.0); rq = 10-q*1.3
                        od.ellipse([qx-rq, qy-rq, qx+rq, qy+rq], fill=HI+(int(255*(1-q/6)),))
                if rt.get("label") and p > 0.5:
                    la = int(255*min(1, (p-0.5)/0.3)); (mx_, my_), _ = at(rt.get("label_at", 0.5)); tw = od.textlength(rt["label"], font=rl_f)
                    bx0 = max(40, min(W-tw-84, mx_+rt.get("label_dx", 30))); by0 = max(150, min(H-200, my_+rt.get("label_dy", -29)))
                    od.rounded_rectangle([bx0, by0, bx0+tw+44, by0+58], 12, fill=BOX+(int(la*0.9),), outline=rc+(la,), width=3)
                    od.text((bx0+22, by0+6), rt["label"], font=rl_f, fill=WH+(la,))
                continue
            a, b, *lab = rt
            p = ease((t-t0)/0.9)
            if p <= 0: continue
            (ax, ay), (bx, by) = SP(*loc(a)), SP(*loc(b)); mx, my = (ax+bx)/2, (ay+by)/2; dist = math.hypot(bx-ax, by-ay)
            nx, ny = -(by-ay)/max(1, dist), (bx-ax)/max(1, dist)
            if ny > 0: nx, ny = -nx, -ny
            cx_, cy_ = mx+nx*dist*0.28, my+ny*dist*0.28; pts = []
            for i in range(61):
                u = i/60*p; pts.append(((1-u)**2*ax+2*(1-u)*u*cx_+u*u*bx, (1-u)**2*ay+2*(1-u)*u*cy_+u*u*by))
            od.line(pts, fill=(0, 0, 0, 120), width=12, joint="curve"); od.line(pts, fill=ORG+(255,), width=7, joint="curve")
            hx, hy = pts[-1]; od.ellipse([hx-9, hy-9, hx+9, hy+9], fill=YEL+(255,))
            if V8 and p >= 1:   # a ship-dot travels the finished route with a short fading trail
                for q in range(6):
                    u = ((t-t0-0.9)/2.6 - q*0.018) % 1.0; qx = (1-u)**2*ax+2*(1-u)*u*cx_+u*u*bx; qy = (1-u)**2*ay+2*(1-u)*u*cy_+u*u*by
                    rq = 10-q*1.3; od.ellipse([qx-rq, qy-rq, qx+rq, qy+rq], fill=HI+(int(255*(1-q/6)),))
            od.ellipse([ax-8, ay-8, ax+8, ay+8], fill=WH+(255,))
            if lab and lab[0] and p > 0.6: rlabels.append((lab[0], p, ax, ay, bx, by, cx_, cy_))
        # pins: drop + label pill (labels flip side to avoid the right edge / each other)
        placed = []
        for (lab, lon, lat, *_), t0 in zip(pins, tp):
            p = min(1, max(0, (t-t0)/0.4))
            if p <= 0: continue
            x, y = SP(lon, lat); y -= 28*(1-ease(p)); a = int(255*min(1, p*1.5)); rr = 13
            od.ellipse([x-rr-5, y-rr-5, x+rr+5, y+rr+5], fill=(0, 0, 0, int(a*0.5)))
            if V8 and p >= 1:   # pulse ring
                ph = ((t-t0-0.4)/1.6) % 1.0; R_ = rr+34*ph; od.ellipse([x-R_, y-R_, x+R_, y+R_], outline=HI+(int(150*(1-ph)),), width=3)
            od.ellipse([x-rr, y-rr, x+rr, y+rr], fill=YEL+(a,), outline=(10, 10, 12, a), width=3)
            tw = od.textlength(lab, font=lab_f); right = x+28+tw+30 < W-40
            lx = x+26 if right else x-26-tw-28; ly = y-26
            for (px, py, pw) in placed:
                if abs(ly-py) < 52 and lx < px+pw and lx+tw+28 > px: ly = py+54
            placed.append((lx, ly, tw+28))
            od.rounded_rectangle([lx, ly, lx+tw+28, ly+50], 10, fill=BOX+(int(a*0.82),))
            od.text((lx+14, ly+5), lab, font=lab_f, fill=WH+(a,))
        for (lab0, p, ax, ay, bx, by, cx_, cy_) in rlabels:
            if True:
                lab = [lab0]
                la = int(255*min(1, (p-0.6)/0.4)); ap = (0.25*ax+0.5*cx_+0.25*bx, 0.25*ay+0.5*cy_+0.25*by)
                tw = od.textlength(lab[0], font=rl_f); bx0, by0 = ap[0]-tw/2-22, ap[1]-70
                if not (0 <= ap[0] <= W and 0 <= ap[1] <= H):   # apex off-screen: label near the on-screen end
                    ap = (0.75*bx+0.25*cx_, 0.75*by+0.25*cy_); bx0, by0 = ap[0]-tw/2-22, ap[1]-80
                bx0 = max(40, min(W-tw-84, bx0)); by0 = max(330 if (m.get("title") or m.get("counter")) else 150, min(H-200, by0))
                ymin = 330 if (m.get("title") or m.get("counter")) else 150
                for off in (0, -62, -124, 62, 124, 186, -186):   # keep clear of pin labels and pins
                    yb_ = by0+off
                    if yb_ < ymin or yb_ > H-200: continue
                    if not any(yb_ < py+54 and yb_+58 > py and bx0 < px+pw+30 and bx0+tw+44 > px-30 for (px, py, pw) in placed): by0 = yb_; break
                od.rounded_rectangle([bx0, by0, bx0+tw+44, by0+58], 12, fill=BOX+(int(la*0.9),), outline=ORG+(la,), width=3)
                od.text((bx0+22, by0+6), lab[0], font=rl_f, fill=YEL+(la,))
        im.alpha_composite(ov); d = ImageDraw.Draw(im)
        # title block (top-left, below the logo bug) + counter (top-right) + source
        if m.get("title"):
            ta = ease(t/0.5)
            if tlayer is not None and ta >= 1: im.alpha_composite(tlayer); tl = None
            else: tl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); tdd = ImageDraw.Draw(tl)
        if m.get("title") and tl is not None:
            tw = tdd.textlength(m["title"], font=title_f); sw = tdd.textlength(m.get("subtitle", ""), font=sub_f) if m.get("subtitle") else 0
            tdd.rounded_rectangle([40, 120, 40+max(tw, sw)+80, 120+(160 if m.get("subtitle") else 105)], 18, fill=BOX+(205,) if V8 else (6, 10, 20, 205))
            tdd.rectangle([60, 140, 72, 140+(120 if m.get("subtitle") else 66)], fill=YEL)
            tdd.text((96, 132), m["title"], font=title_f, fill=WH)
            if m.get("subtitle"): tdd.text((96, 208), m["subtitle"], font=sub_f, fill=GR)
            if ta >= 1: tlayer = tl
            else: tl.putalpha(tl.getchannel("A").point(lambda v: int(v*ta)))
            im.alpha_composite(tl)
        d = ImageDraw.Draw(im)
        if tc is not None and t >= tc:
            p = min(1, (t-tc)/0.9); val, lab = m["counter"]; shown = _countup(val, 1-(2**(-10*p)) if p < 1 else 1)
            vf = MF(96, 900); lf = MF(34, 600); vw = d.textlength(val, font=vf); lw = d.textlength(lab, font=lf); bw = max(vw, lw)+80
            bx0 = W-bw-60; a = int(255*min(1, p*3))
            box = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bdd = ImageDraw.Draw(box)
            ttl_r = 40+max(d.textlength(m.get("title", ""), font=title_f), d.textlength(m.get("subtitle", ""), font=sub_f) if m.get("subtitle") else 0)+80 if m.get("title") else 0
            by_ = 120 if (not V8 or ttl_r+40 < bx0) else H-130-210   # v8: top-right when clear of the title block, else bottom-right
            bdd.rounded_rectangle([bx0, by_, W-60, by_+210], 18, fill=BOX+(int(a*0.85),), outline=YEL+(a,), width=3 if V8 else 4)
            bdd.text((bx0+40, by_+18), shown, font=vf, fill=YEL+(a,)); bdd.text((bx0+40, by_+142), lab, font=lf, fill=WH+(a,))
            im.alpha_composite(box); d = ImageDraw.Draw(im)
        if m.get("source"):
            if THEME == "light": ImageDraw.Draw(im).text((60, H-70), "Source: "+m["source"], font=MF(26, 500), fill=MAPSRC)
            else: shadow(im, (60, H-70), "Source: "+m["source"], MF(26, 500), fill=MAPSRC, r=3)
        im.convert("RGB").save(f"{d_out}/{k:04d}.png"); last[0] = key
    return events + [0.0]

def _countup(big, e):
    import re
    m_ = re.search(r"[0-9][0-9,]*(\.[0-9]+)?", big)
    if not m_ or e >= 1: return big
    t = m_.group(0); dec = len(m_.group(1))-1 if m_.group(1) else 0; v = float(t.replace(",", ""))*e
    s = f"{v:,.{dec}f}" if "," in t else f"{v:.{dec}f}"
    return big[:m_.start()]+s+big[m_.end():]

# ---------------- simple icon set (drawn in PIL; outline or filled) ----------------
def draw_icon(d, kind, x, y, s, col, filled=False, lw=None, bg=SEA):
    """Icon in the box (x, y, s, s). kinds: factory chip person car phone coin building wafer ship bank."""
    lw = lw or max(3, int(s*0.07)); f = col if filled else None
    def R(a, b, c, e, r=0): (d.rounded_rectangle if r else d.rectangle)([x+a*s, y+b*s, x+c*s, y+e*s], *( [int(r*s)] if r else []), fill=f, outline=col, width=lw)
    if kind == "factory":
        pts = [(0.06, 0.92), (0.06, 0.45), (0.32, 0.6), (0.32, 0.45), (0.58, 0.6), (0.58, 0.18), (0.74, 0.18), (0.74, 0.6), (0.94, 0.6), (0.94, 0.92)]
        d.polygon([(x+a*s, y+b*s) for a, b in pts], fill=f, outline=col, width=lw)
        if filled:
            for k in range(3): d.rectangle([x+(0.14+k*0.24)*s, y+0.72*s, x+(0.24+k*0.24)*s, y+0.82*s], fill=bg)
    elif kind == "chip":
        R(0.22, 0.22, 0.78, 0.78, 0.06)
        for k in range(4):
            u = 0.3+k*0.133
            for (a, b, c, e) in ((u, 0.06, u, 0.22), (u, 0.78, u, 0.94), (0.06, u, 0.22, u), (0.78, u, 0.94, u)):
                d.line([x+a*s, y+b*s, x+c*s, y+e*s], fill=col, width=lw)
        d.rectangle([x+0.4*s, y+0.4*s, x+0.6*s, y+0.6*s], fill=bg if filled else None, outline=bg if filled else col, width=lw)
    elif kind == "person":
        d.ellipse([x+0.34*s, y+0.08*s, x+0.66*s, y+0.4*s], fill=f, outline=col, width=lw)
        d.chord([x+0.16*s, y+0.48*s, x+0.84*s, y+1.3*s], 180, 360, fill=f, outline=col, width=lw)
    elif kind == "car":
        d.polygon([(x+0.06*s, y+0.7*s), (x+0.06*s, y+0.5*s), (x+0.24*s, y+0.46*s), (x+0.36*s, y+0.28*s), (x+0.7*s, y+0.28*s),
                   (x+0.82*s, y+0.46*s), (x+0.94*s, y+0.5*s), (x+0.94*s, y+0.7*s)], fill=f, outline=col, width=lw)
        for cx in (0.27, 0.73): d.ellipse([x+(cx-0.1)*s, y+0.6*s, x+(cx+0.1)*s, y+0.8*s], fill=bg if filled else SEA, outline=col, width=lw)
    elif kind == "phone":
        R(0.28, 0.06, 0.72, 0.94, 0.08); d.line([x+0.44*s, y+0.84*s, x+0.56*s, y+0.84*s], fill=bg if filled else col, width=lw)
    elif kind == "coin":
        d.ellipse([x+0.1*s, y+0.1*s, x+0.9*s, y+0.9*s], fill=f, outline=col, width=lw)
        ft = MF(int(s*0.5), 900); tw = d.textlength("$", font=ft); d.text((x+s/2-tw/2, y+s*0.2), "$", font=ft, fill=bg if filled else col)
    elif kind == "building":
        R(0.2, 0.08, 0.8, 0.92)
        for r_ in range(4):
            for c_ in range(2): d.rectangle([x+(0.32+c_*0.22)*s, y+(0.2+r_*0.17)*s, x+(0.44+c_*0.22)*s, y+(0.28+r_*0.17)*s], fill=bg if filled else col)
    elif kind == "wafer":
        d.ellipse([x+0.08*s, y+0.08*s, x+0.92*s, y+0.92*s], fill=f, outline=col, width=lw)
        for k in range(1, 4):
            u = 0.08+k*0.21; c2 = bg if filled else col
            d.line([x+u*s, y+0.2*s, x+u*s, y+0.8*s], fill=c2, width=max(2, lw//2)); d.line([x+0.2*s, y+u*s, x+0.8*s, y+u*s], fill=c2, width=max(2, lw//2))
    elif kind == "ship":
        d.polygon([(x+0.06*s, y+0.6*s), (x+0.94*s, y+0.6*s), (x+0.8*s, y+0.86*s), (x+0.2*s, y+0.86*s)], fill=f, outline=col, width=lw)
        R(0.3, 0.32, 0.62, 0.6)
    elif kind == "bank":
        d.polygon([(x+0.08*s, y+0.34*s), (x+0.5*s, y+0.08*s), (x+0.92*s, y+0.34*s)], fill=f, outline=col, width=lw)
        for k in range(4): d.rectangle([x+(0.16+k*0.2)*s, y+0.4*s, x+(0.24+k*0.2)*s, y+0.8*s], fill=f, outline=col, width=max(2, lw//2))
        d.rectangle([x+0.08*s, y+0.84*s, x+0.92*s, y+0.92*s], fill=f, outline=col, width=lw)
    elif kind in ICONS_V9: ICONS_V9[kind](d, x, y, s, col, f, lw, bg if filled else None)
    else: d.ellipse([x+0.15*s, y+0.15*s, x+0.85*s, y+0.85*s], fill=f, outline=col, width=lw)

# ---------------- v9 pictograms (drawn in code, monochrome; no third-party icon set, so no licence to track) ----------------
def _P(d, x, y, s, pts, col, f, lw): d.polygon([(x+a*s, y+b*s) for a, b in pts], fill=f, outline=col, width=lw)
def _L(d, x, y, s, pts, col, lw): d.line([(x+a*s, y+b*s) for a, b in pts], fill=col, width=lw, joint="curve")
def _E(d, x, y, s, a, b, c, e, col, f, lw): d.ellipse([x+a*s, y+b*s, x+c*s, y+e*s], fill=f, outline=col, width=lw)
def _R(d, x, y, s, a, b, c, e, col, f, lw, r=0):
    (d.rounded_rectangle if r else d.rectangle)([x+a*s, y+b*s, x+c*s, y+e*s], *([int(r*s)] if r else []), fill=f, outline=col, width=lw)
def _ic_truck(d, x, y, s, col, f, lw, bg):
    _R(d, x, y, s, 0.04, 0.3, 0.62, 0.72, col, f, lw); _P(d, x, y, s, [(0.62, 0.42), (0.82, 0.42), (0.96, 0.58), (0.96, 0.72), (0.62, 0.72)], col, f, lw)
    for cx in (0.22, 0.8): _E(d, x, y, s, cx-0.09, 0.66, cx+0.09, 0.84, col, bg or (8, 8, 9), lw)
def _ic_house(d, x, y, s, col, f, lw, bg):
    _P(d, x, y, s, [(0.08, 0.48), (0.5, 0.1), (0.92, 0.48)], col, f, lw); _R(d, x, y, s, 0.18, 0.48, 0.82, 0.9, col, f, lw)
    _R(d, x, y, s, 0.42, 0.62, 0.58, 0.9, col, bg if f else None, max(2, lw-1))
def _ic_money(d, x, y, s, col, f, lw, bg):
    _R(d, x, y, s, 0.06, 0.26, 0.94, 0.74, col, f, lw, 0.05); _E(d, x, y, s, 0.38, 0.36, 0.62, 0.64, col, bg if f else None, lw)
    for a in (0.16, 0.84): _E(d, x, y, s, a-0.03, 0.47, a+0.03, 0.53, col, col, 1)
def _ic_oil(d, x, y, s, col, f, lw, bg):   # oil barrel
    _R(d, x, y, s, 0.2, 0.08, 0.8, 0.92, col, f, lw, 0.08)
    for b in (0.32, 0.68): d.line([x+0.2*s, y+b*s, x+0.8*s, y+b*s], fill=bg if f else col, width=lw)
    _P(d, x, y, s, [(0.5, 0.4), (0.58, 0.52), (0.5, 0.6), (0.42, 0.52)], bg if f else col, bg if f else None, max(2, lw-1))
def _ic_drop(d, x, y, s, col, f, lw, bg):
    _P(d, x, y, s, [(0.5, 0.06), (0.74, 0.46), (0.78, 0.62), (0.7, 0.8), (0.5, 0.9), (0.3, 0.8), (0.22, 0.62), (0.26, 0.46)], col, f, lw)
def _ic_cart(d, x, y, s, col, f, lw, bg):
    _L(d, x, y, s, [(0.04, 0.16), (0.18, 0.16), (0.3, 0.66), (0.84, 0.66)], col, lw); _P(d, x, y, s, [(0.22, 0.28), (0.94, 0.28), (0.86, 0.54), (0.28, 0.54)], col, f, lw)
    for cx in (0.36, 0.78): _E(d, x, y, s, cx-0.07, 0.74, cx+0.07, 0.88, col, f, lw)
def _ic_globe(d, x, y, s, col, f, lw, bg):
    _E(d, x, y, s, 0.08, 0.08, 0.92, 0.92, col, f, lw); c2 = bg if f else col
    _E(d, x, y, s, 0.32, 0.08, 0.68, 0.92, c2, None, max(2, lw-1)); d.line([x+0.08*s, y+0.5*s, x+0.92*s, y+0.5*s], fill=c2, width=max(2, lw-1))
def _ic_plane(d, x, y, s, col, f, lw, bg):
    _P(d, x, y, s, [(0.06, 0.5), (0.4, 0.44), (0.62, 0.1), (0.72, 0.1), (0.6, 0.44), (0.88, 0.44), (0.96, 0.32), (0.98, 0.5), (0.96, 0.68),
                    (0.88, 0.56), (0.6, 0.56), (0.72, 0.9), (0.62, 0.9), (0.4, 0.56)], col, f, lw)
def _ic_container(d, x, y, s, col, f, lw, bg):
    _R(d, x, y, s, 0.06, 0.3, 0.94, 0.72, col, f, lw)
    for k in range(1, 6): u = 0.06+k*0.88/6; d.line([x+u*s, y+0.36*s, x+u*s, y+0.66*s], fill=bg if f else col, width=max(2, lw-1))
def _ic_gear(d, x, y, s, col, f, lw, bg):
    pts = []
    for k in range(16):
        a = 2*math.pi*k/16; r = 0.44 if k % 2 == 0 else 0.34; pts.append((0.5+r*math.cos(a), 0.5+r*math.sin(a)))
    _P(d, x, y, s, pts, col, f, lw); _E(d, x, y, s, 0.38, 0.38, 0.62, 0.62, col, bg if f else None, lw)
def _ic_doc(d, x, y, s, col, f, lw, bg):
    _P(d, x, y, s, [(0.2, 0.06), (0.64, 0.06), (0.8, 0.22), (0.8, 0.94), (0.2, 0.94)], col, f, lw)
    for b in (0.4, 0.55, 0.7): d.line([x+0.32*s, y+b*s, x+0.68*s, y+b*s], fill=bg if f else col, width=max(2, lw-1))
def _ic_trend(d, x, y, s, col, f, lw, bg):
    _L(d, x, y, s, [(0.08, 0.08), (0.08, 0.92), (0.94, 0.92)], col, lw); _L(d, x, y, s, [(0.18, 0.74), (0.4, 0.5), (0.56, 0.62), (0.88, 0.24)], col, lw+1)
    _P(d, x, y, s, [(0.92, 0.18), (0.92, 0.36), (0.76, 0.22)], col, col, 1)
def _ic_down(d, x, y, s, col, f, lw, bg):
    _L(d, x, y, s, [(0.08, 0.08), (0.08, 0.92), (0.94, 0.92)], col, lw); _L(d, x, y, s, [(0.18, 0.26), (0.4, 0.5), (0.56, 0.4), (0.88, 0.76)], col, lw+1)
    _P(d, x, y, s, [(0.92, 0.84), (0.92, 0.64), (0.76, 0.8)], col, col, 1)
def _ic_pump(d, x, y, s, col, f, lw, bg):   # fuel pump
    _R(d, x, y, s, 0.14, 0.1, 0.62, 0.92, col, f, lw, 0.05); _R(d, x, y, s, 0.24, 0.2, 0.52, 0.42, col, bg if f else None, max(2, lw-1))
    _L(d, x, y, s, [(0.62, 0.3), (0.8, 0.42), (0.8, 0.78), (0.88, 0.82), (0.88, 0.36)], col, lw)
def _ic_people(d, x, y, s, col, f, lw, bg):
    for (cx, sc) in ((0.32, 0.85), (0.68, 0.85), (0.5, 1.0)):
        r = 0.13*sc; _E(d, x, y, s, cx-r, 0.2-r+0.1*(1-sc), cx+r, 0.2+r+0.1*(1-sc), col, f or bg or (8, 8, 9), lw)
        d.chord([x+(cx-0.2*sc)*s, y+(0.46+0.08*(1-sc))*s, x+(cx+0.2*sc)*s, y+(1.1)*s], 180, 360, fill=f or bg or (8, 8, 9), outline=col, width=lw)
def _ic_percent(d, x, y, s, col, f, lw, bg):
    d.line([x+0.8*s, y+0.14*s, x+0.2*s, y+0.86*s], fill=col, width=lw+1)
    _E(d, x, y, s, 0.14, 0.12, 0.38, 0.36, col, f, lw); _E(d, x, y, s, 0.62, 0.64, 0.86, 0.88, col, f, lw)
def _ic_scale(d, x, y, s, col, f, lw, bg):
    d.line([x+0.5*s, y+0.12*s, x+0.5*s, y+0.86*s], fill=col, width=lw); d.line([x+0.14*s, y+0.24*s, x+0.86*s, y+0.24*s], fill=col, width=lw)
    d.line([x+0.3*s, y+0.86*s, x+0.7*s, y+0.86*s], fill=col, width=lw)
    for cx in (0.2, 0.8): d.chord([x+(cx-0.16)*s, y+0.36*s, x+(cx+0.16)*s, y+0.68*s], 0, 180, fill=f, outline=col, width=lw); _L(d, x, y, s, [(cx-0.16, 0.52), (cx, 0.24), (cx+0.16, 0.52)], col, max(2, lw-1))
def _ic_capitol(d, x, y, s, col, f, lw, bg):   # government / central-bank building with dome
    d.chord([x+0.3*s, y+0.12*s, x+0.7*s, y+0.52*s], 180, 360, fill=f, outline=col, width=lw)
    _R(d, x, y, s, 0.16, 0.36, 0.84, 0.42, col, f, lw)
    for k in range(5): _R(d, x, y, s, 0.2+k*0.14, 0.46, 0.26+k*0.14, 0.8, col, f, max(2, lw-1))
    _R(d, x, y, s, 0.08, 0.84, 0.92, 0.92, col, f, lw)
def _ic_fire(d, x, y, s, col, f, lw, bg):
    _P(d, x, y, s, [(0.5, 0.06), (0.66, 0.3), (0.78, 0.5), (0.76, 0.72), (0.62, 0.9), (0.38, 0.9), (0.24, 0.72), (0.24, 0.52), (0.36, 0.36), (0.42, 0.52), (0.48, 0.3)], col, f, lw)
ICONS_V9 = {"truck": _ic_truck, "house": _ic_house, "home": _ic_house, "money": _ic_money, "cash": _ic_money, "oil": _ic_oil, "barrel": _ic_oil,
            "drop": _ic_drop, "cart": _ic_cart, "shop": _ic_cart, "globe": _ic_globe, "world": _ic_globe, "plane": _ic_plane, "container": _ic_container,
            "gear": _ic_gear, "doc": _ic_doc, "trend": _ic_trend, "up": _ic_trend, "down": _ic_down, "pump": _ic_pump, "fuel": _ic_pump, "gas": _ic_pump,
            "people": _ic_people, "percent": _ic_percent, "rate": _ic_percent, "scale": _ic_scale, "fed": _ic_capitol, "capitol": _ic_capitol,
            "government": _ic_capitol, "fire": _ic_fire, "war": _ic_fire}
# label words -> pictogram, used when a flow node has no "icon"
ICON_WORDS = [("oil", "oil"), ("crude", "oil"), ("barrel", "oil"), ("opec", "oil"), ("gasoline", "pump"), ("fuel", "pump"), ("petrol", "pump"), ("diesel", "pump"),
              ("truck", "truck"), ("freight", "truck"), ("shipping", "ship"), ("ship", "ship"), ("tanker", "ship"), ("port", "container"), ("container", "container"),
              ("factory", "factory"), ("plant", "factory"), ("manufactur", "factory"), ("chip", "chip"), ("semiconductor", "chip"), ("wafer", "wafer"),
              ("mortgage", "house"), ("house", "house"), ("home", "house"), ("rent", "house"), ("fed", "fed"), ("central bank", "fed"), ("reserve", "fed"),
              ("treasury", "fed"), ("government", "fed"), ("bank", "bank"), ("loan", "bank"), ("credit", "bank"), ("rate", "percent"), ("yield", "percent"),
              ("inflation", "up"), ("price", "trend"), ("cost", "money"), ("dollar", "money"), ("cash", "money"), ("profit", "money"), ("revenue", "money"),
              ("wage", "money"), ("store", "cart"), ("shop", "cart"), ("consumer", "people"), ("household", "people"), ("worker", "people"), ("job", "people"),
              ("people", "people"), ("investor", "person"), ("trader", "person"), ("market", "trend"), ("stock", "trend"), ("war", "fire"), ("attack", "fire"),
              ("export", "globe"), ("import", "globe"), ("global", "globe"), ("world", "globe"), ("plane", "plane"), ("airline", "plane"), ("phone", "phone"),
              ("car", "car"), ("ev ", "car"), ("tariff", "doc"), ("law", "doc"), ("rule", "doc"), ("policy", "doc")]
def auto_icon(label):
    l = " " + (label or "").lower() + " "
    return next((ic for w, ic in ICON_WORDS if w in l), None)

def _panel_head(im, c, W, H, t):
    """Title block for full-screen v7 devices (same type scale as charts)."""
    d = ImageDraw.Draw(im); a = ease(t/0.45); x = 120; y = 100
    if c.get("title"): d.text((x, y-int(16*(1-a))), c["title"], font=MF(64, 800), fill=_fill_blend(SEA, WH, a)); y += 76
    if c.get("subtitle"): d.text((x, y+8), c["subtitle"], font=MF(36, 500), fill=_fill_blend(SEA, GR, a)); y += 54
    if c.get("source"): d.text((60, H-60), "Source: "+c["source"], font=MF(26, 500), fill=GR)
    return y+20

# ---------------- flow diagram ----------------
def _node(n): return {"label": n} if isinstance(n, str) else dict(n)

def flow_frames(c, D, d_out, W=1920, H=1080, sync=None):
    """Money / supply flow. c = {"nodes": [str | {"label", "sub", "icon"}], "edges": [[i, j, "label"]], "layout": chain|hub|cycle,
    "title", "subtitle", "source"}. One step per node (node pops, its incoming edges draw on); older steps dim to 45 %; all
    return to full for the final hold. sync: optional step start times (e.g. narration sentence starts)."""
    os.makedirs(d_out, exist_ok=True); N = [_node(x) for x in c["nodes"]]; E = c.get("edges") or [[i, i+1, ""] for i in range(len(N)-1)]
    lay = c.get("layout", "chain"); n = len(N); nf = int(D*FPS)+1
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8))); top = 330
    lf = MF(44 if n <= 4 else 38, 800); sf = MF(30, 500); el_f = MF(34, 800)
    # node boxes
    box = []
    if lay == "chain":
        bw = min(320, (W-240-(n-1)*170)/n); gap = (W-240-n*bw)/max(1, n-1); cy = 600
        for i in range(n): box.append([120+i*(bw+gap), cy-135, 120+i*(bw+gap)+bw, cy+135])
    elif lay == "hub":
        cx, cy = W/2, 650; bw = 330; box.append([cx-bw/2, cy-100, cx+bw/2, cy+100]); m_ = n-1
        for i in range(m_):
            a_ = -math.pi/2 + 2*math.pi*i/m_ if m_ > 2 else (math.pi if i == 0 else 0); rx, ry = 640, 270
            bx, by = cx+rx*math.cos(a_), cy+ry*math.sin(a_); box.append([bx-bw*0.45, by-85, bx+bw*0.45, by+85])
    else:  # cycle
        cx, cy = W/2, 650; rx, ry = 600, 260; bw = 320
        for i in range(n):
            a_ = -math.pi/2 + 2*math.pi*i/n; bx, by = cx+rx*math.cos(a_), cy+ry*math.sin(a_); box.append([bx-bw/2, by-80, bx+bw/2, by+80])
    picto = c.get("style", "picto" if PICTO_DEFAULT else "box") == "picto"
    if picto:   # v9: pictogram nodes = circle + big icon, label underneath (Study 5: CNBC explains processes with illustrations)
        for nd in N: nd.setdefault("icon", auto_icon(nd.get("label", "")) or "gear")
        R_ = 112 if lay == "chain" else 92
        box = [[(b[0]+b[2])/2-R_, (b[1]+b[3])/2-R_-(40 if lay == "chain" else 30), (b[0]+b[2])/2+R_, (b[1]+b[3])/2+R_-(40 if lay == "chain" else 30)] for b in box]
    if sync and len(sync) >= n: T = list(sync[:n])
    else: T = _ev_times(n, D, 0.5, 0.72, 3.2, 1.2)
    t_all = min(D-0.6, T[-1]+max(1.4, min(2.6, D-T[-1]-1.0)))   # everything back to full brightness
    def anchor(b, tx, ty):
        cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2; dx, dy = tx-cx, ty-cy
        if picto:
            r_ = (b[2]-b[0])/2*1.1; dd = max(1e-6, math.hypot(dx, dy)); return cx+dx/dd*r_, cy+dy/dd*r_
        if dx == 0 and dy == 0: return cx, cy
        sx = (b[2]-b[0])/2/abs(dx) if dx else 1e9; sy = (b[3]-b[1])/2/abs(dy) if dy else 1e9; s_ = min(sx, sy)
        return cx+dx*s_*1.04, cy+dy*s_*1.04
    last = [None]; events = list(T) + [t_all]
    for k in range(nf):
        t = k/FPS; step = max([i for i in range(n) if t >= T[i]], default=-1)
        alls = t >= t_all; key = (step, alls, tuple(round(min(1, max(0, (t-T[i])/0.6)), 2) for i in range(n)), round(min(1, t/0.45), 2), round(min(1, max(0, (t-t_all)/0.4)), 2), k if V8 else 0)
        if key == last[0]: os.link(f"{d_out}/{k-1:04d}.png", f"{d_out}/{k:04d}.png"); continue
        last[0] = key
        im = Image.new("RGBA", (W, H), SEA+(255,)); _panel_head(im, c, W, H, t); L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        def dim(i):
            if alls: return 0.45+0.55*min(1, (t-t_all)/0.4)
            return 1.0 if i == step else 0.45
        for (i, j, *lab) in E:   # edges
            p = ease((t-T[max(i, j)]-0.15)/0.6)
            if p <= 0: continue
            bi, bj = box[i], box[j]; cj = ((bj[0]+bj[2])/2, (bj[1]+bj[3])/2); ci = ((bi[0]+bi[2])/2, (bi[1]+bi[3])/2)
            a0 = anchor(bi, *cj); a1 = anchor(bj, *ci); ex, ey = a0[0]+(a1[0]-a0[0])*p, a0[1]+(a1[1]-a0[1])*p
            al = int(255*dim(max(i, j))); col = YEL+(al,)
            d.line([a0, (ex, ey)], fill=col if not V8 else (col[0], col[1], col[2], int(al*0.55)), width=8 if not V8 else 5)
            if V8 and p >= 1:   # particles: 3 dots flowing along the arrow, speed ~0.55 edge/s
                for q in range(3):
                    u = (t*0.55 + q/3.0) % 1.0; px_, py_ = a0[0]+(a1[0]-a0[0])*u, a0[1]+(a1[1]-a0[1])*u; pa = int(al*min(1, u*5, (1-u)*5))
                    d.ellipse([px_-7, py_-7, px_+7, py_+7], fill=HI+(pa,))
            if V8 and 0 < p < 1:   # leading dot while the arrow draws
                d.ellipse([ex-9, ey-9, ex+9, ey+9], fill=HI+(al,))
            if p > 0.9:
                ang = math.atan2(a1[1]-a0[1], a1[0]-a0[0]); hl = 30
                d.polygon([(ex, ey), (ex-hl*math.cos(ang-0.45), ey-hl*math.sin(ang-0.45)), (ex-hl*math.cos(ang+0.45), ey-hl*math.sin(ang+0.45))], fill=col)
            if lab and lab[0] and p > 0.5:
                la = int(al*min(1, (p-0.5)/0.4)); mx, my = (a0[0]+a1[0])/2, (a0[1]+a1[1])/2
                Lw = [w_ for w_ in wrap(d, lab[0], el_f, 300)][:2]; tw = max(d.textlength(l_, font=el_f) for l_ in Lw); hh = 46*len(Lw)
                yy = my+175 if lay == "chain" else my-hh/2   # chain: labels sit under the arrow, below the boxes
                if picto and lay == "chain": yy = my-150-hh
                if lay == "chain" and not picto: d.line([(mx, my+18), (mx, yy-10)], fill=(YEL[0], YEL[1], YEL[2], int(la*0.5)), width=3)
                if picto and lay == "chain": d.line([(mx, yy+hh+12), (mx, my-20)], fill=(YEL[0], YEL[1], YEL[2], int(la*0.4)), width=2)
                d.rounded_rectangle([mx-tw/2-18, yy-8, mx+tw/2+18, yy+hh+4], 12, fill=BOX+(int(la*0.95),))
                for q, l_ in enumerate(Lw): d.text((mx-d.textlength(l_, font=el_f)/2, yy+q*46), l_, font=el_f, fill=YEL+(la,))
        for i, nd in enumerate(N):   # nodes
            p = min(1, max(0, (t-T[i])/0.35))
            if p <= 0: continue
            sc = 0.85+0.15*_pop(p); b = box[i]; cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2; bw_, bh_ = (b[2]-b[0])*sc, (b[3]-b[1])*sc
            al = int(255*dim(i)*min(1, p*1.5)); on = (i == step and not alls)
            if picto:
                r_ = (b[2]-b[0])/2*sc; lit = on or alls
                if on:
                    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([cx-r_-22, cy-r_-22, cx+r_+22, cy+r_+22], fill=HI+(int(al*0.18*(0.75+0.25*math.sin(t*4))),))
                    L.alpha_composite(gl.filter(ImageFilter.GaussianBlur(20))); d = ImageDraw.Draw(L)
                fill_, ink = (PIC_ON if lit else PIC_OFF)
                d.ellipse([cx-r_, cy-r_, cx+r_, cy+r_], fill=fill_+(al,), outline=HI+(al,), width=3)
                Ic = Image.new("RGBA", (W, H), (0, 0, 0, 0)); isz = r_*1.15
                draw_icon(ImageDraw.Draw(Ic), nd["icon"], cx-isz/2, cy-isz/2, isz, ink+(al,), filled=False, lw=max(4, int(isz*0.06)), bg=fill_); L.alpha_composite(Ic); d = ImageDraw.Draw(L)
                sp_ = min([abs(((box[q][0]+box[q][2])/2)-cx) for q in range(n) if q != i] or [600])
                ty = cy+r_+22; lines = wrap(d, nd["label"], lf, max(220, min(420, sp_-40)))[:2]
                for l_ in lines: d.text((cx-d.textlength(l_, font=lf)/2, ty), l_, font=lf, fill=WH+(al,)); ty += lf.size*1.12
                if nd.get("sub"): d.text((cx-d.textlength(nd["sub"], font=sf)/2, ty+4), nd["sub"], font=sf, fill=GR+(al,))
                continue
            if NODE_DARK:
                nf_, ntx = (PIC_ON if (on or alls) else PIC_OFF); nsub = (80, 80, 84) if (on or alls) else (150, 150, 154)
                if on and V8:   # soft glow behind the active node
                    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle([cx-bw_/2-18, cy-bh_/2-18, cx+bw_/2+18, cy+bh_/2+18], 34, fill=HI+(int(al*0.16*(0.75+0.25*math.sin(t*4))),))
                    L.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18))); d = ImageDraw.Draw(L)
                d.rounded_rectangle([cx-bw_/2, cy-bh_/2, cx+bw_/2, cy+bh_/2], 22, fill=nf_+(al,), outline=HI+(al,) if not (on or alls) else nf_+(al,), width=2)
            else:
                ntx = (14, 16, 22); nsub = (90, 92, 100); nf_ = CREAM
                d.rounded_rectangle([cx-bw_/2, cy-bh_/2, cx+bw_/2, cy+bh_/2], 22, fill=CREAM+(al,), outline=(YEL if on else CREAM)+(al,), width=6 if on else 2)
            ic = nd.get("icon"); ty = cy-bh_/2+24
            if ic:
                Ic = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw_icon(ImageDraw.Draw(Ic), ic, cx-34, ty, 68, ntx+(al,), filled=False, bg=nf_); L.alpha_composite(Ic); d = ImageDraw.Draw(L); ty += 80
            lines = wrap(d, nd["label"], lf, bw_-40)[:3]
            if not ic: ty = cy-(len(lines)*lf.size*1.12 + (sf.size*1.3 if nd.get("sub") else 0))/2
            for l_ in lines: d.text((cx-d.textlength(l_, font=lf)/2, ty), l_, font=lf, fill=ntx+(al,)); ty += lf.size*1.12
            if nd.get("sub"): d.text((cx-d.textlength(nd["sub"], font=sf)/2, ty+4), nd["sub"], font=sf, fill=nsub+(al,))
        im.alpha_composite(L); im.convert("RGB").save(f"{d_out}/{k:04d}.png")
    return events

# ---------------- timeline ----------------
def timeline_frames(c, D, d_out, W=1920, H=1080, sync=None):
    """c = {"items": [[date, label], ...], "title", "subtitle", "source", "now": idx (optional, gets a pulsing marker)}.
    Axis draws on in 0.9 s, then one dated event every 1-2.6 s, alternating above/below; the newest is yellow."""
    os.makedirs(d_out, exist_ok=True); It = c["items"]; n = len(It); nf = int(D*FPS)+1
    x0, x1, ay = 170, W-170, 640; xs = [x0+(x1-x0)*(i+0.5)/n for i in range(n)]
    T = list(sync[:n]) if sync and len(sync) >= n else _ev_times(n, D, 1.0, 0.88 if V8 else 0.75, 3.0 if V8 else 2.6, 0.9)
    df, lf = MF(46, 900), MF(34, 600); last = [None]; colw = (x1-x0)/n - 24
    for k in range(nf):
        t = k/FPS; pa = ease(t/0.9); cur = max([i for i in range(n) if t >= T[i]], default=-1)
        key = (round(pa, 3), cur, tuple(round(min(1, max(0, (t-T[i])/0.35)), 2) for i in range(n)), round(min(1, t/0.45), 2),
               int(t*4) % 2 if c.get("now") is not None and cur >= c["now"] else 0, round(min(1, max(0, (t-T[cur])/0.7)), 2) if (V8 and cur >= 0) else 0)
        if key == last[0]: os.link(f"{d_out}/{k-1:04d}.png", f"{d_out}/{k:04d}.png"); continue
        last[0] = key
        im = Image.new("RGBA", (W, H), SEA+(255,)); _panel_head(im, c, W, H, t); d = ImageDraw.Draw(im)
        d.line([(x0-40, ay), (x0-40+(x1-x0+80)*pa, ay)], fill=AXIS, width=6)
        if V8 and cur >= 0:   # playhead glides to the newest event, white progress line behind it
            prev = xs[cur-1] if cur > 0 else x0-40; ph = prev+(xs[cur]-prev)*_ease_io((t-T[cur])/0.7)
            d.line([(x0-40, ay), (ph, ay)], fill=HI, width=6)
            d.ellipse([ph-22, ay-22, ph+22, ay+22], outline=HI, width=3)
        if pa >= 1: d.polygon([(x1+40, ay-14), (x1+64, ay), (x1+40, ay+14)], fill=AXIS)
        for i, (dt, lab) in enumerate(It):
            p = min(1, max(0, (t-T[i])/0.35))
            if p <= 0: continue
            e = ease(p); up = i % 2 == 0; col = YEL if i == cur else TL_DIM; x = xs[i]
            r_ = 16 if i == cur else 12; d.ellipse([x-r_, ay-r_, x+r_, ay+r_], fill=col, outline=SEA, width=4)
            stem = 70*e; d.line([(x, ay-r_ if up else ay+r_), (x, ay-r_-stem if up else ay+r_+stem)], fill=col, width=4)
            L = wrap(d, lab, lf, colw)[:3]; dw = d.textlength(dt, font=df)
            blk = df.size*1.2 + len(L)*lf.size*1.25; yb = (ay-r_-stem-14-blk) if up else (ay+r_+stem+14)
            yb += (1-e)*(24 if up else -24); a = int(255*min(1, p*1.6))
            d.text((x-dw/2, yb), dt, font=df, fill=(YEL if i == cur else WH)+(a,) if False else (YEL if i == cur else WH))
            yy = yb+df.size*1.25
            for l_ in L: d.text((x-d.textlength(l_, font=lf)/2, yy), l_, font=lf, fill=GR if i != cur else WH); yy += lf.size*1.25
            if c.get("now") is not None and i == c["now"] and t >= T[i] and int(t*4) % 2 == 0:
                d.ellipse([x-30, ay-30, x+30, ay+30], outline=YEL, width=4)
        im.convert("RGB").save(f"{d_out}/{k:04d}.png")
    return T

# ---------------- icon-count graphic ----------------
def icons_frames(c, D, d_out, W=1920, H=1080, sync=None):
    """c = {"rows": [[icon, total, on, label], ...] (outline icons; the first `on` fill yellow one by one),
    "pct": [icon, percent, label] (one big outline icon that fills up to percent), "title", "subtitle", "source"}.
    Rows build one after another (icons pop with 0.08-0.15 s stagger), then the fill rises."""
    os.makedirs(d_out, exist_ok=True); R_ = c.get("rows", []); nf = int(D*FPS)+1; pc = c.get("pct")
    ne = len(R_)*2 + (1 if pc else 0); T = _ev_times(ne, D, 0.6, 0.72, 2.6, 1.0)
    last = [None]; big_f = MF(96, 900); lab_f = MF(40, 600)
    area_w = (W-260-(560 if pc else 0))
    for k in range(nf):
        t = k/FPS; key = (round(min(1, t/0.45), 2),) + tuple(round(min(1.2, max(0, t-x)), 2) for x in T)
        if key == last[0]: os.link(f"{d_out}/{k-1:04d}.png", f"{d_out}/{k:04d}.png"); continue
        last[0] = key
        im = Image.new("RGBA", (W, H), SEA+(255,)); top = _panel_head(im, c, W, H, t); d = ImageDraw.Draw(im)
        y = max(top+40, 360 if len(R_) == 1 else 330); rh = (H-170-y)/max(1, len(R_))
        for r, (ic, tot, on, lab) in enumerate(R_):
            t_pop, t_fill = T[2*r], T[2*r+1]
            per_row = min(tot, (25 if V8 else 20) if not pc else 8); s = min(130, area_w/per_row*0.8); rows_n = math.ceil(tot/per_row)
            s = min(s, (rh-110)/rows_n*0.9); gap = s*0.22
            for i in range(tot):
                p = min(1, max(0, (t-t_pop-i*min(0.15, 1.2/tot))/0.25))
                if p <= 0: continue
                rr, cc = divmod(i, per_row); sc = 0.6+0.4*_pop(p); ss = s*sc
                x = 130+cc*(s+gap)+(s-ss)/2; yy = y+rr*(s+gap)+(s-ss)/2
                fon = i < on and t >= t_fill+i*min(0.15, 1.0/max(1, on))
                draw_icon(d, ic, x, yy, ss, YEL if fon else MUTED, filled=fon)
            # count label: "5 of 12 ..." counts up with the fill
            pf = min(1, max(0, (t-t_fill)/max(0.5, min(0.15, 1.0/max(1, on))*on+0.2)))
            ly = y+rows_n*(s+gap)+10
            if t >= t_pop+0.2:
                num = f"{int(round(on*pf))}" if t >= t_fill else "0"; txt = f"{num} of {tot}"
                d.text((130, ly), txt, font=MF(56, 900), fill=YEL); d.text((130+d.textlength(txt, font=MF(56, 900))+24, ly+14), lab, font=lab_f, fill=WH)
            y += rh
        if pc:
            ic, pct, lab = pc; tp = T[-1]; s = 340; x, yy = W-540, max(top+40, 330)
            if t >= tp-0.6:
                a = min(1, max(0, (t-tp+0.6)/0.4)); col = _fill_blend(SEA, MUTED, a)
                draw_icon(d, ic, x, yy, s, col, filled=False, lw=10)
                fe = ease((t-tp)/1.4) if t >= tp else 0
                if fe > 0:  # fill rises from the bottom, clipped to the icon silhouette
                    mk = Image.new("L", (W, H), 0); draw_icon(ImageDraw.Draw(mk), ic, x, yy, s, 255, filled=True, lw=10, bg=0)
                    cut = Image.new("L", (W, H), 0); ImageDraw.Draw(cut).rectangle([0, yy+s-s*pct/100*fe, W, H], fill=255)
                    from PIL import ImageChops
                    im.paste(YEL, (0, 0), ImageChops.multiply(mk, cut)); d = ImageDraw.Draw(im)
                v = f"{pct*fe:.0f}%"; d.text((x+s/2-d.textlength(v, font=big_f)/2, yy+s+20), v, font=big_f, fill=YEL)
                for q, l_ in enumerate(wrap(d, lab, MF(34, 600), 480)[:3]): d.text((x+s/2-d.textlength(l_, font=MF(34, 600))/2, yy+s+135+q*44), l_, font=MF(34, 600), fill=WH)
        im.convert("RGB").save(f"{d_out}/{k:04d}.png")
    return T

# ---------------- morph bars ----------------
def morph_frames(c, D, d_out, W=1920, H=1080, sync=None):
    """c = {"bars": [[label, value_from, value_to], ...], "from": "2019", "to": "2026", "title", "subtitle", "prefix", "suffix",
    "source"}. Bars build to the 'from' values, hold, then ease to the 'to' values while the period badge flips."""
    os.makedirs(d_out, exist_ok=True); B = c["bars"]; nf = int(D*FPS)+1; mx = max(max(b[1], b[2]) for b in B)
    tb = 0.5; tm = min(max(D*0.45, 3.2), D-3.5); md = min(2.2, max(1.4, D*0.18)); last = [None]
    lf = MF(40, 600); vf = MF(52, 800); bf = MF(56, 900)
    for k in range(nf):
        t = k/FPS; pb = ease((t-tb)/1.2); pm = _ease_io((t-tm)/md)
        key = (round(pb, 3), round(pm, 3), round(min(1, t/0.45), 2), t > tm+md+0.6)
        if key == last[0]: os.link(f"{d_out}/{k-1:04d}.png", f"{d_out}/{k:04d}.png"); continue
        last[0] = key
        im = Image.new("RGBA", (W, H), SEA+(255,)); top = _panel_head(im, c, W, H, t); d = ImageDraw.Draw(im)
        lw = max(d.textlength(b[0], font=lf) for b in B); x0 = 160+lw; gap = min(170, (H-220-top-60)/len(B)); y = top+90
        for i, (lab, a, b) in enumerate(B):
            pe = ease(max(0, min(1, pb*len(B)-i*0.6))); v = (a+(b-a)*pm)*pe; w = int((W-x0-360)*v/mx)
            d.text((120, y+18), lab, font=lf, fill=GR)
            d.rectangle([x0, y, x0+max(w, 14), y+86], fill=YEL if b >= a else DOWN)
            if pm > 0 and a != b and pm < 1: d.rectangle([x0+int((W-x0-360)*a/mx), y-6, x0+int((W-x0-360)*a/mx)+4, y+92], fill=HI)
            ci = {**c, "decimals": 0} if all(float(q).is_integer() for bb in B for q in bb[1:]) and "decimals" not in c else c
            d.text((x0+25+max(w, 14), y+14), fmt(round(v) if ci is not c else v, ci), font=vf, fill=WH); y += gap
        # period badge: from -> to (slides)
        lab_ = c.get("to") if pm >= 0.5 else c.get("from"); 
        if lab_:
            tw = d.textlength(lab_, font=bf); bx = W-tw-220; by = 110; flip = abs(pm-0.5) < 0.5 and 0 < pm < 1
            col = _fill_blend(YEL, WH, 0) if pm >= 0.5 else TL_DIM
            d.rounded_rectangle([bx, by, bx+tw+56, by+90], 16, fill=col); d.text((bx+28, by+10), lab_, font=bf, fill=SEA)
            if t > tm+md+0.6 and B and B[0][1]:  # change label under the badge
                ch = c.get("change_label")
                if ch: d.text((bx+28, by+105), ch, font=MF(34, 700), fill=YEL)
        im.convert("RGB").save(f"{d_out}/{k:04d}.png")
    return [tb, tb+0.6, tm, tm+md, tm+md+0.6]

# ---------------- tilt (2.5D plane) post-process ----------------
def tilt_dir(d_out, D, opt=True, W=1920, H=1080):
    """Re-render every frame in d_out on a tilted plane: tilt eases deg0 -> deg1 (default 22 -> 14 deg) with ~5 % scale
    drift and a slight sideways yaw, over a darker vignetted backdrop. opt: true | {"deg": [22, 14], "drift": 0.05, "yaw": 4}."""
    import cv2, numpy as np, glob
    o = opt if isinstance(opt, dict) else {}; dg = o.get("deg", [22, 14]); dg = dg if isinstance(dg, list) else [dg, max(8, dg-8)]
    drift = o.get("drift", 0.05); yaw = o.get("yaw", 4.0); fs = sorted(glob.glob(f"{d_out}/*.png")); n = len(fs)
    yy, xx = np.mgrid[0:H, 0:W]; r = np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)
    bg = np.zeros((H, W, 3), np.float32); base = np.array(SEA[::-1], np.float32)*0.55
    bg[:] = base; bg *= (1-0.5*np.clip(r-0.3, 0, 1))[..., None]; bg = bg.astype(np.uint8)
    cache = {}
    for k, f in enumerate(fs):
        p = _ease_io(k/max(1, n-1)); th = math.radians(dg[0]+(dg[1]-dg[0])*p); ya = math.radians(yaw*(1-2*p)); s = 0.86*(1+drift*p)
        fl = 2.2*W; pts = []
        for (x, y) in ((-W/2, -H/2), (W/2, -H/2), (W/2, H/2), (-W/2, H/2)):
            y1 = y*math.cos(th); z1 = -y*math.sin(th)          # top edge leans away from camera
            x2 = x*math.cos(ya)+z1*math.sin(ya); z2 = -x*math.sin(ya)+z1*math.cos(ya)
            pts.append((W/2+s*x2*fl/(fl+z2), H/2+40+s*y1*fl/(fl+z2)))
        M = cv2.getPerspectiveTransform(np.float32([(0, 0), (W, 0), (W, H), (0, H)]), np.float32(pts))
        rp = os.path.realpath(f); st = os.stat(f).st_ino
        src = cv2.imread(f); out = bg.copy()
        warped = cv2.warpPerspective(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        mask = cv2.warpPerspective(np.full((H, W), 255, np.uint8), M, (W, H))
        sh = cv2.resize(cv2.GaussianBlur(cv2.resize(mask, (W//4, H//4)), (0, 0), 7), (W, H))
        out = cv2.multiply(out, cv2.cvtColor(255-(sh*0.6).astype(np.uint8), cv2.COLOR_GRAY2BGR), scale=1/255)
        np.copyto(out, warped, where=(mask > 127)[..., None])
        cv2.polylines(out, [np.int32(pts)], True, tuple(int(v) for v in TILT_EDGE[::-1]), 2, cv2.LINE_AA)
        tmp = f+".t.png"; cv2.imwrite(tmp, out); os.replace(tmp, f)   # replaces hard links with real files
    return n

# ---------------- punch word (opt-in) ----------------
def punch_png(path, word, prog, W=1920, H=1080):
    """Centre-screen punch word: footage dimmed 40 %, heavy white word (numbers yellow), scale 1.15 -> 1.0 ease-out (<= 0.3 s)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if word:
        p = ease(prog/0.3); im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(102*p))))
        f = MF(190, 900); d = ImageDraw.Draw(im)
        while d.textlength(word, font=f) > W-300: f = MF(f.size-10, 900)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); tw = d.textlength(word, font=f)
        import re as _r
        shadow(L, ((W-tw)/2, H/2-f.size*0.62), word, f, fill=YEL if _r.search(r"[0-9]", word) else OV, r=8)
        sc = 1.15-0.15*p
        if sc != 1: L2 = L.resize((int(W*sc), int(H*sc)), Image.LANCZOS); L = L2.crop((int((L2.width-W)/2), int((L2.height-H)/2), int((L2.width-W)/2)+W, int((L2.height-H)/2)+H))
        L.putalpha(L.getchannel("A").point(lambda a_: int(a_*min(1, p*1.4)))); im.alpha_composite(L)
    im.save(path)

# ---------------- end screen overlay ----------------
def endscreen_png(path, es, prog, W=1920, H=1080, logo=None):
    """20 s end screen over dimmed footage: a 16:9 'watch next' slot (left) where YouTube's video element goes, plus a
    subscribe slot (right). es = {"video": "earlier video title", "line": "Watch next"}."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); a = ease(prog/0.6)
    im.alpha_composite(Image.new("RGBA", (W, H), (4, 6, 12, int(150*a)))); d = ImageDraw.Draw(im)
    vx, vy, vw, vh = 170, 300, 880, 495; off = int(40*(1-a))
    d.rounded_rectangle([vx-off, vy, vx+vw-off, vy+vh], 20, fill=(10, 14, 24, int(200*a)), outline=CREAM+(int(255*a),), width=5)
    d.text((vx-off, vy-78), es.get("line", "WATCH NEXT").upper(), font=MF(44, 800), fill=YEL+(int(255*a),))
    tf = MF(52, 800); L = wrap(d, es.get("video", ""), tf, vw-120)[:3]; y = vy+vh/2-len(L)*32
    for l_ in L: d.text((vx-off+(vw-d.textlength(l_, font=tf))/2, y), l_, font=tf, fill=OV+(int(255*a),)); y += 64
    cx, cy, rr = 1440+off, vy+vh/2, 190
    d.ellipse([cx-rr, cy-rr, cx+rr, cy+rr], outline=CREAM+(int(255*a),), width=5, fill=(10, 14, 24, int(200*a)))
    if logo is not None:
        lg = logo.copy(); lg.putalpha(lg.getchannel("A").point(lambda v: int(v*a))); im.alpha_composite(lg, (int(cx-lg.width/2), int(cy-lg.height/2-30)))
    sf = MF(40, 800); tw = d.textlength("SUBSCRIBE", font=sf); d.text((cx-tw/2, cy+rr+30), "SUBSCRIBE", font=sf, fill=YEL+(int(255*a),))
    im.save(path)

# ---------------- clip luma (near-black guard) ----------------
_LUMA = {}
def clip_luma(path, ss, dur):
    """Mean luma 0-1 of 3 frames across [ss, ss+dur] (cached)."""
    k = (path, round(ss, 1), round(dur, 1))
    if k in _LUMA: return _LUMA[k]
    import cv2
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 30; vals = []
    for u in (0.15, 0.5, 0.85):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int((ss+dur*u)*fps)); ok, fr = cap.read()
        if ok: vals.append(float(cv2.cvtColor(cv2.resize(fr, (64, 36)), cv2.COLOR_BGR2GRAY).mean())/255)
    cap.release(); _LUMA[k] = sum(vals)/len(vals) if vals else 0.5; return _LUMA[k]

def measure_changes(path, thr=15/255, spacing=0.75):
    """Study-3 metric on a rendered file: visual-change events (mean abs frame diff > 15/255 at 4 fps, 64x36 grey,
    events >= 0.75 s apart). -> (events/min, longest gap s, gap start s, n events)."""
    import subprocess, numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=4,scale=64:36,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 36, 64).astype(np.float32); d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))/255
    t = (np.arange(len(d))+1)/4; ev = []
    for i in np.where(d > thr)[0]:
        if not ev or t[i]-ev[-1] >= spacing: ev.append(float(t[i]))
    dur = len(a)/4; b = [0.0]+ev+[dur]; g = np.diff(b); k = int(np.argmax(g))
    return round(len(ev)/dur*60, 1), round(float(g[k]), 1), round(b[k], 1), len(ev)

# ---------------- v8 end card (minimal, monochrome) ----------------
def endcard_frames(c, D, d_out, W=1920, H=1080, logo=None):
    """v8 ending card (user 2026-10-29 disliked the long v7 end block): black, logo + wordmark, a thin white rule, and two
    quiet slots where YouTube's end-screen elements sit (left: 16:9 video, right: subscribe circle). No VO.
    c = {"dur": 10, "line": "Watch next", "video": optional title text inside the slot, "slots": true}.
    Slots: video x 250-1050, y 400-850 (800x450); subscribe circle centre (1470, 625) r 150. Everything eases in over ~1.2 s,
    then the card holds with a very slow 2 % push (YouTube elements cover the slots)."""
    os.makedirs(d_out, exist_ok=True); n = int(D*FPS)+1; brand = c.get("brand", "ROTATION")
    f = MF(64, 800); lf = MF(26, 700); tf = MF(40, 800)
    base_logo = logo
    for k in range(n):
        t = k/FPS; a1 = ease(t/0.7); a2 = ease((t-0.45)/0.7); a3 = ease((t-0.8)/0.7); fo = 1.0
        im = Image.new("RGBA", (W, H), (6, 6, 7, 255)); d = ImageDraw.Draw(im)
        # logo + wordmark, centred, top
        tw = d.textlength(brand, font=f); lw = base_logo.width if base_logo is not None else 0; gap = 22; tot = lw+gap+tw; x0 = (W-tot)/2; y0 = 150+int(18*(1-a1))
        if base_logo is not None:
            lg = base_logo.copy(); lg.putalpha(lg.getchannel("A").point(lambda v: int(v*a1))); im.alpha_composite(lg, (int(x0), int(y0+6)))
        d.text((x0+lw+gap, y0), brand, font=f, fill=(255, 255, 255, int(255*a1)))
        rw = int(560*a2); d.rectangle([(W-rw)//2, 278, (W+rw)//2, 279], fill=(255, 255, 255, int(200*a2)))
        if c.get("slots", True):
            al = int(255*a3); off = int(26*(1-a3))
            vx0, vy0, vx1, vy1 = 250, 400+off, 1050, 850+off
            d.rounded_rectangle([vx0, vy0, vx1, vy1], 10, outline=(255, 255, 255, int(al*0.85)), width=2, fill=(16, 16, 18, al))
            ln = c.get("line", "Watch next").upper(); d.text((vx0, vy0-46), ln, font=lf, fill=(150, 150, 154, al))
            if c.get("video"):
                L = wrap(d, c["video"], tf, 680)[:3]; yy = (vy0+vy1)/2-len(L)*26
                for l_ in L: d.text(((vx0+vx1)/2-d.textlength(l_, font=tf)/2, yy), l_, font=tf, fill=(235, 235, 238, al)); yy += 52
            cx, cy, rr = 1470, 625+off, 150
            d.ellipse([cx-rr, cy-rr, cx+rr, cy+rr], outline=(255, 255, 255, int(al*0.85)), width=2, fill=(16, 16, 18, al))
            if base_logo is not None:
                sl = base_logo.resize((int(base_logo.width*1.5), int(base_logo.height*1.5)), Image.LANCZOS); sl.putalpha(sl.getchannel("A").point(lambda v: int(v*a3)))
                im.alpha_composite(sl, (int(cx-sl.width/2), int(cy-sl.height/2)))
            st = "SUBSCRIBE"; d.text((cx-d.textlength(st, font=lf)/2, cy+rr+22), st, font=lf, fill=(150, 150, 154, al))
        sc = 1.0+0.02*_ease_io(t/D)
        out = im.convert("RGB")
        if sc > 1.0005:
            big = out.resize((int(W*sc), int(H*sc)), Image.BICUBIC); ox, oy = (big.width-W)//2, (big.height-H)//2; out = big.crop((ox, oy, ox+W, oy+H))
        out.save(f"{d_out}/{k:04d}.png")
    return [0.0, 0.45, 0.8]

def blend_in(d_out, prev_png, nfr=10, W=1920, H=1080):
    """v8 transition into a full-screen graphic: the previous scene's last frame scales up 1.00->1.06 and fades while the
    graphic settles from 0.97->1.00 (a soft push-through instead of a hard cut). Rewrites the first nfr frames."""
    import glob
    fs = sorted(glob.glob(f"{d_out}/*.png"))[:nfr]
    if not fs or not os.path.exists(prev_png): return 0
    pv = Image.open(prev_png).convert("RGB").resize((W, H), Image.LANCZOS)
    for k, f in enumerate(fs):
        e = _ease_io((k+1)/(nfr+1)); a = Image.open(f).convert("RGB")
        s1 = 1.0+0.06*e; b1 = pv.resize((int(W*s1), int(H*s1)), Image.BICUBIC); ox, oy = (b1.width-W)//2, (b1.height-H)//2; b1 = b1.crop((ox, oy, ox+W, oy+H))
        s2 = 0.97+0.03*e; a2 = a.resize((int(W*s2), int(H*s2)), Image.BICUBIC); bg = Image.new("RGB", (W, H), a.getpixel((4, 4))); bg.paste(a2, ((W-a2.width)//2, (H-a2.height)//2))
        out = Image.blend(b1, bg, e); tmp = f+".b.png"; out.save(tmp); os.replace(tmp, f)
    return len(fs)

def measure_changes_v8(path, thr=20/255, frac=0.003, win=0.5):
    """Finer 'visible change' metric (v8): within every 0.5 s step, does >= 0.3 % of a 160x90 grey frame change by > 20/255?
    Catches moving dots, drawing lines and counters that the study-3 metric (global mean diff) misses.
    -> (longest gap s, gap start s)."""
    import subprocess, numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={1/win},scale=160:90,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 90, 160).astype(np.float32)/255
    ch = (np.abs(np.diff(a, axis=0)) > thr).mean(axis=(1, 2)) > frac
    t = (np.arange(len(ch))+1)*win; ev = [0.0]+[float(x) for x in t[ch]]+[len(a)*win]; g = np.diff(ev); k = int(np.argmax(g))
    return round(float(g[k]), 1), round(ev[k], 1)


# ---------------- v9 subtle panel texture (optional, monochrome) ----------------
def panel_texture(path, W=1920, H=1080, alpha=13, seed=7):
    """Faint topographic contour lines + fine grain, white at very low alpha, for full-screen graphic panels (Study 5:
    WSJ/CNBC give every graphic one textured 'world'). Written once and overlaid by ffmpeg."""
    if os.path.exists(path): return path
    import numpy as np
    rng = np.random.default_rng(seed); h, w = H//6, W//6; f = np.zeros((h, w))
    for k in range(2, 5):
        sc = 2**k; n_ = rng.standard_normal((h//sc+2, w//sc+2))
        f += np.array(Image.fromarray(((n_-n_.min())/(np.ptp(n_)+1e-9)*255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32)/255*(0.5**(4-k))
    f = np.array(Image.fromarray((f/f.max()*255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(14)), np.float32)/255
    lines = (np.abs(((f*9) % 1.0) - 0.5) > 0.482).astype(np.float32)          # iso-lines every 1/14 of the field
    grain = rng.random((H, W)).astype(np.float32)
    a = np.clip(lines*alpha + (grain > 0.5)*3, 0, 255).astype(np.uint8)
    im = Image.new("RGBA", (W, H), (255, 255, 255, 0)); im.putalpha(Image.fromarray(a)); im.save(path); return path
