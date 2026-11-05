"""SFX add-on (user "good", 2026-11-03): extra choices for the existing sfxlib families. SOUND v10 levels are unchanged
(sfxlib level-matches every file to its family target), so these are new picks, not a new mix.
  openverse : CC0 / public-domain-mark sounds only from the Openverse audio API (no key). Creator + landing URL kept for credits.
  earshot   : sounds made in code from the earshot bank (MIT, github.com/Leonxlnx/earshot), installed WITHOUT models/torch.
Both write into sfx2/ and sfx2/index.json (source, licence, creator, page). Run once; the repo ships the results.
Usage: python pipeline/sfx_addon.py openverse|earshot|both"""
import json, os, subprocess, sys, time, urllib.request, urllib.parse
import numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from common import ROOT, UA
sys.path.insert(0, ROOT); import sfxlib
if os.environ.get("SFX_DIR"): sfxlib.D = os.environ["SFX_DIR"]; sfxlib.IDX = f"{sfxlib.D}/index.json"

OV = {  # family -> openverse queries (kept: up to 4 per family, <= family max duration)
    "whoosh": ["whoosh", "swish", "swoosh"], "boom": ["impact hit", "cinematic hit"], "riser": ["riser"], "click": ["click"],
    "paper": ["paper"], "coins": ["coins", "cash register"], "ping": ["ping", "ding"]}
ES = {  # family -> earshot bank ids (code-made, audited clean per the bank)
    "whoosh": ["whoosh_fast/crisp", "whoosh_fast/tight", "swish/soft", "swish/bright", "whoosh_big/thump"],
    "boom": ["cut_hit/punch", "cut_hit/sub", "whoosh_big/thump_deep"], "riser": ["riser/build", "riser/dark", "reverse_swell/short"],
    "click": ["click/soft", "click/thock", "knock/wood"], "pop": ["ui_pop/soft", "ui_pop/step", "ui_pop/boop", "drip/plink"],
    "tick": ["knock/snap", "knock/plastic"], "ping": ["notify/mid_tine", "notify/mid_wood"], "shutter": ["shutter/snap", "shutter/dslr"],
    "glitch": ["glitch/mid", "glitch/burst"]}


def add(ix, sid, fam, src_file, title, licence, page, source, creator=""):
    mp3 = f"{sfxlib.D}/{sid}.mp3"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src_file, "-af", "silenceremove=start_periods=1:start_threshold=-50dB",
                        "-ac", "2", "-ar", str(sfxlib.SR), "-b:a", "192k", mp3])
    if r.returncode or not os.path.exists(mp3): return False
    a = sfxlib.decode(mp3)
    if len(a) < sfxlib.SR * 0.05: os.remove(mp3); return False
    env = np.abs(a).max(1); pk = int(np.argmax(env))
    ix[sid] = dict(file=f"{sid}.mp3", family=fam, title=title, dur=round(len(a) / sfxlib.SR, 2), peak=round(pk / sfxlib.SR, 3),
                   peak_db=round(float(20 * np.log10(env.max() + 1e-9)), 1), licence=licence, page=page, source=source, creator=creator,
                   fetched=time.strftime("%Y-%m-%d"))
    print(" +", fam, sid, title[:50], ix[sid]["dur"], flush=True); return True


def openverse():
    ix = sfxlib.load(); n = 0
    for fam, qs in OV.items():
        maxd = sfxlib.FAM[fam][1]; have = 0
        for q in qs:
            if have >= 4: break
            u = "https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode({"q": q, "license": "cc0,pdm", "page_size": 20}); time.sleep(4)
            try: res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read())["results"]
            except Exception as e: print("openverse fail", q, e); continue
            for r in res:
                if have >= 4: break
                lic = (r.get("license") or "").lower(); d = (r.get("duration") or 99999) / 1000; sid = f"ov_{r['id'][:8]}"
                if lic not in ("cc0", "pdm") or d > maxd or d < 0.1 or sid in ix: continue
                tmp = f"/tmp/{sid}.{r.get('filetype') or 'mp3'}"
                if subprocess.run(["curl", "-s", "-L", "--max-time", "60", "-A", UA["User-Agent"], "-o", tmp, r["url"]]).returncode: continue
                licence = "CC0 1.0 (public domain dedication)" if lic == "cc0" else "Public Domain Mark"
                if add(ix, sid, fam, tmp, r.get("title", ""), licence, r.get("foreign_landing_url", ""), "openverse", r.get("creator") or ""): have += 1; n += 1
                os.remove(tmp)
    sfxlib.save(ix); print("openverse added", n)


def earshot():
    ix = sfxlib.load(); n = 0
    for fam, ids in ES.items():
        for bid in ids:
            sid = "es_" + bid.replace("/", "_")
            if sid in ix: continue
            wav = f"/tmp/{sid}.wav"
            r = subprocess.run([sys.executable, "-m", "earshot", "sfx", "render", bid, "-o", wav], capture_output=True, text=True)
            if r.returncode: print("earshot fail", bid, r.stderr[-200:]); continue
            if add(ix, sid, fam, wav, f"earshot {bid}", "MIT (earshot, sound made in code)", "https://github.com/Leonxlnx/earshot", "earshot"): n += 1
            os.remove(wav)
    sfxlib.save(ix); print("earshot added", n)


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "both"
    if m in ("openverse", "both"): openverse()
    if m in ("earshot", "both"): earshot()
