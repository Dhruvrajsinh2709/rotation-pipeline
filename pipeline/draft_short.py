"""Draft today's Rotation Short spec with the NVIDIA API (FUNNEL 2x rules).
1. Newest long spec in specs/long/ with fewer than 2 funnel Shorts in state/funnel.json -> Short #1 (its most shocking
   number + twist) or #2 (a different angle: the Rotation calculation, who wins, or the dated catalyst).
   Facts come ONLY from that long video's verified spec; every number is checked against it.
2. Otherwise the spare slot: the day's biggest business/markets story from RSS, facts only from the fetched article.
Writes specs/shorts/<date>_<slug>.json and prints its path. --test writes to specs/test/ and leaves state alone.
Usage: python pipeline/draft_short.py [--test] [--long specs/long/X.json] [--n 1|2]"""
import json, os, re, sys, time, glob, urllib.request, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__)); from common import *

A = sys.argv[1:]; TEST = "--test" in A
STATE = f"{ROOT}/state/funnel.json"; os.makedirs(f"{ROOT}/state", exist_ok=True)
funnel = json.load(open(STATE)) if os.path.exists(STATE) else {}
EXAMPLE = json.load(open(f"{ROOT}/specs/shorts/spec_2026-11-04.json"))
EXAMPLE.pop("output", None)
_s1 = EXAMPLE["scenes"][0]; _s1.pop("hook_card", None); _s1.pop("stat", None)
_s1["clash"] = [["Fares", "+34%", "win"], ["IndiGo loss", "Rs 1,879 cr", "lose"]]   # FRAME 1 CLASH shape for the model

RULES = """You write the JSON spec for one YouTube Short on "Rotation" (@RotationNews), a faceless CNBC/WSJ-style business channel.
Hard rules:
- Output ONE JSON object only, same keys and shape as the example. No commentary.
- 32-42 seconds when read at ~170 words per minute: 75-100 words of narration in total across all scene "text" plus "outro.text".
- 6-8 scenes. Scene 1: the subject on screen + the clash said in the first 8 spoken words. Give scene 1 "clash": [[label, value, "win"], [label, value, "lose"]]:
  two numbers from the FACTS that fight each other, each label 1-2 words, value short (e.g. [["Fares","+34%","win"],["IndiGo loss","Rs 1,879 cr","lose"]]). Green = winner/positive, red = loser/negative. No "stat" on scene 1.
- MATH: never combine numbers yourself. Say "X minus Y" or "losing Z on each" ONLY if that exact result is in the FACTS. Two numbers in one sentence must measure the same thing (same unit, same period, same basis).
- FOOTAGE: pick the clip whose TITLE literally shows the subject (the named company's planes/stores/logo, the named country/city). Never show another company's brand (e.g. a FedEx plane for IndiGo). For an Indian story never show US dollar bills unless that line is about dollars; prefer rupee/India clips. A generic clip only when no literal one fits.
- Number + twist by 12 s, why-it-matters by 30 s. Mark the turn scene with "turn": true. Mixed sentence length. Plain words: explain any jargon in one line.
- At most 2 graphics in total ("stat" or "card" of type compare). Cards: {"type":"compare","title","items":[[label,value],[label,value]],"source"}.
- Every scene: "clip": [ONE id from the clip catalog], "tags": 2-3 concrete nouns, "nat": one of [airport, city, street, office, industrial, traffic, market, crowd, port, sea, nature, room], "blur": false (footage always fills the full 9:16 screen).
- "outro": {"text": an open question built ONLY from the FACTS (or a dated next event, but ONLY if that exact event and date are written in the FACTS), then a loop line that leads back to the first sentence, "tags": [...], "nat": [...]}. No "follow"/"subscribe" call to action.
- OTHER BRANDS: never pick a clip that could show a different company (another airline's plane, a rival's shop, a foreign courier). For planes, stores, logos or vehicles use ONLY [SUBJECT] clips; generic clips only for neutral things (money, people, offices, fuel, city).
- NO PREDICTIONS: never say what will happen next (next quarter, next results date, a government decision, a fund) unless the FACTS say it word for word. When unsure, leave it out.
- "music": {"mood": one of doc|tense|light|ambient|pulse, "mood2": another}. "rate": "+24%". "tags": 3 topic nouns.
- "title": a search-worded question/claim people type (e.g. "Why X is losing money even after Y"), <= 70 characters, not the same pattern as the long video's title.
- "sources": the source list, copied from the facts given.
- Use ONLY numbers, names and dates that appear in the FACTS. Never invent a figure, quote or date. Round only as the facts do.
- Optional "quote": {"text","who","role","source"} ONLY if that exact quote text appears in the FACTS.
"""


def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def pick_long():
    if "--long" in A: return A[A.index("--long") + 1]
    longs = sorted(glob.glob(f"{ROOT}/specs/long/spec_20*.json"), reverse=True)
    for p in longs:
        if funnel.get(os.path.basename(p), 0) < 2: return p
    return None


