import sys as _s; _s.path.insert(0,'/workspace/work/yt'); import wordtime
"""Rotation Explains renderer (new series, 2026-10-30). Standalone: does NOT touch make_long / make_story / gfx / v9gfx /
opener / mixbus behaviour; it only imports their libraries read-only (mixbus.mix, musiclib.build_bed, natlib.build,
v9gfx.endcard_frames) and draws its own graphics with explain_gfx.py.

Usage:  PYTHONPATH=/workspace/work/pylib python3 make_explain.py long/spec_explain_demo.json
Env:    ONLY=3,4 (re-render those scene segments only), NOAUDIO=1, KEEP=1, WORK=<dir>
Spec keys: see SPEC_KEYS.md, section "Rotation Explains"."""
import asyncio, hashlib, json, os, subprocess, sys, time, math, wave
import numpy as np
sys.path.insert(0, "/workspace/work/yt")
import edge_tts
from PIL import Image
import explain_gfx as G

YT = "/workspace/work/yt"; CL = f"{YT}/clips"
NARRATOR = "en-US-AndrewMultilingualNeural"
PEAK = {'click': 0.193, 'hit': 0.087, 'riser': 2.535, 'slice': 0.188, 'whoosh': 1.065, 'whoosh_soft': 0.715}
VOL = {'click': 0.35, 'hit': 0.9, 'riser': 0.35, 'slice': 0.4, 'whoosh': 0.35, 'whoosh_soft': 0.3}
GRADE = 'eq=contrast=1.05:saturation=0.96:gamma=0.99:brightness=-0.02,vignette=angle=PI/7'
COLOR = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]

def sh(cmd, **kw): return subprocess.run(cmd, check=True, **kw)
def dur(p):
    try: return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode().strip())
    except ValueError: return 0.0   # broken/unknown-length file: treated as unusable

_logo = None
def logo_mark(h):
    # 2026-10-30: user picked the cream-ribbon-on-orange logo (brand_logo_v2_cream_orange.png) for sting + end card; old mask = banner/logo.jpg (see *.bak16.py)
    global _logo
    if _logo is None: _logo = Image.open('/workspace/work/yt/brand_logo_disc.png').convert('RGBA')
    return _logo.resize((h, h), Image.LANCZOS)

# ------------------------------------------------------------------ TTS (cached, word boundaries)
async def tts(text, voice, rate, cache):
    h = hashlib.md5(f"{voice}|{rate}|{text}".encode()).hexdigest()[:12]; cp = f"{cache}/tts_{h}"
    if os.path.exists(cp+".json") and os.path.exists(cp+".mp3"): return cp+".mp3", [tuple(x) for x in json.load(open(cp+".json"))]
    for k in range(5):
        try:
            if wordtime.needs_align(voice):
                ws = await wordtime.synth(text, voice, rate, cp+".tmp.mp3"); break
            c = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary"); ws = []
            with open(cp+".tmp.mp3", "wb") as fh:
                async for ch in c.stream():
                    if ch["type"] == "audio": fh.write(ch["data"])
                    elif ch["type"] == "WordBoundary": ws.append((ch["offset"]/1e7, (ch["offset"]+ch["duration"])/1e7, ch["text"]))
            break
        except Exception as e:
            if k == 4: raise
            await asyncio.sleep(5*(k+1))
    os.replace(cp+".tmp.mp3", cp+".mp3"); json.dump(ws, open(cp+".json", "w")); return cp+".mp3", ws

def norm(w): return "".join(ch for ch in w.lower() if ch.isalnum() or ch == ".").strip(".")

