"""Rotation clip library fetcher (v8, 2026-10-29).
Searches free commercial-use footage sources by keyword, downloads the highest resolution available
(prefers 2160p, min 1080p, rejects low bitrate / vertical / short files), caches to clips/ and records
source + licence + tags in clips/index.json.

Sources (all free for commercial use, no attribution required):
  mixkit  - Mixkit Free License (https://mixkit.co/license/#videoFree). Public files: <id>-2160.mp4 / -1080.mp4
            exist for many older clips; newer clips are 720 only on the free tier (skipped).
  coverr  - Coverr License (https://coverr.co/license/). 1080p public files; 'premium', AI-generated and temp
            uploads are skipped.
  nasa    - NASA media, public domain (https://www.nasa.gov/nasa-brand-center/images-and-media/), ~orig.mp4.
Pexels / Pixabay need a (free) API key: their sites return 403 to scripted requests. Not used.

CLI:  python3 clipfetch.py search "cargo ship" [n]      -> download up to n new clips for the keyword
      python3 clipfetch.py batch kw1,kw2,...  [n]        -> several keywords
      python3 clipfetch.py stats
Library API (used by make_long.py): load_index(), pick(tags, text, exclude, n)
"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse, concurrent.futures as cf, fcntl

CL = "/workspace/work/yt/clips"; IDX = f"{CL}/index.json"; USED = f"{CL}/used.json"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
LIC = {"mixkit": "Mixkit Free License (commercial use, no attribution) https://mixkit.co/license/#videoFree",
       "coverr": "Coverr License (free commercial use, no attribution) https://coverr.co/license/",
       "nasa": "NASA media, public domain (US Gov work) https://www.nasa.gov/nasa-brand-center/images-and-media/"}
MIN_KBPS = {2160: 12000, 1440: 8000, 1080: 3800}
STOP = set("a an the of in on at to and with for from by over into its is are video stock free clip shot view".split())

import threading, urllib.error
_PG = threading.Semaphore(2)
def get(url, timeout=30):
    for k in range(6):
        try:
            with _PG:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=timeout) as r: out = r.read().decode("utf-8", "ignore")
                if "mixkit.co" in url: time.sleep(3.0)
                return out
        except urllib.error.HTTPError as e:
            if e.code == 429 and k < 5: time.sleep(10*(k+1)); continue
            raise

def head_ok(url):
    try:
        req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=20) as r: return r.status in (200, 206)
    except Exception: return False

def load_index():
    if os.path.exists(IDX): return json.load(open(IDX))
    return {}

def save_index(ix):
    tmp = IDX + ".tmp"; json.dump(ix, open(tmp, "w"), indent=0); os.replace(tmp, IDX)

def words(s): return [w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2]

def probe(path):
    try:
        o = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
              "stream=width,height,bit_rate,r_frame_rate:format=duration,bit_rate", "-of", "json", path]).decode())
        s = o["streams"][0]; f = o["format"]; br = int(s.get("bit_rate") or f.get("bit_rate") or 0)//1000
        a, b = s["r_frame_rate"].split("/"); return dict(w=s["width"], h=s["height"], kbps=br, fps=round(int(a)/max(1, int(b)), 2), dur=round(float(f["duration"]), 2))
    except Exception: return None

# ---------------- source search: return [(cid, title, page, [candidate urls best-first])] ----------------
ALG = ("ZKRSER95J1", "9279146abe17592c4cc491f4124dc5ef", "mixkit_prod_v4")   # Mixkit's public site search (Algolia) - not rate-limited like mixkit.co
def algolia(query, n=60, page=0, typ="video"):
    req = urllib.request.Request(f"https://{ALG[0]}-dsn.algolia.net/1/indexes/{ALG[2]}/query", method="POST",
        data=json.dumps({"query": query, "hitsPerPage": n, "page": page, "filters": f"type:{typ}"}).encode(),
        headers={"X-Algolia-Application-Id": ALG[0], "X-Algolia-API-Key": ALG[1], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())["hits"]

def s_mixkit(kw, pages=1):
    """Mixkit via its Algolia index: licenseType (free|restricted), tags and the 1080/2160 file urls come with each hit."""
    out = []
    for pg in range(pages):
        try: hits = algolia(kw, 60, pg)
        except Exception as e: print("algolia fail", e); break
        for h in hits:
            o = h.get("overviewData") or {}
            if h.get("licenseType") != "free" or h.get("orientation") != "horizontal": continue
            urls = [u for u in (o.get("video_2160_url"), o.get("video_1080_url")) if u]
            if not urls: continue
            vid = h["itemId"]; title = h.get("title") or o.get("urlSlug", "").replace("-", " ")
            out.append((f"mk_{vid}", title + " | " + " ".join(h.get("tags") or []), f"https://mixkit.co/free-stock-video/{o.get('urlSlug','x')}-{vid}/", urls))
    return out

def s_coverr(kw):
    try: h = get("https://coverr.co/s?q=" + urllib.parse.quote(kw))
    except Exception: return []
    out = []
    for slug in sorted(set(re.findall(r'cdn\.coverr\.co/videos/(coverr-[a-z0-9-]+)/', h))):
        if any(x in slug for x in ("premium", "temp", "ai-generation", "paywall")): continue
        m = re.search(r"-(\d+)$", slug); cid = "cv_" + (m.group(1) if m else slug[7:40])
        out.append((cid, slug[7:].rsplit("-", 1)[0].replace("-", " "), f"https://coverr.co/videos/{slug[7:]}", [f"https://cdn.coverr.co/videos/{slug}/1080p.mp4"]))
    return out

def s_nasa(kw):
    try: j = json.loads(get("https://images-api.nasa.gov/search?media_type=video&q=" + urllib.parse.quote(kw)))
    except Exception: return []
    out = []
    for it in j["collection"]["items"][:25]:
        d = it["data"][0]; nid = d["nasa_id"]
        try: files = json.loads(get(it["href"]))
        except Exception: continue
        c = [u for u in files if u.endswith("~orig.mp4")] + [u for u in files if u.endswith("~large.mp4")]
        if c: out.append(("nasa_" + re.sub(r"[^A-Za-z0-9]+", "_", nid)[:40], d.get("title", nid), f"https://images.nasa.gov/details/{urllib.parse.quote(nid)}", [u.replace(" ", "%20").replace("http://", "https://") for u in c]))
    return out

SOURCES = {"mixkit": s_mixkit, "coverr": s_coverr, "nasa": s_nasa}

def fetch_one(cid, title, page, urls, src, kw):
    path = f"{CL}/{cid}.mp4"
    if os.path.exists(path): return cid, "exists", None
    # Mixkit: only licenseType "free" hits are returned by s_mixkit (the Restricted licence is personal/non-commercial only)
    for u in urls:
        if not head_ok(u): continue
        os.makedirs(f"{CL}/.tmp", exist_ok=True); tmp = f"{CL}/.tmp/cf_{cid}.mp4"
        r = subprocess.run(["curl", "-s", "-L", "--max-time", "240", "-A", UA["User-Agent"], "-o", tmp, u])
        if r.returncode != 0: continue
        pr = probe(tmp)
        if not pr: os.remove(tmp); continue
        res = 2160 if pr["h"] >= 2000 else 1440 if pr["h"] >= 1400 else 1080 if pr["h"] >= 1060 else 0
        if pr["w"] <= pr["h"] or res == 0 or pr["dur"] < 5 or pr["kbps"] < MIN_KBPS[res]:
            os.remove(tmp); print("  reject", cid, pr, flush=True); return cid, f"rejected {pr}", None
        subprocess.run(["cp", tmp, path]); os.remove(tmp)
        return cid, "ok", dict(file=f"{cid}.mp4", source=src, licence=LIC[src], url=u, page=page, title=title.split(" | ")[0],
                               tags=sorted(set(words(title) + (words(kw) if src != "coverr" or set(words(title)) & set(words(kw)) else []))), kw=[kw], fetched=time.strftime("%Y-%m-%d"), **pr)
    return cid, "no hd file", None

def search(kw, n=8, sources=("mixkit", "coverr")):
    ix = load_index(); cands = []
    for s in sources:
        for c in SOURCES[s](kw): cands.append((s,) + c)
    new = []; got = 0; seen = set()
    for s, cid, title, page, urls in cands:
        if cid in seen: continue
        if s == "coverr" and not (set(words(title)) & set(words(kw))): continue
        seen.add(cid)
        if cid in ix:
            if kw not in ix[cid].get("kw", []): ix[cid]["kw"] = ix[cid].get("kw", []) + [kw]; ix[cid]["tags"] = sorted(set(ix[cid]["tags"] + words(kw)))
            continue
        new.append((cid, title, page, urls, s, kw))
    res = []
    with cf.ThreadPoolExecutor(6) as ex:
        futs = [ex.submit(fetch_one, *a) for a in new[:max(n*3, 12)]]
        for f in cf.as_completed(futs):
            cid, st, meta = f.result(); res.append((cid, st))
            if meta and got < n: ix[cid] = meta; got += 1
            elif meta: os.remove(f"{CL}/{cid}.mp4")
    # merge under a lock (several batches may run)
    with open(IDX + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX); cur = load_index()
        for k, v in ix.items():
            if k not in cur: cur[k] = v
            else: cur[k]["kw"] = sorted(set(cur[k].get("kw", []) + v.get("kw", []))); cur[k]["tags"] = sorted(set(cur[k]["tags"] + v["tags"]))
        save_index(cur)
    print(kw, "->", got, "new;", sum(1 for _, s in res if s.startswith("rejected")), "rejected;", sum(1 for _, s in res if s == "no hd file"), "720-only;", sum(1 for _, s in res if s == "restricted licence"), "restricted", flush=True)
    return got

# ---------------- selection API ----------------
def recent_used(n_videos=6):
    if not os.path.exists(USED): return set()
    u = json.load(open(USED)); s = set()
    for v in u[-n_videos:]: s |= set(v.get("clips", []))
    return s

def log_used(video, clips):
    u = json.load(open(USED)) if os.path.exists(USED) else []
    u.append({"video": video, "date": time.strftime("%Y-%m-%d"), "clips": sorted(set(clips))}); json.dump(u, open(USED, "w"), indent=0)

def score(meta, tags, text):
    t = set(meta.get("tags", [])); q = set(words(" ".join(tags))); tw = set(words(text or ""))
    s = 3*len(t & q) + 1*len(t & tw)
    s += {2160: 1.0, 1440: 0.6}.get(meta.get("h", 0) >= 2000 and 2160 or (meta.get("h", 0) >= 1400 and 1440), 0)
    return s

def pick(tags, text="", exclude=(), n=1, min_score=1):
    ix = load_index(); ex = set(exclude)
    c = sorted(((score(m, tags, text), k) for k, m in ix.items() if k not in ex and os.path.exists(f"{CL}/{k}.mp4") and not m.get("bad") and m.get("w", 1920) > m.get("h", 1080)), reverse=True)
    return [k for s, k in c if s >= min_score][:n]


# ======================= v9 (Study 5, 2026-10-30): subject-match gate + public-domain / CC sources =======================
# Ambiguous words never count as a match on their own: "vessel" (Hudson Yards staircase), "container" (food tub), "bank" (river),
# "plant" (flower), "chip" (snack), "crane" (bird), "apple" (fruit), "oil" (painting/cooking) ... They add 0.5 only when at
# least one unambiguous scene tag also matches.
AMBIG = set("""vessel vessels container containers bank banks plant plants chip chips crane cranes apple port ports mouse bull bear
shell tank tanks crude fed rate rates market markets trade power energy capital interest chart charts office building buildings line
lines board record spring fall oil gas jet tower towers light bar bars stock stocks bond bonds note notes share shares cell cells
pitch strike fan fans drive drives screen screens tablet tablets bill bills check cheque cash coin coins gold green field fields
mine mines fund funds yield yields hike hikes cut cuts amazon meta""".split())
LIC_V9 = {"wikimedia": "Wikimedia Commons ({lic}) - attribution recorded per clip",
          "dvids": "DVIDS, public domain (US Government work; DVIDS terms https://www.dvidshub.net/about/copyright)",
          "fed": "Federal Reserve Board, public domain (https://www.federalreserve.gov/disclaimer.htm); cite the Board",
          "usgov": "US Government work, public domain (17 U.S.C. 105)"}
OK_LIC = re.compile(r"^(public domain|pd\b|pd-|cc0|cc by \d|cc-by-\d|cc by \d\.\d|cc-by \d)", re.I)

def match_score(meta, tags, text="", detail=False):
    """v9 subject match: distinct unambiguous scene-tag words found in the clip's title words + clip tags (1 each), ambiguous
    words +0.5 only alongside an unambiguous hit, narration nouns in the title +0.5 each (max +1). Gate default match_min = 2."""
    def fold(ws):
        o = set(ws)
        for t in list(o): o.add(t[:-1] if t.endswith("s") else t + "s")   # crude plural/singular folding
        return o
    title_w = fold(words(meta.get("title", ""))); kw_w = fold(words(" ".join(meta.get("kw", []))))
    tag_w = fold(meta.get("tags", [])); ct = tag_w | title_w
    tl = " " + " ".join(re.findall(r"[a-z]+", meta.get("title", "").lower())) + " "
    phr = [t.lower() for t in (tags or []) if " " in t.strip()]
    ph_hit = [p_ for p_ in phr if (" " + " ".join(re.findall(r"[a-z]+", p_)) + " ") in tl]   # multi-word tag found as a phrase in the title
    q = set(words(" ".join(t for t in (tags or []) if t.lower() not in ph_hit)))
    # a word only present because it was our own search keyword (not in the clip's title or its source tags) counts half
    single = set(words(" ".join(t for t in (tags or []) if " " not in t.strip())))
    def wt(w): return (1.0 if (w in title_w or (w in tag_w and w not in kw_w)) else 0.5) * (1.0 if (w in single or not phr) else 0.5)   # words of an unmatched phrase tag count half
    hard = sorted(w for w in q if w in ct and w not in AMBIG); soft = sorted(w for w in q if w in ct and w in AMBIG)
    s = sum(wt(w) for w in hard) + (0.5*len(soft) if (hard or ph_hit) else 0) + 2.0*len(ph_hit)
    if not ph_hit and hard and not (set(hard) & title_w) and meta.get("source") in ("mixkit", "coverr"): s = min(s, 1.0)   # stock: the TITLE must name the subject
    tw = set(w for w in words(text or "") if w not in AMBIG and w not in q)
    s += min(1.0, 0.5*len(tw & title_w)) if hard else 0
    return (round(s, 2), hard + ph_hit, soft) if detail else round(s, 2)

def pick_matched(tags, text="", exclude=(), n=1, match_min=2.0, prefer_hi=True):
    """v9 picks: only clips whose match_score >= match_min, best first (2160p breaks ties). -> [(clip_id, score)]."""
    ix = load_index(); ex = set(exclude); out = []
    for k, m in ix.items():
        if k in ex or m.get("bad") or not os.path.exists(f"{CL}/{k}.mp4") or m.get("w", 1920) <= m.get("h", 1080): continue
        s = match_score(m, tags, text)
        if s >= match_min: out.append((s + (0.3 if prefer_hi and m.get("h", 0) >= 2000 else 0), s, k))
    out.sort(reverse=True)
    return [(k, s) for _, s, k in out[:n]]

def _to_mp4(src, dst, still=False, dur=10.0):
    """Transcode webm/ogv/mov to H.264 mp4 (keeps audio); a still image becomes a dur-second 1920x1080 clip with a slow push."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if still:
        vf = (f"scale=2304:1296:force_original_aspect_ratio=increase:flags=lanczos,crop=2304:1296,"
              f"zoompan=z='1+0.06*on/{int(dur*24)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(dur*24)}:s=1920x1080:fps=24,format=yuv420p")
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", src, "-t", f"{dur}", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", dst]
    else:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", dst]
    return subprocess.run(cmd).returncode == 0

