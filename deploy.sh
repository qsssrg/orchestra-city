#!/bin/zsh
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "$HOME/orchestra-city" || exit 1
LOG="$HOME/claudecode/logs/orchestra-city.log"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') build ===" >> "$LOG"
python3 build_pages.py >> "$LOG" 2>&1 || { echo "build failed" >> "$LOG"; exit 1; }
git add -A docs >> "$LOG" 2>&1
if ! git diff --cached --quiet; then
  git commit -q -m "auto: city update $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
  git push -q origin main >> "$LOG" 2>&1 && echo "pushed" >> "$LOG"
else
  echo "no change" >> "$LOG"
fi
