#!/usr/bin/env python3
"""Rotation collage thumbnail (Bloomberg-Originals-inspired, own fonts/colours), trial 2026-10-30.
Cut-out subject (rembg) over a duotone place photo, big brand-orange disc behind the subject,
film grain, 2-3 words title-case Poppins ExtraBold white w/ shadow, small orange logo bottom-left.
Usage: PYTHONPATH=/workspace/work/pylib python3 make_thumb_collage.py '{"subject":"cut.png" or "frame.png",
  "bg":"place.png","words":["Hike","Again?"],"tint":[12,40,80],"disc":true,"subj_h":640,"subj_x":640,"out":"x.jpg"}'
"""
import json, sys, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps, ImageChops
sys.path.insert(0, "/workspace/work/yt")
W, H = 1280, 720; FD = "/workspace/work/yt/fonts/"; OR = (250, 78, 2)
def cover(im, w, h, fx=0.5):
    s = max(w/im.width, h/im.height); im = im.resize((int(im.width*s+1), int(im.height*s+1)), Image.LANCZOS)
    x = int((im.width-w)*fx); y = (im.height-h)//2; return im.crop((x, y, x+w, y+h))
def cutout(p):
    im = Image.open(p)
    if im.mode == "RGBA" and im.split()[3].getextrema()[0] < 10: return im
    from rembg import remove, new_session
    return remove(im.convert("RGB"), session=new_session("u2net_human_seg"))
def logo(h):
    src = Image.open('/workspace/work/yt/banner/logo.jpg').convert('L')
    a = src.point(lambda v: 255 if v > 200 else (0 if v < 150 else int((v-150)*255/50)))
    m = Image.new('RGBA', src.size, OR + (0,)); m.putalpha(a); m = m.crop(a.getbbox())
    return m.resize((int(m.width*h/m.height), h), Image.LANCZOS)
def main(c):
    t = tuple(c.get("tint", (10, 38, 78)))
    bg = cover(Image.open(c["bg"]).convert("RGB"), W, H, c.get("bgfx", 0.5)).filter(ImageFilter.GaussianBlur(c.get("blur", 2)))
    g = ImageOps.autocontrast(bg.convert("L"))
    bg = ImageOps.colorize(g, black=(4, 8, 16), white=tuple(min(255, v*3) for v in t), mid=t).convert("RGBA")
    # vignette
    v = Image.new("L", (W, H), 0); ImageDraw.Draw(v).ellipse([-300, -250, W+300, H+250], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(120)); dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    bg = Image.composite(bg, dark, v)
    sub = cutout(c["subject"]); sub = sub.crop(sub.split()[3].getbbox())
    sh = c.get("subj_h", 660); sub = sub.resize((int(sub.width*sh/sub.height), sh), Image.LANCZOS)
    sx = c.get("subj_x", 820) - sub.width//2; sy = H - sh + c.get("subj_dy", 0)
    if c.get("disc", True):
        r = c.get("disc_r", 270); cx, cy = c.get("subj_x", 820), sy + int(sh*0.30)
        d = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(d).ellipse([cx-r, cy-r, cx+r, cy+r], fill=OR + (255,))
        bg.alpha_composite(d)
    # rising arrow (behind subject)
    ar = c.get("arrow")
    if ar:
        al = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ad = ImageDraw.Draw(al)
        pts = [tuple(p) for p in ar["pts"]]; wdt = ar.get("w", 34); col = tuple(ar.get("color", (255, 255, 255))) + (255,)
        ad.line(pts, fill=col, width=wdt, joint="curve")
        import math
        (x1, y1), (x2, y2) = pts[-2], pts[-1]; ang = math.atan2(y2-y1, x2-x1); L = wdt*2.6
        tip = (x2 + math.cos(ang)*L*0.6, y2 + math.sin(ang)*L*0.6)
        l = (x2 + math.cos(ang+2.4)*L, y2 + math.sin(ang+2.4)*L); r = (x2 + math.cos(ang-2.4)*L, y2 + math.sin(ang-2.4)*L)
        ad.polygon([tip, l, r], fill=col)
        sh_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh_.putalpha(al.split()[3].point(lambda x: int(x*0.7)))
        bg.alpha_composite(sh_.filter(ImageFilter.GaussianBlur(10)), (8, 10)); bg.alpha_composite(al)
    def prop(pr):
        im = Image.open(pr["img"]).convert("RGBA"); hh = pr.get("h", 200)
        im = im.resize((int(im.width*hh/im.height), hh), Image.LANCZOS).rotate(pr.get("rot", 0), expand=True, resample=Image.BICUBIC)
        a_ = im.split()[3]; s_ = Image.new("RGBA", im.size, (0, 0, 0, 0)); s_.putalpha(a_.point(lambda x: int(x*0.55)))
        bg.alpha_composite(s_.filter(ImageFilter.GaussianBlur(10)), (pr["x"]+10, pr["y"]+12)); bg.alpha_composite(im, (pr["x"], pr["y"]))
    for pr in c.get("props", []):
        if not pr.get("front"): prop(pr)
    # subject shadow + subject
    a = sub.split()[3]; shd = Image.new("RGBA", sub.size, (0, 0, 0, 0)); shd.putalpha(a.point(lambda x: int(x*0.6)))
    bg.alpha_composite(shd.filter(ImageFilter.GaussianBlur(14)), (sx+14, sy+10))
    sub = ImageEnhance.Contrast(ImageEnhance.Color(sub).enhance(1.15)).enhance(1.08)
    bg.alpha_composite(sub, (sx, sy))
    for pr in c.get("props", []):
        if pr.get("front"): prop(pr)
    # words
    d = ImageDraw.Draw(bg); words = c["words"]; maxw = c.get("text_w", 560); x0 = c.get("text_x", 60)
    sz = 170
    while max(d.textlength(w, font=ImageFont.truetype(FD+"Poppins-ExtraBold.ttf", sz)) for w in words) > maxw and sz > 60: sz -= 4
    f = ImageFont.truetype(FD+"Poppins-ExtraBold.ttf", sz); lh = int(sz*0.98)
    y = c.get("text_y", (H - lh*len(words))//2 - 10)
    tl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(tl)
    for i, w in enumerate(words):
        td.text((x0, y + i*lh), w, font=f, fill=(255, 255, 255), stroke_width=0)
    sha = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sha.putalpha(tl.split()[3].point(lambda x: int(x*0.85)))
    bg.alpha_composite(sha.filter(ImageFilter.GaussianBlur(8)), (4, 6)); bg.alpha_composite(tl)
    # grain
    random.seed(7); n = Image.effect_noise((W, H), 28).convert("L")
    bg = Image.blend(bg.convert("RGB"), ImageChops.overlay(bg.convert("RGB"), Image.merge("RGB", (n, n, n))), 0.18).convert("RGBA")
    bg.alpha_composite(logo(c.get("logo_h", 56)), (34, H - c.get("logo_h", 56) - 30))
    bg.convert("RGB").save(c["out"], quality=92); print("thumb", c["out"])
if __name__ == "__main__": main(json.loads(sys.argv[1]))
