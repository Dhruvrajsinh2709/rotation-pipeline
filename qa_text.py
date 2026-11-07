#!/usr/bin/env python3
"""Study 13 (2026-11-07) text QA for any Rotation render.
1) NARRATION: transcribe the final audio (whisper base.en, plain, no prompt) and compare to the spec's script.
   Hard fail if word match < 85 % or any script number is missing from what is heard.
2) CAPTIONS (Shorts / videos with burned captions): OCR the caption band every 0.5 s with tesseract and check
   (a) every caption read appears in the script, (b) no caption text stays unchanged for more than 3.5 s while the
   narration is speaking (the frozen-caption bug of 2026-11-06).
Usage: PYTHONPATH=/workspace/work/pylib python3 qa_text.py <render.mp4> <spec.json> [--no-captions]
Writes qa/<name>/text_report.json; prints HARD FAIL lines; exit code 2 on hard fail."""
import json, os, re, subprocess, sys, difflib
import numpy as np
sys.path.insert(0, "/workspace/work/yt")

NUMW = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
def norm_words(t):
    t = t.lower().replace("%", " percent").replace("₹", " rupees ").replace("$", " dollars ")
    t = re.sub(r"(\d),(\d)", r"\1\2", t)
    return [NUMW.get(w, w) for w in re.findall(r"[a-z]+|\d+(?:\.\d+)?", t)]

def script_text(spec):
    parts = []
    for k in ("open_place",):
        if isinstance(spec.get(k), dict) and spec[k].get("text"): parts.append(spec[k]["text"])
    for sc in spec.get("scenes", []):
        for k in ("text", "vo"):
            if isinstance(sc.get(k), str): parts.append(sc[k])
        if isinstance(sc.get("quote"), dict) and sc["quote"].get("text"): parts.append(sc["quote"]["text"])
    for k in ("outro", "closer"):
        v = spec.get(k)
        if isinstance(v, dict) and v.get("text"): parts.append(v["text"])
        elif isinstance(v, str): parts.append(v)
    return " ".join(parts)

def transcribe(path):
    from wordtime import _model
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    segs, _ = _model().transcribe(a, beam_size=5, language="en", word_timestamps=True)
    words = [(w.start, w.end, w.word.strip()) for s in segs for w in (s.words or [])]
    return words

def ocr_band(path, fps=2, band=(1240, 1500)):
    tmp = "/tmp/qa_text_frames"; os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    y0, y1 = band
    subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},crop=1000:{y1-y0}:40:{y0},format=gray,lutyuv=y='if(gt(val,225),0,255)'",
                    f"{tmp}/f_%05d.png"], check=True)
    out = []
    for i, f in enumerate(sorted(os.listdir(tmp))):
        t = subprocess.run(["tesseract", os.path.join(tmp, f), "-", "--psm", "7", "-l", "eng"], capture_output=True, text=True).stdout.strip()
        out.append((i / fps, re.sub(r"\s+", " ", t)))
    return out

def main():
    path, specp = sys.argv[1], sys.argv[2]; caps = "--no-captions" not in sys.argv
    spec = json.load(open(specp)); name = os.path.splitext(os.path.basename(path))[0]
    qd = f"/workspace/work/yt/qa/{name}"; os.makedirs(qd, exist_ok=True)
    script = script_text(spec); sw = norm_words(script)
    heard = transcribe(path); hw = norm_words(" ".join(w[2] for w in heard))
    sm = difflib.SequenceMatcher(None, sw, hw, autojunk=False); match = sum(b.size for b in sm.get_matching_blocks()) / max(1, len(sw))
    nums = sorted(set(re.findall(r"\d+(?:\.\d+)?", " ".join(sw)))); hd = "".join(w for w in hw if w.isdigit() or w.replace(".", "").isdigit()).replace(".", "")
    missing = [n for n in nums if n not in hw and n.replace(".", "") not in hd]
    hard = []
    if match < 0.85: hard.append(f"narration matches the script only {match:.0%} (min 85%)")
    if missing: hard.append(f"numbers in the script not heard in the audio: {missing}")
    rep = {"narration_match": round(match, 3), "numbers_missing": missing}
    wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
    if caps and len(wh) == 2 and int(wh[1]) > int(wh[0]):   # burned captions only on vertical Shorts
        frames = ocr_band(path)
        sset = set(sw); bad = []; frozen = []
        run_t, run_txt = 0.0, None
        speech = [(a, b) for a, b, _ in heard]
        def speaking(t0, t1): return sum(max(0, min(b, t1) - max(a, t0)) for a, b in speech) > 0.75 * (t1 - t0)
        for t, txt in frames:
            ws = [w for w in norm_words(txt) if len(w) > 2]
            real = [w for w in ws if len(w) >= 4 or w.isdigit()]
            if len(real) >= 2 and sum(w in sset for w in real) / len(real) < 0.5: bad.append((t, txt))
            key = " ".join(ws)
            if key != run_txt:
                if run_txt and t - run_t > 3.5 and speaking(run_t, t): frozen.append((round(run_t, 1), round(t - run_t, 1), run_txt))
                run_t, run_txt = t, key
        rep.update({"caption_frames": len(frames), "caption_not_in_script": bad[:10], "caption_frozen": frozen})
        if len(bad) > max(4, 0.3 * len(frames)): hard.append(f"{len(bad)} caption frames don't match the script, e.g. {bad[:3]}")
        if frozen: hard.append(f"caption frozen while narration runs: {frozen}")
    rep["note"] = "caption OCR is rough on busy footage; mismatch only fails above 30% of frames. Read the listed frames on the QA sheets."
    rep["hard_fail"] = hard
    json.dump(rep, open(f"{qd}/text_report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))
    for h in hard: print("HARD FAIL", h)
    sys.exit(2 if hard else 0)

if __name__ == "__main__": main()
