#!/usr/bin/env python3
"""
Dashboard-Generator für Stromverbrauch Tobis Auto.
Wird vom scheduled Task aufgerufen.
Usage: python3 generate_dashboard.py <base_path>
"""
import json, sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "."
STORE_PATH = f"{BASE}/data_store.json"
HTML_PATH  = f"{BASE}/index.html"
RATE       = 0.30
START_KM   = 66800

with open(STORE_PATH) as f:
    store = json.load(f)

sessions = store["sessions"]
now = datetime.now()
current_month = now.strftime("%Y-%m")
last_month_dt = datetime(now.year if now.month > 1 else now.year - 1,
                          now.month - 1 if now.month > 1 else 12, 1)
last_month = last_month_dt.strftime("%Y-%m")

total_kwh  = round(sum(s["kwh"] for s in sessions), 2)
total_cost = round(total_kwh * RATE, 2)
curr_kwh   = round(sum(s["kwh"] for s in sessions if s["time"].startswith(current_month)), 2)
curr_cost  = round(curr_kwh * RATE, 2)
last_kwh   = round(sum(s["kwh"] for s in sessions if s["time"].startswith(last_month)), 2)
last_cost  = round(last_kwh * RATE, 2)

monthly = defaultdict(lambda: {"kwh": 0.0, "count": 0})
for s in sessions:
    m = s["time"][:7]
    monthly[m]["kwh"] += s["kwh"]
    monthly[m]["count"] += 1

monthly_sorted = sorted(monthly.keys())
chart_kwh    = [round(monthly[m]["kwh"], 2) for m in monthly_sorted]
chart_costs  = [round(monthly[m]["kwh"] * RATE, 2) for m in monthly_sorted]

daily = defaultdict(float)
for s in sessions:
    if s["time"].startswith(current_month):
        daily[s["time"][:10]] += s["kwh"]
daily_sorted = sorted(daily.keys())

monthly_table = []
for m in sorted(monthly.keys(), reverse=True):
    monthly_table.append({
        "month": m, "count": monthly[m]["count"],
        "kwh": round(monthly[m]["kwh"], 2),
        "cost": round(monthly[m]["kwh"] * RATE, 2),
        "current": m == current_month
    })

WEEKDAYS = ["Mo","Di","Mi","Do","Fr","Sa","So"]
all_sessions_table = []
for s in sessions:
    try:
        dt = datetime.fromisoformat(s["time"])
        weekday = WEEKDAYS[dt.weekday()]
        date_str = dt.strftime("%d.%m.%Y")
    except:
        weekday = ""; date_str = s["time"][:10]
    all_sessions_table.append({
        "date": date_str, "weekday": weekday,
        "start": s["start"], "end": s["end"], "duration": s["duration"],
        "kwh": s["kwh"], "cost": round(s["kwh"] * RATE, 2)
    })

last_updated = store.get("last_updated","")
try:
    last_updated_str = datetime.fromisoformat(last_updated).strftime("%d.%m.%Y %H:%M Uhr")
except:
    last_updated_str = last_updated

