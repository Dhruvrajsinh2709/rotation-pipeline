"""Rotation audio bus (Study 2, 2026-10-29), shared by make_story.py and make_long.py.
- music high-passed at 130 Hz (2 x 12 dB/oct) so the bass sits well under the voice
- music ducked to DUCK_DB (-24 dB, inside the -22..-26 target) below the voice while it speaks,
  opened to OPEN_DB below the voice on music-only stretches (sting, question/agenda cards)
- short music dips (< -40 dB for 0.4 s) at sentence ends: 4-6 per 3 min (min 2 per video)
- explicit gain envelope (numpy -> wav -> amultiply) instead of a sidechain, so levels are deterministic
- gain-to-target + gentle limiter + trim: -14 LUFS, peaks under ~-1.5 dBTP, loudness range kept (no dynamic loudnorm)."""
import subprocess, json, re, wave, os
import numpy as np

DUCK_DB = -24.0; OPEN_DB = -9.0; HP = "highpass=f=130,highpass=f=130"
SR = 44100; FR = 100  # envelope control rate (Hz)

def _ebur(path, af=""):
    o = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", (af+"," if af else "")+"ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1]); L = float(re.findall(r"LRA:\s+(-?[\d.]+) LU", o)[-1])
    return I, L

def silences(path, n=-38, d=0.25):
    o = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", f"silencedetect=n={n}dB:d={d}", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", o)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", o)]
    return [(max(0, a), b) for a, b in zip(st, en)] + ([(st[-1], 1e9)] if len(st) > len(en) else [])

def pick_dips(sil, T, per3=5, min_n=2, open_s=1.2):
    """Sentence-end gaps of 0.45-1.2 s (not the long card gaps), spread evenly through the video."""
    cands = [(a, b) for a, b in sil if 0.55 <= b-a < open_s and a > 2.0 and b < T-2.5]
    n = max(min_n, round(T/180*per3)); n = min(n, len(cands)); out = []
    for k in range(n):
        tgt = T*(k+0.5)/n
        best = min((c for c in cands if c not in out), key=lambda c: abs(c[0]-tgt), default=None)
        if best: out.append(best)
    return sorted((a+0.02, min(a+0.50, b-0.02)) for a, b in out)   # ~0.4 s fully under -40 dB after the ramps

def envelope(T, sil, dips, Lv, Lm, fade=2.0, open_s=1.2, duck_db=None, open_db=None, duck_curve=None, open_curve=None, swell_db=0.0, off=None, boost=None):
    """v10 extras (Study 10): duck_curve/open_curve = [(t0, t1, db)] override the level per region (loud cold open, quiet
    chapters, full title); swell_db lifts short sentence gaps (0.45-1.2 s); off = [(t0, t1)] music fully out (1.5 s ramps);
    boost = [(t0, t1, db)] extra gain (nat layer during music-off stretches)."""
    n = int(T*FR)+2; t = np.arange(n)/FR
    duck = Lv+(DUCK_DB if duck_db is None else duck_db)-Lm; opn = Lv+(OPEN_DB if open_db is None else open_db)-Lm
    db = np.full(n, duck); od = np.full(n, opn)
    for a, b, v in (duck_curve or []): db[(t >= a) & (t < b)] = Lv+v-Lm
    for a, b, v in (open_curve or []): od[(t >= a) & (t < b)] = Lv+v-Lm
    base = db.copy()
    for a, b in sil:
        if b-a >= open_s:  # music-only stretch (cards, sting)
            a2, b2 = a+0.25, b-0.25
            if b2 > a2: m_ = (t >= a2) & (t <= b2); db[m_] = od[m_]
        elif swell_db and 0.45 <= b-a < open_s:
            m_ = (t >= a+0.05) & (t <= b-0.05); db[m_] = base[m_] + swell_db
    for a, b, v in (boost or []): db[(t >= a) & (t < b)] += v
    k = int(0.25*FR); g = 10**(db/20)
    g = np.convolve(np.pad(g, (k, k), mode="edge"), np.ones(2*k+1)/(2*k+1), mode="valid")[:n]  # 0.25 s ramps
    for a, b in dips:  # hard-ish dips with 60 ms ramps
        r = 0.06; m = np.clip(np.minimum((t-a)/r, (b-t)/r), 0, 1); g = g*(1-m) + 1e-4*m
    for a, b in (off or []):   # music out: 1.5 s ramps down/up
        r = 1.5; m = np.clip(np.minimum((t-a)/r, (b-t)/r), 0, 1); g = g*(1-m) + 1e-5*m
    if fade: g = g*np.clip((T-t)/fade, 0, 1)
    return np.interp(np.arange(int(T*SR))/SR, t, g)

