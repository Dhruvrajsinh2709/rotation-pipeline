#!/usr/bin/env bash
# One video end to end on the runner: draft spec (NVIDIA) -> prefetch clips -> render -> package.
# Usage: pipeline/run.sh short|explain|long [SPEC.json] [test]
set -euo pipefail
KIND=$1; SPEC=${2:-}; TEST=${3:-}
cd /workspace/work/yt
export PYTHONUNBUFFERED=1 STORY_WORK=/tmp/story HF_HOME=$HOME/.cache/hf
T=""; [ "$TEST" = "test" ] && T="--test"
if [ -z "$SPEC" ]; then
  if [ "$KIND" = short ]; then python pipeline/draft_short.py $T | tee /tmp/draft.log
  else python pipeline/draft_long.py "$KIND" $T | tee /tmp/draft.log; fi
  SPEC=$(grep '^SPEC ' /tmp/draft.log | tail -1 | cut -d' ' -f2)
  # Save the drafted script to main right away, so a failed render can be re-run
  # with workflow_dispatch spec=<path> in minutes instead of drafting again.
  if [ -z "$TEST" ] && [ -n "${GH_TOKEN:-}" ]; then
    REL=${SPEC#"$PWD"/}
    gh api -X PUT "repos/$GITHUB_REPOSITORY/contents/$REL" \
      -f message="save drafted spec $(basename "$SPEC")" \
      -f content="$(base64 -w0 "$SPEC")" >/dev/null \
      && echo "SPEC_SAVED $REL" || echo "SPEC_SAVE_FAILED $REL"
  fi
fi
echo "spec: $SPEC"
if [ "$KIND" = short ]; then python pipeline/prefetch.py "$SPEC" --k 4 --cap 60
else python pipeline/prefetch.py "$SPEC" --k 2 --cap 220; fi
start=$(date +%s)
case $KIND in
  short)   python make_story.py "$SPEC" 2>&1 | tee /tmp/render.log ;;
  explain) python make_explain.py "$SPEC" 2>&1 | tee /tmp/render.log ;;
  long)    python make_long.py "$SPEC" 2>&1 | tee /tmp/render.log ;;
esac
echo "RENDER_MINUTES $(( ($(date +%s)-start)/60 ))"
python pipeline/finish.py "$SPEC" "$KIND" | tee /tmp/finish.log
cp /tmp/render.log "dist/$(python -c "import json,os;print(os.path.splitext(os.path.basename(json.load(open('$SPEC'))['output']))[0])")/render.log"
echo "SPEC_USED $SPEC"
