"""Rotation SFX library v10 (Study 10, 2026-11-01).
Families of short Mixkit sound effects (Mixkit Sound Effects Free License: commercial use, no attribution,
https://mixkit.co/license/#sfxFree) in sfx2/, indexed in sfx2/index.json {id: {file, family, title, dur, peak, rms, page}}.
resolve(): event family -> a concrete file, random per video, never the same file twice in a row inside a family,
and files used in the last 4 videos are de-prioritised. render(): all events into one stereo wav (numpy), each sound
level-matched to a family target so a click never shouts and a boom never whispers."""
import json, os, subprocess, random, time, urllib.request
import numpy as np

D = "/workspace/work/yt/sfx2"; IDX = f"{D}/index.json"; USED = f"{D}/used.json"; SR = 44100
ALG = ("ZKRSER95J1", "9279146abe17592c4cc491f4124dc5ef", "mixkit_prod_v4")
LIC = "Mixkit Sound Effects Free License (commercial use, no attribution) https://mixkit.co/license/#sfxFree"
# family -> (search queries, max duration s, target peak dBFS before the master gain, how many to keep)
FAM = {
    "whoosh":  (["whoosh", "swoosh", "air woosh", "fast whoosh", "soft whoosh"], 3, -20, 10),
    "click":   (["click", "mouse click", "interface click", "button click", "switch click"], 1.5, -24, 10),
    "tick":    (["tick", "clock tick", "counter tick", "wood tick"], 1.5, -26, 6),
    "pop":     (["pop", "bubble pop", "interface pop", "cork pop"], 1.5, -24, 8),
    "paper":   (["paper", "page turn", "paper slide", "paper flip"], 3, -24, 8),
    "pen":     (["pencil writing", "marker writing", "pen writing", "chalk"], 4, -28, 5),
    "coins":   (["coins", "cash register", "coin drop", "money"], 3, -24, 6),
    "shutter": (["camera shutter", "camera click", "photo shutter"], 2, -24, 4),
    "type":    (["typewriter", "keyboard typing", "typing"], 4, -28, 4),
    "boom":    (["cinematic boom", "deep impact", "cinematic hit", "bass hit", "dramatic impact"], 5, -16, 8),
    "riser":   (["riser", "cinematic rise", "rising tension", "uplifter"], 6, -20, 6),
    "ping":    (["notification ping", "ding", "bell ping", "digital ping"], 2.5, -26, 6),
    "stamp":   (["stamp", "rubber stamp", "thud"], 2, -22, 4),
    "glitch":  (["glitch", "digital glitch", "data"], 2, -28, 4),
}

def load(): return json.load(open(IDX)) if os.path.exists(IDX) else {}
def save(ix): json.dump(ix, open(IDX, "w"), indent=1)

def _alg(q, n=40):
    req = urllib.request.Request(f"https://{ALG[0]}-dsn.algolia.net/1/indexes/{ALG[2]}/query", method="POST",
        data=json.dumps({"query": q, "hitsPerPage": n, "filters": "type:sfx"}).encode(),
        headers={"X-Algolia-Application-Id": ALG[0], "X-Algolia-API-Key": ALG[1], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())["hits"]

def decode(path, sr=SR):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"])
    return np.frombuffer(raw, np.float32).reshape(-1, 2)

def fetch_family(fam):
    qs, maxd, _, keep = FAM[fam]; ix = load(); os.makedirs(D, exist_ok=True)
    have = sum(1 for v in ix.values() if v["family"] == fam); seen = set(ix)
    for q in qs:
        if have >= keep: break
        for h in _alg(q):
            if have >= keep: break
            o = h.get("overviewData") or {}
            if isinstance(o, str): continue
            dur = o.get("duration") or 99; sid = f"s{h['itemId']}"
            if dur > maxd or sid in seen or not o.get("download_url"): continue
            seen.add(sid); tmp = f"{D}/{sid}.wav"; mp3 = f"{D}/{sid}.mp3"
            if subprocess.run(["curl", "-s", "-L", "--max-time", "60", "-o", tmp, o["download_url"]]).returncode: continue
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", "silenceremove=start_periods=1:start_threshold=-50dB",
                                "-ac", "2", "-ar", str(SR), "-b:a", "192k", mp3]); os.remove(tmp)
            if r.returncode or not os.path.exists(mp3): continue
            a = decode(mp3); 
            if len(a) < SR*0.05: os.remove(mp3); continue
            env = np.abs(a).max(1); pk = int(np.argmax(env))
            ix[sid] = dict(file=f"{sid}.mp3", family=fam, title=h.get("title", ""), dur=round(len(a)/SR, 2), peak=round(pk/SR, 3),
                           peak_db=round(float(20*np.log10(env.max()+1e-9)), 1), licence=LIC,
                           page=f"https://mixkit.co/free-sound-effects/{o.get('urlSlug') or h.get('urlSlug') or 'x'}/", q=q,
                           fetched=time.strftime("%Y-%m-%d"))
            have += 1; print(" sfx", fam, sid, ix[sid]["title"], ix[sid]["dur"], flush=True)
    save(ix); return have

def recent(n=4):
    if not os.path.exists(USED): return set()
    return {f for v in json.load(open(USED))[-n:] for f in v.get("files", [])}

def resolve(events, seed="", log_video=None):
    """events: [(family_or_legacy_name, t)] -> [(path, t, peak_s, gain)] . Unknown families pass through as None."""
    ix = load(); rng = random.Random(seed); rec = recent(); last = {}; out = []; used = []
    by = {}
    for k, v in ix.items():
        if not v.get("bad"): by.setdefault(v["family"], []).append(k)
    for e in events:
        fam, t = e[0], e[1]; off_db = e[2] if len(e) > 2 else 0.0
        c = sorted(by.get(fam, []))
        if not c: out.append(None); continue
        fresh = [k for k in c if k not in rec and k != last.get(fam)] or [k for k in c if k != last.get(fam)] or c
        k = rng.choice(fresh); last[fam] = k; m = ix[k]; used.append(k)
        gain = 10**((FAM[fam][2] + off_db - m["peak_db"])/20)
        out.append((f"{D}/{m['file']}", float(t), m["peak"], gain))
    if log_video:
        u = json.load(open(USED)) if os.path.exists(USED) else []
        u.append({"video": log_video, "date": time.strftime("%Y-%m-%d"), "files": sorted(set(used))}); json.dump(u, open(USED, "w"), indent=0)
    return out

def render(resolved, T, out_wav, min_gap=0.12):
    """Mix resolved events into one stereo wav of T s. Events closer than min_gap to the previous one are dropped."""
    bed = np.zeros((int(T*SR)+SR, 2), np.float32); cache = {}; lastt = -9; n = 0
    for r in sorted([x for x in resolved if x], key=lambda x: x[1]):
        path, t, pk, g = r
        if t - lastt < min_gap: continue
        a = cache.get(path)
        if a is None: a = cache[path] = decode(path)
        i0 = int(max(0.0, t - pk)*SR); i1 = min(len(bed), i0+len(a))
        if i1 <= i0: continue
        bed[i0:i1] += a[:i1-i0]*g; lastt = t; n += 1
    bed = bed[:int(T*SR)]; pk = np.abs(bed).max() or 1
    if pk > 0.98: bed *= 0.98/pk
    raw = (bed*32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", out_wav], input=raw, check=True)
    return n

if __name__ == "__main__":
    import sys
    if sys.argv[1] == "fetch":
        for f in (sys.argv[2:] or FAM): print(f, fetch_family(f))
