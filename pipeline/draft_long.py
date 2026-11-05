"""Long video spec for the Wednesday "Rotation Explains" (make_explain.py) or the Saturday deep dive (make_long.py).
Order of preference:
  1. specs/queue/<date>_<kind>.json  (a spec Hark or the user committed: researched + verified; best quality)
  2. NVIDIA draft from today's news: pick a story in the 3 lanes, fetch 3-5 articles, outline, then chapter-by-chapter
     scenes in the same shape as the last published spec of that format. Every number is checked against the articles.
Writes specs/long/spec_<date>_<slug>.json and prints SPEC <path>.
Usage: python pipeline/draft_long.py explain|long [--test]"""
import json, os, re, sys, time, glob, urllib.request, urllib.parse, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__)); from common import *

KIND = sys.argv[1]; TEST = "--test" in sys.argv; DAY = time.strftime("%Y-%m-%d")
EX = {"explain": "spec_2026-11-04_explain_indigo.json", "long": "spec_2026-11-01_pump-gap.json"}[KIND]
EXAMPLE = json.load(open(f"{ROOT}/specs/long/{EX}"))
FORMAT = {"explain": "ROTATION EXPLAINS (Wednesday): 8:30-9 min, ONE company or filing, TLDR-Business style: doc-zoom highlights, stepped bar charts with source footer, keyword/split cards, tile grids, icon flows, exec lower third. Question/trouble title.",
          "long": "WEEKEND DEEP DIVE (Saturday): 8-10 min, v9 look: open_place dateline, cold open 75-100 s with 3+ voices, title_card, 4 chapters with agenda, a map/flow/timeline device in ch2, re-hook at ~60 %, closer + end card."}[KIND]
OUT = f"{ROOT}/specs/{'test' if TEST else 'long'}"; os.makedirs(OUT, exist_ok=True)


def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def rss(url):
    try:
        root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
        return [{"title": (i.findtext("title") or "").strip(), "link": (i.findtext("link") or "").strip(),
                 "desc": re.sub("<[^>]+>", "", i.findtext("description") or "")[:240]} for i in root.iter("item")]
    except Exception as e: print("rss fail", url[:80], e); return []


def research():
    items = []
    for f in ["https://www.cnbc.com/id/10001147/device/rss/rss.html", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
              "https://www.livemint.com/rss/companies", "https://feeds.bbci.co.uk/news/business/rss.xml", "https://www.cnbc.com/id/19854910/device/rss/rss.html"]:
        items += rss(f)
    pub = open(f"{ROOT}/state/published_titles.txt").read() if os.path.exists(f"{ROOT}/state/published_titles.txt") else ""
    menu = "\n".join(f"{i}. {x['title']} | {x['desc']}" for i, x in enumerate(items[:90]))
    pick = extract_json(chat("You are the editor of Rotation, a business YouTube channel. Lanes: Big Tech/AI money; oil/energy/shipping; Indian companies/economy. Reply JSON only.",
        f"Format: {FORMAT}\nAlready published (avoid repeats):\n{pub[-3000:]}\n\nPick ONE story for this format with hard numbers and a lasting question. STORIES:\n{menu}\n\n"
        "Reply {\"i\": index, \"topic\": \"...\", \"search\": \"3-6 word news search query\"}", 400))
    main = items[int(pick["i"])]; links = [main["link"]]
    for it in rss("https://www.bing.com/news/search?format=rss&q=" + urllib.parse.quote(pick["search"])):
        if it["link"] not in links: links.append(it["link"])
    docs = []
    for u in links[:8]:
        try:
            t = page_text(u, 12000)
            if len(t) > 1500: docs.append(f"SOURCE {len(docs)+1}: {u}\n{t}")
        except Exception as e: print("fetch fail", u[:80], e)
        if len(docs) >= 5: break
    if len(docs) < 2: raise SystemExit("not enough sources fetched for a long video")
    return pick["topic"], "\n\n".join(docs)