def write_wav(path, x):
    # stereo on purpose: a mono gain track upmixed by ffmpeg gets the -3 dB pan law and throws the levels off
    q = (np.clip(x, 0, 1)*32767).astype("<i2"); q = np.repeat(q, 2)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(q.tobytes())

def contour(T, segs):
    """segs: [(t0, t1, gain_db)] per scene -> voice gain curve with 0.15 s ramps (boundaries sit in pauses)."""
    n = int(T*FR)+2; t = np.arange(n)/FR; db = np.zeros(n)
    for a, b, g in segs: db[(t >= a) & (t < b)] = g
    k = int(0.15*FR); g = 10**(db/20)
    g = np.convolve(np.pad(g, (k, k), mode="edge"), np.ones(2*k+1)/(2*k+1), mode="valid")[:n]
    return np.interp(np.arange(int(T*SR))/SR, t, g)

def auto_contour(scene_times, punch, amt=2.75):
    """+amt dB (2.75) on 'punch' scenes (hook, stats, cards, questions), -amt dB on explainer scenes.
    Human-style emphasis; lifts the loudness range of steady TTS from ~3 LU into the 5-8 LU target."""
    p = list(punch)
    if not (0.3 <= sum(p)/max(1, len(p)) <= 0.7): p = [i % 2 == 0 for i in range(len(p))]
    return [(a, b, amt if q else -amt) for (a, b), q in zip(scene_times, p)]

