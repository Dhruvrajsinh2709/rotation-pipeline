"""Word timings for edge-tts voices that return no WordBoundary (e.g. en-US-AndrewMultilingualNeural,
the narrator since 2026-11-01: user chose it as "voice 1").
synth(text, voice, rate, path) -> [(start, end, word)] in seconds, words = script tokens stripped of punctuation.
Audio via SentenceBoundary, timings via faster-whisper word timestamps aligned to the script with difflib.
"""
import asyncio, re, subprocess, difflib
import numpy as np
import edge_tts

_M = None
def _model():
    global _M
    if _M is None:
        from faster_whisper import WhisperModel
        _M = WhisperModel("base.en", device="cpu", compute_type="int8")
    return _M

def needs_align(voice):
    return "Multilingual" in (voice or "")

def _norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())

async def synth(text, voice, rate, path):
    c = edge_tts.Communicate(text, voice, rate=rate, boundary="SentenceBoundary")
    with open(path, "wb") as fh:
        async for ch in c.stream():
            if ch["type"] == "audio": fh.write(ch["data"])
    return align(path, text)

def align(path, text):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    dur = len(audio) / 16000.0
    toks = [t for t in text.split() if _norm(t)]
    def _try(**kw):
        segs, _ = _model().transcribe(audio, word_timestamps=True, language="en", **kw)
        hw_ = [(w.start, w.end, w.word.strip()) for s in segs for w in (s.words or [])]
        out_ = [None] * len(toks)
        sm = difflib.SequenceMatcher(None, [_norm(t) for t in toks], [_norm(w[2]) for w in hw_], autojunk=False)
        for a, b, n in sm.get_matching_blocks():
            for k in range(n): out_[a + k] = (hw_[b + k][0], hw_[b + k][1])
        return hw_, out_
    hw, out = _try(beam_size=1, initial_prompt=text[:200])
    if sum(o is not None for o in out) < 0.8 * len(toks):   # 2026-11-06: the prompt can make whisper hallucinate; retry plain
        hw2, out2 = _try(beam_size=5)
        if sum(o is not None for o in out2) > sum(o is not None for o in out): hw, out = hw2, out2
    # 2026-11-06: drop matches that go backwards in time (whisper mis-heard a sentence and matched a later word at 0 s,
    # which froze the oil Short #2 caption on its last line for 5 s); if under half the words match, spread by letters
    last = -1.0
    for k in range(len(out)):
        if out[k] is not None:
            if out[k][0] < last - 1e-3: out[k] = None
            else: last = out[k][0]
    if sum(o is not None for o in out) < 0.5 * len(toks):
        print("wordtime: alignment weak, spreading words by length", flush=True)
        t0 = hw[0][0] if hw else 0.05; t1 = max(t0 + 0.5, (hw[-1][1] if hw else dur - 0.1))
        L = [len(_norm(t)) + 2 for t in toks]; tot = float(sum(L)); acc = t0
        for k, l in enumerate(L): out[k] = (acc, acc + (t1 - t0) * l / tot); acc = out[k][1]
    # fill gaps by spreading unmatched tokens between known neighbours (numbers read as words etc.)
    i = 0
    while i < len(toks):
        if out[i] is None:
            j = i
            while j < len(toks) and out[j] is None: j += 1
            t0 = out[i - 1][1] if i > 0 else (hw[0][0] if hw else 0.05)
            t1 = out[j][0] if j < len(toks) else (hw[-1][1] if hw else dur)
            if t1 <= t0: t1 = t0 + 0.25 * (j - i)
            step = (t1 - t0) / (j - i)
            for k in range(i, j): out[k] = (t0 + step * (k - i), t0 + step * (k - i + 1))
            i = j
        else: i += 1
    return [(float(a), float(b), re.sub(r"^[^\w$₹%]+|[^\w%]+$", "", t)) for (a, b), t in zip(out, toks)]

if __name__ == "__main__":
    import sys
    ws = asyncio.run(synth("Brent crude settled at $117.64 a barrel on Friday, up 13.6% in October.",
                           "en-US-AndrewMultilingualNeural", "+16%", "/tmp/wt.mp3"))
    print(ws)