def check(scenes, facts):
    txt = json.dumps(scenes, ensure_ascii=False)
    spoken = " ".join(s.get("text", "") for s in scenes)
    return unverified_numbers(spoken + " " + txt.replace('"dur"', ""), facts)


def draft(topic, facts):
    head = {k: v for k, v in EXAMPLE.items() if k != "scenes"}
    sample = EXAMPLE["scenes"][:14]
    sys_ = (f"You write JSON specs for Rotation (@RotationNews) videos. {FORMAT}\nRules: use ONLY facts, numbers, names, dates and quotes from the SOURCES; "
            "every jargon term gets a one-line plain explanation; one real opposing view; the title's twist is the first spoken sentence; ~170 words per minute; "
            "quotes only verbatim from the sources; never invent. Clip ids only from the catalog. Reply JSON only.")
    cat, ids = clip_catalog(re.findall(r"[a-z]+", facts.lower()[:20000]), n=140)
    outline = extract_json(chat(sys_, f"TOPIC: {topic}\nSOURCES:\n{facts[:30000]}\n\nWrite the outline: {{\"title\": search-worded question title <= 70 chars, "
        "\"chapters\": [{\"name\", \"beats\": [5-10 one-line beats with the numbers they use], \"seconds\"}] (4-5 chapters, total 500-560 s), "
        "\"sources\": [\"Outlet, title, date: url\", ...]}", 3000))
    scenes = []
    for ci, ch in enumerate(outline["chapters"]):
        fb = ""
        for attempt in range(3):
            part = extract_json(chat(sys_, f"TOPIC: {topic}\nTITLE: {outline['title']}\nSOURCES:\n{facts[:30000]}\n\nCLIP CATALOG:\n{cat}\n\n"
                f"TOP-LEVEL KEYS OF THE EXAMPLE (already handled): {json.dumps(head, ensure_ascii=False)[:2500]}\n\nEXAMPLE SCENES (shape only):\n{json.dumps(sample, ensure_ascii=False)[:14000]}\n\n"
                f"Write ONLY the scenes for chapter {ci+1}/{len(outline['chapters'])}: {json.dumps(ch, ensure_ascii=False)}. "
                f"{'Start with the cold open.' if ci == 0 else 'Continue from the previous chapter, which ended: ' + (scenes[-1].get('text', '') if scenes else '')} "
                "Reply {\"scenes\": [...]} in exactly the example's scene shape." + fb, 4000))
            sc = part.get("scenes", []); bad = check(sc, facts)
            for s in sc:
                for key in ("shots", "clip"):
                    if key in s:
                        v = s[key] if isinstance(s[key], list) else [s[key]]
                        s[key] = [x for x in v if x.split("@")[0] in ids] or v[:0]
                        if not s[key]: s.pop(key)
            if not bad: break
            fb = f"\nYOUR LAST DRAFT USED NUMBERS NOT IN THE SOURCES: {bad}. Remove or correct them."
            print("chapter", ci + 1, "check failed", bad, flush=True)
        else: raise SystemExit(f"chapter {ci+1} failed the fact check")
        scenes += sc
    spec = dict(head); spec.update(title=outline["title"], sources=outline.get("sources", []), scenes=scenes)
    spec.pop("music_tracks", None); spec.pop("endcard_bg", None)
    return spec


if __name__ == "__main__":
    q = sorted(glob.glob(f"{ROOT}/specs/queue/{DAY}_{KIND}*.json"))
    if q:
        spec = json.load(open(q[0])); print("using queued spec", q[0])
    else:
        topic, facts = research(); spec = draft(topic, facts)
    name = f"{DAY}_{'explain_' if KIND == 'explain' else ''}{slug(spec.get('title', KIND))}"
    spec["output"] = f"{ROOT}/out/{name}.mp4"
    p = f"{OUT}/spec_{name}.json"; json.dump(spec, open(p, "w"), indent=1, ensure_ascii=False)
    print("SPEC", p)
    if os.environ.get("GITHUB_OUTPUT"): log(os.environ["GITHUB_OUTPUT"], f"spec={p}\nname={name}")
