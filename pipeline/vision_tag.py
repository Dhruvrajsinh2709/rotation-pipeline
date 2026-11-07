"""Study 13 (2026-11-07): describe what every library clip ACTUALLY shows, with an NVIDIA vision model.
Input: vision/frames/<clip_id>.jpg (two frames side by side, 25% and 70% of the clip). Output: vision/vision.json
{clip_id: {"desc": one sentence, "tags": [...], "brands": [...], "text": bool, "still": bool, "model": m}}.
Resumable: skips ids already in vision.json; saves every 25 clips. Never prints the key."""
import base64, json, os, sys, time, urllib.request, glob
NV = "https://integrate.api.nvidia.com/v1/chat/completions"
# 2026-11-07: gemma-3-12b-it + phi-3-vision answered 404 on every call; nemotron returned content=null (reasoning model).
MODELS = ["meta/llama-3.2-90b-vision-instruct", "nvidia/nemotron-3.5-super-vl-120b-a12b"]
PROMPT = ("These are two frames (side by side) from one short stock video clip. Answer ONLY with JSON, no prose: "
          '{"desc": "<one literal sentence: what is shown, the kind of place, and any country clue>", '
          '"tags": ["<6 concrete nouns, e.g. oil tanker, refinery, airport, cash, petrol pump>"], '
          '"brands": ["<any company names, logos, airline liveries or shop signs you can read, else empty>"], '
          '"text": <true if large on-screen text, captions, slides or documents fill much of the frame>, '
          '"still": <true if the two frames look identical (a still photo)>}')
def call(key, model, b64):
    body = json.dumps({"model": model, "max_tokens": 300 if "llama" in model else 2000, "temperature": 0, "messages": [{"role": "user", "content": [
        {"type": "text", "text": PROMPT}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}]}]}).encode()
    req = urllib.request.Request(NV, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r: msg = json.loads(r.read())["choices"][0]["message"]
    out = msg.get("content") or msg.get("reasoning_content") or ""
    if "</think>" in out: out = out.split("</think>")[-1]
    s = out[out.find("{"): out.rfind("}") + 1]; return json.loads(s)
def main():
    key = os.environ["NVIDIA_API_KEY"]; path = "vision/vision.json"
    db = json.load(open(path)) if os.path.exists(path) else {}
    files = sorted(glob.glob("vision/frames/*.jpg")); todo = [f for f in files if os.path.basename(f)[:-4] not in db]
    limit = int(os.environ.get("VISION_LIMIT", "2000")); todo = todo[:limit]
    print(f"vision: {len(db)} done, {len(todo)} to do", flush=True)
    models = list(MODELS); n = 0; t_end = time.time() + float(os.environ.get("VISION_MINUTES", "300")) * 60
    for f in todo:
        if time.time() > t_end: break
        cid = os.path.basename(f)[:-4]; b64 = base64.b64encode(open(f, "rb").read()).decode()
        for m in list(models):
            try:
                r = call(key, m, b64); r["model"] = m; db[cid] = r; n += 1; break
            except Exception as e:
                code = getattr(e, "code", None); print("vision skip", cid, m, type(e).__name__, code, flush=True)
                if code in (401, 403, 404, 410): models.remove(m); models.append(m)
                if code == 429: time.sleep(20)
        if n and n % 25 == 0: json.dump(db, open(path, "w"), indent=0); print("vision saved", len(db), flush=True)
        time.sleep(1.2)
    json.dump(db, open(path, "w"), indent=0); print("vision done", len(db), "of", len(files), flush=True)
if __name__ == "__main__": main()
