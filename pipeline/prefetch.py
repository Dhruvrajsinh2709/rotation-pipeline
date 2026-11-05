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


def get(cid):
    m = IX[cid]; p = f"{CL}/{cid}.mp4"
    if os.path.exists(p) and os.path.getsize(p) > 10000: return cid, "cached"
    if not m.get("url"): return cid, "no-url"
    tmp = p + ".part"
    try:
        req = urllib.request.Request(m["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as fh:
            while True:
                b = r.read(1 << 20)
                if not b: break
                fh.write(b)
        subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", tmp], check=True, capture_output=True)
        os.replace(tmp, p); return cid, "ok"
    except Exception as e:
        if os.path.exists(tmp): os.remove(tmp)
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
