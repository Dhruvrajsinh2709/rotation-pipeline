"""Download the library clips a spec needs (the repo keeps only clips/index.json, not the 37 GB of video).
Explicit ids in the spec (clip, shots, endcard_bg, actuality clips ...) are fetched, plus the top-K tag matches per scene
so the renderers' no-repeat / dark-clip swaps have real alternatives on disk. Cached between runs by actions/cache.
Usage: python pipeline/prefetch.py SPEC.json [--k 4] [--cap 70]"""
import json, os, re, subprocess, sys, urllib.request, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__)); from common import ROOT, UA

CL = f"{ROOT}/clips"; IX = json.load(open(f"{CL}/index.json"))
WORD = re.compile(r"[a-z]+")


def ok_meta(m): return m.get("url") and not m.get("bad") and "restricted" not in str(m.get("licence", "")).lower()


def score(m, tags, text):
    t = set(m.get("tags", [])); q = set(WORD.findall(" ".join(tags).lower())); tw = set(WORD.findall((text or "").lower()))
    return 3 * len(t & q) + len(t & tw) + (1.0 if m.get("h", 0) >= 2000 else 0)


def wanted(spec, k):
    explicit, extra = [], []
    def walk(x, tags_up=()):
        if isinstance(x, dict):
            tags = list(x.get("tags") or []) + list(tags_up)
            for key, v in x.items():
                if isinstance(v, str) and v.split("@")[0] in IX: explicit.append(v.split("@")[0])
                elif isinstance(v, list):
                    for e in v:
                        if isinstance(e, str) and e.split("@")[0] in IX: explicit.append(e.split("@")[0])
            if x.get("tags") or x.get("text"):
                c = sorted((score(m, tags, x.get("text", "")), cid) for cid, m in IX.items() if ok_meta(m) and m.get("w", 1920) > m.get("h", 1080))
                extra.extend(cid for s, cid in reversed(c[-k:]) if s >= 3)
            for v in x.values(): walk(v, tuple(spec.get("tags") or []) if x is spec else tags_up)
        elif isinstance(x, list):
            for v in x: walk(v, tags_up)
    walk(spec)
    seen, out = set(), []
    for c in explicit + extra:
        if c not in seen: seen.add(c); out.append(c)
    return out, set(explicit)


def to_mp4(src, dst, still, dur=10.0):
    """Same as clipfetch._to_mp4: a photo becomes a 10 s 1920x1080 slow push; webm/ogv become H.264 mp4."""
    if still:
        vf = (f"scale=2304:1296:force_original_aspect_ratio=increase:flags=lanczos,crop=2304:1296,"
              f"zoompan=z='1+0.06*on/{int(dur*24)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(dur*24)}:s=1920x1080:fps=24,format=yuv420p")
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", src, "-t", f"{dur}", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", dst]
    else:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, "-t", "60", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", dst]
    return subprocess.run(cmd).returncode == 0


def get(cid):
    m = IX[cid]; p = f"{CL}/{cid}.mp4"
    if os.path.exists(p) and os.path.getsize(p) > 10000: return cid, "cached"
    if not m.get("url"): return cid, "no-url"
    ext = m["url"].split("?")[0].rsplit(".", 1)[-1].lower()
    convert = bool(m.get("still")) or ext in ("webm", "ogv", "mov", "jpg", "jpeg", "png")
    tmp = p + ".part" + (f".{ext}" if convert else "")
    try:
        hdr = dict(UA); hdr["User-Agent"] = "RotationPipeline/1.0 (https://youtube.com/@RotationNews; rotation-bot@users.noreply.github.com)"
        req = urllib.request.Request(m["url"], headers=hdr)
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as fh:
            while True:
                b = r.read(1 << 20)
                if not b: break
                fh.write(b)
        if convert:
            out = p + ".conv.mp4"
            if not to_mp4(tmp, out, bool(m.get("still")) or ext in ("jpg", "jpeg", "png")): raise ValueError("convert failed")
            os.remove(tmp); tmp = out
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", tmp], check=True, capture_output=True, text=True).stdout.strip()
        if float(d) < 0.5: raise ValueError("no duration")   # 'N/A' (HTML page or broken file) raises too
        os.replace(tmp, p); return cid, "ok"
    except Exception as e:
        for f in (tmp, p + ".conv.mp4"):
            if os.path.exists(f): os.remove(f)
        return cid, f"fail {type(e).__name__}"


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1])); a = sys.argv[2:]
    k = int(a[a.index("--k") + 1]) if "--k" in a else 4; cap = int(a[a.index("--cap") + 1]) if "--cap" in a else 70
    ids, exp = wanted(spec, k); ids = [c for c in ids if c in exp] + [c for c in ids if c not in exp][: max(0, cap - len(exp))]
    print(f"prefetch {len(ids)} clips ({len(exp)} named in spec)", flush=True)
    res = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for cid, st in ex.map(get, ids): res[cid] = st
    bad = [c for c in exp if res.get(c, "").startswith(("fail", "no-url"))]
    print("prefetch done:", {s: sum(1 for v in res.values() if v == s) for s in set(res.values())}, "| named clips missing:", bad, flush=True)
