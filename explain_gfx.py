"""Rotation Explains graphics (new series, 2026-10-30). TLDR-Business-style explainer devices in the Rotation brand:
single accent = brand orange #FA4E02 on cream #F8F1E4 / off-white, near-black text, Poppins / Montserrat (no serif, no yellow).
Everything is drawn natively at 2560x1440 (no upscaling). Each device is a class with .frame(t) -> PIL RGBA image.
Opaque devices (doc, bars, tiles, split, section) fill the frame; overlay devices (keyword card over footage, flow, quote,
lower third, pops, headline, stat, agenda, title card) return transparent RGBA laid over (darkened) footage.
Used only by make_explain.py; no other renderer imports it."""
import math, os, re, html
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 2560, 1440
OR = (250, 78, 2); CREAM = (248, 241, 228); OFF = (250, 247, 242); INK = (17, 17, 17); GREY = (112, 106, 98)
LGREY = (222, 215, 203); DARK = (21, 20, 19); WHITE = (255, 255, 255); OR_L = (255, 206, 178)
FD = "/workspace/work/yt/fonts"
_fc = {}
def F(size, kind="x", wg=800):
    """kind: x = Poppins ExtraBold, s = Poppins SemiBold, m = Montserrat VF at weight wg."""
    k = (size, kind, wg)
    if k not in _fc:
        if kind == "x": f = ImageFont.truetype(f"{FD}/Poppins-ExtraBold.ttf", size)
        elif kind == "s": f = ImageFont.truetype(f"{FD}/Poppins-SemiBold.ttf", size)
        else: f = ImageFont.truetype(f"{FD}/Montserrat-VF.ttf", size); f.set_variation_by_axes([wg])
        _fc[k] = f
    return _fc[k]

def cl(p): return max(0.0, min(1.0, p))
def eo4(p): p = cl(p); return 1-(1-p)**4
def eio(p): p = cl(p); return 4*p*p*p if p < 0.5 else 1-(-2*p+2)**3/2
def back(p, s=1.9):
    p = cl(p); p -= 1; return 1 + (s+1)*p*p*p + s*p*p
def lerp(a, b, p): return a+(b-a)*p
def rgba(c, a=1.0): return tuple(c[:3]) + (int(255*cl(a)),)

def spaced(d, xy, text, font, fill, track=0.12, anchor="l"):
    """Letter-spaced caps text. anchor l / c / r. Returns width."""
    sp = font.size*track; ws = [d.textlength(ch, font=font) for ch in text]; tw = sum(ws)+sp*(len(text)-1)
    x, y = xy
    if anchor == "c": x -= tw/2
    elif anchor == "r": x -= tw
    for ch, w in zip(text, ws): d.text((x, y), ch, font=font, fill=fill); x += w+sp
    return tw

def spaced_w(d, text, font, track=0.12): return sum(d.textlength(ch, font=font) for ch in text)+font.size*track*(len(text)-1)

def wrap(d, text, font, maxw):
    L = [""]
    for w in text.split():
        x = (L[-1]+" "+w).strip()
        if d.textlength(x, font=font) > maxw and L[-1]: L.append(w)
        else: L[-1] = x
    return L

def fit_font(d, lines_text, kind, size, maxw, maxlines, minsize=40, wg=800):
    while size > minsize:
        f = F(size, kind, wg); L = wrap(d, lines_text, f, maxw)
        if len(L) <= maxlines: return f, L
        size -= 4
    f = F(minsize, kind, wg); return f, wrap(d, lines_text, f, maxw)

_shc = {}
def _paste_clip(im, lay, x, y):
    cx0, cy0 = max(0, -x), max(0, -y); cut = lay.crop((cx0, cy0, lay.width, lay.height))
    if cut.width > 0 and cut.height > 0: im.alpha_composite(cut, (max(0, x), max(0, y)))

