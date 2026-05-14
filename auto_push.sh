#!/bin/bash
# Vollautomatische Pipeline: output.csv → Dashboard → Git Push → Netlify
# Wird von launchd aufgerufen wenn sich output.csv ändert

REPO_DIR="$HOME/ePropulsion DE Dropbox/Michael Held/01 PRIVAT/Datenaustausch/Tobis Auto/Stromabrechnungen"
LOG="$REPO_DIR/auto_push.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

cd "$REPO_DIR" || exit 1

echo "[$DATE] 🔄 Neue output.csv erkannt – starte Pipeline..." >> "$LOG"

# Lock-Dateien aufräumen
rm -f .git/index.lock .git/HEAD.lock

# Schritt 1: CSV verarbeiten + data_store.json aktualisieren
python3 - << 'PYEOF' >> "$LOG" 2>&1
import pandas as pd, json, sys
from datetime import datetime
from pathlib import Path
import os

BASE = os.path.expanduser(
    "~/ePropulsion DE Dropbox/Michael Held/01 PRIVAT/Datenaustausch/Tobis Auto/Stromabrechnungen"
)
CSV_PATH   = f"{BASE}/output.csv"
STORE_PATH = f"{BASE}/data_store.json"

df_new = pd.read_csv(CSV_PATH)
df_new.columns = df_new.columns.str.strip()
df_new = df_new.dropna(subset=["Time", "Charged:(kWh)"])

if len(df_new) == 0 or df_new["Charged:(kWh)"].sum() == 0:
    print("⚠️ CSV leer oder alle kWh=0 – abgebrochen")
    sys.exit(1)

if Path(STORE_PATH).exists():
    with open(STORE_PATH) as f:
        store = json.load(f)
    existing_times = set(e["time"] for e in store["sessions"])
else:
    store = {"sessions": [], "last_updated": None, "total_sessions": 0}
    existing_times = set()

if len(df_new) < len(store["sessions"]):
    print(f"⚠️ CSV ({len(df_new)}) < Store ({len(store['sessions'])}) – CSV ignoriert")
    sys.exit(0)

new_entries = []
for _, row in df_new.iterrows():
    t = str(row["Time"]).strip()
    if t not in existing_times:
        new_entries.append({
            "time": t,
            "start": str(row["Start:"]).strip(),
            "end": str(row["End:"]).strip(),
            "duration": str(row["Duration:"]).strip(),
            "kwh": round(float(row["Charged:(kWh)"]), 2)
        })

if new_entries:
    store["sessions"].extend(new_entries)
    store["sessions"].sort(key=lambda x: x["time"], reverse=True)
    store["last_updated"] = datetime.now().isoformat()
    store["total_sessions"] = len(store["sessions"])
    with open(STORE_PATH, "w") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    print(f"✅ {len(new_entries)} neue Einträge hinzugefügt (gesamt: {store['total_sessions']})")
else:
    print("ℹ️ Keine neuen Einträge")
PYEOF

# Schritt 2: HTML-Dashboard generieren
python3 "$REPO_DIR/generate_dashboard.py" "$REPO_DIR" >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
    echo "[$DATE] ❌ Dashboard-Generierung fehlgeschlagen" >> "$LOG"
    exit 1
fi

# Schritt 3: Git commit + push
git add index.html data_store.json output.csv
if git diff --cached --quiet; then
    echo "[$DATE] ℹ️ Keine Änderungen – kein Push nötig." >> "$LOG"
    exit 0
fi

git commit -m "auto update $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
git push origin main >> "$LOG" 2>&1

if [ $? -eq 0 ]; then
    echo "[$DATE] ✅ Push erfolgreich → Netlify Deploy gestartet" >> "$LOG"
else
    echo "[$DATE] ❌ Push fehlgeschlagen" >> "$LOG"
fi
