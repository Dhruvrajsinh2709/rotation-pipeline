import sys as _s; _s.path.insert(0,'/workspace/work/yt'); import wordtime
"""CNBC-style story Short: full-bleed B-roll, narrator VO, bold white captions, stat cards."""
import asyncio, subprocess, textwrap, sys, json
import edge_tts, os
sys.path.insert(0, '/workspace/work/yt'); import gfx
from PIL import ImageFilter, Image, ImageDraw, ImageFont

OUT = "/workspace/work/yt"; W, H = 1080, 1920
WK = os.environ.get("STORY_WORK", OUT); os.makedirs(WK, exist_ok=True)   # temp files (v8: demos can render in their own dir)
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ANTON = "/workspace/work/yt/fonts/Anton-Regular.ttf"; PB = "/workspace/work/yt/fonts/Poppins-ExtraBold.ttf"; PS = "/workspace/work/yt/fonts/Poppins-SemiBold.ttf"
FA = lambda s: ImageFont.truetype(ANTON, s); FP = lambda s: ImageFont.truetype(PB, s); FS = lambda s: ImageFont.truetype(PS, s)
F = lambda s: ImageFont.truetype(B, s)
ACC = (0, 150, 255); VOICE = "en-US-AndrewMultilingualNeural"; BRAND = "ROTATION"
MUSIC = f"{OUT}/music.mp3"; FINAL = f"{OUT}/jio_story_v5.mp4"

# (clip id, narration, optional stat card (big, label))
scenes = [
 ("hd_42096", "This is the biggest IPO India has ever seen.", ("₹30,200 CR", "India's largest-ever IPO")),
 ("hd_4308", "Jio Platforms raised about 30,200 crore rupees, roughly 3.2 billion dollars. And on October 28th, it hit the stock market.", None),
 ("chart:price", "Shares listed at 1,358 rupees, 21 percent above the IPO price of 1,119. By the closing bell, they were up nearly 27 percent.", None),
 ("hd_49845", "That valued Jio at about 13 lakh crore rupees, ahead of Bharti Airtel and HDFC Bank. Only its parent, Reliance Industries, is worth more.", ("#2", "Most valuable listed company in India")),
 ("chart:subs", "Demand was massive. The issue was subscribed 22 times, and big institutions bid for more than 70 times the shares set aside for them.", None),
 ("hd_4401", "Nearly 1.4 crore applications poured in, a record.", ("1.39 CR", "Applications")),
 ("hd_4915", "So why the frenzy? Jio runs India's largest telecom network by subscribers, and it's backed by Meta and Google.", None),
 ("hd_41541", "The debut also pushed the Ambani group's listed companies past the Tata group in total market value.", None),
 ("hd_42648", "The next test: Jio's likely entry into India's key stock indices, which could pull in even more money from index funds.", None),
 ("hd_49878", "Follow Rotation for more stories on the money moving the world.", None),
]

def dur(p):
    try: return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).decode().strip())
    except ValueError: return 0.0   # broken/unknown-length file: treated as unusable

async def tts(i, text, voice=None, rate=None):
    import asyncio as _a
    for k in range(4):
        try: return await _tts(i, text, voice, rate)
        except Exception as e:
            if k==3: raise
            await _a.sleep(5*(k+1))

RATE = "+5%"
async def _tts(i, text, voice=None, rate=None):
    if wordtime.needs_align(voice or VOICE):
        return [(a, w) for a, b, w in await wordtime.synth(text, voice or VOICE, rate or RATE, f"{WK}/s{i}.mp3")]
    c = edge_tts.Communicate(text, voice or VOICE, rate=rate or RATE, boundary="WordBoundary"); words = []
    with open(f"{WK}/s{i}.mp3","wb") as fh:
        async for ch in c.stream():
            if ch["type"]=="audio": fh.write(ch["data"])
            elif ch["type"]=="WordBoundary": words.append((ch["offset"]/1e7, ch["text"]))
    return words

def stroke_center(d, y, t, font, fill=(255,255,255)):
    w = d.textlength(t, font=font); d.text(((W-w)/2, y), t, font=font, fill=fill, stroke_width=8, stroke_fill=(0,0,0))

YEL=(240,180,0)

def _accent(spec):
    """Brand-orange accent on the mono look (user 2026-10-30). spec "accent": "#RRGGBB" | null (null/false = pure B/W)."""
    a = spec.get("accent", "#FA4E02")
    if not a: return None
    a = a.lstrip("#"); return tuple(int(a[i:i+2], 16) for i in (0, 2, 4))
_mf={}
def MF(sz, wg=700):
    k=(sz,wg)
    if k not in _mf:
        f=ImageFont.truetype("/workspace/work/yt/fonts/Montserrat-VF.ttf", sz); f.set_variation_by_axes([wg]); _mf[k]=f
    return _mf[k]

def shadow_text(im, xy, t, font, fill=(255,255,255)):
    sh = Image.new("RGBA", im.size, (0,0,0,0)); ImageDraw.Draw(sh).text((xy[0]+4,xy[1]+5), t, font=font, fill=(0,0,0,230))
    sh = sh.filter(ImageFilter.GaussianBlur(6)); im.alpha_composite(sh)
    ImageDraw.Draw(im).text(xy, t, font=font, fill=fill)

_logo=None
def logo_mark(h):
    # 2026-10-30: user picked the cream-ribbon-on-orange logo (brand_logo_v2_cream_orange.png) for sting + end card; old mask = banner/logo.jpg (see *.bak16.py)
    global _logo
    if _logo is None: _logo = Image.open('/workspace/work/yt/brand_logo_disc.png').convert('RGBA')
    return _logo.resize((h, h), Image.LANCZOS)

def title_block(im, title, bottom=1350):
    # CNBC-style opener: centred white logo + wordmark, title with yellow bar on its left; grows upward from `bottom`
    d=ImageDraw.Draw(im)
    for sz in (84,78,72,66,60):
        f=MF(sz,800); L=[""]
        for w in title.split():
            x=(L[-1]+" "+w).strip()
            if d.textlength(x,font=f)>780 and L[-1]: L.append(w)
            else: L[-1]=x
        if len(L)<=3: break
    lh=int(sz*1.18); top=bottom-len(L)*lh
    mw=max(d.textlength(l,font=f) for l in L); bw=16+34+mw; x0=int((W-bw)/2)
    mk=logo_mark(54); wf=MF(46,800); ww=d.textlength(BRAND,font=wf); lw=mk.width+14+ww; lx=int((W-lw)/2); ly=top-96
    im.alpha_composite(mk,(lx,ly)); shadow_text(im,(lx+mk.width+14,ly-2),BRAND,wf)
    d=ImageDraw.Draw(im); d.rectangle([x0,top+int(sz*0.15),x0+16,top+len(L)*lh-int(sz*0.1)],fill=YEL)
    y=top
    for l in L: shadow_text(im,(x0+50,y),l,f); y+=lh

