#!/usr/bin/env python3
"""Pre-upload QA for Rotation videos (user rule 2026-11-01: check frame by frame, fix, then upload).

Usage: python3 qa_frames.py <video.mp4> [--fps 1] [--out DIR]
Writes DIR/sheet_XX.jpg (20 labelled frames each, 1 per second by default) + DIR/report.json,
prints a summary. Exit 1 if an automatic hard check fails.
The agent MUST then open EVERY sheet with read_file and inspect it (see QA block in prompts).
"""
import json, os, re, subprocess, sys, glob, shutil

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(2)
    vid = a[0]
    fps = float(a[a.index('--fps') + 1]) if '--fps' in a else 1.0
    base = os.path.splitext(os.path.basename(vid))[0]
    out = a[a.index('--out') + 1] if '--out' in a else f'/workspace/work/yt/qa/{base}'
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)

    p = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', vid]).stdout)
    v = next(s for s in p['streams'] if s['codec_type'] == 'video')
    aud = [s for s in p['streams'] if s['codec_type'] == 'audio']
    dur = float(p['format']['duration'])
    W, H = int(v['width']), int(v['height'])
    vertical = H > W

    # frames -> contact sheets (5x4, labelled with timestamp)
    tw = 216 if vertical else 384
    fdir = os.path.join(out, 'f'); os.makedirs(fdir)
    run(['ffmpeg', '-v', 'error', '-i', vid, '-vf',
         f"fps={fps},scale={tw}:-2,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
         f"text='%{{pts\\:hms}}':x=6:y=6:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.7",
         os.path.join(fdir, '%05d.jpg')])
    frames = sorted(glob.glob(os.path.join(fdir, '*.jpg')))
    per = 20
    sheets = []
    for i in range(0, len(frames), per):
        n = len(sheets) + 1
        lst = os.path.join(out, f'l{n}.txt')
        with open(lst, 'w') as f:
            for fr in frames[i:i + per]:
                f.write(f"file '{fr}'\n")
        sp = os.path.join(out, f'sheet_{n:02d}.jpg')
        run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf',
             'tile=5x4:padding=4:color=gray', '-frames:v', '1', '-q:v', '3', sp])
        os.remove(lst); sheets.append(sp)
    # 2026-11-06: catch title slates / text cards baked into source clips (a Navy video slate slipped into a test cut)
    slates = []
    try:
        from PIL import Image
        for k, fr in enumerate(frames):
            im = Image.open(fr); px = list(im.convert('L').getdata()); n = len(px)
            dark = sum(1 for x in px if x < 25) / n; bright = sum(1 for x in px if x > 200) / n
            sat = sum(1 for p in im.convert('HSV').getdata() if p[1] > 90 and p[2] > 60) / n
            if dark > 0.8 and bright > 0.02 and sat < 0.02: slates.append(round(k / fps, 1))   # black + white text, no colour (our cards carry orange/green)
    except Exception as e: print('slate check skipped', e)
    shutil.rmtree(fdir)

    # automatic checks
    r = run(['ffmpeg', '-v', 'info', '-i', vid, '-vf',
             'blackdetect=d=0.5:pix_th=0.08,freezedetect=n=0.003:d=2.5', '-an', '-f', 'null', '-'])
    black = [(float(s), float(e)) for s, e in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', r.stderr)]
    fs = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', r.stderr)]
    fe = [float(x) for x in re.findall(r'freeze_end: ([\d.]+)', r.stderr)]
    freezes = list(zip(fs, fe + [dur] * (len(fs) - len(fe))))
    silences, lufs = [], None
    if aud:
        r = run(['ffmpeg', '-v', 'info', '-i', vid, '-af', 'silencedetect=n=-45dB:d=1.5,ebur128', '-vn', '-f', 'null', '-'])
        ss = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r.stderr)]
        se = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r.stderr)]
        silences = list(zip(ss, se + [dur] * (len(ss) - len(se))))
        m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
        lufs = float(m[-1]) if m else None

    hard = []
    if not aud: hard.append('no audio stream')
    long_black = [b for b in black if b[1] - b[0] > 1.0 and b[0] > 0.3 and b[1] < dur - 0.3]
    if long_black: hard.append(f'black >1s at {long_black}')
    if [s for s in silences if s[1] - s[0] > 3 and s[1] < dur - 1]: hard.append('audio silent >3s mid-video')
    if vertical and (W, H) != (1080, 1920): hard.append(f'Short is {W}x{H}, expected 1080x1920')
    if vertical and dur > 60: hard.append(f'Short is {dur:.1f}s (>60s)')
    if not vertical and H < 1080: hard.append(f'long video only {H}p')
    if lufs is not None and not (-17.5 <= lufs <= -11.5): hard.append(f'loudness {lufs} LUFS off target -14')

    # 2026-11-06 pace gate (oil Short #2 held stills 7-8 s): Shorts may not hold one shot longer than 4.5 s
    cuts = []
    if vertical:
        r = run(['ffmpeg', '-v', 'info', '-i', vid, '-vf', "scale=270:-2,select='gt(scene,0.25)',showinfo", '-an', '-f', 'null', '-'])
        cuts = [float(x) for x in re.findall(r'pts_time:([\d.]+)', r.stderr)]
        b = [0.0] + cuts + [dur]; gaps = [(round(b[k], 1), round(b[k+1]-b[k], 1)) for k in range(len(b)-1)]
        longs = [g for g in gaps if g[1] > 4.5]
        if longs: hard.append(f'shots held too long (start s, length s) {longs}; max 4.5 s, aim 2-3 s')
    if vertical and slates: hard.append(f'text slate / black card frames at {slates} s (source clip title card?) - swap that clip')
    rep = dict(video=vid, duration=round(dur, 2), size=f'{W}x{H}', fps=v.get('r_frame_rate'),
               audio=bool(aud), lufs=lufs, black=black, freezes=freezes, silences=silences,
               sheets=sheets, frames=len(frames), hard_fail=hard, shots=len(cuts)+1 if vertical else None)
    json.dump(rep, open(os.path.join(out, 'report.json'), 'w'), indent=1)
    print(json.dumps({k: rep[k] for k in rep if k != 'sheets'}, indent=1))
    print(f'{len(sheets)} sheets in {out} -> open EVERY one with read_file')
    sys.exit(1 if hard else 0)

if __name__ == '__main__':
    main()
