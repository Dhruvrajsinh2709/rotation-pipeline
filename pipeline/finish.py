"""Package a finished render for upload: 1080p upload copy (<= 95 MB, +faststart), description, spec, QA sheets.
Writes dist/<name>/ : video.mp4, description.txt, spec.json, qa/ (sheets + report.json), info.json.
Usage: python pipeline/finish.py SPEC.json short|explain|long"""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__)); from common import ROOT

spec_p, kind = sys.argv[1], sys.argv[2]; spec = json.load(open(spec_p))
name = os.path.splitext(os.path.basename(spec["output"]))[0]; src = spec["output"]
D = f"{ROOT}/dist/{name}"; shutil.rmtree(D, ignore_errors=True); os.makedirs(D)


def probe(p):
    j = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", p]))
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return float(j["format"]["duration"]), int(v["width"]), int(v["height"]), os.path.getsize(p)


dur, w, h, size = probe(src); up = f"{D}/video.mp4"
if size <= 95e6 and max(w, h) <= 1920:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-c", "copy", "-movflags", "+faststart", up], check=True)
else:   # long-form 1440p master -> 1080p upload copy sized for ~90 MB (big files crash Studio)
    kbps = int(min(14000, 90e6 * 8 / dur / 1000 - 192)); vf = "scale=1920:1080:flags=lanczos" if w >= h else "scale=1080:1920:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-b:v", f"{kbps}k",
                    "-maxrate", f"{int(kbps*1.5)}k", "-bufsize", f"{kbps*2}k", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", up], check=True)

# QA sheets (Hark opens every sheet before upload)
qa = subprocess.run(["python3", f"{ROOT}/qa_frames.py", up, "--out", f"{D}/qa"] + (["--fps", "0.5"] if kind != "short" else []), capture_output=True, text=True)
print(qa.stdout[-3000:], qa.stderr[-1500:])
try:
    _hf = json.load(open(f"{D}/qa/report.json")).get("hard_fail") or []
except Exception: _hf = []
if _hf:   # 2026-11-06: a QA hard fail (long shots, text slates, loudness...) blocks the render from being shipped
    open(f"{D}/QA_FAILED.txt", "w").write("\n".join(_hf) + "\n"); print("QA HARD FAIL:", _hf)

# description: line 1 repeats the title's search words; sources; disclosures (title/Related video/links finished by Hark at upload)
ix = json.load(open(f"{ROOT}/clips/index.json")); used = set()
def walk(x):
    if isinstance(x, dict): [walk(v) for v in x.values()]
    elif isinstance(x, list): [walk(v) for v in x]
    elif isinstance(x, str) and x.split("@")[0] in ix: used.add(x.split("@")[0])
walk(spec)
credits = sorted({f"{ix[c].get('title','')[:60]} ({ix[c].get('source')}, {ix[c].get('licence','')[:60]})" for c in used
                  if ix[c].get("source") in ("wikimedia", "dvids", "nasa", "fed")})
desc = [spec.get("title", ""), "", "Sources:"] + [f"- {s}" for s in spec.get("sources", [])] + [""]
desc += ["Narration and quotes are read by AI voices; quotes are real and sourced.",
         "Footage: Mixkit and Coverr (free licences)" + ("; " + "; ".join(credits) if credits else "") + ". Charts: Rotation.",
         "This video is for information only and is not investment advice."]
open(f"{D}/description.txt", "w").write("\n".join(desc) + "\n")
shutil.copy(spec_p, f"{D}/spec.json")
d2, w2, h2, s2 = probe(up)
info = {"name": name, "kind": kind, "title": spec.get("title"), "duration_s": round(d2, 1), "res": f"{w2}x{h2}", "upload_mb": round(s2 / 1e6, 1),
        "funnel": spec.get("funnel"), "qa_exit": qa.returncode}
json.dump(info, open(f"{D}/info.json", "w"), indent=1); print("PACKAGE", json.dumps(info))
if os.environ.get("GITHUB_OUTPUT"):
    open(os.environ["GITHUB_OUTPUT"], "a").write(f"dist={D}\nname={name}\n")