def draft(facts, angle, words, extra="", focus=()):
    cat, ids = clip_catalog(words, focus=focus)
    user = (f"ANGLE: {angle}\n\nFACTS (the only allowed facts):\n{facts[:24000]}\n\n{extra}\nCLIP CATALOG (id | title | tags), use only these ids:\n{cat}\n\n"
            f"EXAMPLE SPEC (shape and tone only, not its facts):\n{json.dumps(EXAMPLE, ensure_ascii=False)}")
    fb = ""
    for attempt in range(7):
        try:
            spec = extract_json(chat(RULES, user + fb))
            if not isinstance(spec, dict) or not spec.get("scenes"): raise ValueError("no scenes")
        except Exception as e:   # truncated or broken JSON: just ask again
            print("draft JSON unusable:", type(e).__name__, str(e)[:120], flush=True); continue
        spoken = " ".join(sc.get("text", "") for sc in spec.get("scenes", [])) + " " + (spec.get("outro") or {}).get("text", "")
        graphics = json.dumps([[sc.get("stat"), sc.get("card"), sc.get("hook_card"), sc.get("clash")] for sc in spec.get("scenes", [])], ensure_ascii=False)
        bad = unverified_numbers(spoken + " " + graphics, facts)
        nw = len(spoken.split()); errs = []
        if bad: errs.append(f"these numbers are not in the FACTS: {bad}. Use only numbers from the FACTS.")
        if not 70 <= nw <= 104: errs.append(f"narration is {nw} words; it must be 75-100.")
        for sc in spec.get("scenes", []):
            cl = sc.get("clip") or []
            if isinstance(cl, str): cl = sc["clip"] = [cl]
            if not cl or any(c not in ids for c in cl): errs.append(f"scene clip {cl} is not from the catalog.")
            q = sc.get("quote")
            if q and q.get("text", "") not in facts: sc.pop("quote"); print("dropped a quote not found verbatim in facts")
            sc.pop("actuality", None)
        india = "₹" in facts or " crore" in facts
        for sc in spec.get("scenes", []):   # foreign banknotes are banned for India stories unless the line is about dollars
            if india and "dollar" not in sc.get("text", "").lower():
                for c in sc.get("clip") or []:
                    line = next((l for l in cat.splitlines() if l.startswith(c + " |")), "").lower()
                    if "dollar" in line or "euro" in line: errs.append(f"clip {c} shows dollar/euro notes in an India story; pick a rupee, India or neutral clip for: {sc.get('text','')[:60]}")
        sc1 = (spec.get("scenes") or [{}])[0]
        cl = sc1.get("clash")
        if not (isinstance(cl, list) and len(cl) == 2 and all(isinstance(x, list) and len(x) >= 2 for x in cl)):
            errs.append('scene 1 needs "clash": [[label, value, "win"], [label, value, "lose"]] with two numbers from the FACTS.')
        else: sc1.pop("stat", None); sc1.pop("hook_card", None)
        if not errs:
            aud = audit(spec, facts)
            if aud: errs.append("a fact audit found these problems (DELETE those claims or replace them with a sentence built only from the FACTS): " + "; ".join(aud))
        if not errs:
            o = spec.setdefault("outro", {})
            subj_all = [l.split(" | ")[0] for l in cat.splitlines() if "[SUBJECT]" in l]
            oc = o.get("clip") or []
            if isinstance(oc, str): oc = [oc]
            if not oc or (subj_all and not all(c in subj_all for c in oc)):   # outro must show the subject (11-06 test: champagne glasses); pin an unused subject clip
                used = {c for sc in spec["scenes"] for c in (sc.get("clip") or [])}
                subj = [c for c in subj_all if c not in used] or subj_all
                if subj: o["clip"] = [subj[-1] if len(subj) > 1 else subj[0]]; print("outro pinned to subject clip", o["clip"], flush=True)
            if focus: spec["subject"] = list(focus)   # renderer keeps scene-1/outro replacements on clips of the subject
            return spec
        print("draft check failed:", errs, flush=True)
        fb = ("\n\nYOUR LAST DRAFT (edit THIS draft; keep every line that passed, change only what the problems name):\n" + json.dumps(spec, ensure_ascii=False) +
              "\n\nIT FAILED THESE CHECKS, fix them and return the full JSON again:\n- " + "\n- ".join(errs))
    raise SystemExit("could not produce a Short spec that passes the fact checks")