def brand_tag(im):
    # 2026-10-30: user asked to remove the top-left logo + name from long and short videos
    import os
    if not os.environ.get('SHOW_BUG'): return
    # top-left: white logo mark + ROTATION wordmark (no yellow bar)
    mk=logo_mark(58); im.alpha_composite(mk,(60,108)); shadow_text(im,(60+mk.width+16,108),BRAND,MF(44,800))

import re as _re
def countup(big, e):
    # animate the first number in `big` from 0 to its value, keeping prefix/suffix and comma/decimal format
    m = _re.search(r"[0-9][0-9,]*(\.[0-9]+)?", big)
    if not m or e >= 1: return big
    t = m.group(0); dec = len(m.group(1))-1 if m.group(1) else 0; v = float(t.replace(",",""))*e
    n = f"{v:,.{dec}f}" if "," in t else f"{v:.{dec}f}"
    return big[:m.start()]+n+big[m.end():]

def _ease4(p): p = max(0.0, min(1.0, p)); return 1-(1-p)**4

def _fade_layer(L, a, dy=0, sc=1.0, cx=W/2, cy=H/2):
    """v8 Shorts: eased entrance for an overlay layer (alpha a, rise dy px, scale sc about cx, cy)."""
    if sc != 1.0:
        L2 = L.resize((int(W*sc), int(H*sc)), Image.LANCZOS); L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        L.alpha_composite(L2, (int(cx-cx*sc), int(cy-cy*sc)))
    if dy:
        L2 = Image.new("RGBA", (W, H), (0, 0, 0, 0)); L2.alpha_composite(L, (0, int(dy))); L = L2
    if a < 1: L.putalpha(L.getchannel("A").point(lambda v: int(v*a)))
    return L

def overlay(cap, stat, path, card=None, loc=None, title=None, stat_prog=1.0, stat_alpha=1.0, hook=None, pills=None, pill_t=-1, stk=None, stk_t=-1,
            card_p=1.0, loc_p=1.0, hook_a=1.0, qcard=None, q_p=None, lt=None, lt_p=None):
    im = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(im)
    if qcard and q_p is not None:   # v9 Shorts: speaker card for a real quote read by a second AI voice (cached per progress step)
        qp = f"{WK}/_q_{abs(hash((json.dumps(qcard, sort_keys=True), q_p, spec.get('ai_voice_note', True))))}.png"
        if not os.path.exists(qp): v9gfx.quote_png_v(qp, qcard, q_p, spec.get("ai_voice_note", True))
        im.alpha_composite(Image.open(qp).convert("RGBA")); d = ImageDraw.Draw(im)
    if card:
        if card_p >= 1: gfx.card(im, card, True)
        else:   # v8: card eases in over 0.4 s (fade + 3 % settle + 24 px rise)
            e = _ease4(card_p); L = Image.new("RGBA",(W,H),(0,0,0,0)); gfx.card(L, card, True)
            im.alpha_composite(_fade_layer(L, e, dy=24*(1-e), sc=0.97+0.03*e))
        d = ImageDraw.Draw(im)
    for y in range(H-600, H):
        a = int(120*(y-(H-600))/600); d.line([(0,y),(W,y)], fill=(0,0,0,a))
    if hook:   # Study 2: 0-3 s headline card (pin moves into it); v8: eases out over the last 0.3 s
        _hc = (lambda T: gfx.clash_card(T, hook["clash"], True)) if isinstance(hook, dict) else (lambda T: gfx.hook_card(T, hook, loc, True))
        if hook_a >= 1: _hc(im)
        else:
            L = Image.new("RGBA",(W,H),(0,0,0,0)); _hc(L); e = _ease4(hook_a)
            im.alpha_composite(_fade_layer(L, e, dy=-30*(1-e)))
        d = ImageDraw.Draw(im)
    brand_tag(im)
    if loc and not hook:
        if loc_p >= 1: gfx.loc_tag(im, loc, 54, 196, True)
        else:   # v8: pin tag slides in from the left
            e = _ease4(loc_p); L = Image.new("RGBA",(W,H),(0,0,0,0)); gfx.loc_tag(L, loc, 54-int(50*(1-e)), 196, True)
            im.alpha_composite(_fade_layer(L, e))
        d = ImageDraw.Draw(im)
    if title: title_block(im, title); d = ImageDraw.Draw(im)
    if stat:
        big, label = stat; sz = 190
        e_cnt = 1-(2**(-10*min(stat_prog,1))) if stat_prog<1 else 1.0   # easeOutExpo count-up over the 0.7 s window
        e_pop = 1-(1-min(stat_prog/0.4,1))**3                                 # easeOutCubic pop-in
        while d.textlength(big, font=MF(sz,900)) > W-220: sz -= 6
        f9 = MF(sz,900); bw = d.textlength(big, font=f9) + 90; x0 = (W-bw)/2; y0 = 340 if title else 640
        bb = d.textbbox((0,0), big, font=f9); th = bb[3]-bb[1]
        shown = countup(big, e_cnt)
        L = Image.new("RGBA",(W,H),(0,0,0,0)); ld = ImageDraw.Draw(L)
        # soft dark scrim so the yellow number reads on bright footage
        _sc = Image.new("RGBA",(W,H),(0,0,0,0)); ImageDraw.Draw(_sc).rounded_rectangle([W*0.12, y0-30, W*0.88, y0+th+200], 60, fill=(0,0,0,120))
        L.alpha_composite(_sc.filter(ImageFilter.GaussianBlur(50)))
        # no box (user 2026-10-29): big yellow count-up number with soft shadow
        shadow_text(L, ((W-ld.textlength(shown,font=f9))/2, y0+45-bb[1]), shown, f9, fill=YEL)
        lf = MF(52,600); shadow_text(L, ((W-ld.textlength(label,font=lf))/2, y0+th+120), label, lf)
        if e_pop < 1:
            sc = 0.86+0.14*e_pop; cx, cy = W/2, y0+(th+90)/2
            L2 = L.resize((int(W*sc),int(H*sc)), Image.LANCZOS); L = Image.new("RGBA",(W,H),(0,0,0,0))
            L.alpha_composite(L2,(int(cx-cx*sc),int(cy-cy*sc)))
            a = L.getchannel("A").point(lambda v: int(v*e_pop)); L.putalpha(a)
        if stat_alpha < 1: L.putalpha(L.getchannel("A").point(lambda v: int(v*stat_alpha)))
        im.alpha_composite(L); d = ImageDraw.Draw(im)
    if pills and pill_t >= 0: gfx.pills_row(im, pills, pill_t, True); d = ImageDraw.Draw(im)
    if stk and stk_t >= 0: gfx.sticker(im, stk, stk_t, True); d = ImageDraw.Draw(im)
    if lt and lt_p is not None:   # v9 Shorts: name/role lower third for public-domain actuality (blur-fill band)
        lp_ = f"{WK}/_lt_{abs(hash((json.dumps(lt, sort_keys=True), lt_p)))}.png"
        if not os.path.exists(lp_): v9gfx.lower_third_png_v(lp_, lt.get("who", ""), lt.get("role"), lt.get("credit"), lt_p, lt.get("source"))
        im.alpha_composite(Image.open(lp_).convert("RGBA")); d = ImageDraw.Draw(im)
    if cap:
        # CNBC match (user 2026-10-29): smaller, narrower so it clears the Shorts side rail, a bit higher
        sz = 64
        while d.textlength(cap, font=MF(sz,700)) > 760: sz -= 2
        f = MF(sz,700)
        if V9:   # v9: soft dark halo behind the caption so white text holds on bright footage (same font/size/position)
            cw_ = d.textlength(cap, font=f); hl = Image.new("RGBA", (W, H), (0,0,0,0))
            ImageDraw.Draw(hl).rounded_rectangle([(W-cw_)/2-40, 1352, (W+cw_)/2+40, 1360+sz+22], 40, fill=(0,0,0,95))
            im.alpha_composite(hl.filter(ImageFilter.GaussianBlur(22))); d = ImageDraw.Draw(im)
        shadow_text(im, ((W-d.textlength(cap,font=f))/2, 1360), cap, f)
    im.save(path)

