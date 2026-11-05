"""Rotation natural-sound / ambience library (v9, Study 5, 2026-10-30).
Study 5: CNBC/WSJ voices sit 10-16 dB over a bed of music + location sound that changes on every cut; ours sat 23.5 dB
over near-silence ("TTS in a vacuum"). This module keeps a small ambience library and builds the per-scene `nat` track.

Source: Mixkit sound effects, searched through Mixkit's public Algolia index (type sfx). Licence: Mixkit Sound Effects
Free License - free for commercial use, no attribution required (https://mixkit.co/license/#sfxFree).
Clip audio: a clip whose index entry has audio_ok (public-domain DVIDS / government video) can feed its own sound.

CLI:  python3 natlib.py fetch "city traffic,office ambience,..." [per_kw]
      python3 natlib.py list
API:  pick(tags) -> nat id ; build(segments, T, out_wav) where segments = [(t0, t1, source)] source = nat id | ("clip", path, ss)
"""
import json, os, re, subprocess, sys, time, urllib.request, wave
import numpy as np

ND = "/workspace/work/yt/nat"; IDX = f"{ND}/index.json"; SR = 44100
ALG = ("ZKRSER95J1", "9279146abe17592c4cc491f4124dc5ef", "mixkit_prod_v4")
LIC = "Mixkit Sound Effects Free License (commercial use, no attribution) https://mixkit.co/license/#sfxFree"
STOP = set("a an the of in on at to and with for from by loop ambience ambient background sound sounds noise".split())
# scene-tag words -> ambience words, so "port", "trading floor" or "factory" find something usable
SYN = {"port": "harbor sea waves", "harbor": "sea waves harbor", "ship": "sea waves", "ocean": "sea waves", "sea": "sea waves",
       "city": "city traffic urban", "street": "city traffic urban", "traffic": "city traffic", "washington": "city traffic urban",
       "office": "office", "bank": "office", "trading": "office crowd", "press": "crowd conference", "conference": "crowd conference",
       "factory": "industrial machine", "plant": "industrial machine", "refinery": "industrial machine wind", "oil": "industrial wind",
       "desert": "wind", "field": "wind birds", "farm": "birds wind", "house": "birds suburb", "home": "birds suburb", "neighborhood": "birds suburb",
       "store": "crowd restaurant", "restaurant": "restaurant crowd", "cafe": "restaurant crowd", "shopping": "crowd restaurant",
       "rain": "rain", "storm": "rain thunder", "airport": "airport", "plane": "airport", "train": "train", "car": "city traffic",
       "highway": "city traffic", "truck": "city traffic", "construction": "construction", "crowd": "crowd", "people": "crowd"}

def words(s): return [w for w in re.findall(r"[a-z]+", (s or "").lower()) if w not in STOP and len(w) > 2]
def load(): return json.load(open(IDX)) if os.path.exists(IDX) else {}