def shadow(im, box, r=28, a=70, off=(0, 14), radius=24):
    """Soft drop shadow, blurred on a local layer only (cached by geometry)."""
    x0, y0, x1, y1 = [int(v) for v in box]; m = 3*r; a = int(a)
    key = (x1-x0, y1-y0, r, a, radius)
    if key not in _shc:
        lay = Image.new("RGBA", (x1-x0+2*m, y1-y0+2*m), (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle([m, m, m+x1-x0, m+y1-y0], radius, fill=(0, 0, 0, a))
        _shc[key] = lay.filter(ImageFilter.GaussianBlur(r))
        if len(_shc) > 400: _shc.clear()
    _paste_clip(im, _shc[key], x0-m+off[0], y0-m+off[1])

_tsc = {}
def text_shadow(im, xy, t, f, fill, r=6, a=170):
    """Text with a soft shadow; the blur runs on a small local layer (cached per text/font/alpha step)."""
    a = int(a)
    if a >= 8:
        key = (t, f.size, f.path if hasattr(f, "path") else id(f), r, a // 16)
        if key not in _tsc:
            l, tp, rr, bt = ImageDraw.Draw(im).textbbox((0, 0), t, font=f); m = 3*r
            lay = Image.new("RGBA", (rr-l+2*m+6, bt-tp+2*m+8), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((m-l+3, m-tp+5), t, font=f, fill=(0, 0, 0, (a//16)*16)); _tsc[key] = (lay.filter(ImageFilter.GaussianBlur(r)), l, tp, m)
            if len(_tsc) > 800: _tsc.clear()
        lay, l, tp, m = _tsc[key]; _paste_clip(im, lay, int(xy[0]+l-m), int(xy[1]+tp-m))
    ImageDraw.Draw(im).text(xy, t, font=f, fill=fill)

_grain = None
def grain():
    """Very faint paper texture for the cream panels (fixed seed, cached)."""
    global _grain
    if _grain is None:
        import random
        rnd = random.Random(7); g = Image.effect_noise((W//4, H//4), 18).resize((W, H), Image.BICUBIC)
        _grain = g.point(lambda v: int(abs(v-128)*0.5))
    return _grain

def panel(color=CREAM, tex=True):
    im = Image.new("RGBA", (W, H), rgba(color))
    if tex:
        g = grain(); dark = Image.new("RGBA", (W, H), (60, 40, 20, 0)); dark.putalpha(g.point(lambda v: min(255, v//3)))
        im.alpha_composite(dark)
    return im

def footer(im, title, source, a=1.0, y=1352):
    """Chart / document footer bar: near-black bar, chart title left (cream), source right (light grey)."""
    d = ImageDraw.Draw(im); d.rectangle([0, y, W, H], fill=rgba(INK, a))
    d.rectangle([0, y, 14, H], fill=rgba(OR, a))
    d.text((70, y+22), title, font=F(36, "s"), fill=rgba(CREAM, a))
    f = F(30, "m", 600); d.text((W-70-d.textlength(source, font=f), y+27), source, font=f, fill=rgba((190, 184, 174), a))

def arrow_head(d, p_end, p_prev, size, fill):
    ang = math.atan2(p_end[1]-p_prev[1], p_end[0]-p_prev[0])
    pts = [p_end, (p_end[0]-size*math.cos(ang-0.45), p_end[1]-size*math.sin(ang-0.45)),
           (p_end[0]-size*math.cos(ang+0.45), p_end[1]-size*math.sin(ang+0.45))]
    d.polygon(pts, fill=fill)

def bezier(p0, p1, p2, n=60):
    return [((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0], (1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]) for t in [i/n for i in range(n+1)]]

def draw_curve(im, pts, prog, color, width=8, head=34, ss=2):
    """Draw-on curve with arrowhead (antialiased via 2x supersampling of the bounding box)."""
    if prog <= 0: return
    k = max(2, int(len(pts)*cl(prog))); P = pts[:k]
    xs = [p[0] for p in P]; ys = [p[1] for p in P]; pad = head+width+6
    x0, y0, x1, y1 = int(min(xs)-pad), int(min(ys)-pad), int(max(xs)+pad), int(max(ys)+pad)
    lay = Image.new("RGBA", ((x1-x0)*ss, (y1-y0)*ss), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    Q = [((x-x0)*ss, (y-y0)*ss) for x, y in P]
    d.line(Q, fill=color, width=width*ss, joint="curve")
    r = width*ss/2
    for q in (Q[0], Q[-1]): d.ellipse([q[0]-r, q[1]-r, q[0]+r, q[1]+r], fill=color)
    if prog >= 0.98 and head: arrow_head(d, Q[-1], Q[-4] if len(Q) > 4 else Q[0], head*ss, color)
    lay = lay.resize((x1-x0, y1-y0), Image.LANCZOS); im.alpha_composite(lay, (x0, y0))

def draw_ring(im, box, prog, color, width=9, start=-200, ss=2):
    """Hand-drawn style circle around a box: arc draws on from `start` over ~380 deg."""
    if prog <= 0: return
    x0, y0, x1, y1 = [int(v) for v in box]; pad = width+4
    lay = Image.new("RGBA", ((x1-x0+2*pad)*ss, (y1-y0+2*pad)*ss), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    end = start + 380*cl(prog)
    d.arc([pad*ss, pad*ss, (x1-x0+pad)*ss, (y1-y0+pad)*ss], start, end, fill=color, width=width*ss)
    lay = lay.resize((x1-x0+2*pad, y1-y0+2*pad), Image.LANCZOS); im.alpha_composite(lay, (x0-pad, y0-pad))

def aa_ellipse(im, box, fill, ss=3, outline=None, width=0):
    x0, y0, x1, y1 = [int(v) for v in box]
    lay = Image.new("RGBA", ((x1-x0+4)*ss, (y1-y0+4)*ss), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.ellipse([2*ss, 2*ss, (x1-x0+2)*ss, (y1-y0+2)*ss], fill=fill, outline=outline, width=width*ss)
    im.alpha_composite(lay.resize((x1-x0+4, y1-y0+4), Image.LANCZOS), (x0-2, y0-2))

# ------------------------------------------------------------------ icons (drawn in code, ink on white circles)
def icon(d, name, cx, cy, s, col=INK, w=None):
    """Simple line pictograms, size s ~ half-width."""
    w = w or max(6, int(s*0.11))
    if name == "cash":   # banknote stack
        for k in (1, 0):
            o = k*s*0.22
            d.rounded_rectangle([cx-s+o, cy-s*0.55-o, cx+s+o, cy+s*0.55-o], int(s*0.12), outline=col, width=w, fill=WHITE)
        d.ellipse([cx-s*0.27, cy-s*0.27, cx+s*0.27, cy+s*0.27], outline=col, width=w)
    elif name == "server":   # rack with 3 units
        d.rounded_rectangle([cx-s*0.75, cy-s, cx+s*0.75, cy+s], int(s*0.1), outline=col, width=w)
        for k in range(3):
            y = cy-s+s*0.18+k*s*0.6; d.rounded_rectangle([cx-s*0.55, y, cx+s*0.55, y+s*0.42], int(s*0.06), outline=col, width=max(4, w-2))
            d.ellipse([cx+s*0.3, y+s*0.15, cx+s*0.42, y+s*0.27], fill=col)
    elif name == "down":   # falling trend line with arrow
        P = [(cx-s, cy-s*0.6), (cx-s*0.35, cy+s*0.05), (cx+s*0.05, cy-s*0.3), (cx+s*0.8, cy+s*0.6)]
        d.line(P, fill=col, width=w+2, joint="curve"); arrow_head(d, (cx+s*0.95, cy+s*0.75), P[-2], s*0.5, col)
    elif name == "up":
        P = [(cx-s, cy+s*0.6), (cx-s*0.35, cy-s*0.05), (cx+s*0.05, cy+s*0.3), (cx+s*0.8, cy-s*0.6)]
        d.line(P, fill=col, width=w+2, joint="curve"); arrow_head(d, (cx+s*0.95, cy-s*0.75), P[-2], s*0.5, col)
    elif name == "chip":
        d.rounded_rectangle([cx-s*0.6, cy-s*0.6, cx+s*0.6, cy+s*0.6], int(s*0.1), outline=col, width=w)
        d.rectangle([cx-s*0.25, cy-s*0.25, cx+s*0.25, cy+s*0.25], fill=col)
        for k in range(4):
            o = -s*0.42+k*s*0.28
            for (a, b, c_, e) in ((cx+o, cy-s*0.6, cx+o, cy-s*0.95), (cx+o, cy+s*0.6, cx+o, cy+s*0.95), (cx-s*0.6, cy+o, cx-s*0.95, cy+o), (cx+s*0.6, cy+o, cx+s*0.95, cy+o)):
                d.line([(a, b), (c_, e)], fill=col, width=max(4, w-2))
    elif name == "building":
        d.rectangle([cx-s*0.8, cy-s*0.4, cx+s*0.8, cy+s*0.85], outline=col, width=w)
        d.polygon([(cx-s*0.95, cy-s*0.4), (cx, cy-s*0.95), (cx+s*0.95, cy-s*0.4)], outline=col, width=w)
        for k in range(3): d.rectangle([cx-s*0.55+k*s*0.4, cy-s*0.05, cx-s*0.35+k*s*0.4, cy+s*0.6], fill=col)
    elif name == "search":
        d.ellipse([cx-s*0.75, cy-s*0.75, cx+s*0.25, cy+s*0.25], outline=col, width=w+2)
        d.line([(cx+s*0.12, cy+s*0.12), (cx+s*0.85, cy+s*0.85)], fill=col, width=w+6)
    elif name == "cloud":
        for (ox, oy, r) in ((-0.42, 0.12, 0.42), (0.05, -0.18, 0.55), (0.5, 0.15, 0.4)):
            d.ellipse([cx+(ox-r)*s, cy+(oy-r)*s, cx+(ox+r)*s, cy+(oy+r)*s], fill=col)
        d.rectangle([cx-s*0.42, cy+s*0.1, cx+s*0.5, cy+s*0.55], fill=col)
    elif name == "car":
        d.rounded_rectangle([cx-s, cy-s*0.1, cx+s, cy+s*0.5], int(s*0.2), outline=col, width=w)
        d.polygon([(cx-s*0.6, cy-s*0.1), (cx-s*0.35, cy-s*0.6), (cx+s*0.4, cy-s*0.6), (cx+s*0.65, cy-s*0.1)], outline=col, width=w)
        for ox in (-0.55, 0.55): d.ellipse([cx+ox*s-s*0.22, cy+s*0.35, cx+ox*s+s*0.22, cy+s*0.79], fill=col)

def magnifier(im, cx, cy, r, a=1.0):
    d = ImageDraw.Draw(im)
    aa_ellipse(im, [cx-r, cy-r, cx+r, cy+r], fill=(255, 255, 255, int(70*a)), outline=rgba(INK, a), width=max(8, r//7))
    ang = math.radians(45); x0, y0 = cx+r*math.cos(ang)*0.95, cy+r*math.sin(ang)*0.95
    d.line([(x0, y0), (x0+r*0.9, y0+r*0.9)], fill=rgba(INK, a), width=max(14, r//4))

# ================================================================== devices
class Doc:
    """Document zoom: whole-document thumbnail (left) + zoomed page (right). Orange highlight bar sweeps across the row,
    hand-drawn orange ring around the number, curved arrow + caps callout. Optional magnifier intro on the thumbnail.
    c = {page_png, bbox_html, target (exact token, e.g. "(51,355)"), extra_rings [tokens], callout, title, source,
         thumb_label, page_no, cues {hl, ring, callout}, dur}"""
    def __init__(self, c, cues, dur):
        self.c = c; self.cues = cues; self.dur = dur
        self.page = Image.open(c["page_png"]).convert("RGB"); self.pw = float(c.get("page_w_pt", 612.0)); self.ph = float(c.get("page_h_pt", 792.0)); self.k = self.page.width/self.pw   # px per pt
        words = []
        for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', open(c["bbox_html"]).read()):
            words.append((float(m[1]), float(m[2]), float(m[3]), float(m[4]), html.unescape(m[5])))
        tgt = [w for w in words if w[4] == c["target"]]
        if c.get("target_n"): tgt = tgt[c["target_n"]:]
        self.t = tgt[0]
        row = [w for w in words if abs((w[1]+w[3])/2-(self.t[1]+self.t[3])/2) < 3]
        self.row = (min(w[0] for w in row), min(w[1] for w in row), max(w[2] for w in row), max(w[3] for w in row))
        self.rings = [self.t] + [next(w for w in words if w[4] == tok and abs(w[1]-self.t[1]) < 40) for tok in c.get("extra_rings", [])]
        th_h = 700; self.thumb = self.page.resize((int(self.page.width*th_h/self.page.height), th_h), Image.LANCZOS)
        self.PX, self.PY, self.PW, self.PH = 760, 96, 1700, 1180   # zoom panel
        self.cw0, self.cw1 = c.get("crop_w", [520, 460]); anc = c.get("anchor", "left")
        if anc == "left": self.cx = self.row[0]-10+self.cw1/2
        elif anc == "right": self.cx = self.row[2]+10-self.cw1/2
        else: self.cx = c.get("cx_pt", (self.row[0]+self.row[2])/2)
        self.cy = (self.row[1]+self.row[3])/2
        self.base = panel(CREAM)

    def crop_geom(self, t):
        cw = lerp(self.cw0, self.cw1, eio(t/self.dur)); ch = cw*self.PH/self.PW
        cx = min(max(self.cx, cw/2), self.pw-cw/2); cy = min(max(self.cy - ch*0.06, ch/2), self.ph-ch/2)
        return cx-cw/2, cy-ch/2, cw, ch

    def frame(self, t):
        c = self.c; cu = self.cues; im = self.base.copy(); d = ImageDraw.Draw(im)
        a_in = eo4(t/0.55)
        # --- left: document thumbnail stack (whole page) ---
        tx, ty = 130, 250; tw, th = self.thumb.size
        for k in (2, 1):
            shadow(im, (tx+k*22, ty-k*22, tx+tw+k*22, ty+th-k*22), r=18, a=40, radius=4)
            d.rectangle([tx+k*22, ty-k*22, tx+tw+k*22, ty+th-k*22], fill=(244, 242, 238), outline=(214, 208, 198), width=2)
        shadow(im, (tx, ty, tx+tw, ty+th), r=18, a=60, radius=4); im.paste(self.thumb, (tx, ty))
        d.rectangle([tx, ty, tx+tw, ty+th], outline=(200, 194, 184), width=2)
        s = th/self.ph; x0, y0, cw, ch = self.crop_geom(t)
        d.rectangle([tx+x0*s, ty+y0*s, tx+(x0+cw)*s, ty+(y0+ch)*s], outline=rgba(OR, a_in), width=5)
        lab = c.get("thumb_label", ""); f = F(28, "m", 800); yl = ty+th+44
        for l in wrap(d, lab.upper(), f, tw-20) if lab else []: spaced(d, (tx, yl), l, f, rgba(INK), 0.08); yl += 40
        if c.get("page_no"): spaced(d, (tx, yl+6), c["page_no"].upper(), F(26, "m", 600), rgba(GREY), 0.1)
        # magnifier intro over the thumbnail
        if t < 1.25:
            pm = eio(t/0.9); mx = lerp(tx+tw*0.2, tx+(self.t[0]+self.t[2])/2*s, pm); my = lerp(ty+th*0.15, ty+self.cy*s, pm)
            magnifier(im, mx, my, 70, a=1-cl((t-0.9)/0.35))
        # --- right: zoomed page panel ---
        sc = lerp(0.94, 1.0, a_in); pw, ph = int(self.PW*sc), int(self.PH*sc); px = int(self.PX+(self.PW-pw)/2); py = int(self.PY+(self.PH-ph)/2)
        k = self.k; crop = self.page.crop((int(x0*k), int(y0*k), int((x0+cw)*k), int((y0+ch)*k))).resize((pw, ph), Image.BICUBIC).convert("RGBA")
        m = pw/cw
        def P(xp, yp): return ((xp-x0)*m, (yp-y0)*m)
        # highlight bar (multiply) sweeping left -> right
        ph_ = eo4((t-cu["hl"])/0.6)
        r0 = P(self.row[0]-6, self.row[1]-3.2); r1 = P(self.row[2]+6, self.row[3]+3.2)
        if ph_ > 0:
            xe = lerp(r0[0], r1[0], ph_); box = (int(max(0, r0[0])), int(r0[1]), int(min(pw, xe)), int(r1[1]))
            if box[2] > box[0]:
                reg = crop.crop(box); tint = Image.new("RGBA", reg.size, OR_L+(255,)); crop.paste(ImageChops.multiply(reg, tint), box[:2])
            # veil the rest of the page so the row pops
            veil = Image.new("RGBA", (pw, ph), (255, 255, 255, int(120*ph_))); vd = ImageDraw.Draw(veil)
            vd.rectangle([0, int(r0[1])-2, pw, int(r1[1])+2], fill=(0, 0, 0, 0)); crop.alpha_composite(veil)
        pim = crop; shadow(im, (px, py, px+pw, py+ph), r=30, a=int(80*a_in), radius=6)
        pim.putalpha(int(255*a_in)); im.alpha_composite(pim, (px, py))
        # rings around the number(s)
        for j, w_ in enumerate(self.rings):
            pr = eio((t-cu["ring"]-0.45*j)/0.7)
            if pr > 0:
                b0 = P(w_[0]-9, w_[1]-6); b1 = P(w_[2]+9, w_[3]+6)
                draw_ring(im, (px+b0[0], py+b0[1], px+b1[0], py+b1[1]), pr, rgba(OR), width=10)
        # callout + curved arrow
        pc = eo4((t-cu["callout"])/0.5)
        if pc > 0 and c.get("callout"):
            tb0 = P(self.t[0]-9, self.t[1]-6); tb1 = P(self.t[2]+9, self.t[3]+6)
            ring_cx, ring_top, ring_bot = px+(tb0[0]+tb1[0])/2, py+tb0[1], py+tb1[1]
            if "\n" in c["callout"]: f = F(c.get("callout_size", 76), "x"); L = c["callout"].upper().split("\n")
            else: f, L = fit_font(d, c["callout"].upper(), "x", 76, 1050, 2, 50)
            lh = int(f.size*1.12); bh = lh*len(L); bw = max(d.textlength(l, font=f) for l in L)
            below = (ring_top-py) < ph*0.5
            cx_ = px+90; cy_ = (ring_bot+150) if below else (ring_top-150-bh)
            cy_ = min(max(cy_, py+40), py+ph-bh-40)
            # cream backing plate for legibility
            pad = 26; d.rounded_rectangle([cx_-pad, cy_-pad+int(18*(1-pc)), cx_+bw+pad, cy_+bh+pad*0.6+int(18*(1-pc))], 14, fill=rgba(CREAM, 0.94*pc))
            for i, l in enumerate(L): d.text((cx_, cy_+i*lh+int(18*(1-pc))), l, font=f, fill=rgba(INK, pc))
            st = (cx_+bw+pad+10, cy_+bh*0.5); en = (ring_cx-(tb1[0]-tb0[0])*0.55, (ring_bot+18) if below else (ring_top-18))
            ctrl = ((st[0]+en[0])/2, st[1] if below else en[1]-0)
            ctrl = (en[0]-40, st[1]) if below else (en[0]-40, st[1])
            draw_curve(im, bezier(st, ctrl, en), eio((t-cu["callout"]-0.15)/0.6), rgba(OR), width=9, head=36)
        footer(im, c["title"], c["source"], a=1.0)
        return im

class Bars:
    """Flat bar chart on off-white, one bar at a time (value label pops), highlight bar orange, others near-black.
    c = {title, bars [[label, value, display]], ymax, ystep, prefix, suffix, source, annot {text, from, to}}"""
    def __init__(self, c, cues, dur):
        self.c = c; self.cues = cues; self.dur = dur; self.base = panel(OFF)
        d = ImageDraw.Draw(self.base); self.X0, self.X1, self.Y0, self.Y1 = 330, 2330, 250, 1180
        ymax = c["ymax"]; st = c["ystep"]; f = F(32, "m", 600)
        v = 0
        while v <= ymax+1e-6:
            y = self.Y(v); d.line([(self.X0, y), (self.X1, y)], fill=(226, 220, 210) if v else (60, 58, 55), width=2 if v else 4)
            lab = f"{c.get('prefix','')}{v:g}{c.get('suffix','')}"; d.text((self.X0-24-d.textlength(lab, font=f), y-22), lab, font=f, fill=GREY); v += st
        if c.get("y_label"): spaced(d, (self.X0-260, self.Y0-90), c["y_label"].upper(), F(26, "m", 800), GREY, 0.1)
        n = len(c["bars"]); self.slot = (self.X1-self.X0)/n; self.bw = self.slot*0.56
    def Y(self, v): return self.Y1 - (self.Y1-self.Y0)*v/self.c["ymax"]
    def frame(self, t):
        c = self.c; im = self.base.copy(); d = ImageDraw.Draw(im); n = len(c["bars"]); hl = c.get("highlight", n-1)
        for i, b in enumerate(c["bars"]):
            lab, val, disp = b[0], b[1], (b[2] if len(b) > 2 else f"{val}")
            cx = self.X0+self.slot*(i+0.5); p = eo4((t-self.cues[i])/0.6)
            fl = F(36, "m", 800); col = INK if p > 0 else (170, 164, 154)
            d.text((cx-d.textlength(lab, font=fl)/2, self.Y1+26), lab, font=fl, fill=col)
            if p <= 0: continue
            h = (self.Y1-self.Y(val))*p; colb = OR if i == hl else INK
            d.rectangle([cx-self.bw/2, self.Y1-h, cx+self.bw/2, self.Y1-2], fill=colb)
            q = back((t-self.cues[i]-0.3)/0.4)
            if q > 0:
                fv = F(int(60*max(0.2, q)), "x"); tw = d.textlength(disp, font=fv)
                d.text((cx-tw/2, self.Y1-h-24-fv.size*1.05), disp, font=fv, fill=OR if i == hl else INK)
        an = c.get("annot")
        if an:
            pa = eo4((t-self.cues[-1]-0.9)/0.6)
            if pa > 0:
                i0, i1 = an.get("from", 0), an.get("to", n-1)
                xa = self.X0+self.slot*(i0+0.5); xb = self.X0+self.slot*(i1+0.5)
                ya = self.Y(c["bars"][i0][1])-120; yb = self.Y(c["bars"][i1][1])-130
                top = min(ya, yb)-150
                draw_curve(im, bezier((xa, ya), ((xa+xb)/2, top), (xb-20, yb-20)), pa, rgba(OR), width=8, head=34)
                f = F(52, "x"); tw = d.textlength(an["text"], font=f); bx = (xa+xb)/2-tw/2; by = top+(yb-top)*0.12
                q = back((t-self.cues[-1]-1.2)/0.45)
                if q > 0:
                    pad = 26; d.rounded_rectangle([bx-pad, by-12, bx+tw+pad, by+f.size+18], 40, fill=rgba(OR))
                    d.text((bx, by-4), an["text"], font=f, fill=WHITE)
        footer(im, c["title"], c["source"])
        return im

class Keyword:
    """Huge keyword on brand orange (over footage at ~10 %), optional caps sub-line. c = {word, sub}"""
    def __init__(self, c, cues, dur): self.c = c; self.cues = cues; self.dur = dur
    def frame(self, t):
        c = self.c; im = Image.new("RGBA", (W, H), rgba(OR, 0.90*eo4(t/0.25))); d = ImageDraw.Draw(im)
        p = eo4(t/0.55); w = c["word"]; f0 = F(360, "x"); fit = min(1.0, (W*0.86)/max(1, d.textlength(w, font=f0)*1.12)); f = F(int(360*fit*lerp(1.12, 1.0, p)), "x"); tw = d.textlength(w, font=f)
        y = H/2-f.size*0.68 - (60 if c.get("sub") else 0)
        text_shadow(im, ((W-tw)/2, y), w, f, rgba(CREAM, p), r=10, a=int(60*p))
        if c.get("sub"):
            q = eo4((t-self.cues[0])/0.5); fs = F(64, "m", 800)
            rw = int(900*q); d.rectangle([(W-rw)/2, y+f.size*1.18, (W+rw)/2, y+f.size*1.18+8], fill=rgba(CREAM, q))
            spaced(d, (W/2, y+f.size*1.18+44+int(20*(1-q))), c["sub"].upper(), fs, rgba(INK, q), 0.16, "c")
        return im

class Split:
    """Two-part card: left orange share, right near-black share, proportional split that slides to the real ratio.
    c = {tag, left {label, value, pct}, right {label, value, pct}, source}"""
    def __init__(self, c, cues, dur): self.c = c; self.cues = cues; self.dur = dur
    def frame(self, t):
        c = self.c; im = Image.new("RGBA", (W, H), rgba(INK)); d = ImageDraw.Draw(im)
        L, R = c["left"], c["right"]; frac = L["pct"]/100.0
        p0 = eo4(t/0.6); p1 = eio((t-self.cues[0]+0.2)/0.8)
        xs = W*lerp(0.5, frac, p1)*p0 + 0*(1-p0)
        d.rectangle([0, 0, xs, H], fill=OR)
        def side(x0, x1, s, pv, col_txt, col_sub):
            if pv <= 0: return
            cx = (x0+x1)/2; f = F(int(250*lerp(0.8, 1, back(pv, 1.4))), "x"); val = f"{int(round(s['pct']*cl(pv/0.8)))}%"
            tw = d.textlength(val, font=f); d.text((cx-tw/2, 420), val, font=f, fill=rgba(col_txt, cl(pv*2)))
            fl, Ls = fit_font(d, s["label"], "x", 92, (x1-x0)-160, 2, 56)
            for i, l in enumerate(Ls): d.text((cx-d.textlength(l, font=fl)/2, 760+i*fl.size*1.1+int(30*(1-eo4(pv)))), l, font=fl, fill=rgba(col_txt, eo4(pv)))
            if s.get("sub"):
                fs = F(36, "m", 800); spaced(d, (cx, 760+len(Ls)*fl.size*1.1+40), s["sub"].upper(), fs, rgba(col_sub, eo4(pv)), 0.12, "c")
        side(0, xs, L, eo4((t-self.cues[0])/0.8), CREAM, INK)
        side(xs, W, R, eo4((t-self.cues[1])/0.8), CREAM, (170, 164, 154))
        if c.get("tag"):
            q = eo4((t-0.2)/0.5); ft = F(34, "m", 800); tw = spaced_w(d, c["tag"].upper(), ft, 0.14)
            d.rounded_rectangle([W/2-tw/2-40, 120, W/2+tw/2+40, 200], 40, fill=rgba(CREAM, q)); spaced(d, (W/2, 138), c["tag"].upper(), ft, rgba(INK, q), 0.14, "c")
        if c.get("source"):
            fs = F(28, "m", 600); d.text((70, H-70), c["source"], font=fs, fill=rgba((235, 225, 210), 0.9))
        return im

class Tiles:
    """Numbered tile cards that fill in one by one, focus dims the others, stamp badge for the key number.
    c = {title, tiles [{name, desc, value, delta, neg}], stamp {tile, text, cue}, source}"""
    def __init__(self, c, cues, dur):
        self.c = c; self.cues = cues; self.dur = dur; self.base = panel(CREAM)
        n = len(c["tiles"]); self.tw, self.th, gap = 640, 800, 90
        self.x0 = (W-(n*self.tw+(n-1)*gap))/2; self.gap = gap; self.y0 = 360
    def frame(self, t):
        c = self.c; im = self.base.copy(); d = ImageDraw.Draw(im); n = len(c["tiles"]); cu = self.cues
        if c.get("title"):
            q = eo4(t/0.5); spaced(d, (W/2, 120), c["title"].upper(), F(38, "m", 800), rgba(GREY, q), 0.16, "c")
        cur = max([i for i in range(n) if t >= cu[i]] or [-1]); unfocus = c.get("unfocus_t")
        for i, tl in enumerate(c["tiles"]):
            x = self.x0+i*(self.tw+self.gap); y = self.y0
            pin = back((t-0.12*i)/0.55, 1.3); 
            if pin <= 0: continue
            dim = 1.0
            if cur >= 0 and cur != i and t >= cu[i] and not (unfocus and t >= unfocus): dim = 0.42
            if t < cu[i] and cur >= 0: dim = 0.75
            yy = y+int(60*(1-cl(pin))); a = cl(pin)
            shadow(im, (x, yy, x+self.tw, yy+self.th), r=24, a=int(55*a), radius=36)
            d.rounded_rectangle([x, yy, x+self.tw, yy+self.th], 36, fill=rgba(WHITE, a))
            # number circle above the tile
            ccx, ccy, r = x+self.tw/2, yy-70, 50
            act = t >= cu[i]
            aa_ellipse(im, [ccx-r, ccy-r, ccx+r, ccy+r], fill=rgba(OR if act else (190, 182, 170), a))
            fn = F(54, "x"); d.text((ccx-d.textlength(str(i+1), font=fn)/2, ccy-fn.size*0.62), str(i+1), font=fn, fill=rgba(WHITE, a))
            pf = eo4((t-cu[i])/0.6)
            if pf > 0:
                al = pf*dim; ty = yy+70+int(24*(1-pf))
                fN = F(84, "x"); d.text((x+self.tw/2-d.textlength(tl["name"], font=fN)/2, ty), tl["name"], font=fN, fill=rgba(INK, al))
                fd_ = F(34, "m", 800); Ls = wrap(d, tl["desc"].upper(), fd_, self.tw-110)
                for j, l in enumerate(Ls[:4]): spaced(d, (x+self.tw/2, ty+150+j*48), l, fd_, rgba(GREY, al), 0.06, "c")
                pv = eo4((t-cu[i]-0.5)/0.6)
                if pv > 0:
                    fv = F(118, "x"); v = tl["value"]; d.text((x+self.tw/2-d.textlength(v, font=fv)/2, yy+self.th-300+int(20*(1-pv))), v, font=fv, fill=rgba(OR, pv*dim))
                    fdl = F(46, "m", 800); dl = tl.get("delta", "")
                    if dl: d.text((x+self.tw/2-d.textlength(dl, font=fdl)/2, yy+self.th-140), dl, font=fdl, fill=rgba(INK if not tl.get("neg") else OR, pv*dim))
                    if tl.get("vlabel"): spaced(d, (x+self.tw/2, yy+self.th-345), tl["vlabel"].upper(), F(28, "m", 800), rgba(GREY, pv*dim), 0.12, "c")
        stp = c.get("stamp")
        if stp:
            ps = (t-stp["t"])/0.32
            if ps > 0:
                i = stp["tile"]; x = self.x0+i*(self.tw+self.gap); sc = lerp(1.9, 1.0, eo4(ps)); r = int(118*sc)
                cx, cy = x+self.tw-10, self.y0-30
                lay = Image.new("RGBA", (r*2+40, r*2+40), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay); o = 20
                ld.ellipse([o, o, o+2*r, o+2*r], fill=rgba(OR)); ld.ellipse([o+12*sc, o+12*sc, o+2*r-12*sc, o+2*r-12*sc], outline=rgba(WHITE), width=max(3, int(5*sc)))
                fs = F(max(20, int(54*sc)), "x"); tw_ = ld.textlength(stp["text"], font=fs); ld.text((o+r-tw_/2, o+r-fs.size*0.66), stp["text"], font=fs, fill=WHITE)
                if stp.get("sub"):
                    fss = F(max(10, int(22*sc)), "m", 800); w2 = spaced_w(ld, stp["sub"].upper(), fss, 0.1); spaced(ld, (o+r, o+r+fs.size*0.42), stp["sub"].upper(), fss, WHITE, 0.1, "c")
                lay = lay.rotate(-12, resample=Image.BICUBIC); lay.putalpha(lay.getchannel("A").point(lambda v: int(v*cl(ps*2))))
                im.alpha_composite(lay, (int(cx-lay.width/2), int(cy-lay.height/2)))
        footer(im, c.get("ftitle", "Alphabet revenue by segment, Q3 2026"), c["source"])
        return im

class Flow:
    """Icon flow over darkened footage: white circles + drawn icons, curved arrows draw on, labels + values.
    c = {title, nodes [{icon, label, value, accent}], ops ["-", "="], source}"""
    def __init__(self, c, cues, dur): self.c = c; self.cues = cues; self.dur = dur
    def frame(self, t):
        c = self.c; im = Image.new("RGBA", (W, H), (8, 8, 8, int(150*eo4(t/0.4)))); d = ImageDraw.Draw(im)
        n = len(c["nodes"]); xs = [W/2+(i-(n-1)/2)*720 for i in range(n)]; y = 700; R = 160
        if c.get("title"):
            q = eo4(t/0.5); spaced(d, (W/2, 170), c["title"].upper(), F(44, "m", 800), rgba(CREAM, q), 0.18, "c")
            d.rectangle([W/2-60*q, 240, W/2+60*q, 247], fill=rgba(OR, q))
        for i, nd in enumerate(c["nodes"]):
            p = back((t-self.cues[i])/0.5, 1.6)
            if i > 0:
                pa = eio((t-self.cues[i]+0.45)/0.55)
                st = (xs[i-1]+R*0.75, y-R*0.8); en = (xs[i]-R*0.8, y-R*0.85)
                draw_curve(im, bezier(st, ((st[0]+en[0])/2, y-R*1.9), en), pa, rgba(WHITE, 0.95), width=9, head=38)
                ops = c.get("ops") or []
                if i-1 < len(ops) and pa > 0.6:
                    q = back((pa-0.6)/0.4); ox, oy = (st[0]+en[0])/2, y-R*1.42; rr = 46*q
                    if rr > 2:
                        aa_ellipse(im, [ox-rr, oy-rr, ox+rr, oy+rr], fill=rgba(OR)); fo = F(int(max(8, 70*q)), "x"); op = ops[i-1]
                        d.text((ox-d.textlength(op, font=fo)/2, oy-fo.size*0.70), op, font=fo, fill=WHITE)
            if p <= 0: continue
            r = R*max(0.01, p); cx = xs[i]
            aa_ellipse(im, [cx-r, y-r, cx+r, y+r], fill=rgba(OR if nd.get("accent") else WHITE))
            if p > 0.6: icon(d, nd["icon"], cx, y, R*0.5*min(1, p), col=WHITE if nd.get("accent") else INK)
            q = eo4((t-self.cues[i]-0.15)/0.5)
            fl = F(36, "m", 800); spaced(d, (cx, y+R+50+int(16*(1-q))), nd["label"].upper(), fl, rgba(CREAM, q), 0.12, "c")
            fv = F(104, "x"); v = nd["value"]; tw = d.textlength(v, font=fv)
            text_shadow(im, (cx-tw/2, y+R+100+int(16*(1-q))), v, fv, rgba(OR if nd.get("accent") else CREAM, q), r=8, a=int(140*q))
        if c.get("source"): d.text((70, H-80), c["source"], font=F(28, "m", 600), fill=rgba((200, 194, 184), eo4(t/0.5)))
        return im

class Section:
    """Section header: big caps on dark background, orange number badge + bar wipe. c = {num, text}"""
    def __init__(self, c, cues, dur): self.c = c; self.dur = dur; self.base = panel(DARK, tex=True)
    def frame(self, t):
        c = self.c; im = self.base.copy(); d = ImageDraw.Draw(im)
        f, L = fit_font(d, c["text"].upper(), "x", 170, 2000, 2, 90); lh = f.size*1.08; tot = lh*len(L)
        y0 = H/2-tot/2+40
        pb = back(t/0.45, 1.5); r = 64*max(0.01, pb)
        if pb > 0:
            aa_ellipse(im, [W/2-r, y0-150-r, W/2+r, y0-150+r], fill=rgba(OR)); fn = F(int(max(8, 76*pb)), "x")
            d.text((W/2-d.textlength(c["num"], font=fn)/2, y0-150-fn.size*0.64), c["num"], font=fn, fill=WHITE)
        for i, l in enumerate(L):
            p = eo4((t-0.15-0.1*i)/0.55); tw = d.textlength(l, font=f)
            lay = Image.new("RGBA", (W, int(lh)+20), (0, 0, 0, 0)); ImageDraw.Draw(lay).text(((W-tw)/2, int(30*(1-p))+4), l, font=f, fill=rgba(CREAM, p))
            im.alpha_composite(lay, (0, int(y0+i*lh)))
        pw = eo4((t-0.35)/0.6); bw = 520*pw; d.rectangle([W/2-bw/2, y0+tot+40, W/2+bw/2, y0+tot+52], fill=OR)
        return im

class LowerThird:
    """Exec name card (no photo): orange bar, white name tab, near-black role tab. c = {who, role}"""
    def __init__(self, c, cues, dur): self.c = c; self.dur = dur; self.t0 = cues[0] if cues else 0.3
    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = self.c
        p = eo4((t-self.t0)/0.5) * (1-eo4((t-(self.dur-0.45))/0.4))
        if p <= 0: return im
        x = 150-int(60*(1-p)); y = 1080; fn = F(64, "x"); fr = F(38, "m", 700)
        nw = d.textlength(c["who"].upper(), font=fn); rw = spaced_w(d, c["role"].upper(), fr, 0.1)
        d.rectangle([x, y, x+16, y+200], fill=rgba(OR, p))
        d.rectangle([x+16, y, x+16+nw+70, y+112], fill=rgba(WHITE, p)); d.text((x+50, y+14), c["who"].upper(), font=fn, fill=rgba(INK, p))
        d.rectangle([x+16, y+112, x+16+rw+70, y+200], fill=rgba(INK, 0.92*p)); spaced(d, (x+50, y+130), c["role"].upper(), fr, rgba(CREAM, p), 0.1)
        return im

class Pops:
    """Keyword pops over footage (lower-left orange box), each timed to its cue. c = {items [[text, sub]]}; cues = per item."""
    def __init__(self, c, cues, dur): self.c = c; self.cues = cues; self.dur = dur
    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for (it, t0) in zip(self.c["items"], self.cues):
            hold = it[2] if len(it) > 2 else 2.0
            p = eo4((t-t0)/0.35)*(1-eo4((t-t0-hold)/0.3))
            if p <= 0: continue
            txt = it[0]; sub = it[1] if len(it) > 1 else ""
            f = F(96, "x"); tw = d.textlength(txt, font=f); x = 150; y = 1040+int(40*(1-p))
            d.rectangle([x, y, x+tw+80, y+150], fill=rgba(OR, p)); d.text((x+40, y+12), txt, font=f, fill=rgba(WHITE, p))
            if sub:
                fs = F(36, "m", 800); sw = spaced_w(d, sub.upper(), fs, 0.12)
                d.rectangle([x, y+150, x+sw+80, y+222], fill=rgba(INK, 0.92*p)); spaced(d, (x+40, y+166), sub.upper(), fs, rgba(CREAM, p), 0.12)
        return im

class Headline:
    """Recreated news headline card (real headline, outlet credited) over dimmed footage. c = {outlet, date, text, credit}"""
    def __init__(self, c, cues, dur): self.c = c; self.dur = dur; self.t0 = cues[0] if cues else 0.4; self.t1 = c.get("out", dur)
    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = self.c
        p = eo4((t-self.t0)/0.45)*(1-eo4((t-self.t1)/0.35))
        if p <= 0: return im
        im = Image.new("RGBA", (W, H), (0, 0, 0, int(90*p))); d = ImageDraw.Draw(im)
        bw = 1900; f, L = fit_font(d, c["text"], "s", 92, bw-180, 3, 60); lh = f.size*1.2
        bh = 190+len(L)*lh+60; x0 = (W-bw)/2; y0 = 300+int(50*(1-p))
        shadow(im, (x0, y0, x0+bw, y0+bh), r=30, a=int(110*p), radius=18)
        d.rounded_rectangle([x0, y0, x0+bw, y0+bh], 18, fill=rgba(CREAM, p))
        fo = F(40, "x"); ow = d.textlength(c["outlet"], font=fo)
        d.rounded_rectangle([x0+90, y0+80, x0+90+ow+56, y0+148], 34, fill=rgba(OR, p)); d.text((x0+118, y0+84), c["outlet"], font=fo, fill=rgba(WHITE, p))
        spaced(d, (x0+90+ow+90, y0+96), c["date"].upper(), F(32, "m", 700), rgba(GREY, p), 0.1)
        for i, l in enumerate(L): d.text((x0+90, y0+190+i*lh), l, font=f, fill=rgba(INK, p))
        if c.get("credit"): d.text((x0+90, y0+bh+24), c["credit"], font=F(28, "m", 600), fill=rgba((235, 230, 222), p))
        return im

class Stat:
    """Big stat callout over footage: number counts up on an orange slab + caps label. c = {value, label, num, prefix, suffix, dec}"""
    def __init__(self, c, cues, dur): self.c = c; self.dur = dur; self.t0 = cues[0] if cues else 0.3; self.t1 = c.get("out", dur-0.3)
    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = self.c
        p = eo4((t-self.t0)/0.35)*(1-eo4((t-self.t1)/0.3))
        if p <= 0: return im
        cu = eo4((t-self.t0)/0.7); v = c["num"]*cu; txt = f"{c.get('prefix','')}{v:.{c.get('dec',0)}f}{c.get('suffix','')}"
        f = F(260, "x"); tw = d.textlength(c["value"], font=f); x = 150; y = 300+int(40*(1-p))
        d.rectangle([x, y, x+tw+120, y+330], fill=rgba(OR, p)); d.text((x+60, y+10), txt, font=f, fill=rgba(WHITE, p))
        fs = F(44, "m", 800); sw = spaced_w(d, c["label"].upper(), fs, 0.12)
        d.rectangle([x, y+330, x+max(tw+120, sw+100), y+430], fill=rgba(INK, 0.92*p)); spaced(d, (x+50, y+356), c["label"].upper(), fs, rgba(CREAM, p), 0.12)
        return im

class Agenda:
    """'In this video' list on the right over footage; items tick in on cues. c = {items}"""
    def __init__(self, c, cues, dur): self.c = c; self.cues = cues; self.dur = dur
    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        p0 = eo4((t-self.cues[0]+0.4)/0.4)*(1-eo4((t-(self.dur-0.35))/0.3))
        if p0 <= 0: return im
        x0 = 1560; y0 = 360
        if not hasattr(self, "_g"):
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).rectangle([1380, 0, W, H], fill=(8, 8, 8, 150)); self._g = g.filter(ImageFilter.GaussianBlur(60))
        g = self._g
        if p0 < 0.999: g = g.copy(); g.putalpha(g.getchannel("A").point(lambda v: int(v*p0)))
        im.alpha_composite(g)
        d = ImageDraw.Draw(im); spaced(d, (x0, y0), "IN THIS VIDEO", F(40, "m", 800), rgba(OR, p0), 0.2)
        for i, (it, c0) in enumerate(zip(self.c["items"], self.cues)):
            p = eo4((t-c0)/0.45)*(p0 if p0 < 1 else 1)
            if p <= 0: continue
            y = y0+110+i*190; r = 46
            aa_ellipse(im, [x0, y, x0+2*r, y+2*r], fill=rgba(OR, p)); fn = F(52, "x")
            d.text((x0+r-d.textlength(str(i+1), font=fn)/2, y+r-fn.size*0.64), str(i+1), font=fn, fill=rgba(WHITE, p))
            text_shadow(im, (x0+130+int(30*(1-p)), y+6), it, F(72, "x"), rgba(CREAM, p), r=6, a=int(150*p))
        return im

class Verdict:
    """'The short version' card: orange over footage, small caps tag + big verdict lines revealed on cues. c = {tag, lines}"""
    def __init__(self, c, cues, dur): self.c = c; self.cues = cues; self.dur = dur
    def frame(self, t):
        im = Image.new("RGBA", (W, H), rgba(OR, 0.92*eo4(t/0.3))); d = ImageDraw.Draw(im); c = self.c
        q = eo4(t/0.5); spaced(d, (200, 330+int(20*(1-q))), c["tag"].upper(), F(52, "m", 800), rgba(INK, q), 0.2)
        d.rectangle([200, 420, 200+300*q, 432], fill=rgba(INK, q))
        y = 520
        for i, (ln, c0) in enumerate(zip(c["lines"], self.cues)):
            p = eo4((t-c0)/0.5); f, L = fit_font(d, ln, "x", 116, 2160, 1, 84)
            for l in L:
                if p > 0: text_shadow(im, (200, y+int(30*(1-p))), l, f, rgba(CREAM if i == 0 else WHITE, p), r=8, a=int(50*p))
                y += f.size*1.14
            y += 40
        return im

class Quote:
    """Speaker card for a REAL sourced quote read by an AI voice. c = {text, who, role, source}; cue[0] = quote start."""
    def __init__(self, c, cues, dur): self.c = c; self.cues = cues; self.dur = dur
    def frame(self, t):
        c = self.c; p = eo4((t-self.cues[0]+0.35)/0.45)
        im = Image.new("RGBA", (W, H), (6, 6, 6, int(165*p))); d = ImageDraw.Draw(im)
        if p <= 0: return im
        x0 = 260; fq = F(330, "x"); d.text((x0-30, 120+int(30*(1-p))), "\u201c", font=fq, fill=rgba(OR, p))
        f, L = fit_font(d, c["text"], "s", 96, 2000, 4, 60); lh = f.size*1.22
        y = 470
        for i, l in enumerate(L):
            pl = eo4((t-self.cues[0]-0.08*i)/0.5); text_shadow(im, (x0, y+int(24*(1-pl))), l, f, rgba(CREAM, pl), r=6, a=int(140*pl)); y += lh
        y += 50; d.rectangle([x0, y, x0+160*p, y+8], fill=rgba(OR, p)); y += 44
        d.text((x0, y), c["who"], font=F(60, "x"), fill=rgba(WHITE, p)); y += 84
        spaced(d, (x0, y), c["role"].upper(), F(34, "m", 700), rgba((210, 204, 194), p), 0.1)
        d.text((x0, H-110), "Source: "+c["source"], font=F(30, "m", 600), fill=rgba((200, 194, 184), p))
        fn = F(26, "m", 800); nt = "QUOTE READ BY AI VOICE"; nw = spaced_w(d, nt, fn, 0.14)
        d.rounded_rectangle([W-150-nw-40, H-122, W-150, H-66], 8, outline=rgba((200, 194, 184), p), width=2); spaced(d, (W-150-nw-20, H-110), nt, fn, rgba((200, 194, 184), p), 0.14)
        return im

class TitleCard:
    """Series title card over dimmed footage: logo + letter-spaced series name, orange rule, big episode title. c = {series, title}"""
    def __init__(self, c, cues, dur, logo=None): self.c = c; self.dur = dur; self.logo = logo
    def frame(self, t):
        c = self.c; im = Image.new("RGBA", (W, H), (8, 8, 8, int(150*eo4(t/0.3)))); d = ImageDraw.Draw(im)
        out = 1-eo4((t-(self.dur-0.35))/0.35); p1 = eo4((t-0.1)/0.5)*out; p2 = eo4((t-0.4)/0.6)*out; p3 = eo4((t-0.6)/0.6)*out
        fs = F(52, "m", 800); s = c.get("series", "ROTATION EXPLAINS").upper(); sw = spaced_w(d, s, fs, 0.32)
        lw = self.logo.width if self.logo is not None else 0; x0 = (W-(lw+30+sw))/2; y = 470
        if self.logo is not None and p1 > 0:
            lg = self.logo.copy(); lg.putalpha(lg.getchannel("A").point(lambda v: int(v*p1))); im.alpha_composite(lg, (int(x0), int(y-4)))
        spaced(d, (x0+lw+30, y), s, fs, rgba(CREAM, p1), 0.32)
        rw = 760*p2; d.rectangle([W/2-rw/2, y+100, W/2+rw/2, y+110], fill=rgba(OR, p2))
        f, L = fit_font(d, c["title"], "x", 150, 2100, 2, 90)
        for i, l in enumerate(L):
            tw = d.textlength(l, font=f); text_shadow(im, ((W-tw)/2, y+170+i*f.size*1.1+int(30*(1-p3))), l, f, rgba(WHITE, p3), r=10, a=int(150*p3))
        return im

class Credit:
    """Small photo credit (CC BY attribution) bottom-right over footage. c = {text}"""
    def __init__(self, c, cues, dur): self.c = c; self.dur = dur
    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = F(26, "m", 600)
        tw = d.textlength(self.c["text"], font=f); text_shadow(im, (W-70-tw, H-66), self.c["text"], f, rgba((235, 232, 226), 0.9), r=4, a=200)
        return im

class Stack:
    """Composite several overlay devices in one RGBA frame (each with its own local time offset)."""
    def __init__(self, items): self.items = items   # [(device, t_offset, t_start, t_end)]
    def frame(self, t):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for dev, off, a, b in self.items:
            if a <= t < b: im.alpha_composite(dev.frame(t-off))
        return im

DEVICES = {"doc": Doc, "bars": Bars, "keyword": Keyword, "split": Split, "tiles": Tiles, "flow": Flow, "section": Section,
           "lower": LowerThird, "pops": Pops, "headline": Headline, "stat": Stat, "agenda": Agenda, "verdict": Verdict,
           "quote": Quote, "title": TitleCard, "credit": Credit}
OPAQUE = {"doc", "bars", "split", "tiles", "section"}