def chart_frames(kind, D, d_out):
    import os; os.makedirs(d_out, exist_ok=True); n = int(D*30)+1
    BG=(6,12,28); GRID=(30,42,70); G=YEL; WH=(245,247,250); GR=(140,150,175)
    MONO = gfx.THEME == "mono"; AREA_ = (40,40,42) if MONO else (70,55,10)
    if MONO: BG=(9,9,10); GRID=(40,40,42); GR=(150,150,152)
    for k in range(n):
        p = min(1, k/(n*0.6)); e = 1-(1-p)**3
        im = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(im)
        if kind=="price":
            d.text((80,240),"JIO PLATFORMS",font=MF(84,900),fill=WH); d.text((80,360),"Share price, Oct 28, 2026 (₹)",font=MF(42,500),fill=GR)
            pts=[("IPO price",1119),("Listing",1358),("Close",1419)]
            x0,x1,yb,yt=150,860,960,560; lo,hi=1000,1550
            for v in (1100,1200,1300,1400):
                y=yb-(v-lo)/(hi-lo)*(yb-yt); d.line([(x0,y),(x1+40,y)],fill=GRID,width=2); d.text((x1+60,y-22),str(v),font=MF(32,500),fill=GR)
            xs=[x0+i*(x1-x0)/2 for i in range(3)]; ys=[yb-(v-lo)/(hi-lo)*(yb-yt) for _,v in pts]
            seg=e*2; poly=[(xs[0],ys[0])]
            for i in range(2):
                if seg>i:
                    t=min(1,seg-i); poly.append((xs[i]+(xs[i+1]-xs[i])*t, ys[i]+(ys[i+1]-ys[i])*t))
            d.polygon(poly+[(poly[-1][0],yb),(xs[0],yb)],fill=AREA_); d.line(poly,fill=G,width=12,joint="curve")
            for i,(lab,v) in enumerate(pts):
                if seg>=i-0.02:
                    d.ellipse([xs[i]-18,ys[i]-18,xs[i]+18,ys[i]+18],fill=WH)
                    t=f"₹{v:,}"; tw=d.textlength(t,font=MF(54,800)); d.text((xs[i]-tw/2,ys[i]-110),t,font=MF(54,800),fill=WH)
                    tw=d.textlength(lab,font=MF(36,500)); d.text((xs[i]-tw/2,yb+30),lab,font=MF(36,500),fill=GR)
            if e>0.99: d.rounded_rectangle([80,1080,400,1170],20,fill=G); d.text((108,1086),"+26.8%",font=MF(58,900),fill=BG); d.text((430,1100),"first-day gain",font=MF(42,500),fill=WH)
        else:
            d.text((80,240),"WHO WANTED IN",font=MF(84,900),fill=WH); d.text((80,360),"Times subscribed, by investor type",font=MF(42,500),fill=GR)
            bars=[("Institutions",70.55),("Non-institutional",14.0),("Overall",22.19),("Retail",2.72)]
            for i,(lab,v) in enumerate(bars):
                y=470+i*190; w=int((W-260)*v/70.55*e)
                d.text((80,y),lab,font=MF(40,500),fill=GR); d.rounded_rectangle([80,y+60,80+max(w,20),y+130],14,fill=G if lab!="Overall" else (255,255,255))
                d.text((100+max(w,20),y+60),f"{v*e:.1f}x",font=MF(52,800),fill=WH)
        im.save(f"{d_out}/{k:04d}.png")

def cover_overlay(title, path):
    # Rotation's own cover (user picked A, 2026-10-29): footage top, flat logo-orange slab bottom, cream headline + logo
    OR=(250,78,2); CR=(248,241,228); top=1060
    im = Image.new("RGBA",(W,H),(0,0,0,25)); d = ImageDraw.Draw(im)
    d.rectangle([0,top,W,H],fill=OR+(255,)); d.rectangle([0,top-10,W,top],fill=CR+(255,))
    n = Image.effect_noise((W,H-top),40).convert("L").point(lambda v: int(v*0.06))
    gr = Image.new("RGBA",(W,H-top),(255,255,255,0)); gr.putalpha(n); im.alpha_composite(gr,(0,top))
    mk=logo_mark(54); a=mk.getchannel("A"); mk=Image.new("RGBA",mk.size,CR+(0,)); mk.putalpha(a)
    im.alpha_composite(mk,(75,top+50)); d=ImageDraw.Draw(im); d.text((75+mk.width+14,top+48),BRAND,font=MF(46,800),fill=CR)
    sz=104
    while True:
        f=MF(sz,900); L=[""]
        for w in title.split():
            x=(L[-1]+" "+w).strip()
            if d.textlength(x,font=f)>W-150 and L[-1]: L.append(w)
            else: L[-1]=x
        if len(L)*sz*1.13 <= H-top-230 or sz<=70: break
        sz-=4
    y=top+150
    for l in L: d.text((75,y),l,font=f,fill=CR); y+=int(sz*1.13)
    im.save(path)