data_json = json.dumps({
    "sessions": all_sessions_table, "monthly": monthly_table,
    "chart_labels": monthly_sorted, "chart_kwh": chart_kwh, "chart_costs": chart_costs,
    "daily_labels": daily_sorted, "daily_kwh": [round(daily[d],2) for d in daily_sorted],
    "stats": {
        "total_kwh": total_kwh, "total_cost": total_cost,
        "curr_kwh": curr_kwh, "curr_cost": curr_cost,
        "last_kwh": last_kwh, "last_cost": last_cost,
        "current_month": current_month, "last_month": last_month,
        "last_updated": last_updated_str,
        "total_sessions": len(sessions), "start_km": START_KM
    }
}, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚡ Stromverbrauch – Tobis Auto</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0f172a;color:#e2e8f0;font-family:'Inter',system-ui,sans-serif;min-height:100vh;padding-bottom:2rem}}
  .header{{padding:1.25rem 1rem 0;max-width:700px;margin:0 auto}}
  .header h1{{font-size:1.3rem;font-weight:700;color:#f1f5f9}}
  .header p{{font-size:0.75rem;color:#475569;margin-top:0.2rem}}
  .tab-bar{{display:flex;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;border-bottom:1px solid #1e293b;margin-top:1.1rem;padding:0 1rem;max-width:700px;margin-left:auto;margin-right:auto}}
  .tab-bar::-webkit-scrollbar{{display:none}}
  .tab-btn{{flex-shrink:0;background:none;border:none;border-bottom:2px solid transparent;color:#64748b;font-family:inherit;font-size:0.85rem;font-weight:500;padding:0.65rem 1rem;cursor:pointer;transition:all 0.15s;white-space:nowrap}}
  .tab-btn:hover{{color:#94a3b8}}
  .tab-btn.active{{color:#38bdf8;border-bottom-color:#38bdf8}}
  .tab-content{{display:none;padding:1.25rem 1rem;max-width:700px;margin:0 auto}}
  .tab-content.active{{display:block}}
  .kpi-grid{{display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem}}
  .kpi-card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:1rem}}
  .kpi-card.accent{{border-color:#38bdf8;background:#0c1a2e;grid-column:span 2}}
  .kpi-label{{font-size:0.7rem;color:#64748b;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem}}
  .kpi-value{{font-size:1.6rem;font-weight:700;color:#38bdf8;line-height:1}}
  .kpi-sub{{font-size:0.78rem;color:#94a3b8;margin-top:0.3rem}}
  .eff-card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:1.25rem;margin-bottom:1rem}}
  .eff-title{{font-size:0.7rem;color:#64748b;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.85rem}}
  .eff-input-row{{display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;margin-bottom:1rem}}
  .km-input{{background:#0f172a;border:1px solid #475569;border-radius:8px;color:#f1f5f9;font-size:1.1rem;font-weight:600;font-family:inherit;padding:0.5rem 0.75rem;width:150px;outline:none;transition:border-color 0.15s}}
  .km-input:focus{{border-color:#38bdf8}}
  .km-input::placeholder{{color:#475569;font-weight:400;font-size:0.9rem}}
  .km-unit{{color:#64748b;font-size:0.85rem}}
  .start-badge{{background:#0f172a;border:1px solid #334155;border-radius:6px;padding:0.4rem 0.65rem;font-size:0.75rem;color:#64748b}}
  .start-badge b{{color:#94a3b8}}
  .eff-results{{display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem}}
  .eff-stat{{display:flex;flex-direction:column;gap:0.2rem}}
  .eff-stat-label{{font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.04em}}
  .eff-stat-value{{font-size:1.4rem;font-weight:700;color:#34d399;line-height:1.1}}
  .eff-stat-value.muted{{color:#94a3b8;font-size:1.1rem}}
  .eff-hint{{font-size:0.72rem;color:#334155;margin-top:0.85rem}}
  .chart-card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:1.25rem;margin-bottom:1rem}}
  .chart-card canvas{{max-height:240px}}
  .chart-title{{font-size:0.7rem;color:#64748b;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:1rem}}
  .table-card{{background:#1e293b;border:1px solid #334155;border-radius:12px;overflow:hidden;margin-bottom:1rem}}
  .row-card{{padding:0.85rem 1rem;border-bottom:1px solid #0f172a}}
  .row-card:last-child{{border-bottom:none}}
  .row-card-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem}}
  .row-date{{font-weight:600;color:#f1f5f9;font-size:0.9rem}}
  .row-kwh{{font-weight:700;color:#38bdf8;font-size:1rem}}
  .row-meta{{font-size:0.75rem;color:#64748b}}
  .row-cost{{font-size:0.75rem;color:#94a3b8;text-align:right;margin-top:0.15rem}}
  .month-row{{padding:0.85rem 1rem;border-bottom:1px solid #0f172a;display:flex;justify-content:space-between;align-items:center}}
  .month-row:last-child{{border-bottom:none}}
  .month-row.current{{background:#0c2540}}
  .month-name{{font-weight:600;color:#f1f5f9;font-size:0.9rem}}
  .month-row.current .month-name{{color:#38bdf8}}
  .month-kwh{{font-weight:700;color:#38bdf8;font-size:0.95rem}}
  .month-sub{{font-size:0.72rem;color:#64748b}}
  .pagination{{display:flex;gap:0.4rem;justify-content:center;flex-wrap:wrap;padding:1rem}}
  .pagination button{{background:#0f172a;border:1px solid #334155;color:#94a3b8;padding:0.4rem 0.75rem;border-radius:6px;cursor:pointer;font-size:0.8rem;font-family:inherit;transition:all 0.15s}}
  .pagination button:hover,.pagination button.active{{background:#38bdf8;color:#0f172a;border-color:#38bdf8;font-weight:600}}
  .pagination button:disabled{{opacity:0.3;cursor:not-allowed}}
  .page-info{{text-align:center;font-size:0.75rem;color:#475569;padding-bottom:0.75rem}}
</style>
</head>
<body>
<div class="header">
  <h1>⚡ Stromverbrauch – Tobis Auto</h1>
  <p id="last-updated">Letzte Aktualisierung: …</p>
</div>
<div class="tab-bar">
  <button class="tab-btn active" onclick="showTab('overview',this)">Übersicht</button>
  <button class="tab-btn" onclick="showTab('efficiency',this)">Effizienz</button>
  <button class="tab-btn" onclick="showTab('charts',this)">Verlauf</button>
  <button class="tab-btn" onclick="showTab('monthly',this)">Monate</button>
  <button class="tab-btn" onclick="showTab('sessions',this)">Ladevorgänge</button>
</div>
<div id="tab-overview" class="tab-content active">
  <div class="kpi-grid">
    <div class="kpi-card accent"><div class="kpi-label">Gesamtverbrauch</div><div class="kpi-value" id="kpi-total-kwh">–</div><div class="kpi-sub" id="kpi-total-cost">–</div></div>
    <div class="kpi-card"><div class="kpi-label">Aktueller Monat</div><div class="kpi-value" id="kpi-curr-kwh">–</div><div class="kpi-sub" id="kpi-curr-cost">–</div></div>
    <div class="kpi-card"><div class="kpi-label">Letzter Monat</div><div class="kpi-value" id="kpi-last-kwh">–</div><div class="kpi-sub" id="kpi-last-cost">–</div></div>
    <div class="kpi-card"><div class="kpi-label">Ladevorgänge</div><div class="kpi-value" id="kpi-sessions">–</div><div class="kpi-sub">gesamt</div></div>
  </div>
</div>
<div id="tab-efficiency" class="tab-content">
  <div class="eff-card">
    <div class="eff-title">kWh pro 100 km</div>
    <div class="eff-input-row">
      <input type="number" id="current-km" class="km-input" placeholder="z.B. 68500" min="66800" step="1"/>
      <span class="km-unit">km</span>
      <div class="start-badge">Start: <b>66.800 km</b></div>
    </div>
    <div class="eff-results">
      <div class="eff-stat"><div class="eff-stat-label">Gefahren</div><div class="eff-stat-value muted" id="driven-km">–</div></div>
      <div class="eff-stat"><div class="eff-stat-label">Ø Verbrauch</div><div class="eff-stat-value" id="kwh-per-100">–</div></div>
      <div class="eff-stat"><div class="eff-stat-label">Kosten/100km</div><div class="eff-stat-value" id="cost-per-100">–</div></div>
    </div>
    <p class="eff-hint">💡 Kilometerstand wird im Browser gespeichert.</p>
  </div>
</div>
<div id="tab-charts" class="tab-content">
  <div class="chart-card"><div class="chart-title">Monatsverlauf (kWh)</div><canvas id="monthlyChart"></canvas></div>
  <div class="chart-card"><div class="chart-title" id="daily-title">Aktueller Monat – Tage</div><canvas id="dailyChart"></canvas></div>
</div>
<div id="tab-monthly" class="tab-content">
  <div class="table-card" id="monthly-list"></div>
</div>
<div id="tab-sessions" class="tab-content">
  <div class="table-card" id="sessions-list"></div>
  <div class="pagination" id="pagination"></div>
  <p class="page-info" id="page-info"></p>
</div>
<script>
const DATA={data_json};
const START_KM=DATA.stats.start_km;
const stats=DATA.stats;
document.getElementById('last-updated').textContent='Letzte Aktualisierung: '+stats.last_updated;
document.getElementById('kpi-total-kwh').textContent=stats.total_kwh.toFixed(1)+' kWh';
document.getElementById('kpi-total-cost').textContent=stats.total_cost.toFixed(2)+' € @ 0,30 €/kWh';
document.getElementById('kpi-curr-kwh').textContent=stats.curr_kwh.toFixed(1)+' kWh';
document.getElementById('kpi-curr-cost').textContent=stats.curr_cost.toFixed(2)+' € ('+stats.current_month+')';
document.getElementById('kpi-last-kwh').textContent=stats.last_kwh.toFixed(1)+' kWh';
document.getElementById('kpi-last-cost').textContent=stats.last_cost.toFixed(2)+' € ('+stats.last_month+')';
document.getElementById('kpi-sessions').textContent=stats.total_sessions;
document.getElementById('daily-title').textContent=stats.current_month+' – Tagesverlauf';
function showTab(id,btn){{document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.getElementById('tab-'+id).classList.add('active');btn.classList.add('active');if(id==='charts')initCharts();localStorage.setItem('strom_tab',id);}}
let chartsInited=false;
function initCharts(){{if(chartsInited)return;chartsInited=true;
new Chart(document.getElementById('monthlyChart'),{{type:'bar',data:{{labels:DATA.chart_labels,datasets:[{{label:'kWh',data:DATA.chart_kwh,backgroundColor:'#38bdf8',borderRadius:5,borderSkipped:false}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>` ${{ctx.parsed.y.toFixed(1)}} kWh = ${{(ctx.parsed.y*0.30).toFixed(2)}} €`}}}}}},scales:{{x:{{ticks:{{color:'#64748b',font:{{size:11}}}},grid:{{color:'#0f172a'}}}},y:{{ticks:{{color:'#64748b',font:{{size:11}}}},grid:{{color:'#334155'}},beginAtZero:true}}}}}}}});
new Chart(document.getElementById('dailyChart'),{{type:'line',data:{{labels:DATA.daily_labels,datasets:[{{label:'kWh',data:DATA.daily_kwh,borderColor:'#38bdf8',backgroundColor:'rgba(56,189,248,0.1)',tension:0.3,fill:true,pointBackgroundColor:'#38bdf8',pointRadius:4}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>` ${{ctx.parsed.y.toFixed(1)}} kWh = ${{(ctx.parsed.y*0.30).toFixed(2)}} €`}}}}}},scales:{{x:{{ticks:{{color:'#64748b',font:{{size:11}}}},grid:{{color:'#0f172a'}}}},y:{{ticks:{{color:'#64748b',font:{{size:11}}}},grid:{{color:'#334155'}},beginAtZero:true}}}}}}}});
}}
const monthlyList=document.getElementById('monthly-list');
DATA.monthly.forEach(m=>{{const div=document.createElement('div');div.className='month-row'+(m.current?' current':'');div.innerHTML=`<div><div class="month-name">${{m.month}}</div><div class="month-sub">${{m.count}} Ladevorgänge</div></div><div class="month-stats"><div class="month-kwh">${{m.kwh.toFixed(1)}} kWh</div><div class="month-sub">${{m.cost.toFixed(2)}} €</div></div>`;monthlyList.appendChild(div);}});
const PAGE_SIZE=20;let currentPage=1;const totalPages=Math.ceil(DATA.sessions.length/PAGE_SIZE);
function renderPage(page){{const list=document.getElementById('sessions-list');list.innerHTML='';DATA.sessions.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE).forEach(s=>{{const div=document.createElement('div');div.className='row-card';div.innerHTML=`<div class="row-card-top"><span class="row-date">${{s.date}} <span style="color:#475569;font-weight:400;font-size:0.8rem">${{s.weekday}}</span></span><span class="row-kwh">${{s.kwh.toFixed(1)}} kWh</span></div><div style="display:flex;justify-content:space-between;align-items:center"><span class="row-meta">🕐 ${{s.start}} – ${{s.end}} · ${{s.duration}}</span><span class="row-cost">${{s.cost.toFixed(2)}} €</span></div>`;list.appendChild(div);}});document.getElementById('page-info').textContent=`Seite ${{page}} von ${{totalPages}} · ${{DATA.sessions.length}} Einträge`;renderPagination(page);}}
function renderPagination(page){{const pg=document.getElementById('pagination');pg.innerHTML='';const btn=(label,p,disabled,active)=>{{const b=document.createElement('button');b.textContent=label;b.disabled=disabled;if(active)b.classList.add('active');b.onclick=()=>{{currentPage=p;renderPage(p);window.scrollTo(0,0);}};pg.appendChild(b);}};btn('‹',page-1,page===1,false);for(let p=1;p<=totalPages;p++){{if(p===1||p===totalPages||Math.abs(p-page)<=1)btn(p,p,false,p===page);else if(Math.abs(p-page)===2){{const s=document.createElement('span');s.textContent='…';s.style.cssText='color:#475569;padding:0 0.2rem;line-height:2';pg.appendChild(s);}}}}btn('›',page+1,page===totalPages,false);}}
renderPage(1);
const kmInput=document.getElementById('current-km');
function updateEff(){{const v=parseInt(kmInput.value);if(!kmInput.value||isNaN(v)||v<=START_KM){{document.getElementById('driven-km').textContent='–';document.getElementById('kwh-per-100').textContent='–';document.getElementById('cost-per-100').textContent='–';return;}}const driven=v-START_KM;const per100=stats.total_kwh/driven*100;document.getElementById('driven-km').textContent=driven.toLocaleString('de-DE')+' km';document.getElementById('kwh-per-100').textContent=per100.toFixed(1)+' kWh';document.getElementById('cost-per-100').textContent=(per100*0.30).toFixed(2)+' €';localStorage.setItem('strom_km',kmInput.value);}}
const saved=localStorage.getItem('strom_km');if(saved){{kmInput.value=saved;updateEff();}}
kmInput.addEventListener('input',updateEff);
const savedTab=localStorage.getItem('strom_tab');if(savedTab){{const b=document.querySelector(`.tab-btn[onclick*="${{savedTab}}"]`);if(b)showTab(savedTab,b);}}
</script>
</body>
</html>"""

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ index.html geschrieben ({len(html):,} Zeichen)")