def add_local(cid, path, source, licence, page, title, tags, attribution="", dateline=None, audio_ok=False, still=False, extra=None):
    """Register a clip already on disk (e.g. a public-domain government video) in clips/index.json."""
    pr = probe(path) or {}
    meta = dict(file=os.path.basename(path), source=source, licence=licence, url=(extra or {}).get("url", ""), page=page, title=title,
                tags=sorted(set(words(title) + words(" ".join(tags)))), kw=[], fetched=time.strftime("%Y-%m-%d"), attribution=attribution,
                dateline=dateline, audio_ok=audio_ok, still=still, **pr)
    meta.update({k: v for k, v in (extra or {}).items() if k != "url"})
    with open(IDX + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX); cur = load_index(); cur[cid] = meta; save_index(cur)
    return meta

def s_wikimedia(kw, media="video", n=30):
    """Wikimedia Commons search (File namespace). Keeps Public domain / CC0 / CC BY only (no BY-SA, no NC/ND); records the
    artist + licence for the end credits. media: video | image."""
    q = kw + (" filetype:video" if media == "video" else " filetype:bitmap")
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit=%d&gsrsearch=%s"
         "&prop=imageinfo&iiprop=url|size|extmetadata|mediatype&iiurlwidth=3840") % (n, urllib.parse.quote(q))
    try: j = json.loads(get(u))
    except Exception as e: print("commons fail", e); return []
    out = []
    for p in (j.get("query") or {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]; m = ii.get("extmetadata", {})
        lic = re.sub("<[^>]+>", "", (m.get("LicenseShortName") or {}).get("value", "")).strip()
        if not OK_LIC.match(lic) or re.search(r"\bSA\b|NC|ND", lic): continue
        w, h = ii.get("width", 0), ii.get("height", 0)
        if media == "video" and (h < 700 or w <= h): continue
        if media == "image" and (w < 1600 or w <= h): continue
        artist = re.sub("<[^>]+>", "", (m.get("Artist") or {}).get("value", "")).strip()[:80]
        title = p["title"][5:].rsplit(".", 1)[0].replace("_", " ")
        date = re.sub("<[^>]+>", "", (m.get("DateTimeOriginal") or {}).get("value", "")).strip()[:20]
        import hashlib; cid = "wm_" + re.sub(r"[^A-Za-z0-9]+", "_", title)[:36].strip("_") + "_" + hashlib.md5(title.encode()).hexdigest()[:6]
        url = ii.get("url"); out.append((cid, title, ii.get("descriptionurl", ""), [url], dict(lic=lic, artist=artist, date=date, still=(media == "image"), w=w, h=h)))
    return out

def fetch_wikimedia(kw, n=4, media="video", exact=None):
    """exact: only accept the file whose title (without extension) equals this string (used by `url` on a File: page)."""
    ix = load_index(); got = 0
    for cid, title, page, urls, info in s_wikimedia(kw, media):
        if got >= n: break
        if cid in ix or (exact and title.lower() != exact.lower()): continue
        if os.path.exists(f"{CL}/{cid}.mp4") and os.path.getsize(f"{CL}/{cid}.mp4") > 10000: ok = True
        else: ok = None
        os.makedirs(f"{CL}/.tmp", exist_ok=True); ext = urls[0].split("?")[0].rsplit(".", 1)[-1].lower(); tmp = f"{CL}/.tmp/{cid}.{ext}"
        if ok: pass
        elif subprocess.run(["curl", "-s", "-L", "--max-time", "300", "-A", "RotationBot/1.0 (dhruvrajsinhs394@gmail.com)", "-o", tmp, urls[0].split("?")[0]]).returncode: continue
        if not ok and not info["still"]:   # keep at most the first 60 s of long videos (a b-roll pick never needs more)
            t2 = tmp + ".cut." + ext; subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-t", "60", "-c", "copy", t2])
            if os.path.exists(t2) and os.path.getsize(t2) > 1000: os.replace(t2, tmp)
        if not ok: ok = _to_mp4(tmp, f"{CL}/{cid}.mp4", still=info["still"]); os.remove(tmp)
        if not ok: continue
        attr = f"\"{title}\" by {info['artist'] or 'unknown'}, {info['lic']}, via Wikimedia Commons"
        add_local(cid, f"{CL}/{cid}.mp4", "wikimedia", LIC_V9["wikimedia"].format(lic=info["lic"]), page, title, words(kw), attribution=attr,
                  still=info["still"], extra={"url": urls[0], "src_w": info["w"], "src_h": info["h"], "date_taken": info["date"], "kw": [kw]})
        got += 1; print("  wikimedia", cid, info["lic"], info["w"], "x", info["h"], flush=True)
    print(kw, "-> wikimedia", got, "new", flush=True); return got

def fetch_dvids(page_url, tags=()):
    """DVIDS video page -> public-domain clip with its real place + date (dateline) and the videographer credit.
    DVIDS site search sits behind a bot wall (HTTP 202) and the API needs a key, so find pages with a web search
    (site:dvidshub.net/video <topic>) and pass the URL here: python3 clipfetch.py url <dvids page>."""
    import html as _h
    t = get(page_url); m = re.search(r'https://d34w7g4gy10iej\.cloudfront\.net/video/[^"\s]+\.mp4', t)
    if not m: print("no mp4 on page", page_url); return None
    def field(k):
        i = t.find(k)
        if i < 0: return ""
        s_ = re.sub(r"\s+", " ", re.sub(r"<[^>]*>?", " ", _h.unescape(re.sub(r"<[^>]+>", " ", t[i+len(k):i+len(k)+300])))).strip(); return s_.split("<")[0]
    vid = re.search(r"/video/(\d+)", page_url).group(1); title = _h.unescape(re.search(r'og:title" content="([^"]+)', t).group(1))
    by = field("Video by").split(" Date")[0][:80]; date = field("Date Taken:")[:10]; loc = field("Location:").split(" Video")[0].split(" Web")[0][:60].title()
    if "PUBLIC DOMAIN" not in t.upper(): print("not marked public domain - skipped"); return None
    cid = f"dv_{vid}"; tmp = f"{CL}/.tmp/{cid}.mp4"; os.makedirs(f"{CL}/.tmp", exist_ok=True)
    if subprocess.run(["curl", "-s", "-L", "--max-time", "600", "-A", UA["User-Agent"], "-o", tmp, m.group(0)]).returncode: return None
    subprocess.run(["cp", tmp, f"{CL}/{cid}.mp4"]); os.remove(tmp)
    try: mm, dd, yy = date.split("."); dl = f"{loc}|{time.strftime('%b. %-d, %Y', time.strptime(date, '%m.%d.%Y'))}"
    except Exception: dl = loc
    meta = add_local(cid, f"{CL}/{cid}.mp4", "dvids", LIC_V9["dvids"], page_url, title, list(tags), attribution=f"{title} - video by {by} (DVIDS, public domain)",
                     dateline=dl, audio_ok=True, extra={"url": m.group(0)})
    print("dvids", cid, meta.get("w"), "x", meta.get("h"), dl, flush=True); return cid

def fetch_url(url, tags=()):
    """python3 clipfetch.py url <page> [tags]: DVIDS video page, Wikimedia Commons File: page or NASA images page."""
    if "dvidshub.net/video/" in url: return fetch_dvids(url, tags)
    if "commons.wikimedia.org/wiki/File:" in url:
        name = urllib.parse.unquote(url.split("File:", 1)[1]).replace("_", " "); base = name.rsplit(".", 1)[0]
        return fetch_wikimedia(f'intitle:"{base}"', 1, "image" if name.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")) else "video", exact=base)
    if "images.nasa.gov/details/" in url: return search(urllib.parse.unquote(url.rsplit("/", 1)[1]), 1, sources=("nasa",))
    print("unsupported url", url)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "search": search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif cmd == "batch":
        for kw in sys.argv[2].split(","): search(kw.strip(), int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif cmd == "src":   # python3 clipfetch.py src coverr,nasa "kw1,kw2" n
        for kw in sys.argv[3].split(","): search(kw.strip(), int(sys.argv[4]) if len(sys.argv) > 4 else 6, sources=tuple(sys.argv[2].split(",")))
    elif cmd == "nasa":
        for kw in sys.argv[2].split(","): search(kw.strip(), int(sys.argv[3]) if len(sys.argv) > 3 else 4, sources=("nasa",))
    elif cmd == "legacy":   # index the pre-v8 Mixkit clips (hd_<id> / <id>) with their real title + licence
        ix = load_index()
        for f in sorted(os.listdir(CL)):
            if not f.endswith(".mp4") or f[:-4] in ix: continue
            m = re.fullmatch(r"(?:hd_)?(\d+)\.mp4", f)
            if not m: continue
            vid = m.group(1)
            try:
                req = urllib.request.Request(f"https://{ALG[0]}-dsn.algolia.net/1/indexes/{ALG[2]}/query", method="POST",
                    data=json.dumps({"query": "", "hitsPerPage": 1, "filters": f"type:video AND itemId={vid}"}).encode(),
                    headers={"X-Algolia-Application-Id": ALG[0], "X-Algolia-API-Key": ALG[1], "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r: hh = json.loads(r.read())["hits"]
            except Exception as e: print(f, "algolia fail", e); continue
            if not hh: print(f, "not found"); continue
            h0 = hh[0]; o = h0.get("overviewData") or {}
            title = (h0.get("title") or "") + " | " + " ".join(h0.get("tags") or []); page = f"https://mixkit.co/free-stock-video/{o.get('urlSlug','x')}-{vid}/"
            lic = ["videoFree"] if h0.get("licenseType") == "free" else ["videoRestricted"]
            pr = probe(f"{CL}/{f}") or {}
            meta = dict(file=f, source="mixkit", licence=LIC["mixkit"] if "videoFree" in lic else "Mixkit Restricted License (personal, non-commercial only)",
                        url="", page=page, title=title.split(" | ")[0], tags=sorted(set(words(title))), kw=[], fetched="pre-v8", legacy=True, **pr)
            if "videoFree" not in lic: meta["bad"] = "restricted licence"
            elif pr.get("h", 0) < 1060: meta["bad"] = "below 1080p"
            ix[f[:-4]] = meta; print(f, title, lic, pr.get("h"))
        with open(IDX + ".lock", "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX); cur = load_index(); cur.update({k: v for k, v in ix.items() if k not in cur}); save_index(cur)
    elif cmd == "wikimedia":   # python3 clipfetch.py wikimedia "kw1,kw2" [n] [video|image]
        for kw in sys.argv[2].split(","): fetch_wikimedia(kw.strip(), int(sys.argv[3]) if len(sys.argv) > 3 else 4, sys.argv[4] if len(sys.argv) > 4 else "video")
    elif cmd == "url":         # python3 clipfetch.py url <dvids/commons/nasa page> [tag1,tag2]
        fetch_url(sys.argv[2], sys.argv[3].split(",") if len(sys.argv) > 3 else ())
    elif cmd == "match":       # python3 clipfetch.py match "tag1,tag2" ["narration"]  -> top matches with scores
        for k, s_ in pick_matched(sys.argv[2].split(","), sys.argv[3] if len(sys.argv) > 3 else "", n=15, match_min=0.5): print(s_, k, load_index()[k]["title"])
    elif cmd == "stats":
        ix = load_index(); from collections import Counter
        print(len(ix), "clips;", Counter(v["source"] for v in ix.values()), Counter(("2160" if v["h"] >= 2000 else "1440" if v["h"] >= 1400 else "1080") for v in ix.values()))