SFX = []
GRADE = 'eq=contrast=1.06:saturation=0.94:gamma=0.98:brightness=-0.03,colorbalance=rs=-0.02:bs=0.03:rh=0.03:bh=-0.02,vignette=angle=PI/5,noise=alls=4:allf=t'
PEAK = {'click':0.193,'hit':0.087,'riser':2.535,'slice':0.188,'whoosh':1.065,'whoosh_soft':0.715}
VOL = {'click':0.35,'hit':0.9,'riser':0.35,'slice':0.4,'whoosh':0.35,'whoosh_soft':0.3}
TITLE = None; TITLE_SEC = 0.0  # centre opener removed 2026-10-29 (user: only top left)
spec = {}
if len(sys.argv) > 1:
    spec = json.load(open(sys.argv[1])); TITLE = spec.get("title"); FINAL = spec["output"]
    scenes = spec["scenes"]; RATE = spec.get("rate", RATE)
# normalise: every scene -> dict(clip, text, stat, chart, card, loc, blur)
def _norm(x):
    if isinstance(x, dict): return x
    x = list(x)+[None]*(3-len(x)); return {"clip": x[0], "text": x[1], "stat": x[2]}
scenes = [_norm(x) for x in scenes]
# Study 2 outro (2026-10-29): the old follow line is retired; spec "outro" = dated next catalyst, else the fallback.
OLD_CTA = "Follow Rotation for more stories on the money moving the world."
OUTRO_FALLBACK = "Full breakdown in this weekend's deep dive on Rotation."
_oc = None
if scenes and (scenes[-1].get("text") or "").strip() == OLD_CTA: _oc = scenes.pop()["clip"]
_o = spec.get("outro", None if spec.get("growth1", True) else OUTRO_FALLBACK)   # GROWTH 1 (2026-11-01): no spoken deep-dive CTA fallback
if _o:
    _ot, _ocl = (_o, None) if isinstance(_o, str) else (_o["text"], _o.get("clip"))
    _otag = isinstance(_o, dict) and _o.get("tags") and spec.get("v8", True)   # v8: outro may give only "tags"
    scenes.append({"clip": _ocl or spec.get("outro_clip") or _oc or (None if _otag else "hd_49845"), "text": _ot, "outro": True,
                   "tags": (_o.get("tags") if isinstance(_o, dict) else None) or [],
                   **({"nat": _o["nat"]} if isinstance(_o, dict) and "nat" in _o else {})})
HOOK = scenes[0].get("hook_card", TITLE) if scenes else None   # 0-3 s headline card; fallback = the title
if scenes and scenes[0].get("clash"):   # FRAME 1 CLASH (2026-11-04): green-vs-red number pair replaces the text hook; scene-1 stat waits
    HOOK = {"clash": scenes[0]["clash"]}; scenes[0].pop("stat", None)
# ---- v8 for Shorts (user 2026-10-30: "this video is insane yes same for shorts") ----
# black-and-white graphics, per-video music from the library, no repeated clips, 4K sources + lanczos, no grain, eased graphics.
V8 = spec.get("v8", True) if spec else False
import clipfetch, musiclib
import v9gfx, natlib
# ---- Shorts v9 (user 2026-10-30 08:56 IST: "yes same extra voice and background in the short too") ----
# quote (real sourced quote, second AI voice, speaker card), actuality (public-domain real audio + lower third, blur-fill),
# per-shot nat ambience ducked under the voice, music -18 dB under the voice. "v9": false = exact v8 Shorts.
V9 = bool(spec.get("v9", True)) if (spec and V8) else False
V10 = bool(spec.get("v10", True)) if V9 else False   # Study 10 sound: two cues (switch at the turn), SFX families, varied small sounds
EV10 = []
QVOICE = v9gfx.QuoteVoices(spec.get("voice2")); NATSEG = []; VOX = []
if V8:
    th_ = spec.get("theme", "light")   # user 2026-10-30 "yes shorts same": light palette C (cream, orange + cobalt); "mono" = old dark look
    if th_ in ("mono", "light"):
        ACC_ = _accent(spec); gfx.set_theme("mono", ACC_); gfx.HL_GREY = True; YEL = ACC_ or (255, 255, 255)
    if th_ == "light": gfx.set_theme("light", ACC_ or (250, 78, 2)); gfx.HL_GREY = False
    GRADE = 'eq=contrast=1.05:saturation=0.96:gamma=0.99:brightness=-0.02,vignette=angle=PI/7'   # no grain, lighter vignette (long-form v8 grade)
OW, OH = (spec.get("res", [1080, 1920]) if V8 else [1080, 1920])
CRF = str(spec.get("crf", 16)) if V8 else "18"
USED = set(); REPL = []; IX = clipfetch.load_index() if V8 else {}
RECENT = clipfetch.recent_used(int(spec.get("recent_videos", 4))) if V8 else set()
LOG_USED = bool(spec.get("log_used", True)) if V8 else False
DARK_LUMA = 0.12
SCL = f"scale={OW}:{OH}:flags=lanczos," if (OW, OH) != (1080, 1920) else ""   # graphics/overlays drawn at 1080x1920
COVER = [None]
import math, time as _time
_T_START = _time.time()
CLIPDUR = {}
def cdur(cid):
    if cid not in CLIPDUR: CLIPDUR[cid] = dur(f"{OUT}/clips/{cid}.mp4")
    return CLIPDUR[cid]
BT709 = "setparams=colorspace=bt709:color_trc=bt709:color_primaries=bt709:range=tv"
COLOR_OUT = ["-colorspace","bt709","-color_primaries","bt709","-color_trc","bt709"]
import mixbus

