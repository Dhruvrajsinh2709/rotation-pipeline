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
FORMAT = {"explain": "ROTATION EXPLAINS (Wednesday, STUDY 13): 6:30-8:30 min (~1,100-1,400 words), cold open 20-35 s with the twist first and payoff preview by 0:15, no question card, no agenda card, each chapter ends on an open-loop question, ONE company or filing, TLDR-Business style: doc-zoom highlights, stepped bar charts with source footer, keyword/split cards, tile grids, icon flows, exec lower third. Question/trouble title.",
          "long": "WEEKEND DEEP DIVE (Saturday, STUDY 13): 6:30-8:30 min total (~1,100-1,400 words). Series WHO PAYS? (title ends ' | Rotation: Who Pays?'): who really pays for one big business story, followed through the chain to the end payer. Title 8-14 words, starts Why, names the company/event/year, no puns or colons, number NOT in title. open_place dateline, cold open 20-35 s whose FIRST sentence is the twist and which previews the payoff by 0:15, logo sting, title_card, then chapter 1 at once: NO question card, NO agenda card. 3-4 chapters, each ends on an open-loop question the next answers; a map/flow/timeline device in ch2; re-hook at ~60 %; closer + end card."}[KIND]
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


SKIP_KEYS = {"clip", "shots", "dur", "nat", "music", "sfx", "tags", "id", "t", "start", "end", "mood", "fps", "zoom", "pos", "x", "y", "w", "h", "size"}


def _visible(x):
    """Strings a viewer sees or hears (narration, cards, charts, quotes); clip ids, timings and layout numbers excluded."""
    if isinstance(x, dict): return " ".join(_visible(v) for k, v in x.items() if k not in SKIP_KEYS)
    if isinstance(x, list): return " ".join(_visible(v) for v in x)
    if isinstance(x, (int, float)): return ""          # bare numbers in JSON are durations/positions; chart values are checked via strings below
    return str(x) if isinstance(x, str) else ""


def _clean(t):
    t = re.sub(r"#[0-9A-Fa-f]{3,8}\b|\b[a-z]+_[\w@.-]+", " ", t)   # hex colours, clip ids
    # spoken money "4 dollars and 44 cents" -> "4.44" so it matches the source's $4.44 (was wrongly scrubbed 2026-11-07)
    return re.sub(r"(\d+) (?:dollars?|rupees?|euros?|pounds?) and (\d{1,2}) (?:cents?|paise|pence)", lambda m: f"{m.group(1)}.{int(m.group(2)):02d}", t)


def scrub(scenes, bad):
    """Last resort: delete narration sentences / graphic keys that carry an unsourced number, keep the rest of the chapter."""
    pat = re.compile(r"(?<![\d.,])(?:" + "|".join(re.escape(b) for b in bad) + r")(?![\d])")
    def hit(x): return bool(pat.search(_clean(_visible(x).replace(",", ""))))
    out = []
    for sc in scenes:
        for k in [k for k in sc if k not in SKIP_KEYS and k != "text"]:
            if hit(sc[k]): print("scrub key", k, str(sc[k])[:120], flush=True); sc.pop(k)
        if "text" in sc:
            sents = re.split(r"(?<=[.!?])\s+", sc["text"]); keep = [x for x in sents if not hit(x)]
            if len(keep) < len(sents): print("scrub text", [x for x in sents if hit(x)], flush=True)
            sc["text"] = " ".join(keep)
        if sc.get("text") or any(k in sc for k in ("card", "chart", "quote", "title")): out.append(sc)
    return out


def check(scenes, facts):
    txt = _clean(_visible(scenes))   # drop leftover ids like mk_4008, wiki_123@2
    vals = " ".join(str(v) for s in scenes for k in ("chart", "bars", "values", "data") if k in s for v in (s[k] if isinstance(s[k], list) else [s[k]]))
    return unverified_numbers(txt + " " + vals, facts)


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
            for x in sc:
                t = _clean(_visible(x))
                for b in bad:
                    i = t.find(b)
                    if i >= 0: print("   ", b, "in:", t[max(0, i-80):i+40].replace("\n", " "), flush=True)
        else:
            sc = scrub(sc, bad); bad2 = check(sc, facts)
            if bad2 or len(sc) < 3: raise SystemExit(f"chapter {ci+1} failed the fact check {bad2}")
            print("chapter", ci + 1, "scrubbed to pass", flush=True)
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