def mix(voice_mp4, music, sfx, T, out_mp4, sfx_dir="/workspace/work/yt/sfx", PEAK=None, VOL=None, max_sfx=60, tmp="/tmp/mixbus", vo_segs=None, fade=2.0,
        duck_db=None, nat=None, nat_db=(-22.0, -13.0), duck_curve=None, open_curve=None, swell_db=0.0, music_off=None, sfx_wav=None, sfx_db=0.0, dips_per3=5):
    """voice_mp4: concatenated video with voice track. sfx: [(name, t)]. Writes out_mp4 (video copied).
    v9 (long-form only; Shorts call this without the new args and are unchanged): duck_db = music level under the voice
    (v9 long: -18 dB, was -24); nat = natural-sound wav (natlib.build) mixed nat_db[0] dB under the voice while it speaks and
    nat_db[1] dB under voice level in VO-free gaps, so the bed changes with every cut."""
    tag = os.path.splitext(os.path.basename(out_mp4))[0]; tmp = f"{tmp}_{tag}"; os.makedirs(tmp, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", voice_mp4, "-vn", "-ac", "2", "-ar", str(SR), f"{tmp}/vo.wav"], check=True)
    Lv, _ = _ebur(f"{tmp}/vo.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", music, "-t", f"{T:.3f}", "-ac", "2", "-ar", str(SR), f"{tmp}/mu.wav"], check=True)
    Lm, _ = _ebur(f"{tmp}/mu.wav", HP)   # loudness of the stretch of music actually used
    sil = silences(f"{tmp}/vo.wav"); dips = pick_dips(sil, T, per3=dips_per3)
    vc = contour(T, vo_segs or [])
    write_wav(f"{tmp}/env.wav", envelope(T, sil, dips, Lv, Lm, fade=fade, duck_db=duck_db, duck_curve=duck_curve, open_curve=open_curve, swell_db=swell_db, off=music_off)*vc)   # music follows the voice contour: stays DUCK_DB under it
    write_wav(f"{tmp}/venv.wav", vc*0.5)  # x0.5 headroom (16-bit wav holds 0..1); undone below
    ins = ["-i", f"{tmp}/vo.wav", "-stream_loop", "-1", "-i", music, "-i", f"{tmp}/env.wav", "-i", f"{tmp}/venv.wav"]; fx = []; lab = []
    if nat and os.path.exists(nat):   # v9 nat layer: level-match then its own envelope (speech-ducked, open in gaps, no sentence dips)
        try: Ln, _ = _ebur(nat)
        except Exception: Ln = None
        if Ln is not None and Ln > -70:
            write_wav(f"{tmp}/nenv.wav", envelope(T, sil, [], Lv, Ln, fade=fade, duck_db=nat_db[0], open_db=nat_db[1], boost=[(a, b, 8.0) for a, b in (music_off or [])]))
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", nat, "-i", f"{tmp}/nenv.wav", "-filter_complex",
                            f"[0:a]aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo,apad,atrim=0:{T:.3f}[n];[1:a]aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo[e];[n][e]amultiply,highpass=f=80[o]",
                            "-map", "[o]", "-c:a", "pcm_f32le", f"{tmp}/nat_env.wav"], check=True)
            sfx = [("__nat__", 0.0)] + list(sfx)
    if sfx_wav and os.path.exists(sfx_wav):   # v10: all sound effects pre-rendered into one layer (sfxlib.render), scaled to the voice
        g_ = 10**((Lv + 18.0 + sfx_db)/20)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", sfx_wav, "-af", f"volume={g_:.4f},aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo,apad,atrim=0:{T:.3f}",
                        "-c:a", "pcm_f32le", f"{tmp}/sfx_l.wav"], check=True)
        sfx = [x for x in sfx if x[0] == "__nat__"] + [("__sfx__", 0.0)]
    for k, (nm, t) in enumerate(sfx[:max_sfx]):
        if nm == "__sfx__":
            ins += ["-i", f"{tmp}/sfx_l.wav"]; fx.append(f"[{k+4}:a]aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates={SR}[x{k}]"); lab.append(f"[x{k}]"); continue
        if nm == "__nat__":
            ins += ["-i", f"{tmp}/nat_env.wav"]; fx.append(f"[{k+4}:a]aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates={SR}[x{k}]"); lab.append(f"[x{k}]"); continue
        ins += ["-i", f"{sfx_dir}/{nm}.mp3"]; ms = max(0, int((t-PEAK[nm])*1000))
        fx.append(f"[{k+4}:a]volume={VOL[nm]},adelay={ms}|{ms},aformat=channel_layouts=stereo:sample_rates={SR}[x{k}]"); lab.append(f"[x{k}]")
    fc = (f"[1:a]{HP},aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo,atrim=0:{T:.3f}[m];"
          f"[2:a]aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo[e];[m][e]amultiply[md];"
          f"[0:a]aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo[v0];"
          f"[3:a]aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo,volume=2.0[ve];[v0][ve]amultiply[vo];")
    if fx: fc += ";".join(fx)+";"+"".join(lab)+f"amix=inputs={len(lab)}:normalize=0:duration=longest[sx];[vo][md][sx]amix=inputs=3"
    else: fc += "[vo][md]amix=inputs=2"
    fc += ":duration=first:normalize=0[a]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[a]", "-t", f"{T:.3f}", "-c:a", "pcm_f32le", f"{tmp}/pre.wav"], check=True)
    I0, _ = _ebur(f"{tmp}/pre.wav"); G = -14.0 - I0
    # gain to target, then a gentle peak limiter (~-2.5 dBFS) so the final trim keeps true peak under -1.5 dBTP
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{tmp}/pre.wav", "-af", f"volume={G:.2f}dB,alimiter=limit=0.75:attack=4:release=60:level=false",
                    "-c:a", "pcm_f32le", f"{tmp}/lim.wav"], check=True)
    I1, _ = _ebur(f"{tmp}/lim.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", voice_mp4, "-i", f"{tmp}/lim.wav", "-map", "0:v", "-map", "1:a",
                    "-af", f"volume={-14.0-I1:.2f}dB", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{T:.3f}",
                    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart", f"{tmp}/final.mp4"], check=True)
    subprocess.run(["cp", f"{tmp}/final.mp4", out_mp4], check=True)
    I, LRA = _ebur(out_mp4)
    print(f"AUDIO voice {Lv:.1f} LUFS, music(hp) {Lm:.1f}, duck {DUCK_DB if duck_db is None else duck_db} dB, nat {'on' if nat else 'off'}, v10 off {music_off or []} sfx {'layer' if sfx_wav else 'legacy'}, dips {len(dips)} at {[round(a,1) for a,b in dips]}, final I {I:.1f} LUFS, LRA {LRA:.1f} LU", flush=True)
    return dict(I=I, LRA=LRA, dips=dips, Lv=Lv, Lm=Lm)


def actuality_wav(src, ss, d_, out_mp3, Lref, gain_db=0.0, tmp="/tmp"):
    """v9 actuality (shared with make_long's inline version): cut d_ s of real audio at ss, band-limit 90 Hz-9 kHz,
    6 ms / 150 ms fades, level-match to the narrator loudness Lref (+gain_db), soft limit; writes out_mp3 (mono 24 kHz)."""
    w0 = f"{tmp}/act_{os.path.basename(out_mp3)}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{float(ss):.2f}", "-t", f"{float(d_):.2f}", "-i", src, "-vn", "-ac", "1", "-ar", "24000",
                    "-af", f"highpass=f=90,lowpass=f=9000,afade=t=in:d=0.06,afade=t=out:st={max(0, float(d_)-0.15):.2f}:d=0.15", w0], check=True)
    La = _ebur(w0)[0]
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", w0, "-af", f"volume={Lref-La+float(gain_db):.2f}dB,alimiter=limit=0.9", "-ac", "1", "-ar", "24000",
                    "-b:a", "128k", out_mp3], check=True)
    return out_mp3

