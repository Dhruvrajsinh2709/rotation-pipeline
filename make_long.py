import sys as _s; _s.path.insert(0,'/workspace/work/yt'); import wordtime
"""CNBC-style long-form (16:9) explainer: B-roll + VO, yellow stat callouts, chapter cards, source credits.
TLDR-style opener devices (sting, question, subscribe, stack/doc/pills cards) + running captions added 2026-10-29 (opener.py)."""
import asyncio, subprocess, sys, json, os
import edge_tts
from PIL import Image as _PILI
_SK = [False]
_orig_save = _PILI.Image.save
def _save(self, fp, *a, **k):
    if _SK[0] and isinstance(fp, str) and fp.endswith(".png") and os.path.exists(fp): return None
    return _orig_save(self, fp, *a, **k)
_PILI.Image.save = _save
sys.path.insert(0, '/workspace/work/yt'); import gfx, opener, clipfetch, musiclib, natlib, v9gfx
from PIL import ImageFilter, Image, ImageDraw, ImageFont

OUT = "/workspace/work/yt/long"; CL = "/workspace/work/yt/clips"; W, H = 1920, 1080
VOICE = "en-US-AndrewMultilingualNeural"; BRAND = "ROTATION"; MUSIC = "/workspace/work/yt/music.mp3"
YEL = (240, 180, 0); WH = (255, 255, 255)

def _accent(spec):
    """Brand-orange accent on the mono look (user 2026-10-30). spec "accent": "#RRGGBB" | null (null/false = pure B/W)."""
    a = spec.get("accent", "#FA4E02")
    if not a: return None
    a = a.lstrip("#"); return tuple(int(a[i:i+2], 16) for i in (0, 2, 4))
F = 30                # v9: output frame rate (long-form v9 default 24 = film cadence of CNBC/WSJ); 30 for v8/v7
VOICE2 = v9gfx.VOICE2   # v9 quote voices (distinct from the narrator); shared list in v9gfx.py (Shorts v9 uses the same pool)
OW, OH = 2560, 1440   # v8: final long-form render size (graphics are drawn at 1920x1080 and lanczos-scaled)
_mf = {}
def MF(sz, wg=700):
    k = (sz, wg)
    if k not in _mf:
        f = ImageFont.truetype("/workspace/work/yt/fonts/Montserrat-VF.ttf", sz); f.set_variation_by_axes([wg]); _mf[k] = f
    return _mf[k]

def shadow_text(im, xy, t, font, fill=WH, r=5):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0]+3, xy[1]+4), t, font=font, fill=(0, 0, 0, 220))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(r))); ImageDraw.Draw(im).text(xy, t, font=font, fill=fill)

def wrap(d, text, font, maxw):
    L = [""]
    for w in text.split():
        x = (L[-1]+" "+w).strip()
        if d.textlength(x, font=font) > maxw and L[-1]: L.append(w)
        else: L[-1] = x
    return L

_logo = None
def logo_mark(h):
    # 2026-10-30: user picked the cream-ribbon-on-orange logo (brand_logo_v2_cream_orange.png) for sting + end card; old mask = banner/logo.jpg (see *.bak16.py)
    global _logo
    if _logo is None: _logo = Image.open('/workspace/work/yt/brand_logo_disc.png').convert('RGBA')
    return _logo.resize((h, h), Image.LANCZOS)

def bug(im):
    # 2026-10-30: user asked to remove the top-left logo + name from long and short videos
    if not os.environ.get('SHOW_BUG'): return
    # top-left: white logo mark + ROTATION wordmark, no yellow bar (matches Shorts, 2026-10-29)
    mk = logo_mark(44); im.alpha_composite(mk, (60, 50)); shadow_text(im, (60+mk.width+12, 50), BRAND, MF(34, 800), r=3)

import re as _re
def countup(big, e):
    m = _re.search(r"[0-9][0-9,]*(\.[0-9]+)?", big)
    if not m or e >= 1: return big
    t = m.group(0); dec = len(m.group(1))-1 if m.group(1) else 0; v = float(t.replace(",", ""))*e
    n = f"{v:,.{dec}f}" if "," in t else f"{v:.{dec}f}"
    return big[:m.start()]+n+big[m.end():]

def overlay(stat, source, path, title=None, chapter=None, card=None, loc=None, stat_prog=1.0, shown=99, stat_alpha=1.0):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if card:
        ct = card.get("type")
        if ct == "stack": opener.stack_card(im, card, MF, wrap, shown)
        elif ct == "doc": opener.doc_card(im, card, MF, wrap)
        elif ct == "pills": opener.pills_card(im, card, MF, shown)
        else: gfx.card(im, card, False)
        d = ImageDraw.Draw(im)
        if ct in ("stack", "doc", "pills") and card.get("source"): source = card["source"]
        else: source = None
    if title:  # opening title card
        im = Image.new("RGBA", (W, H), (0, 0, 0, 110)); d = ImageDraw.Draw(im)
        f = MF(104, 800); L = wrap(d, title, f, 1300); y = H/2 - len(L)*62
        d.rectangle([140, y+10, 156, y+len(L)*124-14], fill=YEL)
        for l in L: shadow_text(im, (190, y), l, f); y += 124
        bug(im); im.save(path); return
    if chapter:  # chapter card: dark band with number + name
        num, name = chapter
        im = Image.new("RGBA", (W, H), (0, 0, 0, 120)); d = ImageDraw.Draw(im)
        d.rectangle([140, 430, 156, 650], fill=YEL)
        d.text((190, 430), num.upper(), font=MF(44, 700), fill=YEL)
        shadow_text(im, (190, 500), name, MF(110, 800))
        bug(im); im.save(path); return
    bug(im)
    if loc: gfx.loc_tag(im, loc, 56, 118, False)
    if stat:  # no box: big yellow count-up number, eased pop-in (user 2026-10-29)
        big, label = stat; sz = 170
        e_cnt = 1-(2**(-10*min(stat_prog, 1))) if stat_prog < 1 else 1.0   # count-up over the 0.7 s window
        e_pop = 1-(1-min(stat_prog/0.4, 1))**3
        while d.textlength(big, font=MF(sz, 900)) > 1300: sz -= 6
        f9 = MF(sz, 900); bb = d.textbbox((0, 0), big, font=f9); th = bb[3]-bb[1]; y0 = 300
        shown = countup(big, e_cnt)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
        # soft dark scrim so the yellow number reads on bright footage
        _sc = Image.new("RGBA",(W,H),(0,0,0,0)); ImageDraw.Draw(_sc).rounded_rectangle([W*0.12, y0-30, W*0.88, y0+th+200], 60, fill=(0,0,0,120))
        L.alpha_composite(_sc.filter(ImageFilter.GaussianBlur(50)))
        shadow_text(L, ((W-ld.textlength(shown, font=f9))/2, y0+45-bb[1]), shown, f9, fill=YEL)
        lf = MF(50, 600); shadow_text(L, ((W-ld.textlength(label, font=lf))/2, y0+th+120), label, lf)
        if e_pop < 1:
            sc = 0.86+0.14*e_pop; cx, cy = W/2, y0+(th+90)/2
            L2 = L.resize((int(W*sc), int(H*sc)), Image.LANCZOS); L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            L.alpha_composite(L2, (int(cx-cx*sc), int(cy-cy*sc))); L.putalpha(L.getchannel("A").point(lambda v: int(v*e_pop)))
        if stat_alpha < 1: L.putalpha(L.getchannel("A").point(lambda v: int(v*stat_alpha)))
        im.alpha_composite(L); d = ImageDraw.Draw(im)
    if source:
        shadow_text(im, (60, H-70), "Source: " + source, MF(26, 500), fill=(235, 235, 235), r=3)
    im.save(path)

def chart_frames(kind, D, d_out):
    os.makedirs(d_out, exist_ok=True); n = int(D*30)+1
    BG = (6, 12, 28); GRID = (30, 42, 70); G = YEL; GR = (140, 150, 175)
    for k in range(n):
        p = min(1, k/(n*0.5)); e = 1-(1-p)**3
        im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
        if kind == "price":
            d.text((120, 110), "Jio Platforms share price", font=MF(64, 800), fill=WH); d.text((120, 195), "October 28, 2026, in rupees", font=MF(36, 500), fill=GR)
            pts = [("IPO price", 1119), ("Listing", 1358), ("Close", 1419)]
            x0, x1, yb, yt = 220, 1560, 900, 360; lo, hi = 1000, 1550
            for v in (1100, 1200, 1300, 1400, 1500):
                y = yb-(v-lo)/(hi-lo)*(yb-yt); d.line([(x0-40, y), (x1+60, y)], fill=GRID, width=2); d.text((x1+90, y-20), f"{v:,}", font=MF(30, 500), fill=GR)
            xs = [x0+i*(x1-x0)/2 for i in range(3)]; ys = [yb-(v-lo)/(hi-lo)*(yb-yt) for _, v in pts]
            seg = e*2; poly = [(xs[0], ys[0])]
            for i in range(2):
                if seg > i:
                    t = min(1, seg-i); poly.append((xs[i]+(xs[i+1]-xs[i])*t, ys[i]+(ys[i+1]-ys[i])*t))
            d.polygon(poly+[(poly[-1][0], yb), (xs[0], yb)], fill=(70, 55, 10)); d.line(poly, fill=G, width=10, joint="curve")
            for i, (lab, v) in enumerate(pts):
                if seg >= i-0.02:
                    d.ellipse([xs[i]-15, ys[i]-15, xs[i]+15, ys[i]+15], fill=WH)
                    t = f"₹{v:,}"; tw = d.textlength(t, font=MF(50, 800)); d.text((xs[i]-tw/2, ys[i]-95), t, font=MF(50, 800), fill=WH)
                    tw = d.textlength(lab, font=MF(34, 500)); d.text((xs[i]-tw/2, yb+25), lab, font=MF(34, 500), fill=GR)
            if e > 0.99:
                d.rectangle([1320, 110, 1600, 195], fill=G); d.text((1345, 118), "+26.8%", font=MF(54, 900), fill=BG)
            d.text((60, H-60), "Source: NSE, Reuters", font=MF(26, 500), fill=GR)
        else:
            d.text((120, 110), "Who wanted in", font=MF(64, 800), fill=WH); d.text((120, 195), "Times subscribed, by investor type", font=MF(36, 500), fill=GR)
            bars = [("Institutions", 70.55), ("Overall", 22.19), ("Non-institutional", 14.0), ("Retail", 2.72)]
            for i, (lab, v) in enumerate(bars):
                y = 320+i*165; w = int(1150*v/70.55*e)
                d.text((120, y+18), lab, font=MF(38, 600), fill=GR)
                d.rectangle([520, y, 520+max(w, 16), y+85], fill=G if lab != "Overall" else WH)
                d.text((545+max(w, 16), y+14), f"{v*e:.1f}x", font=MF(50, 800), fill=WH)
            d.text((60, H-60), "Source: NSE, Business Standard", font=MF(26, 500), fill=GR)
        im.save(f"{d_out}/{k:04d}.png")

def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode())

WORDS = {}
async def tts(i, text, rate="+3%", voice=None):
    import hashlib
    voice = voice or VOICE; h = hashlib.md5((f"{VOICE}|{rate}|{text}" if voice == VOICE else f"{voice}|{rate}|{text}").encode()).hexdigest()[:12]; cp = f"{OUT}/tts_{h}"
    if os.path.exists(cp+".json") and os.path.exists(cp+".mp3"): return cp+".mp3", [tuple(x) for x in json.load(open(cp+".json"))]
    a, w = await _tts_retry(i, text, rate, voice); os.replace(a, cp+".mp3"); json.dump(w, open(cp+".json", "w")); return cp+".mp3", w

