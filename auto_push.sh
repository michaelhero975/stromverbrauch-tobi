#!/bin/bash
# Vollautomatische Pipeline: output.csv → Dashboard → Git Push → Netlify
REPO_DIR="$HOME/ePropulsion DE Dropbox/Michael Held/01 PRIVAT/Datenaustausch/Tobis Auto/Stromabrechnungen"
LOG="$REPO_DIR/auto_push.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

cd "$REPO_DIR" || exit 1

echo "[$DATE] 🔄 Neue output.csv erkannt – starte Pipeline..." >> "$LOG"

# Lock-Dateien aufräumen
rm -f .git/index.lock .git/HEAD.lock

# Schritt 1: CSV verarbeiten – nur mit eingebauten Python-Modulen (kein pandas)
python3 - << 'PYEOF' >> "$LOG" 2>&1
import csv, json, sys, os
from datetime import datetime
from pathlib import Path

BASE       = os.path.expanduser("~/ePropulsion DE Dropbox/Michael Held/01 PRIVAT/Datenaustausch/Tobis Auto/Stromabrechnungen")
CSV_PATH   = f"{BASE}/output.csv"
STORE_PATH = f"{BASE}/data_store.json"

# CSV einlesen
rows = []
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items()}
        if row.get("Time") and row.get("Charged:(kWh)"):
            try:
                kwh = float(row["Charged:(kWh)"])
                rows.append(row)
            except ValueError:
                pass

if not rows:
    print("⚠️ CSV leer oder ungültig – abgebrochen")
    sys.exit(1)

total_kwh = sum(float(r["Charged:(kWh)"]) for r in rows)
if total_kwh == 0:
    print("⚠️ Alle kWh-Werte sind 0 – abgebrochen")
    sys.exit(1)

print(f"CSV: {len(rows)} Zeilen, {total_kwh:.1f} kWh gesamt")

# Store laden
if Path(STORE_PATH).exists():
    with open(STORE_PATH) as f:
        store = json.load(f)
    existing_times = set(e["time"] for e in store["sessions"])
else:
    store = {"sessions": [], "last_updated": None, "total_sessions": 0}
    existing_times = set()

if len(rows) < len(store["sessions"]):
    print(f"⚠️ CSV ({len(rows)}) < Store ({len(store['sessions'])}) – CSV ignoriert")
    sys.exit(0)

# Neue Einträge hinzufügen
new_entries = []
for row in rows:
    t = row["Time"]
    if t not in existing_times:
        new_entries.append({
            "time": t,
            "start": row.get("Start:", ""),
            "end":   row.get("End:", ""),
            "duration": row.get("Duration:", ""),
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