def phone_check(out_mp4, tag=None, tmp="/tmp/mixbus"):
    """Phone-speaker balance check from the stems mixbus.mix left in its tmp dir: loudness of voice vs music vs nat after a
    phone-speaker band (HP 300 Hz, LP 7 kHz), measured while the voice speaks. Returns dB gaps (voice minus bed)."""
    tag = tag or os.path.splitext(os.path.basename(out_mp4))[0]; t = f"{tmp}_{tag}"; PH = "highpass=f=300,highpass=f=300,lowpass=f=7000"
    def st(fc, ins, name):
        subprocess.run(["ffmpeg", "-y", "-v", "error", *sum([["-i", x] for x in ins], []), "-filter_complex", fc, "-map", "[o]", f"{t}/{name}.wav"], check=True)
        return f"{t}/{name}.wav"
    T = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{t}/vo.wav"]).decode())
    mu = st(f"[0:a]{HP},atrim=0:{T:.3f}[m];[m][1:a]amultiply[o]", [f"{t}/mu.wav", f"{t}/env.wav"], "ph_mu")
    res = {}
    for nm, p in (("voice", f"{t}/vo.wav"), ("music", mu), ("nat", f"{t}/nat_env.wav")):
        if not os.path.exists(p): continue
        try: res[nm] = _ebur(p, PH)[0]
        except Exception: pass
    out = {k: round(v, 1) for k, v in res.items()}
    if "voice" in res:
        for k in ("music", "nat"):
            if k in res: out[f"voice_over_{k}_dB"] = round(res["voice"]-res[k], 1)
    print("PHONE CHECK (300 Hz-7 kHz band, integrated):", out, flush=True)
    return out