async def _tts_retry(i, text, rate, voice=None):
    for k in range(5):
        try: return await _tts(i, text, rate, voice)
        except Exception as e:
            if k == 4: raise
            await asyncio.sleep(6*(k+1))

async def _tts(i, text, rate="+3%", voice=None):
    if wordtime.needs_align(voice or VOICE): ws = await wordtime.synth(text, voice or VOICE, rate, f"{OUT}/s{i}.mp3")
    else: ws = None
    c = edge_tts.Communicate(text, voice or VOICE, rate=rate, boundary="WordBoundary") if ws is None else None; ws = ws or []
    if c is not None:
     with open(f"{OUT}/s{i}.mp3", "wb") as fh:
        async for ch in c.stream():
            if ch["type"] == "audio": fh.write(ch["data"])
            elif ch["type"] == "WordBoundary": ws.append((ch["offset"]/1e7, (ch["offset"]+ch["duration"])/1e7, ch["text"]))
    # re-attach punctuation from the script so phrases break naturally
    toks = text.split(); j = 0; out = []
    for (a, b, w) in ws:
        while j < len(toks) and w.lower().strip(".,?!;:'\"") not in toks[j].lower(): j += 1
        out.append((a, b, toks[j] if j < len(toks) else w)); j += 1
    return f"{OUT}/s{i}.mp3", out

SFX = []
PEAK = {'click':0.193,'hit':0.087,'riser':2.535,'slice':0.188,'whoosh':1.065,'whoosh_soft':0.715}
VOL = {'click':0.35,'hit':0.9,'riser':0.35,'slice':0.4,'whoosh':0.35,'whoosh_soft':0.3}
GRADE = 'eq=contrast=1.06:saturation=0.94:gamma=0.98:brightness=-0.03,colorbalance=rs=-0.02:bs=0.03:rh=0.03:bh=-0.02,vignette=angle=PI/5,noise=alls=4:allf=t'
GRADE8 = 'eq=contrast=1.05:saturation=0.96:gamma=0.99:brightness=-0.02,vignette=angle=PI/7'   # v8: no grain, lighter vignette
UPSHARP = 'unsharp=5:5:0.45:5:5:0.0'   # v8: only on sources below 1440p that get upscaled'
BT709 = "setparams=colorspace=bt709:color_trc=bt709:color_primaries=bt709:range=tv"
COLOR_OUT = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
MAX_SHOT = 6.0; TARGET_SHOT = 3.5   # Study 2: stock clips max 6 s, average ~3.5 s
DEVICES = ("map", "flow", "timeline", "icons", "morph")   # v7 full-screen animated devices (gfx.<key>_frames)
DARK_LUMA = 0.12                     # v7: auto-skip near-black clips (mean luma below this)
FALLBACK_POOL = ["hd_4308", "hd_42085", "hd_41541", "hd_4401", "hd_4453", "hd_18249"]
CLIPDUR = {}
def cdur(cid):
    if cid not in CLIPDUR: CLIPDUR[cid] = dur(f"{CL}/{cid}.mp4")
    return CLIPDUR[cid]
def base_dur(sc, D, first_agenda):
    if sc.get("sting"): D = max(D, 3.0)
    elif sc.get("question"): D = max(D, 3.5)
    elif sc.get("subscribe"): D = max(D, 3.0)
    elif sc.get("_agenda") is not None: D = max(D, 3.0 if first_agenda else 2.5)   # v7: later agenda 2.5 s (+2.5 s breath)
    elif sc.get("_breath"): D = max(D, float(sc.get("min", 2.5)))
    elif sc.get("_endcard"): D = max(D, float(sc.get("min", 10)))
    if (sc.get("chart") and isinstance(sc["chart"], dict)) or (isinstance(sc.get("clip"), dict)) or any(sc.get(k) for k in DEVICES): D = max(D, 8.0)  # chart/device scenes 8-20 s
    return max(D, sc.get("min", 0))

