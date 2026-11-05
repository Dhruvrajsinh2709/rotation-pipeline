"""Shared helpers for the Rotation GitHub pipeline: NVIDIA chat calls, JSON extraction, number checks, page text."""
import json, os, re, time, urllib.request, html as _html

ROOT = "/workspace/work/yt"   # the workflow symlinks the repo checkout here so the renderers' paths work unchanged
NV_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELS = [m for m in os.environ.get("NVIDIA_MODEL", "").split(",") if m] + [
    "mistralai/mistral-large-2-instruct", "nvidia/llama-3.1-nemotron-70b-instruct", "deepseek-ai/deepseek-v4.1-flash",
    "moonshotai/kimi-k2.6", "nvidia/nemotron-3-super-120b-a12b", "mistralai/mistral-large"]  # updated 2026-11-05: llama-3.3/qwen2.5/mixtral retired (410/404)
UA = {"User-Agent": "Mozilla/5.0 (RotationPipeline; +https://youtube.com/@RotationNews)"}


_PROBED = None
PREFER = ["nemotron-3-super", "deepseek-v", "kimi", "mistral-large", "nemotron-3-ultra", "llama-3.1-nemotron-70b", "gpt-oss-120b", "qwen3", "llama-4", "gemma-4", "gpt-oss-20b", "nemotron-3.5-lightning", "instruct"]
SKIP = ("embed", "guard", "safety", "vision", "-vl", "coder", "codestral", "codellama", "parse", "reward", "retriever", "translate", "diffusion", "omni", "chatqa")


def _probe(key):
    """Ask NVIDIA which chat models this key can really use today (models get retired often)."""
    global _PROBED
    if _PROBED is not None: return _PROBED
    try:
        with urllib.request.urlopen(urllib.request.Request("https://integrate.api.nvidia.com/v1/models", headers={"Authorization": f"Bearer {key}"}), timeout=30) as r:
            ids = [d["id"] for d in json.loads(r.read())["data"]]
    except Exception as e:
        print("NVIDIA model list failed:", type(e).__name__, flush=True); ids = []
    ids = [i for i in ids if not any(k in i.lower() for k in SKIP)]
    ids.sort(key=lambda i: next((n for n, k in enumerate(PREFER) if k in i.lower()), 99))
    ok = []
    for m in [x for x in MODELS[:1] if x] + ids[:40]:
        body = json.dumps({"model": m, "messages": [{"role": "user", "content": "Reply with the word OK."}], "max_tokens": 16}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(NV_URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}), timeout=25) as r:
                if r.status == 200: ok.append(m); print("NVIDIA usable:", m, flush=True)
        except Exception as e:
            print("NVIDIA skip", m, type(e).__name__, getattr(e, "code", ""), flush=True)
        if len(ok) >= 4: break
    _PROBED = ok or MODELS
    return _PROBED


def chat(system, user, max_tokens=6000, temperature=0.4):
    key = os.environ.get("NVIDIA_API_KEY")
    if not key: raise SystemExit("NVIDIA_API_KEY secret is missing: add it in repo Settings > Secrets and variables > Actions")
    last = None
    for model in _probe(key):
        for attempt in range(2):
            body = json.dumps({"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                               "max_tokens": max_tokens, "temperature": temperature}).encode()
            req = urllib.request.Request(NV_URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=420) as r:
                    out = json.loads(r.read())["choices"][0]["message"].get("content") or ""
                    if not out.strip(): raise ValueError("empty content")
                    print(f"NVIDIA model {model} ok ({len(out)} chars)", flush=True); return out
            except Exception as e:   # never print headers (the key lives there)
                last = f"{model}: {type(e).__name__} {str(e)[:200]}"; print("NVIDIA retry", last, flush=True)
                if getattr(e, "code", None) in (401, 403, 404, 410) or isinstance(e, TimeoutError): break
                time.sleep(8 * (attempt + 1))
    raise SystemExit(f"NVIDIA API failed: {last}")


def extract_json(txt):
    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S)
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", txt, re.S)
    s = m.group(1) if m else txt[txt.find("{"): txt.rfind("}") + 1]
    return json.loads(s)


NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
WORDNUM = {"one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10"}

def nums(text):
    return {n.replace(",", "").rstrip(".") for n in NUM.findall(text or "")}


def unverified_numbers(draft_text, source_text):
    """Every number in the draft must appear in the source text (years and 1-10 counts allowed)."""
    src = nums(source_text) | {n.replace(".0", "") for n in nums(source_text)}
    bad = []
    for n in nums(draft_text):
        if n in src or n.replace(".0", "") in src: continue
        if len(n) == 4 and n.startswith("20"): continue          # years
        if n.isdigit() and int(n) <= 10: continue                # small counts ("three numbers")
        bad.append(n)
    return sorted(set(bad))


def page_text(url, limit=20000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r: raw = r.read().decode("utf-8", "ignore")
    raw = re.sub(r"(?is)<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>", " ", raw)
    t = _html.unescape(re.sub(r"<[^>]+>", " ", raw)); t = re.sub(r"\s+", " ", t)
    return t[:limit]


def spec_text(spec):
    """All spoken/visible text of a spec, flattened (used as the fact source for funnel Shorts)."""
    out = []
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("output", "clip", "shots", "file"): continue
                walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
        elif isinstance(x, str): out.append(x)
        elif isinstance(x, (int, float)) and not isinstance(x, bool): out.append(str(x))
    walk(spec); return "\n".join(out)


def clip_catalog(words, n=90, vertical_ok=True, focus=()):
    """Short catalog of library clips that match the topic words (id | title | tags) for the drafting prompt."""
    ix = json.load(open(f"{ROOT}/clips/index.json")); w = {x.lower() for x in words}
    sc = []
    for k, m in ix.items():
        if m.get("bad") or "restricted" in str(m.get("licence", "")).lower() or not m.get("url"): continue
        t = set(m.get("tags", [])) | set(" ".join(m.get("kw", [])).split()) | set(re.findall(r"[a-z]+", m.get("title", "").lower()))
        s = len(t & w) + (0.5 if m.get("h", 0) >= 2000 else 0) + 8 * len(t & {f.lower() for f in focus})   # named subject first
        if s > 0: sc.append((s, k, m))
    sc.sort(key=lambda x: -x[0])
    return "\n".join(f"{k} | {'[SUBJECT] ' if s >= 8 else ''}{m.get('title','')[:70]} | {','.join(m.get('tags', [])[:8])}" for s, k, m in sc[:n]), {k for _, k, _ in sc[:n]}


def log(path, line):
    with open(path, "a") as fh: fh.write(line.rstrip() + "\n")