# ---------------- v8 clip picking (no repeats, recent-video avoidance, 4K first) ----------------
def ok_clip(cid, L=0.0):
    return os.path.exists(f"{OUT}/clips/{cid}.mp4") and cdur(cid) >= L+0.4 and not IX.get(cid, {}).get("bad") \
        and "restricted" not in str(IX.get(cid, {}).get("licence", "")).lower()

def good_ss(cid, L, pref=None):
    dd = cdur(cid)
    if pref is not None and pref+L <= dd-0.1: return round(pref, 2)
    return round(max(0.0, min(dd-L-0.15, 0.22*(dd-L))), 2)

def pick_lib(tags, text, exclude, n=25, min_score=1):
    """Library picks by tag + narration overlap; ties go to 2160p sources (they survive the 9:16 crop)."""
    ids = clipfetch.pick(tags, text, exclude=exclude, n=200, min_score=min_score)
    sc_ = {k: clipfetch.score(IX.get(k, {}), tags, text) for k in ids}
    ids = [k for k in ids if not IX.get(k, {}).get("bad") and "restricted" not in str(IX.get(k, {}).get("licence", "")).lower()]
    return sorted(ids, key=lambda k: (-sc_[k], -(IX.get(k, {}).get("h") or 1080)))[:n]

def resolve_unique(plan_, sc, own):
    """Replace any shot whose clip is already used in this Short (or bad/restricted) with an unused relevant clip:
    the scene's own clips first, then library picks by tags + narration (recent videos excluded), then any unused pick."""
    out_ = []; tags = list(sc.get("tags") or []) + list(spec.get("tags") or [])
    for (sh, ss, L) in plan_:
        if sh not in USED and ok_clip(sh, 0):
            USED.add(sh); out_.append((sh, ss, L)); continue
        cands = [x for x in own if x not in USED] + pick_lib(tags, sc.get("text") or "", USED | RECENT) + pick_lib(tags, sc.get("text") or "", USED, min_score=0)
        _subj = [w.lower() for w in (spec.get("subject") or [])]
        if _subj and (sc.get("outro") or sc is (spec.get("scenes") or [None])[0]):   # 2026-11-05: outro/scene-1 swaps stay on the subject (was HPCL pump for IndiGo)
            _sl = [k for k, m in IX.items() if not m.get("bad") and any(w in (m.get("title", "") + " " + " ".join(m.get("tags", []))).lower() for w in _subj)]
            cands = [x for x in _sl if x not in USED] + cands
        alt = next((x for x in cands if x not in USED and ok_clip(x, L) and gfx.clip_luma(f"{OUT}/clips/{x}.mp4", good_ss(x, L), L) >= DARK_LUMA), None)
        if alt is None: alt = next((x for x in cands if x not in USED and ok_clip(x, L)), sh)
        REPL.append(f"{sh}->{alt}"); USED.add(alt); out_.append((alt, good_ss(alt, L), L))
    return out_