def audit(spec, facts):
    """Second NVIDIA pass: does any line do math or combine numbers the FACTS do not support, or misstate a fact?"""
    lines = [sc.get("text", "") for sc in spec.get("scenes", [])] + [(spec.get("outro") or {}).get("text", "")]
    lines += [json.dumps(sc.get(k), ensure_ascii=False) for sc in spec.get("scenes", []) for k in ("clash", "stat", "card") if sc.get(k)]
    try:
        r = extract_json(chat("You are a strict fact-checker for a business news channel. Reply JSON only.",
            "FACTS:\n" + facts[:24000] + "\n\nSCRIPT LINES:\n" + "\n".join(f"- {l}" for l in lines) +
            "\n\nList every line that (a) states a number, name or date not supported by the FACTS, (b) does arithmetic that is wrong "
            "(e.g. spends 9,520, earns 8,500, loses 680) or that the FACTS do not state, or (c) puts two numbers side by side that measure "
            "different things. Reply {\"problems\": [\"short description\", ...]} and an empty list if all lines are fine.", 6000, 0.1))
        probs = [str(x) for x in r.get("problems", []) if str(x).strip()][:5]
        print("audit:", probs or "clean", flush=True); return probs
    except (Exception, SystemExit) as e:   # chat() raises SystemExit when every model fails; never kill the run over the audit
        print("audit skipped:", type(e).__name__, flush=True); return []


def rss_story():
    feeds = ["https://www.cnbc.com/id/10001147/device/rss/rss.html", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
             "https://www.livemint.com/rss/companies", "https://feeds.bbci.co.uk/news/business/rss.xml"]
    items = []
    for f in feeds:
        try:
            req = urllib.request.Request(f, headers=UA)
            root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
            for it in root.iter("item"):
                items.append({"title": (it.findtext("title") or "").strip(), "link": (it.findtext("link") or "").strip(), "desc": re.sub("<[^>]+>", "", it.findtext("description") or "")[:200]})
        except Exception as e: print("rss fail", f, e)
    pub = open(f"{ROOT}/state/published_titles.txt").read() if os.path.exists(f"{ROOT}/state/published_titles.txt") else ""
    menu = "\n".join(f"{i}. {x['title']} | {x['desc']}" for i, x in enumerate(items[:80]))
    pick = extract_json(chat("You are the news editor of a business YouTube channel. Lanes: Big Tech/AI money; oil/energy/shipping; Indian companies/economy. Reply JSON only.",
        f"Pick the single biggest business/markets story with hard numbers and a clear 'How/Why X...' angle, not already covered:\n{pub[-3000:]}\n\nSTORIES:\n{menu}\n\nReply {{\"i\": index, \"angle\": \"...\"}}", 300))
    it = items[int(pick["i"])]; txt = page_text(it["link"])
    return it, pick.get("angle", it["title"]), f"SOURCE: {it['title']} ({it['link']})\n{txt}"


if __name__ == "__main__":
    day = time.strftime("%Y-%m-%d")
    lp = pick_long()
    if lp:
        ls = json.load(open(lp)); n = int(A[A.index("--n") + 1]) if "--n" in A else funnel.get(os.path.basename(lp), 0) + 1
        angle = (f"Funnel Short #{n} for the long video \"{ls.get('title')}\". " +
                 ("Use its single most shocking number + twist (its strongest minute)." if n == 1 else
                  "Use a DIFFERENT angle from Short #1: the Rotation calculation, the 'who wins' turn, or the dated catalyst."))
        facts = f"LONG VIDEO TITLE: {ls.get('title')}\nSOURCES: {json.dumps(ls.get('sources', []))}\n" + spec_text(ls)
        spec = draft(facts, angle, re.findall(r"[a-z]+", spec_text(ls).lower()),
                     focus=[w.lower() for w in re.findall(r"\b[A-Z][A-Za-z]{2,}\b", ls.get("title", "")) if w not in ("Why", "Your", "The", "So", "How", "What")])
        spec["funnel"] = {"long_spec": os.path.basename(lp), "n": n, "long_title": ls.get("title")}
        if not spec.get("sources"): spec["sources"] = ls.get("sources", [])
    else:
        it, angle, facts = rss_story()
        spec = draft(facts, angle, re.findall(r"[a-z]+", facts.lower()[:6000]))
        spec["funnel"] = None; spec.setdefault("sources", [it["link"]])
    name = f"{day}_{slug(spec.get('title', 'short'))}"
    spec["output"] = f"{ROOT}/out/{name}.mp4"; spec["log_used"] = not TEST
    d = f"{ROOT}/specs/{'test' if TEST else 'shorts'}"; os.makedirs(d, exist_ok=True)
    p = f"{d}/{name}.json"; json.dump(spec, open(p, "w"), indent=1, ensure_ascii=False)
    if lp and not TEST:
        funnel[os.path.basename(lp)] = funnel.get(os.path.basename(lp), 0) + 1; json.dump(funnel, open(STATE, "w"), indent=1)
    print("SPEC", p)
    if os.environ.get("GITHUB_OUTPUT"): log(os.environ["GITHUB_OUTPUT"], f"spec={p}\nname={name}")
