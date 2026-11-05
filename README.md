# rotation-pipeline (private)
Render pipeline for the YouTube channel **Rotation** (@RotationNews), moved off Hark onto GitHub Actions (2026-11-05).

| Workflow | When (IST) | What |
|---|---|---|
| `short.yml` | daily 18:00 | Funnel 2x Short: newest long video with < 2 Shorts (state/funnel.json) -> NVIDIA draft -> fact check -> render |
| `explain.yml` | Wed 08:30 | Rotation Explains: `specs/queue/<date>_explain*.json` if present, else NVIDIA draft from the news |
| `long.yml` | Sat 08:30 | Weekend deep dive: `specs/queue/<date>_long*.json` if present, else NVIDIA draft |
| `sfx_pack.yml` | manual | SFX add-on: Openverse CC0/PDM sounds + earshot code-made bank into `sfx2/` |

Each run pushes its package to branch `renders/<name>` (video.mp4 <= 95 MB upload copy, description.txt, spec.json, qa/ sheets,
render.log) and keeps it as a 7-day artifact. Hark then fetches the branch, checks the QA sheets and uploads in YouTube Studio
(YouTube API uploads from unaudited projects are locked private), then deletes the branch.

**Secret needed:** `NVIDIA_API_KEY` (Settings > Secrets and variables > Actions). Optional variable `NVIDIA_MODEL`
(comma list; default meta/llama-3.3-70b-instruct, then qwen2.5-72b, mixtral-8x22b).

Clips: only `clips/index.json` is in git; `pipeline/prefetch.py` downloads what a spec needs from Mixkit/Coverr/Wikimedia/NASA
(cached between runs). Renderers expect `/workspace/work/yt`, which `pipeline/setup_runner.sh` symlinks to the checkout.
Rendering code = Hark's locked v9/v10 look (orange accent, light palette C, SOUND v10). Spec keys: `SPEC_KEYS.md`.
Free private-repo limit: 2,000 Actions minutes/month (estimate for this schedule ~950).
