"""Seed Pixabay videos (Pixabay Content License: free commercial use, no attribution) into clips/index.json.
Runs in the Hark sandbox (API key injected by proxy on pixabay.com); the GitHub runner downloads the files in prefetch.py.
Skips AI-generated, vertical and sub-1080p clips. Usage: python pipeline/pixabay_seed.py "kw1,kw2" [per_kw]"""
import json, os, re, sys, time, urllib.request, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); IDX = f"{ROOT}/clips/index.json"
KEY = os.environ.get("PIXABAY_KEY", "__SAVED_KEY__")
LIC = "Pixabay Content License (free commercial use, no attribution) https://pixabay.com/service/license-summary/"
STOP = set("a an the of in on at to and with for from by over into its is are video stock free clip shot view".split())
def words(s): return [w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2]
ix = json.load(open(IDX)); kws = [k.strip() for k in sys.argv[1].split(",") if k.strip()]; per = int(sys.argv[2]) if len(sys.argv) > 2 else 10
added = 0
for kw in kws:
    u = f"https://pixabay.com/api/videos/?key={KEY}&safesearch=true&per_page=50&q=" + urllib.parse.quote(kw)
    try: j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
    except Exception as e: print(kw, "fail", e); time.sleep(2); continue
    n = 0
    for h in j.get("hits", []):
        tags = h.get("tags", ""); cid = f"px_{h['id']}"
        if "ai generated" in tags.lower() or "ai-generated" in tags.lower() or h.get("duration", 0) < 5: continue
        v = None
        for q in ("large", "medium"):
            x = h.get("videos", {}).get(q) or {}
            if x.get("url") and x.get("height", 0) >= 1060 and x.get("width", 0) > x.get("height", 0): v = x; break
        if not v: continue
        if cid in ix:
            ix[cid]["kw"] = sorted(set(ix[cid].get("kw", []) + [kw])); continue
        title = ", ".join(t.strip() for t in tags.split(",")[:4])
        ix[cid] = dict(file=f"{cid}.mp4", source="pixabay", licence=LIC, url=v["url"], page=h.get("pageURL", ""), title=title,
                       tags=sorted(set(words(tags) + words(kw))), kw=[kw], fetched=time.strftime("%Y-%m-%d"), w=v["width"], h=v["height"], dur=h.get("duration"))
        n += 1; added += 1
        if n >= per: break
    print(kw, "->", n, "new", flush=True); time.sleep(0.7)
json.dump(ix, open(IDX, "w"), indent=1, ensure_ascii=False); print("added", added, "total", len(ix))