async def main(spec):
    import mixbus
    os.makedirs(OUT, exist_ok=True); clips = []; T0 = 0.0; SFX.clear(); rate = spec.get("rate", "+3%")
    scenes = [dict(x) for x in spec["scenes"]]; chapters = spec.get("chapters"); CE = float(spec.get("change_every", 3.0))
    global OW, OH, YEL, GRADE, F
    V8 = spec.get("v8", True)
    if V8:
        th_ = spec.get("theme", "light")   # user 2026-10-30 "use c": light cream graphic panels, orange + cobalt (theme "mono" = old dark look)
        if th_ in ("mono", "light"): ACC_ = _accent(spec); gfx.set_theme("mono", ACC_); opener.set_theme("mono", ACC_); YEL = ACC_ or (255, 255, 255)
        if th_ == "light": gfx.set_theme("light", ACC_ or (250, 78, 2))
        OW, OH = spec.get("res", [2560, 1440]); GRADE = GRADE8
    else: OW, OH = W, H
    USED = set(); RECENT = clipfetch.recent_used(int(spec.get("recent_videos", 4))) if V8 else set(); REPL = []; IX = clipfetch.load_index() if V8 else {}
    import time as _time; _t_start = _time.time()
    # ---- v9 (Study 5, user said "fix it" 2026-10-30): 24 fps, match gate, voices, nat sound, inset, title card, credits ----
    V9 = V8 and spec.get("v9", True)
    V10 = V9 and spec.get("v10", True)   # Study 10 sound: a new track per chapter, level curve, music-off stretches, SFX families
    F = int(spec.get("fps", 24)) if V9 else 30; gfx.FPS = F; opener.FPS = F
    MATCH_MIN = float(spec.get("match_min", 2.0)); PICKS = []; FBN = [0]; NATSEG = []; VOX = []; FULLT = []; INSETS = []
    if V9: gfx.AXIS_DEFAULT = bool(spec.get("axis", True)); gfx.PICTO_DEFAULT = bool(spec.get("picto", True)); gfx.HL_GREY = True
    TEX = gfx.panel_texture("/workspace/work/yt/data/texture_v9.png") if V9 and spec.get("texture", True) else None
    # v8 ending: closing line over one strong final shot, then a short minimal end card (no spoken pitch)
    if spec.get("closer"):
        cz = spec["closer"]; cz = {"text": cz} if isinstance(cz, str) else dict(cz)
        scenes.append({"clip": cz.get("clip", scenes[-1].get("clip")), "text": cz["text"], "_closer": True, "keywords": False, "shot": 99, "max_shot": 14,
                       "tags": cz.get("tags"), "min": cz.get("min", 0)})
    if spec.get("endcard", True if V8 and spec.get("closer") else False):
        ec = spec.get("endcard"); ec = dict(ec) if isinstance(ec, dict) else {}; ec.setdefault("dur", 10)
        scenes.append({"clip": "hd_151", "_endcard": ec, "min": float(ec.get("dur", 10)), "keywords": False})
    # v7 ending block: verdict -> bookend callback -> dated catalyst, footage only (no cards / pops), 4-5 s shots
    for e in spec.get("ending", []) or []:
        e = {"text": e} if isinstance(e, str) else dict(e); e["ending"] = True; e.setdefault("clip", scenes[-1].get("clip", "hd_151")); scenes.append(e)
    for sc in scenes:
        if sc.get("ending"): sc["keywords"] = False; sc.setdefault("shot", 4.5); sc.pop("stat", None); sc.pop("card", None)
    if any(sc.get("_endcard") for sc in scenes):   # keep the end card last
        ecs = [sc for sc in scenes if sc.get("_endcard")]; scenes = [sc for sc in scenes if not sc.get("_endcard")] + ecs[-1:]
    # v9: open on the real place (establishing shot + dateline), series title card instead of the logo sting, end card over the same place
    op = spec.get("open_place") if V9 else None
    if op:
        op = dict(op); scenes.insert(0, {"clip": op.get("clip"), "tags": op.get("tags"), "text": op.get("text"), "_open": op, "keywords": False, "shot": 99,
                                         "max_shot": 14, "min": float(op.get("dur", 0 if op.get("text") else 3.5)), "nat": op.get("nat")})
    tc = spec.get("title_card") if V9 else None
    if tc:
        tc = {"title": tc} if isinstance(tc, str) else dict(tc)
        new = {"clip": tc.get("clip"), "tags": tc.get("tags") or (op or {}).get("tags"), "_title": tc, "keywords": False, "shot": 99, "max_shot": 8, "min": float(tc.get("dur", 3.6))}
        k = next((k for k, sc in enumerate(scenes) if sc.get("sting")), None)
        if k is None: k = next((k for k, sc in enumerate(scenes) if sc.get("question") or sc.get("agenda") is not None), None)
        if k is not None and scenes[k].get("sting"): scenes[k] = new
        elif k is not None: scenes.insert(k, new)
    if V9:
        for sc in scenes:
            if isinstance(sc.get("_endcard"), dict):
                bgc = sc["_endcard"].get("bg_clip", "__OPEN__" if op else None)
                if bgc: sc["_ec_bg"] = bgc
            if sc.get("quote") or sc.get("actuality"): sc["keywords"] = False
            if sc.get("actuality") or sc.get("_ec_bg"): sc["shot"] = 99; sc["max_shot"] = 60
    # v7 end screen (~20 s): dimmed footage + watch-next slot + subscribe slot, spoken pitch for one earlier video
    es = spec.get("endscreen")
    if es:
        es = dict(es); scenes.insert(len(scenes)-(1 if scenes[-1].get("_endcard") else 0), {"clip": es.get("clip", scenes[-1].get("clip", "hd_151")), "text": es.get("text"), "_endscreen": es,
                                      "min": float(es.get("dur", 20)), "keywords": False, "shot": es.get("shot", 5.0), "max_shot": 7.0})
    # v7 chapter breath: each later agenda card (2.5 s) is followed by a 2.5 s establishing shot, no VO, music up
    if spec.get("breath", 2.5):
        out = []; seen_ag = False
        for k, sc in enumerate(scenes):
            out.append(sc)
            if sc.get("agenda") is not None or (chapters and sc.get("chapter")):
                if seen_ag:
                    cl = sc.get("breath_clip") or (sc["clip"][1] if isinstance(sc.get("clip"), list) and len(sc["clip"]) > 1 else None)
                    if not cl and k+1 < len(scenes): nc = scenes[k+1].get("clip"); cl = nc[0] if isinstance(nc, list) else nc
                    if isinstance(cl, str): out.append({"clip": cl, "_breath": True, "keywords": False, "min": float(spec.get("breath", 2.5)), "loc": sc.get("breath_loc")})
                    elif spec.get("v8", True): out.append({"tags": sc.get("breath_tags") or sc.get("tags") or [], "_breath": True, "keywords": False, "min": float(spec.get("breath", 2.5)), "loc": sc.get("breath_loc")})
                seen_ag = True
        scenes = out
    # chapter scenes -> agenda (chapter list) when the spec lists chapters
    for sc in scenes:
        if sc.get("agenda") is not None: sc["_agenda"] = int(sc["agenda"])-1
        elif chapters and sc.get("chapter"):
            nm = sc["chapter"][1]; sc["_agenda"] = chapters.index(nm) if nm in chapters else 0
    # ---- pass 1: voice ----
    QV = {}
    def qvoice(who, want=None):   # v9: each quoted speaker gets their own AI voice, never the narrator's
        if want: return want
        pool = list(dict.fromkeys(([spec["voice2"]] if spec.get("voice2") else []) + VOICE2))
        if who not in QV: QV[who] = pool[len(QV) % len(pool)]
        return QV[who]
    for i, sc in enumerate(scenes):
        if V9 and sc.get("quote"):
            q = sc["quote"]; qa, qw = await tts(f"q{i}", q["text"], spec.get("rate2", "+6%"), qvoice(q.get("who", ""), q.get("voice")))
            if sc.get("text"):
                na, nw = await tts(f"p{i}", sc["text"], rate); g = dur(na)+0.35; cat = f"{OUT}/qcat_{i}.mp3"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", na, "-i", qa, "-filter_complex", "[0:a]aresample=24000,apad=pad_dur=0.35[a0];[1:a]aresample=24000[a1];[a0][a1]concat=n=2:v=0:a=1",
                                "-ac", "1", "-b:a", "96k", cat], check=True)
                sc["_a"], sc["_w"], sc["_q0"] = cat, list(nw) + [(a+g, b+g, w) for (a, b, w) in qw], g; sc["_vox"] = [(0.0, "narrator"), (g, QV.get(q.get("who", ""), "voice2"))]
            else: sc["_a"], sc["_w"], sc["_q0"] = qa, qw, 0.0; sc["_vox"] = [(0.0, QV.get(q.get("who", ""), "voice2"))]
            sc["_D"] = dur(sc["_a"])+0.45
        elif sc.get("text"): sc["_a"], sc["_w"] = await tts(f"p{i}", sc["text"], rate); sc["_D"] = dur(sc["_a"])+0.35; sc["_vox"] = [(0.0, "narrator")]
        else: sc["_D"] = 0.0
    if V9 and any(sc.get("actuality") for sc in scenes):   # v9: public-domain primary audio (hearings, briefings, press conferences)
        import mixbus as _mb
        refs = [sc["_a"] for sc in scenes if sc.get("_a") and not sc.get("quote")][:3]
        Lref = sum(_mb._ebur(r)[0] for r in refs)/max(1, len(refs)) if refs else -18.0
        for i, sc in enumerate(scenes):
            ac = sc.get("actuality")
            if not ac: continue
            src = f"{CL}/{ac['clip']}.mp4" if ac.get("clip") else ac["file"]; d_ = float(ac["dur"]); outw = f"{OUT}/act_{i}.wav"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{float(ac.get('ss', 0)):.2f}", "-t", f"{d_:.2f}", "-i", src, "-vn", "-ac", "1", "-ar", "24000",
                            "-af", f"highpass=f=90,lowpass=f=9000,afade=t=in:d=0.06,afade=t=out:st={max(0, d_-0.15):.2f}:d=0.15", outw], check=True)
            La = _mb._ebur(outw)[0]; outg = f"{OUT}/actg_{i}.wav"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", outw, "-af", f"volume={Lref-La+float(ac.get('gain_db', 0)):.2f}dB,alimiter=limit=0.9", outg], check=True)
            sc["_a"], sc["_w"], sc["_D"] = outg, [], d_+0.3; sc["_vox"] = [(0.0, "actuality:" + ac.get("who", "speaker"))]
    def plan_D():
        out = []; seen = False
        for sc in scenes:
            fa = sc.get("_agenda") is not None and not seen
            if sc.get("_agenda") is not None: seen = True
            out.append(base_dur(sc, sc["_D"], fa))
        return out
    # ---- subscribe card at ~60 % of the runtime (Study 2: never in the opener) ----
    sub = spec.get("subscribe")
    if sub and not any(sc.get("subscribe") for sc in scenes):
        Ds = plan_D(); tot = sum(d_ for d_, sc in zip(Ds, scenes) if not sc.get("_endscreen")); acc = 0; best = None; ag = [k for k, sc in enumerate(scenes) if sc.get("_agenda") is not None]
        for k in range(1, len(scenes)):
            acc += Ds[k-1]
            if ag and k <= ag[0]: continue
            if scenes[k].get("_agenda") is not None: continue   # keep chapter starts clean
            if best is None or abs(acc-0.6*tot) < abs(best[1]-0.6*tot): best = (k, acc)
        rh = [k for k, sc in enumerate(scenes) if sc.get("rehook")]   # v7: subscribe right after the re-hook scene if one is marked
        if rh and rh[0]+1 < len(scenes): best = (rh[0]+1, 0)
        sd = {"line": sub, "text": None} if isinstance(sub, str) else sub
        new = {"clip": "hd_151", "subscribe": sd.get("line", "New deep dives every weekend"), "text": sd.get("text")}
        if new["text"]: new["_a"], new["_w"] = await tts("sub", new["text"], rate); new["_D"] = dur(new["_a"])+0.35
        else: new["_D"] = 0.0
        scenes.insert(best[0], new)
    Ds = plan_D()
    # pool for extra shots: neighbouring scenes' clips + spec "pool"
    def clips_of(sc):
        if sc.get("chart") or sc.get("sting") or sc.get("question") or sc.get("subscribe") or sc.get("_endcard") or any(sc.get(k) for k in DEVICES): return []
        c = sc.get("clip"); c = [] if not isinstance(c, (list, str)) else ([c] if isinstance(c, str) else list(c))
        return [x for x in c if os.path.exists(f"{CL}/{x.split('@')[0]}.mp4")]
    shot_lens = []; gfx_events = []; kw_count = 0; times = []; punch = []; sting_at = None; agenda_at = []; prev_full = False
    def ok_clip(cid, L):
        return os.path.exists(f"{CL}/{cid}.mp4") and cdur(cid) >= L+0.4 and not IX.get(cid, {}).get("bad")
    def good_ss(cid, L, pref=None):
        dd = cdur(cid)
        if pref is not None and pref+L <= dd-0.1: return round(pref, 2)
        return round(max(0.0, min(dd-L-0.15, 0.22*(dd-L))), 2)
    def _short_attr(at):   # fix19: '"Title" by Artist, CC BY 2.0, via Wikimedia Commons' -> 'Photo: Artist, CC BY 2.0 / Wikimedia Commons'
        import re as _r
        m = _r.search(r'" by (.+?), (CC[^,]*|Public domain|PD[^,]*)', at or "")
        return (f"Photo: {m.group(1)[:34]}, {m.group(2)} / Wikimedia Commons" if m else (at or "")[:60])
    def relaxed_pick(sc, L, own=()):
        """fix19 (2026-11-01): when nothing passes the match gate, take the best-fitting UNUSED, non-dark library clip by the
        scene's tags (score 1.5 -> 1.0 -> 0.5), then by the video-wide tags; clips named for other scenes are never taken."""
        tags = list(sc.get("tags") or []) + list(spec.get("tags") or []); txt = sc.get("text") or ""
        RSV = RESERVED - set(own)
        for tg, mm in ((tags, 1.5), (tags, 1.0), (list(sc.get("tags") or []), 0.5), (list(spec.get("tags") or []), 1.0)):
            if not tg: continue
            for ex in (USED | RECENT | RSV, USED | RSV):
                for k, _ in clipfetch.pick_matched(tg, txt, exclude=ex, n=30, match_min=mm):
                    if k.startswith("_fb_") or not ok_clip(k, L): continue
                    if gfx.clip_luma(f"{CL}/{k}.mp4", good_ss(k, L), L) < DARK_LUMA: continue
                    PICKS.append((sc.get("_i"), k, clipfetch.match_score(IX.get(k, {}), tags, txt), "relaxed")); return k
        return None
    def resolve_unique(plan_, sc, shots, pool, no_fb=False):
        """v8: replace any shot whose clip is already used in this video (or twice in this plan) with an unused clip:
        the scene's own clips first, then library picks by the scene's tags + narration words (recent videos excluded),
        then the neighbour pool. Logs every replacement (REPL)."""
        out_ = []
        own = [x.split("@")[0] for x in shots]
        tags = list(sc.get("tags") or []) + list(spec.get("tags") or [])
        for (sh, ss, L, *rest) in plan_:
            if sh != "__NEW__" and (sh.startswith("_fb_") or (sh not in USED and ok_clip(sh, 0) and not IX.get(sh, {}).get("bad")
                                                              and not (V9 and sh in RESERVED and sh not in own))):   # fix19: never steal a clip named for another scene
                USED.add(sh); out_.append((sh, ss, L, *rest)); continue
            if V9:   # v9 match gate: only clips that show the scene's subject; nothing matches -> designed plate, never a random clip
                txt = sc.get("text") or ""; RSV = RESERVED - set(own)
                def first_ok(lst):
                    a_ = next((x for x in lst if x not in USED and ok_clip(x, L) and gfx.clip_luma(f"{CL}/{x}.mp4", good_ss(x, L), L) >= DARK_LUMA), None)
                    return a_ or next((x for x in lst if x not in USED and ok_clip(x, L)), None)
                own_ = [x for x in own if x not in USED and not x.startswith("_fb_")]
                strong = [k for k, _ in clipfetch.pick_matched(tags, txt, exclude=USED | RECENT | RSV, n=25, match_min=max(MATCH_MIN, 2.5))]
                alt = first_ok(own_) or first_ok(strong)
                if alt is None and out_ and not out_[-1][0].startswith("_fb_"):   # no strong match: hold the previous shot longer instead of a weak clip or a plate
                    psh, pss, pL, *pr = out_[-1]
                    if pss + pL + L + 0.15 <= cdur(psh): out_[-1] = (psh, pss, pL+L, *pr); PICKS.append((sc.get("_i"), psh, "-", "extend")); continue
                if alt is None and sh == "__NEW__" and no_fb: return None   # change guard: keep the shot unsplit
                if alt is None:
                    weak = [k for k, _ in clipfetch.pick_matched(tags, txt, exclude=USED | RECENT | RSV, n=25, match_min=MATCH_MIN)]
                    weak += [x for x in pool if x not in USED and x not in RSV and clipfetch.match_score(IX.get(x, {}), tags, txt) >= MATCH_MIN]
                    weak += [k for k, _ in clipfetch.pick_matched(tags, txt, exclude=USED | RSV, n=25, match_min=MATCH_MIN)]
                    alt = first_ok(weak)
                if alt is None:   # fix19: relaxed library ladder (by tags, unused) instead of a black plate
                    alt = relaxed_pick(sc, L, own)
                    if alt is None and out_ and not out_[-1][0].startswith("_fb_"):
                        psh, pss, pL, *pr = out_[-1]
                        if pss + pL + L + 0.15 <= cdur(psh): out_[-1] = (psh, pss, pL+L, *pr); PICKS.append((sc.get("_i"), psh, "-", "extend")); continue
                if alt is None and sh == "__NEW__" and no_fb: return None
                if alt is None: alt = make_fb(sc, L); PICKS.append((sc.get("_i"), alt, 0, "fallback-plate"))
                else: PICKS.append((sc.get("_i"), alt, clipfetch.match_score(IX.get(alt, {}), tags, txt), "replace" if sh != "__NEW__" else "split"))
                REPL.append(f"{sh}->{alt}"); USED.add(alt); out_.append((alt, good_ss(alt, L) if not alt.startswith("_fb_") else 0.0, L, *rest)); continue
            cands = [x for x in own if x not in USED]
            cands += clipfetch.pick(tags, sc.get("text") or "", exclude=USED | RECENT, n=25)
            cands += [x for x in pool if x not in USED and x not in RECENT]
            cands += clipfetch.pick(tags, sc.get("text") or "", exclude=USED, n=25, min_score=0)
            alt = next((x for x in cands if x not in USED and ok_clip(x, L) and gfx.clip_luma(f"{CL}/{x}.mp4", good_ss(x, L), L) >= DARK_LUMA), None)
            if alt is None: alt = next((x for x in cands if x not in USED and ok_clip(x, L)), sh if sh != "__NEW__" else own[0])
            REPL.append(f"{sh}->{alt}"); USED.add(alt); out_.append((alt, good_ss(alt, L), L, *rest))
        return out_
    RESERVED = set()
    for sc_ in scenes:
        for k_ in ("clip", "breath_clip"):
            v_ = sc_.get(k_)
            for x in ([v_] if isinstance(v_, str) else v_ if isinstance(v_, list) else []): RESERVED.add(str(x).split("@")[0])
        if isinstance(sc_.get("actuality"), dict) and sc_["actuality"].get("clip"): RESERVED.add(sc_["actuality"]["clip"])
    RESERVED.discard("hd_151")
    def make_fb(sc, L):
        """v9 designed plate when no library clip matches the scene (textured panel + the scene's key phrase), as a clip file."""
        FBN[0] += 1; fid = f"_fb_{os.getpid()}_{FBN[0]}"; png = f"{OUT}/{fid}.png"
        kws = sc.get("keywords") if isinstance(sc.get("keywords"), list) else []
        txt = "" if sc.get("quote") else sc.get("fallback_text") or (kws[0] if kws else None) or (sc.get("stat") or [None])[0] or ""   # fix19: never tag/search words on screen
        v9gfx.fallback_plate(png, txt, sc.get("fallback_sub"), sc.get("loc"), TEX)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", png, "-t", f"{max(L, 3)+1.5:.2f}", "-r", str(F), "-vf", "format=yuv420p", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "16", f"{CL}/{fid}.mp4"], check=True)
        IX[fid] = {"title": "fallback plate", "tags": [], "h": 1080, "w": 1920, "source": "rotation"}; return fid
    SRCNAME = {"fed": "Federal Reserve", "dvids": "DVIDS", "wikimedia": "Wikimedia Commons", "nasa": "NASA", "usgov": "US Government"}
    def nat_for(sc):
        n_ = sc.get("nat")
        if n_ is False: return None
        if isinstance(n_, str) and n_ in natlib.load(): return n_
        words_ = (list(n_) if isinstance(n_, list) else []) + list(sc.get("tags") or []) + list(spec.get("tags") or [])
        return natlib.pick(words_) or spec.get("nat_default")
    OPEN_CLIP = []
    if V9:   # pre-choose the music beds (same choice build_bed makes) so the credits can name them
        _mus = spec.get("music") or {}; _mo = [_mus.get("opener", (_mus.get("moods") or ["doc"])[0])] + list(_mus.get("moods") or ["doc"]) + ([_mus["closer"]] if _mus.get("closer") else [])
        PRE_MUS = dict(_mus.get("tracks") or {})
        if V10:
            _ms = list(_mus.get("moods") or ["doc", "pulse", "tense", "doc", "light"]); _nch = max(1, len(spec.get("chapters") or []))
            _mo = [f"{_mus.get('opener', 'tense')}#o", f"{_ms[0]}#1"] + [f"{_ms[min(c, len(_ms)-1)]}#{c+1}" for c in range(1, _nch)] + ([f"{_mus['closer']}#c"] if _mus.get("closer") else [])
            V10_LABELS = _mo
        for m_ in _mo:
            if m_ not in PRE_MUS and m_ not in musiclib.load(): PRE_MUS[m_] = musiclib.pick(m_.split("#")[0], exclude=list(PRE_MUS.values()), seed=f"{os.path.basename(spec['output']) if spec.get('log_used', True) else ''}{m_}")
    def credit_lists():
        srcs = []
        for sc in scenes:
            for o in [sc] + [sc.get(k) for k in ("chart", "card", "quote", "actuality", "map", "flow", "timeline", "icons", "morph") if isinstance(sc.get(k), dict)]:
                for s_ in str(o.get("source") or "").split(";"):
                    s_ = s_.strip()
                    if s_ and s_ not in srcs: srcs.append(s_)
        foot = []; free = set()
        for k in sorted(USED):
            m = IX.get(k, {}); src = m.get("source")
            if not m or k.startswith("_fb_"): continue
            if src in ("mixkit", "coverr"): free.add(src.title())
            elif m.get("attribution"): foot.append(m["attribution"])
            elif src: foot.append(f"{SRCNAME.get(src, src)}: {m.get('title', k)} ({m.get('licence', '')[:60]})")
        if free: foot.insert(0, " and ".join(sorted(free)) + " (free licences)")
        mus = [musiclib.load()[t]["title"] + " (Mixkit)" for t in dict.fromkeys(PRE_MUS.values()) if t in musiclib.load()] if V9 else []
        vox = ["Narration: AI voice (Microsoft Edge neural TTS)."]
        if any(sc.get("quote") for sc in scenes): vox.append("Quotes are real and sourced; read by separate AI voices.")
        if any(sc.get("actuality") for sc in scenes): vox.append("Real audio: " + ", ".join(sorted(set(sc["actuality"].get("credit") or sc["actuality"].get("source", "") for sc in scenes if sc.get("actuality")))) + " (public domain).")
        if NATSEG or spec.get("nat_default"): mus.append("Natural sound: Mixkit")
        return srcs, foot, mus, vox
    STEP10 = []; KW10 = []; EV10 = []; FULLSET = set()
    CHG = []; kw_times = []; dev_at = {}; dark_skips = []; reframes = 0
    for i, sc in enumerate(scenes):
        sc["_i"] = i
        cid = sc.get("clip", "hd_151"); text = sc.get("text") or ""; D = Ds[i]; W_ = sc.get("_w", [])
        full = sc.get("sting") or sc.get("question") or sc.get("subscribe") or (sc.get("_endcard") and not sc.get("_ec_bg"))
        ag = sc.get("_agenda")
        if sc.get("chart"): cid = sc["chart"]
        dev = next((k for k in DEVICES if sc.get(k)), None)
        if isinstance(cid, dict) and cid.get("type") == "morph": dev = "morph"; sc["morph"] = cid
        if dev: cid = sc[dev]
        ischart = bool(full) or isinstance(cid, dict) or (isinstance(cid, str) and cid.startswith("chart:"))
        CHG.append(T0)
        if sc.get("sting"): sting_at = T0
        if ag is not None: agenda_at.append(round(T0, 1))
        ov = f"{OUT}/ov{i}.png"; kw = dict(title=sc.get("title"), chapter=None if ag is not None else sc.get("chapter"), card=sc.get("card"), loc=sc.get("loc"))
        overlay(None, sc.get("source"), ov, **kw)
        ovin = ["-loop", "1", "-i", ov]
        ctype = (sc.get("card") or {}).get("type")
        # ---- keyword pops / punch word (computed before the shot plan so the change guard can see them) ----
        plain = text and W_ and not full and not ischart and ag is None and not sc.get("title") and not sc.get("_endscreen")
        keep = []
        if plain and not spec.get("captions", False) and not sc.get("stat") and not sc.get("card") and sc.get("keywords", True) is not False:
            ks = sc.get("keywords"); ev = []
            if ks:
                for n_, kword in enumerate(ks):
                    key0 = kword.split()[0].strip("$₹%").lower().rstrip("b").replace(",", "")
                    hit = next((W_[k][0] for k in range(len(W_)) if key0 and key0 in W_[k][2].lower().replace(",", "")), None)
                    ev.append((kword, hit if hit is not None else D*(n_+0.5)/len(ks)))
            else:
                for kword, pos in gfx.auto_keywords(text, sc.get("kw_max", 2)):
                    ev.append((kword, W_[min(pos, len(W_)-1)][0] if W_ else 0.3))
            ev.sort(key=lambda x: x[1])
            for kword, t in ev:
                t = max(0.15, t-0.1)
                if (not keep or t >= keep[-1][1]+1.8) and t+1.0 < D: keep.append((kword, t))
        pw = sc.get("punch")   # v7 opt-in centre punch word (1.4 s), replaces any keyword pop it overlaps
        if pw and plain:
            pw = {"word": pw} if isinstance(pw, str) else dict(pw); tok = (pw.get("at") or pw["word"]).split()[0].lower().strip(".,!?$₹%")
            hit = next((w[0] for w in W_ if tok and tok in w[2].lower()), None); pt = max(0.15, (hit if hit is not None else D*0.4)-0.05)
            pt = min(pt, max(0.15, D-1.5)); keep = [x for x in keep if not (pt-1.6 < x[1] < pt+1.5)] + [("\x01"+pw["word"], pt)]; keep.sort(key=lambda x: x[1])
        # ---- shots ----
        plan = None
        if not ischart:
            shots = clips_of(sc)
            if V9 and sc.get("_ec_bg"): shots = [OPEN_CLIP[0] if sc["_ec_bg"] == "__OPEN__" and OPEN_CLIP else (sc["_ec_bg"] if sc["_ec_bg"] != "__OPEN__" else "")]; shots = [x for x in shots if x]
            if V9 and sc.get("actuality") and sc["actuality"].get("clip") and sc["actuality"].get("show", "inset") != "footage":
                shots = [f"{sc['actuality']['clip']}@{float(sc['actuality'].get('ss', 0)):.2f}"]
            if V9 and isinstance(sc.get("clip"), (str, list)) and not sc.get("_endcard") and not sc.get("actuality"):
                for x in ([sc["clip"]] if isinstance(sc["clip"], str) else sc["clip"]):
                    PICKS.append((i, x.split("@")[0], clipfetch.match_score(IX.get(x.split("@")[0], {}), list(sc.get("tags") or []) + list(spec.get("tags") or []), text), "named"))
            if not shots and V9:   # v9: subject-matched picks only (match_min), else a designed plate
                import math as _m
                tg_ = list(sc.get("tags") or []) + list(spec.get("tags") or []); need_ = max(1, _m.ceil(D/sc.get("shot", TARGET_SHOT))+1)
                pk_ = clipfetch.pick_matched(tg_, text, exclude=USED | RECENT | RESERVED, n=need_, match_min=MATCH_MIN) or clipfetch.pick_matched(tg_, text, exclude=USED | RESERVED, n=need_, match_min=MATCH_MIN)
                pk_ = [(k, s_) for k, s_ in pk_ if cdur(k) >= 3.0]
                for k, s_ in pk_: PICKS.append((i, k, s_, "auto"))
                shots = [k for k, _ in pk_]
                if not shots:   # fix19: relaxed library picks (2-3 clips) before any plate
                    for _q in range(need_):
                        k_ = relaxed_pick(sc, min(D, sc.get("shot", TARGET_SHOT)))
                        if k_ is None: break
                        shots.append(k_); USED.add(k_)
                    for k_ in shots: USED.discard(k_)
                if not shots: fb_ = make_fb(sc, D); shots = [fb_]; PICKS.append((i, fb_, 0, "fallback-plate"))
            if not shots and V8:   # v8: no clip named -> pick unused library clips by the scene's tags + narration
                import math as _m
                shots = clipfetch.pick(list(sc.get("tags") or []) + list(spec.get("tags") or []), text, exclude=USED | RECENT, n=max(1, _m.ceil(D/sc.get("shot", TARGET_SHOT))+1))
                shots = [x for x in shots if cdur(x) >= 3.0] or clipfetch.pick(list(spec.get("tags") or []), text, exclude=USED, n=3, min_score=0)
            shots = shots or ["hd_151"]
            if sc.get("_closer") or sc.get("_open") or sc.get("_ec_bg") or sc.get("actuality") or sc.get("_title"): shots = shots[:1]   # v8 closer / v9 open, end card, actuality: one shot
            pool = []
            for k in (i-1, i+1, i-2, i+2):
                if 0 <= k < len(scenes): pool += [x.split("@")[0] for x in clips_of(scenes[k])]
            pool += spec.get("pool", [])
            cp = [W_[k+1][0]-0.05 for k in range(len(W_)-1) if W_[k][2][-1:] in ".,?!;:"]
            ca = [w[0]-0.05 for w in W_[1:]]
            tgt = sc.get("shot", TARGET_SHOT)
            st_need = 0.0
            if sc.get("stat"):
                dg = [w[0] for w in W_ if any(ch.isdigit() for ch in w[2])]; st0 = max(0.0, dg[0]-0.1) if dg else 0.2
                st0 = min(st0, max(0.0, D-3.6)); sc["_st0"] = st0; st_need = min(MAX_SHOT, st0+3.6)
            plan = gfx.plan_shots(shots, D, tgt, sc.get("max_shot", MAX_SHOT), cp, ca, first_min=st_need,
                                  durs={x: cdur(x) for x in set([y.split("@")[0] for y in shots]+pool)}, pool=pool,
                                  min_shot=1.4)
            # v7 near-black guard: swap any shot whose footage is too dark (mean luma < DARK_LUMA)
            cands = [x.split("@")[0] for x in shots] + pool + ([] if V9 else FALLBACK_POOL)
            if V9: cands = [x for x in cands if x.split("@")[0] in [y.split("@")[0] for y in shots] or clipfetch.match_score(IX.get(x, {}), list(sc.get("tags") or []) + list(spec.get("tags") or []), text) >= MATCH_MIN]
            for j, (sh, ss, L) in enumerate(plan):
                if sh.startswith("_fb_") or (V9 and (sc.get("actuality") or sc.get("_ec_bg") or IX.get(sh, {}).get("source") in ("fed", "dvids", "usgov") or any(x.startswith(sh + "@") for x in shots))): continue
                if gfx.clip_luma(f"{CL}/{sh}.mp4", ss, L) >= DARK_LUMA: continue
                for alt in cands:
                    if not os.path.exists(f"{CL}/{alt}.mp4"): continue
                    if V9 and alt in RESERVED and alt not in [y.split("@")[0] for y in shots]: continue   # fix19
                    a_ss = ss if alt == sh else min(1.0, max(0.0, cdur(alt)-L-0.2))
                    for tryss in (a_ss, 0.0, max(0.0, cdur(alt)*0.5-L/2)):
                        if tryss+L <= cdur(alt)-0.05 and gfx.clip_luma(f"{CL}/{alt}.mp4", tryss, L) >= DARK_LUMA:
                            dark_skips.append(f"{sh}@{ss:.1f}->{alt}@{tryss:.1f}"); plan[j] = (alt, round(tryss, 2), L); break
                    else: continue
                    break
            # v8: every shot gets a clip not used anywhere else in this video (and auto-picks avoid recent videos)
            if V8 and not (V9 and (sc.get("_ec_bg") or (sc.get("actuality") and sc["actuality"].get("clip")))): plan = resolve_unique(plan, sc, shots, pool)
            elif V9 and sc.get("actuality"): USED.update(x for x, *_ in plan)
            if V9 and sc.get("_open") and plan: OPEN_CLIP[:] = [plan[0][0]]
            # v7 change guard: no stretch > CE s without a visible change (cut, keyword/punch, stat) -> split the shot
            # and punch in ~10 % on the second half (reframe on the same clip)
            stw = (sc["_st0"], sc["_st0"]+3.9) if sc.get("_st0") is not None and sc.get("stat") else None
            evs = [t for _, t in keep] + ([stw[0], stw[0]+0.7, stw[1]-0.3] if stw else [])
            if sc.get("_endscreen"): evs = []
            out = []; t0 = 0.0
            for (sh, ss, L) in plan:
                pts = sorted([0.0] + [e-t0 for e in evs if t0 < e < t0+L] + [L]); g = max(b-a for a, b in zip(pts, pts[1:]))
                if g > CE+0.25 and L >= 2.4 and not sc.get("_endscreen") and not sc.get("_breath") and not sc.get("ending") and not sc.get("_closer") \
                        and not (V9 and (sc.get("_open") or sc.get("_title") or sc.get("_ec_bg") or sc.get("actuality") or sh.startswith("_fb_"))):
                    k_ = max(range(len(pts)-1), key=lambda q: pts[q+1]-pts[q]); cut = (pts[k_]+pts[k_+1])/2
                    cut = min(max(cut, 1.2), L-1.2)
                    if stw and t0+cut > stw[0]-0.2 and t0+cut < stw[1]+0.1: cut = stw[1]+0.1-t0   # never split under a stat
                    if 1.2 <= cut <= L-1.2:
                        if V8:   # cut to a fresh, unused clip (no same-clip punch-in: the user read it as a repeat)
                            nx = resolve_unique([("__NEW__", 0.0, L-cut)], sc, shots, pool, no_fb=V9)
                            if nx is None: out.append((sh, ss, L, 0)); reframes -= 1
                            else: nx = nx[0]; out += [(sh, ss, cut, 0), (nx[0], nx[1], L-cut, 0)]
                        else: out += [(sh, ss, cut, 0), (sh, round(ss+cut, 2), L-cut, 1)]
                        reframes += 1
                    else: out.append((sh, ss, L, 0))
                else: out.append((sh, ss, L, 0))
                t0 += L
            plan = out
            shot_lens += [L for _, _, L, _ in plan]
            acc = T0
            for (_, _, L, _) in plan[:-1]: acc += L; CHG.append(acc)
            CHG.extend(T0+t for t in evs)
        else: shot_lens.append(D)
        if V9:   # nat-sound segments (one per shot, so the bed changes on every cut), full-screen graphics time, voices heard
            if not ischart and plan and not sc.get("actuality"):
                ns = nat_for(sc); tt = T0
                for jn, (sh_, ss_, L_, *_r) in enumerate(plan):
                    src_ = ("clip", f"{CL}/{sh_}.mp4", ss_) if (sc.get("nat") == "clip" and IX.get(sh_, {}).get("audio_ok")) else ns
                    g_ = (-3.0 if sc.get("_title") else -6.0 if sc.get("_ec_bg") else 0.0) + (1.2 if jn % 2 else -1.0)
                    if src_ is not None and not sh_.startswith("_fb_"): NATSEG.append((tt, tt+L_, src_, g_))
                    if sh_.startswith("_fb_"): FULLT.append((round(tt, 1), L_, "fallback plate"))
                    tt += L_
            if ischart and not sc.get("_endcard"): FULLT.append((round(T0, 1), D, dev or ("sting" if sc.get("sting") else "question" if sc.get("question") else "subscribe" if sc.get("subscribe") else "chart")))
            if sc.get("_title"): FULLT.append((round(T0, 1), D, "title card"))
            VOX.extend((T0+t_, v_) for t_, v_ in sc.get("_vox", []))
        _SK[0] = (i < int(os.environ.get("RESUME_FROM", "0")) or (os.environ.get("ONLY") and str(i) not in os.environ["ONLY"].split(","))) and os.path.exists(f"{OUT}/sc{i}.mp4")   # fix19b: skipped scenes write no overlay pngs
        # ---- overlay track ----
        EXTRA = []; XF = []   # v9 extra ffmpeg inputs (inset decor, texture, credits) + their filter chains (built after the input count is known)
        INS = {}              # v9 inset decor png per shot index
        if V9 and (sc.get("_open") or sc.get("_title") or sc.get("quote") or sc.get("actuality")) and not sc.get("_ec_bg"):
            kind = "open" if sc.get("_open") else "title" if sc.get("_title") else "quote" if sc.get("quote") else "act"
            q0 = sc.get("_q0", 0.0); tco = sc.get("_title") or {}
            if kind == "open":
                bps_, an_ = [0.3, 0.95], [(0.3, 0.95)]
                def st9(t): return 0.0 if t < 0.3 else (round(min(1, (t-0.3)/0.65), 3) if t < 0.95 else 1.0)
            elif kind == "title":
                bps_, an_ = [1.1, D-0.35], [(0.0, 1.1), (D-0.35, D)]
                def st9(t, D=D): return (round(min(t, 1.1), 3), 1.0 if t < D-0.35 else round(max(0, (D-t)/0.35), 3))
            elif kind == "quote":
                bps_, an_ = [q0, q0+0.45], [(q0, q0+0.45)]
                def st9(t, q0=q0): return None if t < q0 else round(min(0.45, t-q0), 3)
            else:
                t_out = D if D < 8.5 else 6.5
                bps_, an_ = [0.25, 0.65, t_out, min(D, t_out+0.3)], [(0.25, 0.65), (t_out, min(D, t_out+0.3))]
                def st9(t, t_out=t_out): return None if t < 0.25 else (round(min(0.4, t-0.25), 3) if t < t_out else (round(max(0, 0.4-(t-t_out)/0.3*0.4), 3) if t < t_out+0.3 else None))
            cnt9 = [0]
            def rn9(key, i=i, kind=kind, cnt9=cnt9, sc=sc):
                pth = f"{OUT}/v9o{i}_{cnt9[0]}.png"; cnt9[0] += 1
                if key is None: Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(pth); return pth
                if kind == "open":
                    o_ = sc["_open"]; im_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); v9gfx.dateline(im_, o_.get("place"), o_.get("date"), 72, 64, key, big=44); im_.save(pth)
                elif kind == "title": v9gfx.title_card_png(pth, tco.get("series", BRAND), tco["title"], key[0], key[1], logo_mark(46), tco.get("sub"))
                elif kind == "quote": v9gfx.quote_png(pth, sc["quote"], key, spec.get("ai_voice_note", True))
                else:
                    ac_ = sc["actuality"]; v9gfx.lower_third_png(pth, ac_.get("who", ""), ac_.get("role"), ac_.get("credit"), key, ac_.get("source") if key >= 0.39 else None)
                return pth
            open(f"{OUT}/ovl{i}.txt", "w").write(gfx.tl_track(D, bps_, an_, st9, rn9, fps=F)); ovin = ["-f", "concat", "-safe", "0", "-i", f"{OUT}/ovl{i}.txt"]
            if kind == "title": SFX.append(("whoosh_soft", T0)); SFX.append(("hit", T0+0.35))
        elif V9 and sc.get("_ec_bg"):
            fd9 = f"{OUT}/ec{i}"; os.system(f"rm -rf {fd9}")
            srcs, foot, mus, vox = credit_lists()
            band = [("Sources", ", ".join(srcs) or "See description"), ("Footage", "; ".join(foot[:3]) + ("; full list in the description" if len(foot) > 3 else "")), ("Music & voice", "; ".join(mus + vox))]
            CHG.extend(T0+x for x in v9gfx.endcard_frames(sc["_endcard"], D, fd9, logo_mark(64), F, band if spec.get("credits", True) else None))
            ovin = ["-framerate", str(F), "-i", f"{fd9}/%04d.png"]
        elif ctype in ("stack", "pills"):
            n_it = len(sc["card"]["items"]); lst = []
            for k in range(1, n_it+1):
                pk = f"{OUT}/ov{i}_s{k}.png"; overlay(None, sc.get("source"), pk, shown=k, **kw)
                seg = D*0.8/n_it if k < n_it else D - D*0.8/n_it*(n_it-1)
                lst.append(f"file '{pk}'\nduration {seg:.3f}")
                if k > 1: SFX.append(("whoosh_soft", T0 + D*0.8/n_it*(k-1)))
            lst.append(f"file '{OUT}/ov{i}_s{n_it}.png'")
            open(f"{OUT}/ovl{i}.txt", "w").write("\n".join(lst)); ovin = ["-f", "concat", "-safe", "0", "-i", f"{OUT}/ovl{i}.txt"]
        elif ag is not None:
            def st_a(t): return round(t, 3) if t < 0.65 else 99.0
            def rn_a(key, i=i, ag=ag):
                pth = f"{OUT}/ag{i}_{int(key*1000) if key < 99 else 'h'}.png"; opener.agenda_overlay(pth, chapters, ag, key, MF, shadow_text, bug); return pth
            open(f"{OUT}/ovl{i}.txt", "w").write(gfx.tl_track(D, [0.65], [(0, 0.65)], st_a, rn_a)); ovin = ["-f", "concat", "-safe", "0", "-i", f"{OUT}/ovl{i}.txt"]
        elif sc.get("_endscreen"):
            esd = sc["_endscreen"]
            def st_e(t): return round(t, 3) if t < 0.65 else 99.0
            def rn_e(key, i=i, esd=esd):
                pth = f"{OUT}/es{i}_{int(key*1000) if key < 99 else 'h'}.png"; gfx.endscreen_png(pth, esd, key if key < 99 else 9.0, W, H, logo_mark(120)); return pth
            open(f"{OUT}/ovl{i}.txt", "w").write(gfx.tl_track(D, [0.65], [(0, 0.65)], st_e, rn_e)); ovin = ["-f", "concat", "-safe", "0", "-i", f"{OUT}/ovl{i}.txt"]
        elif sc.get("stat") and not sc.get("title"):
            sw = gfx.stat_window(D, sc.get("_st0", 0.2), plan[0][2] if plan else D)
            def st_s(t, sw=sw):
                if sw[0] <= t < sw[3]: return (round(min(1.0, (t-sw[0])/(sw[1]-sw[0])), 3), 1.0 if t < sw[2] else round(max(0, 1-(t-sw[2])/(sw[3]-sw[2])), 3))
                return None
            cnt = [0]
            def rn_s(key, i=i, cnt=cnt):
                pth = f"{OUT}/ov{i}_t{cnt[0]}.png"; cnt[0] += 1
                if key is None: overlay(None, None, pth, **kw)
                else: overlay(sc.get("stat"), sc.get("source"), pth, stat_prog=key[0], stat_alpha=key[1], **kw)
                return pth
            open(f"{OUT}/ovl{i}.txt", "w").write(gfx.tl_track(D, list(sw), [(sw[0], sw[1]), (sw[2], sw[3])], st_s, rn_s))
            ovin = ["-f", "concat", "-safe", "0", "-i", f"{OUT}/ovl{i}.txt"]
        # graphics counted: stat, card, chart, agenda/chapter, title, question
        if sc.get("stat") or sc.get("card") or (ischart and not full) or ag is not None or sc.get("question"): gfx_events.append(T0)
        if dev or (isinstance(cid, dict) and ischart and not full): dev_at.setdefault(dev or ("tilt_chart" if (sc.get("tilt") or cid.get("tilt")) else "chart"), []).append(round(T0, 1))
        if (sc.get("tilt") or (isinstance(cid, dict) and cid.get("tilt"))) and ischart: dev_at.setdefault("tilt", []).append(round(T0, 1))
        if sc.get("sting"): SFX.append(("whoosh", T0+0.05)); SFX.append(("hit", T0+0.45))
        elif sc.get("question") or sc.get("subscribe"): SFX.append(("whoosh", T0))
        elif i > 0 and (ag is not None or sc.get("chapter") or sc.get("chart") or sc.get("card") or dev): SFX.append(("whoosh_soft" if ag is not None else "whoosh", T0))
        elif i > 0 and sc.get("loc"): SFX.append(("slice", T0+0.1))
        c = f"{OUT}/sc{i}.mp4"; skip = (i < int(os.environ.get("RESUME_FROM", "0")) or (os.environ.get("ONLY") and str(i) not in os.environ["ONLY"].split(","))) and os.path.exists(c)   # resume / partial re-render
        if ischart and not skip:
            fd = f"{OUT}/ch{i}"; os.system(f"rm -rf {fd}")
            if sc.get("sting"): opener.sting_frames(D, fd, MF, logo_mark, BRAND)
            elif sc.get("question"): opener.question_frames(D, fd, MF, wrap, sc["question"])
            elif sc.get("subscribe"): opener.subscribe_frames(D, fd, MF, sc["subscribe"] if isinstance(sc["subscribe"], str) else "New deep dives every weekend")
            elif sc.get("_endcard"): CHG.extend(T0+x for x in gfx.endcard_frames(sc["_endcard"], D, fd, W, H, logo_mark(64)))
            elif dev:
                syn = None
                if sc.get("sync") and W_:   # one step per narration sentence/clause start
                    syn = [0.4] + [W_[k+1][0] for k in range(len(W_)-1) if W_[k][2][-1:] in ".;:?!"]
                evd = getattr(gfx, dev+"_frames")(cid, D, fd, W, H, sync=syn); CHG.extend(T0+x for x in evd if x > 0)
                STEP10.extend((dev, T0+x) for x in evd if x > 0.3)
            elif isinstance(cid, dict):
                gfx.chart_frames(cid, D, fd, W, H); ev_, _, _ = gfx.chart_steps(cid, D); CHG.extend(T0+x[2] for x in ev_)
                STEP10.extend(("chart", T0+x[2]) for x in ev_ if x[2] > 0.3)
            else: chart_frames(cid.split(":")[1], D, fd)
            tl_ = sc.get("tilt") or (isinstance(cid, dict) and cid.get("tilt"))
            if V9 and tl_ and tl_ != "force":   # v9: data-heavy charts and devices stay flat; tilt only for single-headline graphics
                npts = (len(cid.get("x", [])) if cid.get("type") == "line" else len(cid.get("bars", [])) if cid.get("bars") else 99) if isinstance(cid, dict) and not dev else 99
                if dev or npts > 3 or cid.get("axis"): print(f"V9 flat: scene {i} tilt ignored (data-heavy; use \"tilt\": \"force\" to override)", flush=True); tl_ = False
            if tl_ and not full: gfx.tilt_dir(fd, D, tl_, W, H)
            if V8 and clips and spec.get("transitions", True) and not sc.get("sting"):
                lp = f"{OUT}/last{i}.png"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.1", "-i", clips[-1], "-frames:v", "1", "-vf", f"scale={W}:{H}:flags=lanczos", lp])
                gfx.blend_in(fd, lp, 12 if prev_full else 9, W, H)
            vin = ["-framerate", str(F), "-i", f"{fd}/%04d.png"]; vf = f"[0:v]fps={F},scale={OW}:{OH}:flags=lanczos,setsar=1,{BT709}[bg]"; nv = 1
        elif not ischart:
            nv = len(plan); vin = []; parts = []
            for j, (sh, ss, sd, rf) in enumerate(plan):
                vin += ["-ss", f"{ss:.2f}", "-stream_loop", "-1", "-i", f"{CL}/{sh}.mp4"]
                zin = j % 2 == 0
                ez = f"(0.5-0.5*cos(PI*min(t/{sd:.2f},1)))"
                ex = f"(iw-ow)/2*(1-{ez})" if zin else f"(iw-ow)/2*{ez}"
                ey = f"(ih-oh)/2*(1-{ez})" if zin else f"(ih-oh)/2*{ez}"
                sw_, sh_ = (int(OW*1.1)//2*2, int(OH*1.1)//2*2) if not rf else (int(OW*1.25)//2*2, int(OH*1.25)//2*2)   # reframe: ~13 % punch-in on the same clip
                if rf: ex, ey = f"(iw-ow)/2+{60 if j % 2 else -60}*{ez}", "(ih-oh)/2"
                srch = IX.get(sh, {}).get("h") or 1080; shp = ("," + UPSHARP) if (V8 and srch < OH) else ""
                ins_on = V9 and not sc.get("_title") and not sc.get("_ec_bg") and not sh.startswith("_fb_") and (bool(sc.get("inset")) or (spec.get("auto_inset", True) and (srch < 1000 or IX.get(sh, {}).get("still"))))
                if ins_on:   # v9 WSJ-style inset: framed footage over a blurred, darkened copy + dateline + credit
                    ix_, iy_, iw_, ih_ = v9gfx.inset_geom(OW, OH); io = sc.get("inset") if isinstance(sc.get("inset"), dict) else {}
                    _own9 = sh in [y.split("@")[0] for y in clips_of(sc)]   # fix19: a scene's place tag only on the footage named for it
                    dl = ((io.get("dateline") if _own9 else None) or IX.get(sh, {}).get("dateline") or ((sc.get("loc") or "") if _own9 else "") or "").split("|")
                    if sc.get("_open"): dl = [""]   # open_place draws its own dateline; avoid a second one on the inset
                    cr = (io.get("credit") if _own9 and io.get("credit") else None) or IX.get(sh, {}).get("credit") or _short_attr(IX.get(sh, {}).get("attribution", "")) or SRCNAME.get(IX.get(sh, {}).get("source"), "")
                    dp = f"{OUT}/ins{i}_{j}.png"; v9gfx.inset_decor_png(dp, dl[0] or None, dl[1] if len(dl) > 1 else None, cr or None); INS[j] = dp; INSETS.append((i, sh))
                    gr_ = GRADE.split(",vignette")[0]
                    parts.append(f"[{j}:v]{BT709},trim=0:{sd:.3f},setpts=PTS-STARTPTS,fps={F},split=2[ia{j}][ib{j}];[ia{j}]scale=640:360:force_original_aspect_ratio=increase,crop=640:360,boxblur=10:2,"
                                 f"scale={OW}:{OH},setsar=1,eq=brightness=-0.22:saturation=0.5[ibg{j}];[ib{j}]scale={iw_}:{ih_}:flags=lanczos,setsar=1{shp},{gr_}[ifg{j}];"
                                 f"[ibg{j}][ifg{j}]overlay={ix_}:{iy_}[ip{j}];[ip{j}][dec{j}]overlay=0:0[p{j}]")
                    continue
                if V9 and (sc.get("_open") or sc.get("_ec_bg")):   # v9 open on the place / end card over the same place: slow push (slowed if the clip is short)
                    slow = max(1.0, (sd+0.3)/max(0.5, cdur(sh)-ss)); spts = f"setpts={slow:.3f}*(PTS-STARTPTS)" if slow > 1.01 else "setpts=PTS-STARTPTS"
                    parts.append(f"[{j}:v]{BT709},{spts},trim=0:{sd:.3f},setpts=PTS-STARTPTS,fps={F},scale=w='trunc({OW}*(1.04+0.06*t/{sd:.2f})/2)*2':h=-2:eval=frame:flags=lanczos,setsar=1,crop={OW}:{OH}:(iw-ow)/2:(ih-oh)/2{shp},{GRADE}[p{j}]")
                    continue
                if sc.get("_closer"):   # v8 closer: one slow, steady push-in (1.00 -> 1.10) on the final shot
                    parts.append(f"[{j}:v]{BT709},trim=0:{sd:.3f},setpts=PTS-STARTPTS,fps={F},scale=w='trunc({OW}*(1.0+0.10*t/{sd:.2f})/2)*2':h=-2:eval=frame:flags=lanczos,setsar=1,crop={OW}:{OH}:(iw-ow)/2:(ih-oh)/2{shp},{GRADE}[p{j}]")
                else:
                    parts.append(f"[{j}:v]{BT709},trim=0:{sd:.3f},setpts=PTS-STARTPTS,scale={sw_}:{sh_}:flags=lanczos,setsar=1,fps={F},crop={OW}:{OH}:'{ex}':'{ey}'{shp},{GRADE}[p{j}]")
            vf = ";".join(parts) + ";" + "".join(f"[p{j}]" for j in range(nv)) + f"concat=n={nv}:v=1:a=0[bg]"
        if full: ovin = ["-f", "lavfi", "-i", f"color=c=black@0.0:s={W}x{H}:r={F},format=rgba"]
        if sc.get("_closer"): ovin = ["-loop", "1", "-i", ov]
        ain = ["-i", sc["_a"]] if sc.get("_a") else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        capin = []; capf = ""
        if plain and spec.get("captions", False):   # running captions: OFF by default (Study 2)
            ph = opener.chunks(W_); lst = []; tcur = 0.0
            blank = f"{OUT}/cap_blank.png"; opener.caption_png(blank, "", MF, shadow_text)
            for k, (a, b, t) in enumerate(ph):
                if a > tcur: lst.append(f"file '{blank}'\nduration {a-tcur:.3f}")
                nb = ph[k+1][0] if k+1 < len(ph) else D
                cp_ = f"{OUT}/cap{i}_{k}.png"; opener.caption_png(cp_, t, MF, shadow_text)
                lst.append(f"file '{cp_}'\nduration {max(0.05, nb-a):.3f}"); tcur = nb
            lst.append(f"file '{blank}'\nduration 1.0"); lst.append(f"file '{blank}'")
            open(f"{OUT}/capl{i}.txt", "w").write("\n".join(lst)); capin = ["-f", "concat", "-safe", "0", "-i", f"{OUT}/capl{i}.txt"]
        elif keep:
            # keyword pops (1.5 s, lower third) and the opt-in punch word (1.4 s, centre), one overlay track
            kw_count += sum(1 for k_, _ in keep if not k_.startswith("\x01")); kw_times.extend(T0+t for _, t in keep); KW10.extend((k_, T0+t) for k_, t in keep); bps = []; anims = []
            for kword, t in keep: L_ = 1.4 if kword.startswith("\x01") else 1.5; bps += [t, min(D, t+L_)]; anims.append((t, t+0.3))
            def st_k(t, keep=keep):
                for kword, a in keep:
                    L_ = 1.4 if kword.startswith("\x01") else 1.5
                    if a <= t < a+L_: return (kword, round(t-a, 3) if t-a < 0.3 else 9.0)
                return ("", 9.0)
            cnt = [0]
            def rn_k(key, i=i, cnt=cnt):
                pth = f"{OUT}/kw{i}_{cnt[0]}.png"; cnt[0] += 1
                if key[0].startswith("\x01"): gfx.punch_png(pth, key[0][1:], key[1], W, H)
                else: gfx.keyword_png(pth, key[0], key[1], W, H)
                return pth
            open(f"{OUT}/capl{i}.txt", "w").write(gfx.tl_track(D, bps, anims, st_k, rn_k))
            capin = ["-f", "concat", "-safe", "0", "-i", f"{OUT}/capl{i}.txt"]
        if capin: capf = f";[{nv+2}:v]format=rgba,fps={F},scale={OW}:{OH}:flags=lanczos[cp];[v0][cp]overlay=0:0[v1]"
        vlab = "[v0]" if capin else "[v1]"
        if ischart: nv = 1
        fin = "[v1]"
        if V9 and not skip:   # extra inputs: inset decor, panel texture, closer credits roll
            base = nv + 2 + (1 if capin else 0)
            for j_, dp in INS.items(): EXTRA += ["-loop", "1", "-framerate", str(F), "-t", f"{plan[j_][2]+0.2:.3f}", "-i", dp]; XF.append(f"[{base}:v]format=rgba,scale={OW}:{OH}:flags=lanczos[dec{j_}]"); base += 1
            if ischart and TEX and not full and not sc.get("sting"):
                k_ = vf.rfind("[bg]"); vf = vf[:k_] + "[bg0]" + vf[k_+4:]; EXTRA += ["-loop", "1", "-i", TEX]
                XF.append(f"[{base}:v]format=rgba,scale={OW}:{OH}:flags=lanczos[tex];[bg0][tex]overlay=0:0[bg]"); base += 1
            if sc.get("_closer") and spec.get("credits", True):
                srcs, foot, mus, vox = credit_lists(); cpng = f"{OUT}/credits{i}.png"; gpng = f"{OUT}/cgrad.png"
                hgt = v9gfx.credits_png(cpng, [("Sources", srcs or ["See description"]), ("Footage", foot or ["Rotation"]), ("Music", mus or ["Mixkit"]), ("Voice", vox)])
                v9gfx.side_gradient_png(gpng, 860); sfac = OW/W; hs = hgt*sfac
                sp = min(110*OH/H, max(45*OH/H, (OH*0.55+hs)/max(1.0, D-1.0)))
                EXTRA += ["-loop", "1", "-i", gpng, "-loop", "1", "-i", cpng]
                XF.append(f"[{base}:v]format=rgba,scale={OW}:{OH}:flags=lanczos[cg];[{base+1}:v]format=rgba,scale=iw*{sfac:.4f}:-1:flags=lanczos[crd];"
                          f"[v1][cg]overlay=0:0[v1c];[v1c][crd]overlay=x={int(1290*sfac)}:y='if(lt(t,0.6),H,H-(t-0.6)*{sp:.1f})'[v1d]"); base += 2; fin = "[v1d]"
        xfs = (";" + ";".join(XF)) if XF else ""
        if not skip: subprocess.run(["ffmpeg", "-y", "-v", "error", *vin, *ovin, *ain, *capin, *EXTRA, "-filter_complex",
            vf+xfs+f";[{nv}:v]format=rgba,fps={F},scale={OW}:{OH}:flags=lanczos[ov];[bg][ov]overlay=0:0{vlab}" + capf + f";{fin}{BT709},format=yuv420p[v];[{nv+1}:a]aresample=44100,apad[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{D:.3f}", "-c:v", "libx264", "-preset", "veryfast" if not V8 else "faster", "-crf", "20" if not V8 else str(spec.get("crf", 17)),
            *(["-g", "60", "-bf", "2"] if V8 else []), *COLOR_OUT,
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", c], check=True)
        clips.append(c); times.append((T0, T0+D)); prev_full = bool(ischart)
        if ischart: FULLSET.add(i)
        if V10 and skip and ischart and not dev and isinstance(cid, dict) and cid.get("type") in ("line", "bar", "dots"):
            try: STEP10.extend(("chart", T0+x[2]) for x in gfx.chart_steps(cid, D)[0] if x[2] > 0.3)
            except Exception: pass
        if V10:   # small matching sounds for cards (Vox rule: nothing moves on screen without a sound)
            if ctype in ("quote", "headline", "stack"): EV10.append(("paper", T0+0.15))
            elif ctype == "doc": EV10.append(("paper", T0+0.1)); EV10.append(("pen", T0+min(1.2, D*0.4)))
            elif ctype in ("compare", "pills"): EV10.append(("click", T0+0.3))
            if sc.get("stat") and not sc.get("title"): EV10.append(("tick", T0+sc.get("_st0", 0.2)))
            if sc.get("loc"): EV10.append(("click", T0+0.35))
        punch.append(bool(sc.get("stat") or sc.get("card") or ischart or "?" in text or sc.get("vo_punch") or i == 0))
        T0 += D; print("scene", i, round(D, 1), "shots", [round(x[2], 1) for x in plan] if plan else (dev or "full"), flush=True)
    with open(f"{OUT}/sl.txt", "w") as fh: fh.write("\n".join(f"file '{c}'" for c in clips))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{OUT}/sl.txt", "-c", "copy", f"{OUT}/voice_cut.mp4"], check=True)
    T = dur(f"{OUT}/voice_cut.mp4")
    segs = [(a, b, float(scenes[k]["vo_gain"])) if "vo_gain" in scenes[k] else None for k, (a, b) in enumerate(times)]
    auto = mixbus.auto_contour(times, punch); segs = [s_ or a_ for s_, a_ in zip(segs, auto)]
    music_path = MUSIC; tracks = []
    if V8:
        mus = spec.get("music") or {}; moods = mus.get("moods") or ["doc"]; segs_m = []; ci = 0
        segs_m.append((0.0, mus.get("opener", moods[0])))
        for k, sc in enumerate(scenes):
            if sc.get("_agenda") is not None and k > 0 and scenes[k].get("_agenda", 0) > 0:
                ci = sc["_agenda"]; segs_m.append((times[k][0], moods[min(ci, len(moods)-1)]))
            if sc.get("_closer") and mus.get("closer"): segs_m.append((times[k][0], mus["closer"]))
        if V10:   # cold open cue -> new cue at the title card (runs through ch1) -> a new cue at every later chapter card
            _ms = list(mus.get("moods") or ["doc", "pulse", "tense", "doc", "light"]); segs_m = [(0.0, V10_LABELS[0])]
            kt = next((k for k, sc in enumerate(scenes) if sc.get("_title") or sc.get("sting")), None)
            if kt is not None: segs_m.append((times[kt][0], V10_LABELS[1]))
            for k, sc in enumerate(scenes):
                if sc.get("_agenda") is not None and k > 0 and sc.get("_agenda", 0) > 0:
                    ci = sc["_agenda"]; segs_m.append((times[k][0], f"{_ms[min(ci, len(_ms)-1)]}#{ci+1}"))
                if sc.get("_closer") and mus.get("closer"): segs_m.append((times[k][0], f"{mus['closer']}#c"))
        segs_m = [x for k, x in enumerate(segs_m) if k == 0 or x[1] != segs_m[k-1][1]]
        music_path = f"{OUT}/music_bed.wav"
        tracks, msegs = musiclib.build_bed(segs_m, T, music_path, xfade=float(mus.get("xfade", 1.6)), video=os.path.basename(spec["output"]) if spec.get("log_used", True) else "",
                                           force=PRE_MUS if V9 else mus.get("tracks"))
        print("V8 music", [(round(a, 1), b, musiclib.load()[b]["title"]) for a, b in msegs], flush=True)
    natw = None
    if V9 and NATSEG and spec.get("nat", True) is not False:
        natw = f"{OUT}/nat_bed.wav"; nlog = natlib.build(NATSEG, T, natw); print(f"V9 nat: {len(NATSEG)} segments, sources {sorted(set(str(x[1]) for x in nlog))}", flush=True)
    extra10 = {}
    if V10:
        import sfxlib
        kt = next((k for k, sc in enumerate(scenes) if sc.get("_title") or sc.get("sting")), None)
        t_title = times[kt][0] if kt is not None else min(60.0, T*0.12); t_title_end = times[kt][1] if kt is not None else t_title
        ke = next((k for k, sc in enumerate(scenes) if sc.get("_closer") or sc.get("_endcard") or sc.get("_ec_bg")), None)
        t_end = times[ke][0] if ke is not None else T
        lv = spec.get("levels10") or {}
        duck_curve = [(0.0, t_title, lv.get("open", -17.0)), (t_title, t_end, lv.get("chapter", -28.0)), (t_end, T+1, lv.get("end", -20.0))]
        open_curve = [(t_title, t_title_end, lv.get("title", -3.0))]
        # music-off stretches: 1-2 per video, 15-38 s of footage scenes inside chapters 2 and 4, place sound only
        off = spec.get("music_off")
        if off is None:
            off = []; ags = [k for k, sc in enumerate(scenes) if sc.get("_agenda") is not None and sc.get("_agenda", 0) > 0]
            want = [ags[0]] if len(ags) < 3 else [ags[0], ags[2]]
            for ka in want:
                nxt = next((k for k in range(ka+1, len(scenes)) if (scenes[k].get("_agenda") is not None and k != ka) or scenes[k].get("_closer") or scenes[k].get("_endcard")), len(scenes))
                runs = []; cur = []
                for k in range(ka+2, nxt):
                    good = k not in FULLSET and not scenes[k].get("actuality") and not scenes[k].get("quote") and not scenes[k].get("subscribe") and not scenes[k].get("card")
                    if good: cur.append(k)
                    elif cur: runs.append(cur); cur = []
                if cur: runs.append(cur)
                run = next((r for r in runs if times[r[-1]][1]-times[r[0]][0] >= 15.0), None)
                if run and times[run[-1]][1]-times[run[0]][0] >= 15.0:
                    a_ = times[run[0]][0]; b_ = min(times[run[-1]][1], a_+38.0); off.append((round(a_, 2), round(b_, 2)))
        off = [tuple(x) for x in (off or [])]
        # SFX families: legacy events mapped, plus keyword pops, chart/map steps, cards
        LEG = {"whoosh": ("whoosh", 0.0), "whoosh_soft": ("whoosh", -5.0), "hit": ("boom", 0.0), "riser": ("riser", 0.0), "click": ("click", 0.0), "slice": ("click", -2.0)}
        ev = [(LEG[n][0], t, LEG[n][1]) for n, t in SFX if n in LEG]
        if kt is not None: ev.append(("riser", t_title + 0.3, -4.0))
        for kw_, t in KW10:
            w_ = kw_.lstrip("\x01")
            fam = "coins" if any(c in w_ for c in "$₹€£") and len([e for e in ev if e[0] == "coins"]) < 4 else "tick" if any(c.isdigit() for c in w_) else "pop"
            ev.append((fam, t + 0.02, -3.0))
        lastst = {}
        for d_, t in sorted(STEP10, key=lambda x: x[1]):
            fam = "ping" if d_ == "map" else "tick" if d_ == "timeline" else "click"
            if t - lastst.get(d_, -9) < 0.9: continue
            lastst[d_] = t; ev.append((fam, t, -4.0))
        ev += [(f, t, -2.0) for f, t in EV10]
        res = sfxlib.resolve(ev, seed=os.path.basename(spec["output"]), log_video=os.path.basename(spec["output"]) if spec.get("log_used", True) else None)
        sfxw = f"{OUT}/sfx_bed.wav"; nsfx = sfxlib.render(res, T, sfxw)
        fams = {}
        for e in ev: fams[e[0]] = fams.get(e[0], 0) + 1
        print(f"V10 sound: duck {duck_curve} title-open {open_curve} music_off {off} sfx {nsfx} events {fams}", flush=True)
        extra10 = dict(duck_curve=duck_curve, open_curve=open_curve, swell_db=float(lv.get("swell", 6.0)), music_off=off, sfx_wav=sfxw,
                       sfx_db=float(spec.get("sfx_db", 0.0)), dips_per3=3)
    mixbus.mix(f"{OUT}/voice_cut.mp4", music_path, SFX, T, spec["output"], PEAK=PEAK, VOL=VOL, vo_segs=segs, fade=1.5 if V8 else 3.0,
               **({"duck_db": float(spec.get("music_db", -18.0)), "nat": natw, "nat_db": tuple(spec.get("nat_db", [-22.0, -13.0]))} if V9 else {}), **extra10)
    if V8 and spec.get("log_used", True): clipfetch.log_used(os.path.basename(spec["output"]), sorted(USED))
    nw = sum(len((sc.get("text") or "").split()) for sc in scenes)
    vo_t = sum(dur(sc["_a"]) for sc in scenes if sc.get("_a"))
    longest = max(shot_lens)
    # ---- v7 reports: longest no-change gap (planned), graphics density curve, device placement ----
    es_t = next((times[k][0] for k, sc in enumerate(scenes) if sc.get("_endscreen") or sc.get("_endcard") or sc.get("_closer")), T)
    ch = sorted(set(round(x, 2) for x in CHG + [es_t] if x <= es_t)); gaps = [(b-a, a) for a, b in zip(ch, ch[1:])]
    gmax = max(gaps) if gaps else (0, 0)
    gt = sorted(gfx_events + kw_times)
    def rate(a, b): return sum(1 for x in gt if a <= x < b)/max(1e-6, (b-a))*60
    r1, rm, rl = rate(0, min(60, T)), rate(60, 0.9*es_t), rate(0.9*es_t, es_t)
    warn = []
    if r1 < 4: warn.append(f"first minute {r1:.1f}/min < 4")
    if not (2.5 <= rm <= 3.5): warn.append(f"middle {rm:.1f}/min outside 2.5-3.5")
    if rl > 1.0: warn.append(f"last 10% {rl:.1f}/min > 1")
    for need in ("map", "flow", "tilt"):
        if not any(0.15*es_t <= x <= 0.75*es_t for x in dev_at.get(need, [])): warn.append(f"no {need} between 15% and 75%")
    print(f"V7 longest planned no-change gap {gmax[0]:.1f}s at {gmax[1]:.1f}s (change_every {CE}); reframes {reframes}; dark clips swapped {dark_skips}", flush=True)
    print(f"V7 density /min: first minute {r1:.1f} (4-5), middle {rm:.1f} (2.5-3), last 10% {rl:.1f} (<=1); devices {dev_at}", flush=True)
    print("V7 WARN " + ("; ".join(warn) if warn else "none"), flush=True)
    print(f"STATS total {T:.1f}s shots {len(shot_lens)} avg {T/len(shot_lens):.2f}s longest {longest:.1f}s words {nw} WPM(total) {nw/T*60:.0f} WPM(voice) {nw/vo_t*60:.0f} "
          f"graphics {len(gfx_events)} (+{kw_count} keyword pops) = {(len(gfx_events)+kw_count)/T*60:.1f}/min sting {sting_at} agenda {agenda_at}", flush=True)
    try:
        em, gl, ga, ne_ = gfx.measure_changes(spec["output"]); print(f"V7 measured (study-3 metric): {em} changes/min, longest gap {gl}s at {ga}s, {ne_} events", flush=True)
    except Exception as ex: print("V7 measure failed", ex)
    if V8:
        try:
            g8, a8 = gfx.measure_changes_v8(spec["output"]); print(f"V8 measured (fine metric): longest no-visible-change gap {g8}s at {a8}s", flush=True)
        except Exception as ex: print("V8 measure failed", ex)
        print(f"V8 clips: {len(USED)} unique, replaced {len(REPL)} repeats/new {REPL}; render time {(_time.time()-_t_start)/60:.1f} min; res {OW}x{OH}", flush=True)
    if V9:   # ---- v9 reports ----
        ecd = sum(b-a for (a, b), sc in zip(times, scenes) if sc.get("_endcard")); rt = T-ecd
        fs = sum(x[1] for x in FULLT); pct = 100*fs/max(1, rt)
        print(f"V9 graphics: full-screen {fs:.1f}s of {rt:.1f}s (excl. end card) = {pct:.0f}% (target 20-30%) {[(a, round(b, 1), c) for a, b, c in FULLT]}", flush=True)
        if pct > 30: print(f"V9 WARN full-screen graphics {pct:.0f}% > 30% - swap a panel for a stat over matching footage", flush=True)
        tct = next((times[k][0] for k, sc in enumerate(scenes) if sc.get("_title") or sc.get("sting")), None)
        vb = sorted(set(v for t_, v in VOX if tct is None or t_ < tct)); va = sorted(set(v for _, v in VOX))
        print(f"V9 cold open: {tct if tct is None else round(tct, 1)}s before the title card, voices {len(vb)} {vb}; voices in video {len(va)} {va}", flush=True)
        if tct is not None and not (75 <= tct <= 100): print(f"V9 WARN cold open {tct:.0f}s outside 75-100 s", flush=True)
        if len(vb) < 3: print("V9 WARN fewer than 3 voices in the cold open", flush=True)
        ch_ = [t_ for t_, v_ in VOX if v_ != "narrator"]; segs_v = [0.0] + ch_ + [rt]; gapv = max(b-a for a, b in zip(segs_v, segs_v[1:])) if len(segs_v) > 1 else rt
        print(f"V9 voice relief: longest stretch without a non-narrator voice {gapv:.0f}s (rule: a new voice every 30-60 s)", flush=True)
        for (sci, k, sco, how) in PICKS: print(f"V9 pick scene {sci}: {k} score {sco} ({how}) {IX.get(k, {}).get('title', '')[:60]}", flush=True)
        weak = [(a, k, sco) for a, k, sco, how in PICKS if how == "named" and sco < MATCH_MIN]
        print(f"V9 weak named clips (score < {MATCH_MIN}): {weak}; fallback plates {sum(1 for p_ in PICKS if p_[3] == 'fallback-plate')}; insets {INSETS}; fps {F}", flush=True)
    # fix19 (2026-11-01): post-render black guard - 1 fps luma scan; any stretch > 1 s of near-black frames outside the
    # intended dark cards (sting, title, question, agenda, subscribe, end card, quote cards) fails the render.
    _bg_fail = []
    try:
        _card = [(a_-0.6, b_+0.6) for (a_, b_), sc in zip(times, scenes) if sc.get("sting") or sc.get("_title") or sc.get("question") or sc.get("agenda") is not None or sc.get("_agenda") is not None
                 or sc.get("subscribe") or sc.get("_endcard") or sc.get("quote") or sc.get("_breath")]
        _o = subprocess.run(["ffmpeg", "-v", "info", "-i", spec["output"], "-vf", "fps=1,scale=320:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        import re as _re
        _y = [float(v) for v in _re.findall(r"YAVG=([0-9.]+)", _o)]
        _dark = [k for k, v in enumerate(_y) if v < 24 and not any(a_ <= k+0.5 <= b_ for a_, b_ in _card)]
        _runs = []; 
        for k in _dark:
            if _runs and k == _runs[-1][1]+1: _runs[-1][1] = k
            else: _runs.append([k, k])
        _bg_fail = [(a_, b_) for a_, b_ in _runs if b_-a_+1 >= 2]
        print(f"BLACK GUARD: {len(_y)} frames scanned, near-black (YAVG<24) outside cards: {len(_dark)} s; stretches >1 s: {_bg_fail or 'none'}", flush=True)
    except Exception as ex: print("BLACK GUARD failed to run", ex, flush=True)
    print("TOTAL", T)
    if _bg_fail and os.environ.get("BLACK_GUARD", "1") != "0": print("BLACK GUARD FAIL - render has black stretches", flush=True); sys.exit(3)

asyncio.run(main(json.load(open(sys.argv[1]))))
