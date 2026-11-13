#!/bin/bash
# ============================================================================
#  Mark-LVI  ->  GitHub   (repo: kanchanlata41286-wq/jarvis_01)
#
#  Git Bash me ye file chalao:
#     bash "/e/all jarvace/Mark-LVI-main/upload-to-github.sh"
#
#  Kya karta hai:
#    1. saari files stage + commit karta hai
#    2. GitHub login maangta hai (browser me ek code daalna hoga)
#    3. repo exist nahi karta to bana deta hai
#    4. push kar deta hai
# ============================================================================
set -e

PROJECT="/e/all jarvace/Mark-LVI-main"
REPO="kanchanlata41286-wq/jarvis_01"
GH="/c/Users/Pc S/AppData/Local/Programs/GitHub CLI/bin/gh.exe"

cd "$PROJECT"

# E: drive "ownership record" nahi rakhta -> warning hatane ke liye
git config --global --add safe.directory "$PROJECT"

echo ""
echo ">>> [1/4] Files stage + commit ..."
git add -A
if git diff --cached --quiet; then
  echo "    (kuch naya nahi - pehle se committed hai)"
else
  git commit -m "Initial commit: Mark-LVI"
  echo "    committed."
fi

echo ""
echo ">>> [2/4] GitHub login ..."
if ! "$GH" auth status >/dev/null 2>&1; then
  echo "    Browser me ye URL kholo aur code daalo:"
  "$GH" auth login --hostname github.com --git-protocol https --web
fi
"$GH" auth setup-git
"$GH" auth status

echo ""
echo ">>> [3/4] Repo check / create ..."
if "$GH" repo view "$REPO" >/dev/null 2>&1; then
  echo "    Repo already exists: https://github.com/$REPO"
else
  echo "    Repo nahi mila - bana raha hoon (PRIVATE) ..."
  "$GH" repo create "$REPO" --private
fi

echo ""
echo ">>> [4/4] Push ..."
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$REPO.git"

# Pehle normal push; agar remote pe pehle se commit hain to force lagta hai.
if ! git push -u origin main; then
  echo "    Normal push reject hua - force kar raha hoon ..."
  git push -u origin main --force
fi

echo ""
echo "============================================================"
echo "  DONE!  https://github.com/$REPO"
echo "============================================================"
