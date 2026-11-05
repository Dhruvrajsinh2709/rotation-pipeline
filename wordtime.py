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
    segs, _ = _model().transcribe(audio, word_timestamps=True, beam_size=1, language="en",
                                  initial_prompt=text[:200])
    hw = [(w.start, w.end, w.word.strip()) for s in segs for w in (s.words or [])]
    toks = [t for t in text.split() if _norm(t)]
    out = [None] * len(toks)
    sm = difflib.SequenceMatcher(None, [_norm(t) for t in toks], [_norm(w[2]) for w in hw], autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n): out[a + k] = (hw[b + k][0], hw[b + k][1])
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
