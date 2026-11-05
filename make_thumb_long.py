"""Rotation long-form thumbnail (16:9, 1280x720), v7 rules (user approved 2026-10-29):
- 2-4 words that do NOT repeat the title, built on a number or a two-value contrast ("$9B vs $0", "3 fabs, 0 running").
- Brand styling kept: darkened footage frame, bottom/left dark gradient, white Montserrat ExtraBold, yellow #F0B400 data accent
  + bar, logo mark + ROTATION tag top-left, orange #FA4E02 rule. Optional hero "art" (e.g. a map frame) on the right.
Usage: python3 make_thumb_long.py '{"title": "...", "text": "3 FABS, 0 RUNNING", "clip": "hd_2381@2", "art": "/path/map.png",
        "out": "/workspace/work/yt/covers/long_<date>_<slug>_thumb.jpg"}'
text forms: "A vs B" | "A, B" (two-value contrast: A white, B yellow) | plain (numbers in yellow)."""
import sys, json, re, subprocess
sys.path.insert(0, '/workspace/work/yt'); import gfx
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
W, H = 1280, 720; YEL = (240, 180, 0); ORG = (250, 78, 2); CREAM = (248, 241, 228); WH = (255, 255, 255)
MONO = True   # v8 (user 2026-10-29: no yellow, black and white): data accent = black text on a white slab, grey rule
STOP = {"the", "a", "an", "of", "to", "in", "is", "and", "why", "how", "its", "it's", "yet", "vs", "on", "for"}

def check(title, text):
    words = text.replace(",", " ").replace("/", " ").split(); n = len([w for w in words if w.lower() != "vs"])
    if not 2 <= n <= 4: raise SystemExit(f"thumbnail text must be 2-4 words, got {n}: {text!r}")
    if not (re.search(r"[0-9]", text) or " vs " in f" {text.lower()} "): raise SystemExit("thumbnail text needs a number or an 'A vs B' contrast")
    tw = {w.lower().strip(".,!?'\"") for w in title.split()} - STOP; xw = {w.lower().strip(".,!?'\"") for w in words} - STOP
    rep = tw & xw
    if len(rep) >= 2 or (xw and len(rep) / len(xw) > 0.5): raise SystemExit(f"thumbnail text repeats the title: {sorted(rep)}")

def frame(clip):
    cid, ss = (clip.split("@") + ["2"])[:2]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", ss, "-i", f"/workspace/work/yt/clips/{cid}.mp4", "-frames:v", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "/tmp/thumb_bg.png"], check=True)
    return Image.open("/tmp/thumb_bg.png").convert("RGB")

def logo(h):
    src = Image.open('/workspace/work/yt/banner/logo.jpg').convert('L')
    a = src.point(lambda v: 255 if v > 200 else (0 if v < 150 else int((v-150)*255/50)))
    m = Image.new('RGBA', src.size, (255, 255, 255, 0)); m.putalpha(a); m = m.crop(a.getbbox())
    return m.resize((int(m.width*h/m.height), h), Image.LANCZOS)

def make(o):
    check(o["title"], o["text"]); bg = ImageEnhance.Brightness(frame(o.get("clip", "hd_4308@2")).filter(ImageFilter.GaussianBlur(o.get("blur", 3)))).enhance(0.45).convert("RGBA")
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for x in range(W): gd.line([(x, 0), (x, H)], fill=(4, 4, 5, int(235*max(0, 1-x/(W*0.78)))))
    bg.alpha_composite(g)
    if o.get("art"):   # hero object on the right (map / chart frame), soft-edged
        art = Image.open(o["art"]).convert("RGBA"); aw = int(W*o.get("art_w", 0.6)); art = art.resize((aw, int(art.height*aw/art.width)), Image.LANCZOS)
        if o.get("art_crop"): art = art.crop(tuple(int(v*aw/1920) for v in o["art_crop"]))
        mk = Image.new("L", art.size, 0); ImageDraw.Draw(mk).ellipse([art.width*0.08, art.height*0.05, art.width*0.98, art.height*0.97], fill=255); mk = mk.filter(ImageFilter.GaussianBlur(45))
        art.putalpha(mk); bg.alpha_composite(art, (W-art.width+10, (H-art.height)//2+30))
    d = ImageDraw.Draw(bg); mk = logo(40); bg.alpha_composite(mk, (52, 40)); d.text((52+mk.width+12, 38), "ROTATION", font=gfx.MF(34, 800), fill=WH)
    t = o["text"].upper()
    if " VS " in f" {t} ": parts = [p.strip() for p in re.split(r"\bVS\b", t)]; mid = "VS"
    elif "," in t: parts = [p.strip() for p in t.split(",", 1)]; mid = None
    else: parts = [t]; mid = None
    x = 92; y = 190 if len(parts) > 1 else 250; maxw = 700 if o.get("art") else 1080
    d.rectangle([52, y+12, 66, y+(430 if len(parts) > 1 else 230)], fill=WH if MONO else YEL)
    def slab(xy, tok, f):   # v8 accent: inverted (black on white) slab
        x_, y_ = xy; bb = d.textbbox((x_, y_), tok, font=f); pad = int(f.size*0.10)
        d.rectangle([bb[0]-pad, bb[1]-pad, bb[2]+pad, bb[3]+pad], fill=WH); d.text((x_, y_), tok, font=f, fill=(8, 8, 9))
    for k, p in enumerate(parts):
        f = gfx.MF(170, 900)
        while d.textlength(p, font=f) > maxw: f = gfx.MF(f.size-6, 900)
        col = WH if (len(parts) > 1 and k == 0) else YEL
        if len(parts) == 1:   # numbers yellow, words white
            xx = x
            for tok in re.split(r"(\S*[0-9]\S*)", p):
                if tok:
                    if MONO and re.search(r"[0-9]", tok): d = ImageDraw.Draw(bg); slab((xx+int(f.size*0.10), y), tok, f); xx += int(f.size*0.2)
                    else: gfx.shadow(bg, (xx, y), tok, f, fill=YEL if re.search(r"[0-9]", tok) else WH, r=8)
                    d = ImageDraw.Draw(bg); xx += d.textlength(tok, font=f)
        elif MONO and k == 1: d = ImageDraw.Draw(bg); slab((x+int(f.size*0.10), y+int(f.size*0.06)), p, f); y += int(f.size*0.12)
        else: gfx.shadow(bg, (x, y), p, f, fill=col, r=8)
        y += int(f.size*1.08)
        if mid and k == 0: gfx.shadow(bg, (x+4, y-18), mid, gfx.MF(60, 900), fill=(170, 170, 174) if MONO else ORG, r=4); y += 50
    d = ImageDraw.Draw(bg); d.rectangle([92, H-58, 92+220, H-54 if MONO else H-50], fill=(200, 200, 204) if MONO else ORG)
    n = Image.effect_noise((W, H), 40).convert("L"); out = Image.blend(bg.convert("RGB"), Image.merge("RGB", (n, n, n)), (2 if MONO else 6)/255)
    out.save(o["out"], quality=92); print("thumb", o["out"])

if __name__ == "__main__": make(json.loads(sys.argv[1]))