# ------------------------------------------------------------------ main
def main(spec_path):
    t_start = time.time(); spec = json.load(open(spec_path)); W, H = G.W, G.H; FPS = spec.get("fps", 24); CRF = spec.get("crf", 15)
    work = os.environ.get("WORK", f"{YT}/explain/work"); os.makedirs(work, exist_ok=True); cache = f"{YT}/explain/tts"; os.makedirs(cache, exist_ok=True)
    IX = json.load(open(f"{CL}/index.json")); rate = spec.get("rate", "+12%"); rate2 = spec.get("rate2", "+6%")
    scenes = spec["scenes"]
    # ---- 1. voices
    async def all_tts():
        out = []
        for sc in scenes:
            a = await tts(sc["text"], NARRATOR, rate, cache) if sc.get("text") else None
            q = await tts(sc["quote"]["text"], sc["quote"].get("voice", "en-GB-SoniaNeural"), rate2, cache) if sc.get("quote") else None
            out.append((a, q))
        return out
    V = asyncio.run(all_tts())
    # ---- 2. timeline
    T = 0.0; plan = []; words_total = 0
    for sc, (a, q) in zip(scenes, V):
        pre = sc.get("pre", 0.15); words = []; vo = []
        if a:
            da = dur(a[0]); vo.append((a[0], pre)); words += [(s+pre, e+pre, w) for s, e, w in a[1]]; end = pre+da; words_total += len(sc["text"].split())
        else: end = 0.0
        qs = None
        if q:
            qs = end + (0.35 if a else 0.45); dq = dur(q[0]); vo.append((q[0], qs)); end = qs+dq; words_total += len(sc["quote"]["text"].split())
        D = sc.get("dur") or (end + sc.get("post", 0.3))
        if sc.get("min"): D = max(D, sc["min"])
        plan.append(dict(t0=T, D=D, words=words, vo=vo, q0=qs)); T += D
    print(f"TIMELINE {T:.1f}s, {len(scenes)} scenes, narration+quote words {words_total}, wpm over voiced time ~{words_total/((T-sum(p['D'] for p,s in zip(plan,scenes) if not s.get('text') and not s.get('quote')))/60):.0f}", flush=True)

    def cue(k, x):
        """Scene-local time for a cue: number = seconds; "q" = quote start; "word" or "word#2" = start of that word in the narration."""
        p = plan[k]
        if isinstance(x, (int, float)): return float(x)
        if x == "q": return p["q0"] or 0.5
        nth = 1
        if "#" in x: x, nth = x.split("#"); nth = int(nth)
        target = norm(x); seen = 0
        for s, e, w in p["words"]:
            if norm(w) == target or (len(target) > 3 and target in norm(w)):
                seen += 1
                if seen == nth: return s
        txt = scenes[k].get("text", ""); i = txt.lower().find(x.lower())
        if i >= 0 and p["words"]: return p["words"][0][0] + (p["words"][-1][1]-p["words"][0][0])*i/max(1, len(txt))
        print(f"  WARN cue '{x}' not found in scene {k}", flush=True); return 1.0
    def cues(k, lst): return [] if isinstance(lst, dict) else [cue(k, x) for x in (lst or [])]

    used = []
    def clip_path(cid):
        m = IX[cid]; return f"{CL}/{m['file']}", m
    def credit_of(m):
        at = m.get("attribution") or ""; lic = m.get("licence", "")
        if "CC BY" in at or "CC BY" in lic:
            # '"Title" by Artist, CC BY 2.0, via Wikimedia Commons' -> 'Photo: Artist / Wikimedia Commons, CC BY 2.0'
            try: artist = at.split('" by ', 1)[1].split(", CC BY")[0]; lic_ = "CC BY" + at.split(", CC BY", 1)[1].split(",")[0]
            except Exception: artist, lic_ = "Wikimedia Commons", "CC BY"
            return f"Photo: {artist} / Wikimedia Commons, {lic_}"
        return None

    # ---- 3. shots per footage scene (cuts snap to word gaps)
    def split_shots(k, sc, D):
        shots = sc.get("shots") or []; n = len(shots); p = plan[k]
        if n == 0: return []
        if sc.get("shot_d"): bounds = [0]+list(np.cumsum(sc["shot_d"][:n-1]))+[D]
        else:
            bounds = [0.0]
            gaps = [(e1+s2)/2 for (s1, e1, w1), (s2, e2, w2) in zip(p["words"], p["words"][1:])]
            for j in range(1, n):
                tgt = D*j/n; best = min(gaps, key=lambda g: abs(g-tgt)) if gaps else tgt
                bounds.append(best if abs(best-tgt) < 0.9 and best > bounds[-1]+1.6 else tgt)
            bounds.append(D)
        out = []
        for j, s in enumerate(shots):
            cid, ss = (s.split("@")[0], float(s.split("@")[1])) if "@" in s else (s, None)
            out.append(dict(clip=cid, ss=ss, d=bounds[j+1]-bounds[j], t0=bounds[j]))
        return out

    # ---- 4. render each segment
    only = set(int(x) for x in os.environ.get("ONLY", "").split(",") if x.strip())
    segs = []; gfx_time = 0.0; shot_lens = []; sfx = []; EV10 = []; nat_segs = []; scene_times = []; punch = []; sheet = []
    for k, sc in enumerate(scenes):
        p = plan[k]; D = p["D"]; T0 = p["t0"]; kind = sc["kind"]; out = f"{work}/seg_{k:02d}.mp4"; segs.append(out)
        scene_times.append((T0, T0+D)); punch.append(kind not in ("footage", "closer"))
        for st in sc.get("sheet", []): sheet.append((T0+st, f"{k:02d} {kind}"))
        g = sc.get("gfx", {}); cu = cues(k, sc.get("cues"))
        footage = []; dev = None; opaque = False; darken = 0.0
        if kind in ("footage", "closer"):
            footage = split_shots(k, sc, D)
        elif kind == "endcard":
            pass
        else:
            cls = G.DEVICES[kind]
            if kind == "title": dev = cls(g, cu, D, logo=logo_mark(78))
            elif kind == "doc": dev = cls(g, {kk: cue(k, vv) for kk, vv in sc["cues"].items()}, D)
            elif kind == "tiles":
                g = dict(g)
                if g.get("stamp"): g["stamp"] = dict(g["stamp"], t=cue(k, g["stamp"]["cue"]))
                if g.get("unfocus"): g["unfocus_t"] = cue(k, g["unfocus"])
                dev = cls(g, cu, D)
            elif kind == "quote": dev = cls(dict(sc["quote"]), [p["q0"]], D)
            else: dev = cls(g, cu, D)
            opaque = kind in G.OPAQUE
            if not opaque: footage = [dict(clip=sc["bg"].split("@")[0], ss=float(sc["bg"].split("@")[1]) if "@" in sc["bg"] else None, d=D, t0=0.0)] if sc.get("bg") else []
            darken = sc.get("darken", 0.0)
            if kind not in ("quote",): gfx_time += D
            if kind in ("doc", "bars", "split", "tiles", "flow", "keyword", "verdict"): sfx.append(("whoosh_soft", T0+0.05))
            if kind == "section": sfx.append(("slice", T0+0.15))
            if kind == "title": sfx.append(("hit", T0+0.1))
            if kind == "doc": sfx.append(("click", T0+cue(k, sc["cues"]["ring"])+0.1))
            if kind == "tiles" and g.get("stamp"): sfx.append(("click", T0+g["stamp"]["t"]))
            if kind in ("bars", "flow", "tiles", "split"): EV10.extend(("click", T0+c_, -5.0) for c_ in (cu or []) if c_ > 0.3)
            if kind == "keyword": EV10.append(("pop", T0+0.1, -3.0))
            if kind == "doc": EV10.append(("pen", T0+cue(k, sc["cues"]["ring"])+0.2, -2.0))
            if kind == "quote": EV10.append(("paper", T0+0.15, -2.0))
        # overlays on footage (pops, lower thirds, headline, stat, agenda, credits)
        items = []
        if dev is not None and not opaque: items.append((dev, 0, 0, D))
        for ov in sc.get("overlays", []):
            c2 = {kk: vv for kk, vv in ov.items() if kk not in ("type", "cues")}
            d2 = G.DEVICES[ov["type"]](c2, cues(k, ov.get("cues")), D); items.append((d2, 0, 0, D))
        for sh_ in footage:
            path, m = clip_path(sh_["clip"]); used.append(sh_["clip"])
            if kind in ("footage", "closer"): shot_lens.append(sh_["d"])
            cr = credit_of(m)
            if cr: items.append((G.Credit({"text": cr}, [], sh_["d"]), 0, sh_["t0"], sh_["t0"]+sh_["d"]))
            if kind in ("footage", "closer") or (dev is not None and not opaque):
                import natlib
                nid = natlib.for_scene(sc.get("nat"), [], [], default="sfx_2930")
                nat_segs.append((T0+sh_["t0"], T0+sh_["t0"]+sh_["d"], nid, sc.get("nat_db", 0.0) if kind in ("footage", "closer") else -6.0))
        if opaque or kind in ("title",):
            nat_segs.append((T0, T0+D, None, 0))
        ov_dev = G.Stack(items) if items else None
        if os.environ.get("DRY"): print(f"  {k:02d} {kind:8s} t0 {T0:6.1f} D {D:5.2f} shots {[round(x['d'],2) for x in footage]} cues {[round(x,2) for x in cu]}", flush=True)
        if os.environ.get("DRY") or (only and k not in only and (os.path.exists(out) or os.environ.get("STRICT_ONLY"))): continue
        t1 = time.time()
        if kind == "endcard": render_endcard(sc, D, out, work, W, H, FPS, CRF, IX)
        else: render_segment(out, D, footage, ov_dev, dev if opaque else None, darken, W, H, FPS, CRF, IX, push=(kind == "closer"))
        print(f"seg {k:02d} {kind:8s} {D:5.2f}s at {T0:6.1f}s  [{time.time()-t1:.0f}s]", flush=True)
    rep = [c for c in set(used) if used.count(c) > 1 and c != spec.get("endcard_bg")]
    print(f"CLIPS {len(set(used))} unique; repeats {rep}; shots {len(shot_lens)} avg {np.mean(shot_lens):.2f}s min {min(shot_lens):.2f} max {max(shot_lens):.2f}", flush=True)
    end_d = sum(p_["D"] for p_, s_ in zip(plan, scenes) if s_["kind"] == "endcard")
    print(f"GRAPHICS full-screen/overlay devices {gfx_time:.1f}s of {T-end_d:.1f}s = {100*gfx_time/(T-end_d):.0f}% (target 45-50%)", flush=True)
    if os.environ.get("DRY") or os.environ.get("STRICT_ONLY"): return
    # ---- 5. concat video
    lst = f"{work}/concat.txt"; open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
    vid = f"{work}/video.mp4"; sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid])
    Tv = dur(vid); print(f"VIDEO {Tv:.2f}s (plan {T:.2f}s)", flush=True)
    if os.environ.get("NOAUDIO"): return
    # ---- 6. voice track
    SRv = 48000; vo = np.zeros(int(Tv*SRv)+SRv, np.float32)
    for p in plan:
        for (mp3, off) in p["vo"]:
            raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", mp3, "-f", "f32le", "-ac", "1", "-ar", str(SRv), "-"])
            x = np.frombuffer(raw, np.float32); i0 = int((p["t0"]+off)*SRv); vo[i0:i0+len(x)] += x[:max(0, len(vo)-i0)]
    vo = vo[:int(Tv*SRv)]; vw = f"{work}/voice.wav"
    with wave.open(vw, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SRv); wf.writeframes((np.clip(vo, -1, 1)*32767).astype(np.int16).tobytes())
    vmp4 = f"{work}/voice.mp4"; sh(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", vw, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "pcm_s16le", "-t", f"{Tv:.3f}", vmp4.replace(".mp4", ".mov")])
    vmp4 = vmp4.replace(".mp4", ".mov")
    # ---- 7. music bed (mood per section) + nat
    import musiclib, natlib, mixbus
    segs_m = []; V10 = spec.get("v10", True)   # Study 10 (locked 2026-11-01): every section cue is its own track
    for p, sc in zip(plan, scenes):
        if sc.get("music"): segs_m.append((p["t0"] if segs_m else 0.0, f"{sc['music']}#{len(segs_m)}" if V10 and sc["music"] in musiclib.MOODS else sc["music"]))
    if not segs_m: segs_m = [(0.0, "doc")]
    mw = f"{work}/music_bed.wav"; tracks = musiclib.build_bed(segs_m, Tv, mw, xfade=1.6, video=os.path.basename(spec["output"]), force=spec.get("music_tracks"))
    print(f"MUSIC {segs_m} -> {tracks}", flush=True)
    nw = f"{work}/nat_bed.wav"
    natlib.build([(a, min(b, Tv), s_, g_) for (a, b, s_, g_) in nat_segs], Tv, nw)
    contour = mixbus.auto_contour(scene_times, punch)
    out = spec["output"]; os.makedirs(os.path.dirname(out), exist_ok=True)
    extra10 = {}
    if V10:
        import sfxlib
        kinds = [sc["kind"] for sc in scenes]; t0s = [p["t0"] for p in plan]; Ds = [p["D"] for p in plan]
        kt = next((k for k, kd in enumerate(kinds) if kd == "title"), None)
        t_title = t0s[kt] if kt is not None else 0.0; t_te = t_title + (Ds[kt] if kt is not None else 0.0)
        ke = next((k for k, kd in enumerate(kinds) if kd in ("closer", "endcard")), None); t_end = t0s[ke] if ke is not None else Tv
        duck_curve = [(0.0, t_title, -17.0), (t_title, t_end, float(spec.get("music_db_chapter", -28.0))), (t_end, Tv+1, -20.0)]
        off = spec.get("music_off")
        if off is None:   # one music-off stretch: first run of footage scenes >= 15 s after 35 % of the video (cap 30 s)
            off = []; run = []
            for k, kd in enumerate(kinds):
                if kd == "footage" and t0s[k] >= 0.35*Tv and k != ke: run.append(k)
                else:
                    if run and t0s[run[-1]]+Ds[run[-1]]-t0s[run[0]] >= 15.0: break
                    run = []
            if run and t0s[run[-1]]+Ds[run[-1]]-t0s[run[0]] >= 15.0: off = [(t0s[run[0]], min(t0s[run[-1]]+Ds[run[-1]], t0s[run[0]]+30.0))]
        LEG = {"whoosh": ("whoosh", 0.0), "whoosh_soft": ("whoosh", -5.0), "hit": ("boom", 0.0), "riser": ("riser", 0.0), "click": ("click", 0.0), "slice": ("click", -2.0)}
        ev = [(LEG[n][0], t, LEG[n][1]) for n, t in sfx if n in LEG] + EV10
        if kt is not None: ev.append(("riser", t_title + 0.1, -4.0))
        res = sfxlib.resolve(ev, seed=os.path.basename(out), log_video=os.path.basename(out) if spec.get("log_used", True) else None)
        sw = f"{work}/sfx_bed.wav"; nsfx = sfxlib.render(res, Tv, sw)
        print(f"V10 sound: duck {duck_curve} music_off {off} sfx {nsfx}", flush=True)
        extra10 = dict(duck_curve=duck_curve, open_curve=[(t_title, t_te, -3.0)], swell_db=6.0, music_off=[tuple(x) for x in off], sfx_wav=sw, dips_per3=3)
    r = mixbus.mix(vmp4, mw, sorted(sfx, key=lambda x: x[1]), Tv, out, PEAK=PEAK, VOL=VOL, vo_segs=contour, duck_db=spec.get("music_db", -18.0),
                   nat=nw, nat_db=tuple(spec.get("nat_db", [-22.0, -13.0])), **extra10)
    try: mixbus.phone_check(out)
    except Exception as e: print("phone check failed", e)
    json.dump(dict(T=Tv, plan=[dict(t0=p["t0"], D=p["D"], kind=s["kind"]) for p, s in zip(plan, scenes)], sheet=sheet, tracks=tracks, clips=sorted(set(used))),
              open(f"{work}/render_meta.json", "w"), indent=1)
    print(f"DONE {out} {dur(out):.2f}s in {(time.time()-t_start)/60:.1f} min", flush=True)

def render_segment(out, D, footage, ov_dev, opaque_dev, darken, W, H, FPS, CRF, IX, push=False):
    n = int(round(D*FPS)); enc = ["-c:v", "libx264", "-preset", "faster", "-crf", str(CRF), "-pix_fmt", "yuv420p", "-g", "48", "-bf", "2", *COLOR, "-an", "-frames:v", str(n), "-r", str(FPS)]
    if opaque_dev is not None:
        p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-vf", "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709", *enc, out], stdin=subprocess.PIPE)
        for i in range(n): p.stdin.write(opaque_dev.frame(i/FPS).convert("RGB").tobytes())
        p.stdin.close(); assert p.wait() == 0; return
    ins = []; fc = []; labs = []
    for j, s in enumerate(footage):
        m = IX[s["clip"]]; path = f"{CL}/{m['file']}"; cd = m.get("dur") or dur(path); d = s["d"]
        ss = s["ss"] if s["ss"] is not None else (0.0 if m.get("still") or cd < d+1.2 else min(1.0, cd-d-0.2))
        if ss+d > cd: ss = max(0.0, cd-d-0.05)
        ins += ["-ss", f"{ss:.3f}", "-t", f"{d+0.2:.3f}", "-i", path]
        sharp = ",unsharp=5:5:0.45:5:5:0.0" if (m.get("h") or 1080) < 1400 else ""
        if push:
            fc.append(f"[{j}:v]fps={FPS},scale={W*2}:{H*2}:force_original_aspect_ratio=increase:flags=lanczos,crop={W*2}:{H*2},"
                      f"zoompan=z='1+0.10*on/{max(1, int(d*FPS))}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}{sharp},{GRADE},format=yuv420p,setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709,setsar=1,trim=duration={d:.4f},setpts=PTS-STARTPTS[v{j}]")
        else:
            z = 1.05 if m.get("still") else 1.09; dirx = "t" if j % 2 == 0 else f"({d:.3f}-t)"
            fc.append(f"[{j}:v]fps={FPS},scale={int(W*z)}:{int(H*z)}:force_original_aspect_ratio=increase:flags=lanczos,"
                      f"crop={W}:{H}:x='(iw-{W})*{dirx}/{d:.3f}':y='(ih-{H})/2'{sharp},{GRADE},format=yuv420p,setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709,setsar=1,trim=duration={d:.4f},setpts=PTS-STARTPTS[v{j}]")
        labs.append(f"[v{j}]")
    if not footage:   # no footage: dark plate
        ins += ["-f", "lavfi", "-t", f"{D:.3f}", "-i", f"color=c=0x151413:s={W}x{H}:r={FPS}"]; fc.append(f"[0:v]setsar=1[base]")
    else:
        fc.append("".join(labs)+f"concat=n={len(labs)}:v=1:a=0[cc]")
        dk = f",eq=brightness={-darken:.2f}:saturation={max(0.2, 1-darken*2):.2f}" if darken else ""
        fc.append(f"[cc]null{dk}[base]")
    if ov_dev is not None:
        k_in = len(footage) if footage else 1
        ins += ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
        fc.append(f"[base][{k_in}:v]overlay=0:0:format=auto,format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709[out]")
    else: fc.append("[base]format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709[out]")
    cmd = ["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[out]", *enc, out]
    if os.environ.get("DEBUG"): print("CMD", " ".join(repr(x) if " " in x or ";" in x else x for x in cmd), flush=True)
    if ov_dev is None: sh(cmd); return
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE); last = None; lb = None
    for i in range(n):
        im = ov_dev.frame(i/FPS); b = im.tobytes(); p.stdin.write(b)
    p.stdin.close(); assert p.wait() == 0

def render_endcard(sc, D, out, work, W, H, FPS, CRF, IX):
    import v9gfx
    d_out = f"{work}/endcard"; os.system(f"rm -rf {d_out}")
    v9gfx.endcard_frames(sc.get("gfx", {}), D, d_out, logo_mark(64), FPS, sc.get("credits"))
    m = IX[sc["bg"]]; path = f"{CL}/{m['file']}"; n = int(round(D*FPS))
    fc = (f"[0:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},{GRADE},eq=brightness=-0.08:saturation=0.5,setsar=1[bg];"
          f"[1:v]scale={W}:{H}:flags=lanczos,format=rgba[ov];[bg][ov]overlay=0:0,format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709[out]")
    sh(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", path, "-framerate", str(FPS), "-i", f"{d_out}/%04d.png", "-filter_complex", fc, "-map", "[out]",
        "-c:v", "libx264", "-preset", "faster", "-crf", str(CRF), "-pix_fmt", "yuv420p", "-g", "48", *COLOR, "-an", "-frames:v", str(n), "-r", str(FPS), out])

if __name__ == "__main__":
    main(sys.argv[1])
