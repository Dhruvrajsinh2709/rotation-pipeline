#!/usr/bin/env bash
# Push dist/<name>/ to its own branch renders/<name> (one orphan commit) so Hark can fetch it with git and upload it in
# YouTube Studio. Then commit the run's state (logs of used clips/music/sfx, funnel count, new spec) back to main.
set -euo pipefail
cd /workspace/work/yt
NAME=$(ls -t dist | head -1); TEST=${1:-}
git config user.name "rotation-bot"; git config user.email "rotation-bot@users.noreply.github.com"
TMP=$(mktemp -d); cp -r "dist/$NAME/." "$TMP/"
( cd "$TMP" && git init -q -b "renders/$NAME" && git add -A && git -c user.name=rotation-bot -c user.email=rotation-bot@users.noreply.github.com commit -qm "render $NAME" \
  && git push -q -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "renders/$NAME" )
echo "pushed branch renders/$NAME"
if [ "$TEST" != "test" ]; then
  git add state specs clips/used.json music/used.json sfx2/used.json sfx2/index.json covers/cover_log.json covers/short_cover_log.json 2>/dev/null || true
  git commit -qm "state after $NAME" || echo "no state change"
  for i in 1 2 3; do git pull -q --rebase origin main && git push -q origin HEAD:main && break; sleep 5; done
fi
echo "render_branch=renders/$NAME" >> "${GITHUB_OUTPUT:-/dev/null}"
