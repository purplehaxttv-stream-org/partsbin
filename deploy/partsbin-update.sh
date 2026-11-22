#!/bin/bash
# Pull-based deploy: fast-forward ~/partsbin to origin/main, restart, health-check, roll back on failure.
set -euo pipefail
APP=/home/purplehaxttv/partsbin
cd "$APP"
git fetch --quiet origin main
OLD=$(git rev-parse HEAD); NEW=$(git rev-parse origin/main)
if [ "$OLD" = "$NEW" ]; then echo "up to date at ${OLD:0:7}"; exit 0; fi
echo "updating ${OLD:0:7} -> ${NEW:0:7}"

BACKUP="data/backups/partsbin-pre-${NEW:0:7}-$(date +%Y%m%d-%H%M%S).db"
sqlite3 data/partsbin.db ".backup $BACKUP"
ls -1t data/backups/partsbin-pre-*.db 2>/dev/null | tail -n +11 | xargs -r rm -f

deploy() {
  .venv/bin/pip install --quiet -r requirements.txt
  sudo /usr/bin/systemctl restart partsbin
  for i in $(seq 1 15); do
    curl -fsS -o /dev/null http://127.0.0.1:5055/ && return 0
    sleep 2
  done
  return 1
}

git merge --ff-only --quiet origin/main
if deploy; then
  echo "deployed ${NEW:0:7}: $(git log -1 --format=%s)"
else
  echo "health check failed on ${NEW:0:7}, rolling back to ${OLD:0:7}" >&2
  git reset --hard --quiet "$OLD"
  deploy && echo "rolled back to ${OLD:0:7}" >&2
  exit 1
fi
