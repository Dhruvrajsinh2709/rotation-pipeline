"""Rotation music library (v8, 2026-10-29).
Tracks: Mixkit Stock Music Free License (commercial use incl. monetised YouTube, no attribution), stored in music/.
music/index.json: {id: {file, title, mood, bpm, dur, licence, page}}; music/used.json: per-video log of tracks used.
build_bed(): one music bed for a whole video: a mood per chapter, crossfades at chapter boundaries (the breath), and
the last segment aligned so the track's own ending lands on the video's last frame (music resolves, no hard fade).
"""
import json, os, subprocess, random, time
import numpy as np

MD = "/workspace/work/yt/music"; IDX = f"{MD}/index.json"; USED = f"{MD}/used.json"; SR = 44100
LIC = "Mixkit Stock Music Free License (commercial use incl. YouTube, no attribution) https://mixkit.co/license/#musicFree"
MOODS = ("doc", "tense", "light", "ambient", "pulse")

def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode())

def decode(path, sr=SR, mono=False):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1" if mono else "2", "-ar", str(sr), "-"])
    x = np.frombuffer(raw, np.float32)
    return x if mono else x.reshape(-1, 2)

def est_bpm(path):
    """Tempo from an onset-strength autocorrelation (spectral flux), 70-170 BPM."""
    sr = 11025; x = decode(path, sr, mono=True); hop = 256; win = 1024
    n = (len(x)-win)//hop
    if n < 50: return 0
    fr = np.lib.stride_tricks.as_strided(x, (n, win), (x.strides[0]*hop, x.strides[0]))
    S = np.abs(np.fft.rfft(fr*np.hanning(win), axis=1)); fl = np.maximum(0, np.diff(np.log1p(S), axis=0)).sum(1)
    fl = fl-fl.mean(); ac = np.correlate(fl, fl, "full")[len(fl)-1:]; fps = sr/hop
    lags = np.arange(len(ac)); bpm = 60*fps/np.maximum(lags, 1); m = (bpm >= 70) & (bpm <= 170)
    return round(float(bpm[m][np.argmax(ac[m])]), 1)

def load(): return json.load(open(IDX)) if os.path.exists(IDX) else {}

def recent(n=4):
    if not os.path.exists(USED): return []
    return [t for v in json.load(open(USED))[-n:] for t in v.get("tracks", [])]

def log_used(video, tracks):
    u = json.load(open(USED)) if os.path.exists(USED) else []
    u.append({"video": video, "date": time.strftime("%Y-%m-%d"), "tracks": list(dict.fromkeys(tracks))}); json.dump(u, open(USED, "w"), indent=0)

def pick(mood, exclude=(), seed=None, min_dur=60):
    ix = load(); bad = set(exclude) | set(recent())
    c = [k for k, v in ix.items() if v["mood"] == mood and k not in bad and v["dur"] >= min_dur and not v.get("bad")]
    if not c: c = [k for k, v in ix.items() if v["mood"] == mood and k not in set(exclude) and not v.get("bad")]   # all used recently: allow
    if not c: c = [k for k, v in ix.items() if not v.get("bad") and k not in set(exclude)]
    return random.Random(seed).choice(sorted(c))

def build_bed(segments, T, out_wav, xfade=1.6, end_resolve=True, video="", force=None):
    """segments: [(t_start, mood or track id)], sorted, first at 0. Writes a stereo wav of exactly T s. Returns tracks used.
    Same mood on consecutive segments keeps the same track playing (no restart). force: {mood: track_id}."""
    ix = load(); force = force or {}; chosen = {}; used = []
    for _, m in segments:
        if m in ix: chosen[m] = m
        elif m not in chosen: chosen[m] = force.get(m) or pick(m.split("#")[0], exclude=list(chosen.values()), seed=f"{video}{m}")   # v10: "mood#n" = its own track
    # merge consecutive same-track segments
    segs = []
    for (t, m) in segments:
        tr = chosen[m]
        if segs and segs[-1][1] == tr: continue
        segs.append((t, tr))
    bed = np.zeros((int(T*SR)+1, 2), np.float32); pos = {}
    for k, (t0, tr) in enumerate(segs):
        t1 = segs[k+1][0] if k+1 < len(segs) else T
        a = decode(f"{MD}/{ix[tr]['file']}"); L = len(a)/SR
        fi = xfade if k > 0 else 0.0; fo = xfade if k+1 < len(segs) else 0.0
        need = (t1-t0)+fo
        last = k+1 == len(segs)
        if last and end_resolve and L >= need+1: off = L-need        # the track's real ending lands on the last frame
        else:
            off = pos.get(tr, ix[tr].get("intro_skip", 0.0))
            if off+need > L: off = max(0.0, min(off, L-need)) if L > need else 0.0
        s0 = int(off*SR); n = int(need*SR)
        seg = a[s0:s0+n]
        if len(seg) < n: seg = np.concatenate([seg, np.zeros((n-len(seg), 2), np.float32)]) if L > need else np.tile(a, (int(n/len(a))+2, 1))[:n]
        g = np.ones(n, np.float32)
        if fi > 0: m_ = int(fi*SR); g[:m_] = np.sin(np.linspace(0, np.pi/2, m_))**2
        if fo > 0: m_ = int(fo*SR); g[-m_:] = np.cos(np.linspace(0, np.pi/2, m_))**2
        if last and not (end_resolve and L >= need+1): m_ = int(2.5*SR); g[-m_:] *= np.linspace(1, 0, m_)   # fallback fade
        i0 = int(t0*SR)   # incoming track fades in over [t0, t0+xfade] while the previous one fades out
        piece = seg*g[:, None]*(0.11/max(0.02, ix[tr].get("rms", 0.11)))   # rough loudness match between tracks
        i1 = min(len(bed), i0+len(piece)); bed[i0:i1] += piece[:i1-i0]
        pos[tr] = off+need; used.append(tr)
    # loudness-match tracks roughly (RMS per track normalised in the index at build time)
    pk = np.max(np.abs(bed)) or 1.0; bed = bed/max(1.0, pk)
    raw = (np.clip(bed, -1, 1)*32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", out_wav], input=raw, check=True)
    if video: log_used(video, used)
    return used, segs

if __name__ == "__main__":
    import sys
    if sys.argv[1] == "index":   # (re)build index.json from music/*.mp3 + moods.json {id: [title, mood]}
        moods = json.load(open(f"{MD}/moods.json")); ix = load()
        for k, (title, mood) in moods.items():
            f = f"{k}.mp3"
            if not os.path.exists(f"{MD}/{f}"): continue
            x = decode(f"{MD}/{f}", 22050, True); rms = float(np.sqrt(np.mean(x**2)))
            st = np.flatnonzero(np.abs(x) > 0.02); intro = round(float(st[0])/22050, 2) if len(st) else 0.0
            ix[k] = dict(file=f, title=title, mood=mood, bpm=est_bpm(f"{MD}/{f}"), dur=round(dur(f"{MD}/{f}"), 1), rms=round(rms, 4),
                         intro_skip=intro, licence=LIC, page=f"https://mixkit.co/free-stock-music/x-{k.split('_')[1]}/", **({"bad": ix[k]["bad"]} if k in ix and ix[k].get("bad") else {}))
            print(k, ix[k]["title"], mood, ix[k]["bpm"], ix[k]["dur"], ix[k]["rms"])
        json.dump(ix, open(IDX, "w"), indent=1)