async def main():
    clips = []; T0 = 0.0; SFX.clear(); times = []; punch = []; shots_all = []
    for i,sc in enumerate(scenes):
        cid = sc.get("chart") or sc.get("clip"); text = sc.get("text") or ""
        q = sc.get("quote") if V9 else None; ac = sc.get("actuality") if V9 else None; q0 = None
        if ac: cid = ac["clip"]; sc.setdefault("vo_gain", 0.0)   # real audio keeps its own dynamics (no emphasis contour)
        if i>0 and (sc.get("chart") or sc.get("card")): SFX.append(("whoosh", T0))
        elif i>0 and sc.get("loc"): SFX.append(("slice", T0+0.1))
        stat = tuple(sc["stat"]) if sc.get("stat") else None
        if q:   # v9: optional narrator lead-in, then the real quote in its own AI voice (one voice per speaker)
            qv = QVOICE(q.get("who", ""), q.get("voice")); qw = await tts(f"q{i}", q["text"], qv, spec.get("rate2", "+12%"))
            if text:
                nw_ = await tts(f"n{i}", text); g_ = dur(f"{WK}/sn{i}.mp3") + 0.3
                subprocess.run(["ffmpeg","-y","-v","error","-i",f"{WK}/sn{i}.mp3","-i",f"{WK}/sq{i}.mp3","-filter_complex",
                                "[0:a]aresample=24000,apad=pad_dur=0.3[a0];[1:a]aresample=24000[a1];[a0][a1]concat=n=2:v=0:a=1","-ac","1","-b:a","96k",f"{WK}/s{i}.mp3"], check=True)
                words = list(nw_) + [(a_+g_, w_) for a_, w_ in qw]; q0 = g_; VOX.append((T0, "narrator"))
            else:
                subprocess.run(["cp", f"{WK}/sq{i}.mp3", f"{WK}/s{i}.mp3"], check=True); words = list(qw); q0 = 0.0
            VOX.append((T0+q0, f"quote:{q.get('who','')} ({qv})")); text = (text + " " + q["text"]).strip()
            SFX.append(("whoosh_soft", T0+q0))
        elif ac:   # v9: public-domain real audio, level-matched to the narrator; captions = the verified transcript in ac["text"]
            refs = [f"{WK}/s{k}.mp3" for k in range(i) if not scenes[k].get("actuality") and not scenes[k].get("quote")][:3]
            Lref = sum(mixbus._ebur(r)[0] for r in refs)/len(refs) if refs else -18.0
            ss_a = float(ac.get("ss", 0)); d_a = float(ac["dur"])
            mixbus.actuality_wav(f"{OUT}/clips/{ac['clip']}.mp4", ss_a, d_a, f"{WK}/s{i}.mp3", Lref, ac.get("gain_db", 0.0), tmp=WK)
            text = ac.get("text") or ""; toks_a = text.split(); wt = []
            if ac.get("words_json") and os.path.exists(ac["words_json"]):
                wj = json.load(open(ac["words_json"]))["words"]; wt = [x["start"]-ss_a for x in wj if ss_a-0.05 <= x["start"] < ss_a+d_a]
            if len(wt) != len(toks_a): wt = [0.1+k*(d_a-0.4)/max(1, len(toks_a)) for k in range(len(toks_a))]
            words = [(max(0.0, t_), w_) for t_, w_ in zip(wt, toks_a)]; VOX.append((T0, f"actuality:{ac.get('who','')}"))
        else:
            words = await tts(i, text)
            if V9: VOX.append((T0, "narrator"))
        D = dur(f"{WK}/s{i}.mp3") + (0.3 if ac else 0.15)
        # re-attach script punctuation to word timings (for sentence-beat cuts)
        toks = text.split(); j = 0; pw = []
        for (a, w) in words:
            if V9:   # v9 fix: edge-tts can return multi-token boundaries ("December 9"); match the first token, consume all, never skip ahead on a miss
                parts = w.split() or [w]; k = j; f0 = parts[0].lower().strip(".,?!;:'\"")
                while k < len(toks) and f0 not in toks[k].lower(): k += 1
                if k < len(toks): e_ = min(len(toks)-1, k+len(parts)-1); pw.append((a, toks[e_])); j = e_+1
                else: pw.append((a, w))
                continue
            while j < len(toks) and w.lower().strip(".,?!;:'\"") not in toks[j].lower(): j += 1
            pw.append((a, toks[j] if j < len(toks) else w)); j += 1
        cuts_pref = [pw[k+1][0]-0.05 for k in range(len(pw)-1) if pw[k][1][-1:] in ".,?!;:"]
        cuts_any = [a-0.05 for a, _ in pw[1:]]
        # caption chunks: up to 4 words, but split early when a chunk would not fit 760 px at the locked 64 px size
        _md = ImageDraw.Draw(Image.new("RGB", (8, 8))); chunks = [[]]
        for wi, w in enumerate(words):
            cand = " ".join(x[1] for x in chunks[-1]+[w]) + ("\u201d\u201d" if q0 is not None else "")
            qsplit = q0 is not None and chunks[-1] and chunks[-1][0][0] < q0-1e-3 <= w[0]-1e-3
            ssplit = V9 and wi > 0 and wi-1 < len(pw) and pw[wi-1][1][-1:] in ".?!"   # v9: a caption never runs across a sentence end
            if chunks[-1] and (qsplit or ssplit or len(chunks[-1]) >= 4 or _md.textlength(cand, font=MF(64,700)) > 760): chunks.append([w])
            else: chunks[-1].append(w)
        chunks = [ch for ch in chunks if ch]
        cst = [0.0]+[ch[0][0] for ch in chunks[1:]]; ctx = [" ".join(w[1] for w in ch) for ch in chunks]
        if q0 is not None:   # v9: the quote's caption chunks carry curly quote marks
            qi = [k for k, ch in enumerate(chunks) if ch[0][0] >= q0-1e-3]
            if qi: ctx[qi[0]] = "\u201c" + ctx[qi[0]]; ctx[qi[-1]] = ctx[qi[-1]] + "\u201d"
        # ---- shots (stat must sit inside one shot; Shorts max shot 7.5 s) ----
        ischart = isinstance(cid, dict) or (isinstance(cid, str) and cid.startswith("chart:"))
        st0 = 0.0
        if stat:
            dg = [a for a, w in pw if any(ch.isdigit() for ch in w)]
            st0 = max(0.0, (dg[0]-0.1) if dg else 0.0)
            if st0 > D-3.6: st0 = max(0.0, D-3.6)
        need = st0+0.7+2.5+0.3+0.1 if stat else 0.0
        plan = None
        if ac:   # v9 actuality: the speaker's own footage at the audio in-point, one shot, shown blur-fill (sharp 16:9 band)
            plan = [(ac["clip"], round(float(ac.get("ss", 0)), 2), D)]; USED.add(ac["clip"]); shots_all.append(round(D, 2))
        elif not ischart:
            shots = list(cid) if isinstance(cid, list) else ([cid] if cid else [])
            if V8:   # v8: drop missing/bad named clips; a scene with only "tags" gets unused library picks
                shots = [x for x in shots if ok_clip(x.split("@")[0])]
                if not shots:
                    tg = list(sc.get("tags") or []) + list(spec.get("tags") or [])
                    shots = pick_lib(tg, text, USED | RECENT, n=max(1, math.ceil(D/3.8))) or pick_lib(tg, text, USED, n=2, min_score=0)
            while len(shots) > 1 and D-need < 1.2*(len(shots)-1): shots.pop()
            plan = gfx.plan_shots(shots, D, max(D/len(shots), 0.1), 7.5, cuts_pref, cuts_any, first_min=need,
                                  durs={x.split("@")[0]: cdur(x.split("@")[0]) for x in shots}, min_shot=1.2)
            if V8: plan = resolve_unique(plan, sc, [x.split("@")[0] for x in shots])
            if i == 0: COVER[0] = plan[0][0]
            shots_all += [round(L, 2) for _, _, L in plan]
        else: shots_all.append(round(D, 2))
        if V9 and plan and not ac:   # v9 nat: one ambience segment per shot (new in-point, +/-1 dB) so the bed changes on every cut
            ns_ = natlib.for_scene(sc.get("nat"), sc.get("tags"), spec.get("tags"), spec.get("nat_default")); tt_ = T0
            for jn, (sh_, ss_, L_) in enumerate(plan):
                src_ = ("clip", f"{OUT}/clips/{sh_}.mp4", ss_) if (sc.get("nat") == "clip" and IX.get(sh_, {}).get("audio_ok")) else ns_
                if src_ is not None: NATSEG.append((tt_, tt_+L_, src_, 1.2 if jn % 2 else -1.0))
                tt_ += L_
        sw = gfx.stat_window(D, st0, plan[0][2] if plan else D) if stat else None
        # ---- overlay timeline: captions, stat (count 0.7 s, hold 2.5-4 s, fade), hook card, pills, sticker ----
        hk = HOOK if (i == 0 and HOOK) else None; hend = min(3.0, D) if hk else 0.0
        pills = sc.get("pill"); stk = sc.get("sticker")
        p0 = max(0.15, hend); p1 = min(D, p0+4.3); k0 = max(0.35, hend+0.1); k1 = min(D, k0+4.2)
        pa = 0.25+0.12*(len(pills)-1) if pills else 0
        if stk: SFX.append(("click", T0+k0))
        bps = cst+[hend]+(list(sw) if sw else [])+([p0, p1] if pills else [])+([k0, k1] if stk else [])
        anims = ([(sw[0], sw[1]), (sw[2], sw[3])] if sw else [])+([(p0, p0+pa)] if pills else [])+([(k0, k0+0.6)] if stk else [])
        # v8 eased entrances: card 0.4 s, loc pin 0.35 s, hook card eases out over its last 0.3 s
        CA = 0.4 if (V8 and sc.get("card")) else 0.0; LA = 0.35 if (V8 and sc.get("loc") and not hk) else 0.0
        HF = (max(0.0, hend-0.3), hend) if (V8 and hk) else None
        anims += ([(0.0, CA)] if CA else [])+([(0.0, LA)] if LA else [])+([HF] if HF else [])
        if q: bps += [q0]; anims += [(q0, q0+0.45)]
        if ac: bps += [0.2]; anims += [(0.2, 0.6)]
        bps += ([CA] if CA else [])+([LA] if LA else [])+(list(HF) if HF else [])
        def state(t):
            ci = max(k for k in range(len(cst)) if cst[k] <= t+1e-6)
            sp = sa = None
            if sw and sw[0] <= t < sw[3]:
                sp = round(min(1.0, (t-sw[0])/(sw[1]-sw[0])), 3); sa = 1.0 if t < sw[2] else round(max(0.0, 1-(t-sw[2])/(sw[3]-sw[2])), 3)
            pt = (round(t-p0, 3) if t-p0 < pa else 99.0) if (pills and p0 <= t < p1) else -1
            kt = (round(t-k0, 3) if t-k0 < 0.6 else 99.0) if (stk and k0 <= t < k1) else -1
            cp = round(t/CA, 3) if CA and t < CA else 1.0; lp = round(t/LA, 3) if LA and t < LA else 1.0
            ha = round(max(0.0, (hend-t)/0.3), 3) if (HF and HF[0] <= t < hend) else 1.0
            qk = (None if t < q0 else round(min(0.45, t-q0), 3)) if q else None
            lk = (None if t < 0.2 else round(min(0.4, t-0.2), 3)) if ac else None
            return (ci, sp, sa, bool(hk and t < hend), pt, kt, cp, lp, ha, qk, lk)
        cnt = [0]
        def render(key):
            ci, sp, sa, hon, pt, kt, cp, lp, ha, qk, lk = key; pth = f"{WK}/o{i}_{cnt[0]}.png"; cnt[0] += 1
            overlay(ctx[ci], stat if sp is not None else None, pth, card=sc.get("card"), loc=sc.get("loc"),
                    stat_prog=sp if sp is not None else 1.0, stat_alpha=sa if sa is not None else 1.0,
                    hook=hk if hon else None, pills=pills, pill_t=pt, stk=stk, stk_t=kt, card_p=cp, loc_p=lp, hook_a=ha,
                    qcard=q, q_p=qk, lt=ac, lt_p=lk)
            return pth
        with open(f"{WK}/ol{i}.txt","w") as fh: fh.write(gfx.tl_track(D, bps, anims, state, render))
        c = f"{WK}/sc{i}.mp4"
        if ischart:
            fd = f"{WK}/ch{i}"; os.system(f"rm -rf {fd}")
            if isinstance(cid, dict): gfx.chart_frames(cid, D, fd, W, H)
            else: chart_frames(cid.split(":")[1], D, fd)
            if V8 and clips:   # v8: soft push-through from the previous shot into the chart
                lp = f"{WK}/last{i}.png"
                subprocess.run(["ffmpeg","-y","-v","error","-sseof","-0.1","-i",clips[-1],"-frames:v","1","-vf",f"scale={W}:{H}:flags=lanczos",lp])
                gfx.blend_in(fd, lp, 9, W, H)
            vin = ["-framerate","30","-i",f"{fd}/%04d.png"]; vf = f"[0:v]fps=30,{SCL}setsar=1,{BT709}[bg]"; nv = 1
        else:
            nv = len(plan); vin = []; parts = []
            for j, (sh, ss, sd) in enumerate(plan):
                vin += ["-ss", f"{ss:.2f}", "-stream_loop","-1","-i",f"{OUT}/clips/{sh}.mp4"]
                if sc.get("blur") == "force" or (ac and ac.get("show", "blur") != "crop"):   # 2026-11-05: full-screen 9:16 crop by default (user: blur band looked weak)
                    if SCL: parts.append(f"[{j}:v]{BT709},trim=0:{sd:.3f},setpts=PTS-STARTPTS[t{j}];" + gfx.blur_fill_vf(f"t{j}", sd, f"q{j}") + f";[q{j}]{SCL}setsar=1[p{j}]")
                    else: parts.append(f"[{j}:v]{BT709},trim=0:{sd:.3f},setpts=PTS-STARTPTS[t{j}];" + gfx.blur_fill_vf(f"t{j}", sd, f"p{j}"))
                else:
                    zin = j % 2 == 0
                    ez = f"(0.5-0.5*cos(PI*min(t/{sd:.2f},1)))"
                    ex = f"(iw-ow)/2*(1-{ez})" if zin else f"(iw-ow)/2*{ez}"
                    ey = f"(ih-oh)/2*(1-{ez})" if zin else f"(ih-oh)/2*{ez}"
                    sw_, sh_ = 2*round(1188*OW/1080/2), 2*round(2112*OW/1080/2)
                    srch = IX.get(sh, {}).get("h") or 1080; shp = ",unsharp=5:5:0.45:5:5:0.0" if (V8 and srch < 2000) else ""   # only upscaled sub-4K sources
                    parts.append(f"[{j}:v]{BT709},trim=0:{sd:.3f},setpts=PTS-STARTPTS,crop=ih*9/16:ih,scale={sw_}:{sh_}:flags=lanczos,setsar=1,fps=30,crop={OW}:{OH}:'{ex}':'{ey}'{shp},{GRADE}[p{j}]")
            vf = ";".join(parts) + ";" + "".join(f"[p{j}]" for j in range(nv)) + f"concat=n={nv}:v=1:a=0[bg]"
        subprocess.run(["ffmpeg","-y","-v","error",*vin,
          "-f","concat","-safe","0","-i",f"{WK}/ol{i}.txt","-i",f"{WK}/s{i}.mp3","-filter_complex",
          vf+f";[{nv}:v]format=rgba,fps=30{',' + SCL[:-1] if SCL else ''}[ov];[bg][ov]overlay=0:0,{BT709},format=yuv420p[v];[{nv+1}:a]apad[a]",
          "-map","[v]","-map","[a]","-t",f"{D:.3f}","-c:v","libx264","-preset","veryfast" if not V8 else "faster","-crf",CRF,
          *(["-profile:v","high","-g","60","-bf","2"] if V8 else []),*COLOR_OUT,
          "-c:a","aac","-ar","44100","-ac","2","-b:a","160k",c], check=True)
        if V10:
            ct_ = (sc.get("card") or {}).get("type")
            if ct_ in ("quote", "headline", "stack"): EV10.append(("paper", T0+0.15, -2.0))
            elif ct_ == "doc": EV10.append(("pen", T0+0.8, -2.0))
            elif ct_: EV10.append(("click", T0+0.3, -2.0))
            if stat: EV10.append(("tick", T0+st0, -2.0))
            if isinstance(sc.get("chart"), dict):
                try:
                    ev_, _, _ = gfx.chart_steps(sc["chart"], D); EV10.extend(("click", T0+x[2], -5.0) for x in ev_ if x[2] > 0.3)
                except Exception: pass
        clips.append(c); times.append((T0, T0+D)); T0 += D
        punch.append(bool(i == 0 or stat or sc.get("card") or q or ischart or "?" in text or sc.get("vo_punch")))
        print("scene", i, round(D, 2), "shots", [round(x[2], 1) for x in plan] if plan else "chart", flush=True)
    with open(f"{WK}/sl.txt","w") as fh: fh.write("\n".join(f"file '{c}'" for c in clips))
    subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",f"{WK}/sl.txt","-c","copy",f"{WK}/voice_cut.mp4"], check=True)
    T = dur(f"{WK}/voice_cut.mp4")
    segs = [(a, b, float(scenes[k]["vo_gain"])) if "vo_gain" in scenes[k] else None for k, (a, b) in enumerate(times)]
    auto = mixbus.auto_contour(times, punch); segs = [s_ or a_ for s_, a_ in zip(segs, auto)]
    music_path = MUSIC
    if V8:   # v8: one library track per Short (recent tracks skipped, shared log with long-form); its real ending lands on the last frame
        mus = spec.get("music") or {}; mood = mus.get("mood") or (mus.get("moods") or ["doc"])[0]
        music_path = f"{WK}/music_bed.wav"
        bed_ = [(0.0, mus.get("track") or mood)]
        if V10 and not mus.get("track"):   # two cues: hook cue, then a new track at the turn (scene "turn": true, else the scene start nearest 45 %)
            m2 = mus.get("mood2") or {"doc": "pulse", "tense": "doc", "light": "doc", "ambient": "pulse", "pulse": "tense"}.get(mood, "doc")
            kt_ = next((k for k, sc in enumerate(scenes) if sc.get("turn")), None)
            tt_ = times[kt_][0] if kt_ is not None else min((a for a, b in times[1:]), key=lambda a: abs(a-0.45*T), default=0.45*T)
            bed_ = [(0.0, f"{mood}#a"), (tt_, f"{m2}#b")]
        tr_, _ = musiclib.build_bed(bed_, T, music_path, xfade=0.8 if V10 else 1.6, video=os.path.basename(FINAL) if LOG_USED else "")
        print("V8 music", [(t_, musiclib.load()[t_]["title"], musiclib.load()[t_]["mood"]) for t_ in tr_], flush=True)
    natw = None
    if V9 and NATSEG and spec.get("nat", True) is not False:
        natw = f"{WK}/nat_bed.wav"; nlog = natlib.build(NATSEG, T, natw)
        print(f"V9 nat: {len(NATSEG)} segments, sources {sorted(set(str(x[1]) for x in nlog))}", flush=True)
    extra10 = {}
    if V10:
        import sfxlib
        LEG = {"whoosh": ("whoosh", -2.0), "whoosh_soft": ("whoosh", -6.0), "hit": ("boom", -3.0), "riser": ("riser", -2.0), "click": ("click", 0.0), "slice": ("click", -2.0)}
        ev = [(LEG[n][0], t, LEG[n][1]) for n, t in SFX if n in LEG] + EV10
        res = sfxlib.resolve(ev, seed=os.path.basename(FINAL), log_video=os.path.basename(FINAL) if LOG_USED else None)
        sfxw = f"{WK}/sfx_bed.wav"; nsfx = sfxlib.render(res, T, sfxw)
        print(f"V10 sound: sfx {nsfx} {sorted(set(e[0] for e in ev))}", flush=True)
        extra10 = dict(duck_curve=[(0.0, 3.0, float(spec.get("hook_music_db", -15.0)))], swell_db=4.0, sfx_wav=sfxw, sfx_db=float(spec.get("sfx_db", 0.0)), dips_per3=4)
    mixbus.mix(f"{WK}/voice_cut.mp4", music_path, SFX, T, FINAL, PEAK=PEAK, VOL=VOL, vo_segs=segs, fade=1.5 if V8 else 2.0,
               **({"duck_db": float(spec.get("music_db", -18.0)), "nat": natw, "nat_db": tuple(spec.get("nat_db", [-22.0, -13.0]))} if V9 else {}), **extra10)
    if V9:
        try: mixbus.phone_check(FINAL)
        except Exception as e_: print("PHONE CHECK failed", e_, flush=True)
        vx = sorted(set(v for _, v in VOX)); print(f"V9 voices: {len(vx)} {vx}; quote/actuality scenes {sum(1 for x in scenes if x.get('quote') or x.get('actuality'))}", flush=True)
    if V8:
        if LOG_USED: clipfetch.log_used(os.path.basename(FINAL), sorted(USED))
        print(f"V8 clips: {len(USED)} unique, replaced {len(REPL)} {REPL}; res {OW}x{OH}; crf {CRF}; render time {(_time.time()-_T_START)/60:.1f} min", flush=True)
    nw = sum(len((sc.get("text") or "").split()) for sc in scenes)
    print(f"STATS shots {len(shots_all)} avg {T/len(shots_all):.2f}s max {max(shots_all):.1f}s words {nw} WPM {nw/T*60:.0f}", flush=True)
    if TITLE:
        s0=scenes[0]; sh=COVER[0] or s0.get("chart") or s0.get("clip"); sh=sh[0] if isinstance(sh,list) else sh
        if isinstance(sh,str) and not sh.startswith("chart:"):
            sh=sh.split("@")[0]
            subprocess.run(["ffmpeg","-y","-v","error","-ss","1","-i",f"{OUT}/clips/{sh}.mp4","-frames:v","1","-vf","crop=ih*9/16:ih,scale=1080:1920","/tmp/cv.png"],check=True)
            os.makedirs(f"{OUT}/covers",exist_ok=True); cp=f"{OUT}/covers/"+os.path.basename(FINAL).replace(".mp4","_cover.jpg")
            import make_short_covers   # 2026-10-30: new cover design every Short, rotating layouts
            lay=make_short_covers.render("/tmp/cv.png",TITLE,cp,spec.get("cover")); print("cover",cp,"layout",lay)
    print(T)

asyncio.run(main())