def algolia(q, n=20):
    req = urllib.request.Request(f"https://{ALG[0]}-dsn.algolia.net/1/indexes/{ALG[2]}/query", method="POST",
        data=json.dumps({"query": q, "hitsPerPage": n, "filters": "type:sfx"}).encode(),
        headers={"X-Algolia-Application-Id": ALG[0], "X-Algolia-API-Key": ALG[1], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())["hits"]

def fetch(kw, per=2, min_dur=20):
    ix = load(); os.makedirs(ND, exist_ok=True); got = 0
    for h in algolia(kw, 30):
        o = h.get("overviewData") or {}; dur = o.get("duration") or 0; nid = f"sfx_{h['itemId']}"
        if dur < min_dur or nid in ix or not o.get("download_url"): continue
        title = h.get("title", ""); tags = [t.lower() if isinstance(t, str) else t.get("name", "").lower() for t in (h.get("tags") or [])]
        tmp = f"{ND}/{nid}.wav"
        if subprocess.run(["curl", "-s", "-L", "--max-time", "120", "-o", tmp, o["download_url"]]).returncode: continue
        mp3 = f"{ND}/{nid}.mp3"
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-ac", "2", "-ar", str(SR), "-b:a", "192k", mp3]); os.remove(tmp)
        if r.returncode: continue
        ix[nid] = dict(file=f"{nid}.mp3", title=title, tags=sorted(set(words(title) + words(" ".join(tags)) + words(kw))), dur=dur, licence=LIC,
                       page=f"https://mixkit.co/free-sound-effects/{(o.get('urlSlug') or 'x')}/", kw=kw, fetched=time.strftime("%Y-%m-%d"))
        got += 1; print("  nat", nid, title, dur, flush=True)
        if got >= per: break
    json.dump(ix, open(IDX, "w"), indent=1); return got

def score(meta, tags):
    q = set()
    for t in words(" ".join(tags or [])): q |= {t} | set(SYN.get(t, "").split())
    return len(q & set(meta["tags"]))

def pick(tags, exclude=(), min_score=1):
    ix = load(); c = sorted(((score(m, tags), k) for k, m in ix.items() if k not in exclude), reverse=True)
    return c[0][1] if c and c[0][0] >= min_score else None

def for_scene(n_, tags=(), spec_tags=(), default=None):
    """Scene `nat` key -> ambience id (shared by make_long logic and make_story): False = none, an index id = that id,
    a word list = those words + tags; otherwise picked from the scene tags + video tags, else `default`."""
    if n_ is False: return None
    if isinstance(n_, str) and n_ in load(): return n_
    w = (list(n_) if isinstance(n_, list) else []) + list(tags or []) + list(spec_tags or [])
    return pick(w) or default

_DEC = {}
def decode(path, ss=0.0, dur=None):
    k = (path, round(ss, 2), round(dur or 0, 2))
    if k in _DEC: return _DEC[k]
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss:.2f}", "-i", path] + (["-t", f"{dur:.2f}"] if dur else []) + ["-vn", "-f", "s16le", "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.float32)/32768
    if len(a): a = a/max(1e-4, float(np.sqrt(np.mean(a**2))))*0.05   # every source normalised to the same RMS (~-26 dBFS)
    _DEC[k] = a; return a

def build(segments, T, out_wav, xf=0.12):
    """segments: [(t0, t1, src, gain_db)], src = nat id | ("clip", path, ss) | None (silence, e.g. full-screen graphics).
    Each segment gets its own in-point (so repeated ambiences never line up), 120 ms crossfades at every cut."""
    ix = load(); bed = np.zeros((int(T*SR)+1, 2), np.float32); log = []
    for n_, (t0, t1, src, gdb) in enumerate(segments):
        if src is None or t1-t0 < 0.2: continue
        L = t1-t0+2*xf
        if isinstance(src, tuple): a = decode(src[1], max(0.0, src[2]-xf), L)
        else:
            if src not in ix: continue
            full = decode(f"{ND}/{ix[src]['file']}")
            if len(full) < SR: continue
            off = int(((n_*7.31) % max(0.1, len(full)/SR - L - 0.5))*SR) if len(full)/SR > L+0.5 else 0
            a = full[off:off+int(L*SR)]
            while len(a) < int(L*SR): a = np.concatenate([a, full[:int(L*SR)-len(a)]])
        if not len(a): continue
        g = np.ones(len(a), np.float32); m = min(len(a)//2, int(2*xf*SR))
        g[:m] = np.sin(np.linspace(0, np.pi/2, m))**2; g[-m:] = np.cos(np.linspace(0, np.pi/2, m))**2
        i0 = max(0, int((t0-xf)*SR)); piece = a*g[:, None]*(10**(gdb/20)); i1 = min(len(bed), i0+len(piece)); bed[i0:i1] += piece[:i1-i0]
        log.append((round(t0, 1), src if not isinstance(src, tuple) else os.path.basename(src[1])))
    raw = (np.clip(bed, -1, 1)*32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", out_wav], input=raw, check=True)
    return log

if __name__ == "__main__":
    if sys.argv[1] == "fetch":
        for kw in sys.argv[2].split(","): print(kw, "->", fetch(kw.strip(), int(sys.argv[3]) if len(sys.argv) > 3 else 2))
    elif sys.argv[1] == "list":
        for k, v in load().items(): print(k, v["dur"], v["title"], v["tags"])
