#!/usr/bin/env python3
"""Dashboard-Generator – aktuelles Design (dunkelgrau, 4 Tabs, Effizienz-Teaser auf Startseite)"""
import json, sys
from datetime import datetime
from collections import defaultdict

BASE       = sys.argv[1] if len(sys.argv) > 1 else "."
STORE_PATH = f"{BASE}/data_store.json"
HTML_PATH  = f"{BASE}/index.html"
RATE       = 0.30
START_KM   = 66800

with open(STORE_PATH) as f:
    store = json.load(f)

sessions = store["sessions"]
now = datetime.now()
current_month = now.strftime("%Y-%m")
last_month_dt = datetime(now.year if now.month > 1 else now.year-1,
                         now.month-1 if now.month > 1 else 12, 1)
last_month = last_month_dt.strftime("%Y-%m")

total_kwh  = round(sum(s["kwh"] for s in sessions), 2)
total_cost = round(total_kwh * RATE, 2)
curr_kwh   = round(sum(s["kwh"] for s in sessions if s["time"].startswith(current_month)), 2)
curr_cost  = round(curr_kwh * RATE, 2)
last_kwh   = round(sum(s["kwh"] for s in sessions if s["time"].startswith(last_month)), 2)
last_cost  = round(last_kwh * RATE, 2)

monthly = defaultdict(lambda: {"kwh": 0.0, "count": 0})
for s in sessions:
    monthly[s["time"][:7]]["kwh"] += s["kwh"]
    monthly[s["time"][:7]]["count"] += 1

monthly_sorted = sorted(monthly.keys())
chart_kwh   = [round(monthly[m]["kwh"], 2) for m in monthly_sorted]
chart_costs = [round(monthly[m]["kwh"] * RATE, 2) for m in monthly_sorted]

daily = defaultdict(float)
for s in sessions:
    if s["time"].startswith(current_month):
        daily[s["time"][:10]] += s["kwh"]
daily_sorted = sorted(daily.keys())

monthly_table = []
for m in sorted(monthly.keys(), reverse=True):
    monthly_table.append({"month": m, "count": monthly[m]["count"],
        "kwh": round(monthly[m]["kwh"], 2), "cost": round(monthly[m]["kwh"]*RATE, 2),
        "current": m == current_month})

WEEKDAYS = ["Mo","Di","Mi","Do","Fr","Sa","So"]
all_sessions_table = []
for s in sessions:
    try:
        dt = datetime.fromisoformat(s["time"])
        weekday = WEEKDAYS[dt.weekday()]
        date_str = dt.strftime("%d.%m.%Y")
    except:
        weekday = ""; date_str = s["time"][:10]
    all_sessions_table.append({"date": date_str, "weekday": weekday,
        "start": s["start"], "end": s["end"], "duration": s["duration"],
        "kwh": s["kwh"], "cost": round(s["kwh"]*RATE, 2)})

last_updated = store.get("last_updated","")
try:
    last_updated_str = datetime.fromisoformat(last_updated).strftime("%d.%m.%Y %H:%M Uhr")
except:
    last_updated_str = last_updated

data_json = json.dumps({
    "sessions": all_sessions_table, "monthly": monthly_table,
    "chart_labels": monthly_sorted, "chart_kwh": chart_kwh, "chart_costs": chart_costs,
    "daily_labels": daily_sorted, "daily_kwh": [round(daily[d],2) for d in daily_sorted],
    "stats": {"total_kwh": total_kwh, "total_cost": total_cost,
        "curr_kwh": curr_kwh, "curr_cost": curr_cost,
        "last_kwh": last_kwh, "last_cost": last_cost,
        "current_month": current_month, "last_month": last_month,
        "last_updated": last_updated_str,
        "total_sessions": len(sessions), "start_km": START_KM}
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
body{{background:#141414;color:#d8d8d8;font-family:'Inter',system-ui,sans-serif;min-height:100vh;padding-bottom:2.5rem}}
.header{{padding:1.25rem 1rem 0;max-width:700px;margin:0 auto}}
.header h1{{font-size:1.25rem;font-weight:700;color:#f0f0f0}}
.header p{{font-size:0.72rem;color:#555;margin-top:0.2rem}}
.tab-bar{{display:flex;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;border-bottom:1px solid #2a2a2a;margin-top:1rem;padding:0 1rem;max-width:700px;margin-left:auto;margin-right:auto}}
.tab-bar::-webkit-scrollbar{{display:none}}
.tab-btn{{flex-shrink:0;background:none;border:none;border-bottom:2px solid transparent;color:#555;font-family:inherit;font-size:0.85rem;font-weight:500;padding:0.6rem 1rem;cursor:pointer;transition:all 0.15s;white-space:nowrap}}
.tab-btn:hover{{color:#aaa}}
.tab-btn.active{{color:#f0f0f0;border-bottom-color:#f0f0f0}}
.tab-content{{display:none;padding:1.25rem 1rem;max-width:700px;margin:0 auto}}
.tab-content.active{{display:block}}
.card{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:12px;padding:1.1rem;margin-bottom:0.85rem}}
.kpi-grid{{display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:0.85rem}}
.kpi-main{{grid-column:span 2;background:#1e1e1e;border:1px solid #3a3a3a;border-radius:12px;padding:1.1rem;margin-bottom:0.85rem}}
.kpi-main-label{{font-size:0.68rem;color:#555;font-weight:500;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.65rem}}
.kpi-main-values{{display:flex}}
.kpi-main-item{{flex:1}}
.kpi-main-item+.kpi-main-item{{border-left:1px solid #2a2a2a;padding-left:1rem}}
.kpi-main-num{{font-size:1.65rem;font-weight:700;color:#f0f0f0;line-height:1}}
.kpi-main-sub{{font-size:0.72rem;color:#555;margin-top:0.25rem}}
.kpi-card{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:12px;padding:1rem}}
.kpi-label{{font-size:0.68rem;color:#555;font-weight:500;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem}}
.kpi-value{{font-size:1.45rem;font-weight:700;color:#c8c8c8;line-height:1}}
.kpi-sub{{font-size:0.75rem;color:#555;margin-top:0.25rem}}
.eff-teaser{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:12px;padding:1rem;margin-bottom:0.85rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap}}
.eff-teaser-left{{display:flex;gap:1.5rem;flex-wrap:wrap;align-items:center}}
.eff-teaser-stat{{display:flex;flex-direction:column}}
.eff-teaser-label{{font-size:0.65rem;color:#555;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.2rem}}
.eff-teaser-value{{font-size:1.25rem;font-weight:700;color:#a8a8a8;line-height:1}}
.eff-teaser-value.highlight{{color:#e8e8e8}}
.eff-update-link{{font-size:0.78rem;color:#888;border:1px solid #333;border-radius:8px;padding:0.4rem 0.75rem;white-space:nowrap;cursor:pointer;background:none;font-family:inherit;transition:all 0.15s}}
.eff-update-link:hover{{color:#f0f0f0;border-color:#666}}
.section-label{{font-size:0.68rem;color:#444;font-weight:500;text-transform:uppercase;letter-spacing:0.06em;margin:1.25rem 0 0.65rem}}
.chart-wrap canvas{{max-height:200px}}
.eff-card{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:12px;padding:1.25rem;margin-bottom:0.85rem}}
.eff-section-label{{font-size:0.68rem;color:#555;font-weight:500;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.85rem}}
.eff-input-row{{display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;margin-bottom:1.1rem}}
.km-input{{background:#141414;border:1px solid #3a3a3a;border-radius:8px;color:#f0f0f0;font-size:1.1rem;font-weight:600;font-family:inherit;padding:0.5rem 0.75rem;width:155px;outline:none;transition:border-color 0.15s}}
.km-input:focus{{border-color:#888}}
.km-input::placeholder{{color:#444;font-weight:400;font-size:0.9rem}}
.km-unit{{color:#555;font-size:0.85rem}}
.start-badge{{background:#141414;border:1px solid #2a2a2a;border-radius:6px;padding:0.4rem 0.65rem;font-size:0.75rem;color:#555}}
.start-badge b{{color:#888}}
.eff-results{{display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem}}
.eff-stat{{display:flex;flex-direction:column;gap:0.2rem}}
.eff-stat-label{{font-size:0.65rem;color:#555;text-transform:uppercase;letter-spacing:0.05em}}
.eff-stat-value{{font-size:1.4rem;font-weight:700;color:#c8c8c8;line-height:1.1}}
.eff-stat-value.muted{{color:#666;font-size:1.1rem}}
.eff-hint{{font-size:0.7rem;color:#3a3a3a;margin-top:0.85rem}}
.table-card{{background:#1e1e1e;border:1px solid #2a2a2a;border-radius:12px;overflow:hidden;margin-bottom:0.85rem}}
.row-card{{padding:0.85rem 1rem;border-bottom:1px solid #1a1a1a}}
.row-card:last-child{{border-bottom:none}}
.row-card-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem}}
.row-date{{font-weight:600;color:#e0e0e0;font-size:0.9rem}}
.row-kwh{{font-weight:700;color:#c8c8c8;font-size:1rem}}
.row-meta{{font-size:0.75rem;color:#555}}
.row-cost{{font-size:0.75rem;color:#777;text-align:right;margin-top:0.15rem}}
.month-row{{padding:0.85rem 1rem;border-bottom:1px solid #1a1a1a;display:flex;justify-content:space-between;align-items:center}}
.month-row:last-child{{border-bottom:none}}
.month-row.current{{background:#222}}
.month-name{{font-weight:600;color:#e0e0e0;font-size:0.9rem}}
.month-row.current .month-name{{color:#f0f0f0}}
.month-kwh{{font-weight:700;color:#c8c8c8;font-size:0.95rem}}
.month-sub{{font-size:0.72rem;color:#555}}
.pagination{{display:flex;gap:0.4rem;justify-content:center;flex-wrap:wrap;padding:1rem}}
.pagination button{{background:#141414;border:1px solid #2a2a2a;color:#777;padding:0.4rem 0.75rem;border-radius:6px;cursor:pointer;font-size:0.8rem;font-family:inherit;transition:all 0.15s}}
.pagination button:hover,.pagination button.active{{background:#333;color:#f0f0f0;border-color:#555}}
.pagination button:disabled{{opacity:0.25;cursor:not-allowed}}
.page-info{{text-align:center;font-size:0.72rem;color:#444;padding-bottom:0.75rem}}
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
  <button class="tab-btn" onclick="showTab('monthly',this)">Monate</button>
  <button class="tab-btn" onclick="showTab('sessions',this)">Ladevorgänge</button>
</div>
<div id="tab-overview" class="tab-content active">
  <div class="kpi-main">
    <div class="kpi-main-label">Gesamtverbrauch</div>
    <div class="kpi-main-values">
      <div class="kpi-main-item"><div class="kpi-main-num" id="kpi-total-kwh">–</div><div class="kpi-main-sub">Kilowattstunden</div></div>
      <div class="kpi-main-item"><div class="kpi-main-num" id="kpi-total-cost">–</div><div class="kpi-main-sub">Kosten @ 0,30 €/kWh</div></div>
    </div>
  </div>
  <div class="kpi-grid">
    <div class="kpi-card"><div class="kpi-label">Aktueller Monat</div><div class="kpi-value" id="kpi-curr-kwh">–</div><div class="kpi-sub" id="kpi-curr-cost">–</div></div>
    <div class="kpi-card"><div class="kpi-label">Letzter Monat</div><div class="kpi-value" id="kpi-last-kwh">–</div><div class="kpi-sub" id="kpi-last-cost">–</div></div>
  </div>
  <div class="eff-teaser">
    <div class="eff-teaser-left">
      <div class="eff-teaser-stat"><div class="eff-teaser-label">Ø Verbrauch</div><div class="eff-teaser-value highlight" id="teaser-kwh100">– kWh/100km</div></div>
      <div class="eff-teaser-stat"><div class="eff-teaser-label">Kosten/100 km</div><div class="eff-teaser-value" id="teaser-cost100">–</div></div>
      <div class="eff-teaser-stat"><div class="eff-teaser-label">Gefahren</div><div class="eff-teaser-value" id="teaser-driven">–</div></div>
    </div>
    <button class="eff-update-link" onclick="showTab('efficiency',document.querySelectorAll('.tab-btn')[1])">km aktualisieren →</button>
  </div>
  <div class="section-label">Monatsverlauf</div>
  <div class="card chart-wrap"><canvas id="monthlyChart"></canvas></div>
  <div class="section-label" id="daily-label">Aktueller Monat – Tage</div>
  <div class="card chart-wrap"><canvas id="dailyChart"></canvas></div>
</div>
<div id="tab-efficiency" class="tab-content">
  <div class="eff-card">
    <div class="eff-section-label">kWh pro 100 km</div>
    <div class="eff-input-row">
      <input type="number" id="current-km" class="km-input" placeholder="z.B. 68500" min="66800" step="1"/>
      <span class="km-unit">km</span>
      <div class="start-badge">Start: <b>66.800 km</b></div>
    </div>
    <div class="eff-results">
      <div class="eff-stat"><div class="eff-stat-label">Gefahren</div><div class="eff-stat-value muted" id="driven-km">–</div></div>
      <div class="eff-stat"><div class="eff-stat-label">Ø Verbrauch</div><div class="eff-stat-value" id="kwh-per-100">–</div></div>
      <div class="eff-stat"><div class="eff-stat-label">Kosten/100 km</div><div class="eff-stat-value" id="cost-per-100">–</div></div>
    </div>
    <p class="eff-hint">Kilometerstand wird im Browser gespeichert.</p>
  </div>
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
const stats=DATA.stats,RATE=0.30,START_KM=stats.start_km;
document.getElementById('last-updated').textContent='Letzte Aktualisierung: '+stats.last_updated;
document.getElementById('kpi-total-kwh').textContent=stats.total_kwh.toFixed(1)+' kWh';
document.getElementById('kpi-total-cost').textContent=stats.total_cost.toFixed(2)+' €';
document.getElementById('kpi-curr-kwh').textContent=stats.curr_kwh.toFixed(1)+' kWh';
document.getElementById('kpi-curr-cost').textContent=stats.curr_cost.toFixed(2)+' € ('+stats.current_month+')';
document.getElementById('kpi-last-kwh').textContent=stats.last_kwh.toFixed(1)+' kWh';
document.getElementById('kpi-last-cost').textContent=stats.last_cost.toFixed(2)+' € ('+stats.last_month+')';
document.getElementById('daily-label').textContent=stats.current_month+' – Tagesverlauf';
function showTab(id,btn){{document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.getElementById('tab-'+id).classList.add('active');if(btn)btn.classList.add('active');localStorage.setItem('strom_tab',id);}}
const co=()=>({{responsive:true,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>` ${{ctx.parsed.y.toFixed(1)}} kWh = ${{(ctx.parsed.y*RATE).toFixed(2)}} €`}}}}}},scales:{{x:{{ticks:{{color:'#555',font:{{size:11}}}},grid:{{color:'#1e1e1e'}}}},y:{{ticks:{{color:'#555',font:{{size:11}}}},grid:{{color:'#2a2a2a'}},beginAtZero:true}}}}}});
new Chart(document.getElementById('monthlyChart'),{{type:'bar',data:{{labels:DATA.chart_labels,datasets:[{{label:'kWh',data:DATA.chart_kwh,backgroundColor:'#3a3a3a',hoverBackgroundColor:'#555',borderRadius:4,borderSkipped:false}}]}},options:co()}});
new Chart(document.getElementById('dailyChart'),{{type:'bar',data:{{labels:DATA.daily_labels,datasets:[{{label:'kWh',data:DATA.daily_kwh,backgroundColor:'#3a3a3a',hoverBackgroundColor:'#555',borderRadius:4,borderSkipped:false}}]}},options:co()}});
const ml=document.getElementById('monthly-list');
DATA.monthly.forEach(m=>{{const d=document.createElement('div');d.className='month-row'+(m.current?' current':'');d.innerHTML=`<div><div class="month-name">${{m.month}}</div><div class="month-sub">${{m.count}} Ladevorgänge</div></div><div style="text-align:right"><div class="month-kwh">${{m.kwh.toFixed(1)}} kWh</div><div class="month-sub">${{m.cost.toFixed(2)}} €</div></div>`;ml.appendChild(d);}});
const PS=20;let cp=1;const tp=Math.ceil(DATA.sessions.length/PS);
function rp(p){{const l=document.getElementById('sessions-list');l.innerHTML='';DATA.sessions.slice((p-1)*PS,p*PS).forEach(s=>{{const d=document.createElement('div');d.className='row-card';d.innerHTML=`<div class="row-card-top"><span class="row-date">${{s.date}} <span style="color:#444;font-weight:400;font-size:0.78rem">${{s.weekday}}</span></span><span class="row-kwh">${{s.kwh.toFixed(1)}} kWh</span></div><div style="display:flex;justify-content:space-between"><span class="row-meta">🕐 ${{s.start}} – ${{s.end}} · ${{s.duration}}</span><span class="row-cost">${{s.cost.toFixed(2)}} €</span></div>`;l.appendChild(d);}});document.getElementById('page-info').textContent=`Seite ${{p}} von ${{tp}} · ${{DATA.sessions.length}} Einträge`;rpg(p);}}
function rpg(p){{const pg=document.getElementById('pagination');pg.innerHTML='';const b=(l,pp,dis,act)=>{{const b=document.createElement('button');b.textContent=l;b.disabled=dis;if(act)b.classList.add('active');b.onclick=()=>{{cp=pp;rp(pp);window.scrollTo(0,0);}};pg.appendChild(b);}};b('‹',p-1,p===1,false);for(let pp=1;pp<=tp;pp++){{if(pp===1||pp===tp||Math.abs(pp-p)<=1)b(pp,pp,false,pp===p);else if(Math.abs(pp-p)===2){{const s=document.createElement('span');s.textContent='…';s.style.cssText='color:#444;padding:0 0.2rem;line-height:2';pg.appendChild(s);}}}}b('›',p+1,p===tp,false);}}
rp(1);
const ki=document.getElementById('current-km');
function ue(){{const v=parseInt(ki.value),ok=ki.value&&!isNaN(v)&&v>START_KM;const dr=ok?v-START_KM:0,p1=ok?stats.total_kwh/dr*100:0;document.getElementById('driven-km').textContent=ok?dr.toLocaleString('de-DE')+' km':'–';document.getElementById('kwh-per-100').textContent=ok?p1.toFixed(1)+' kWh':'–';document.getElementById('cost-per-100').textContent=ok?(p1*RATE).toFixed(2)+' €':'–';document.getElementById('teaser-kwh100').textContent=ok?p1.toFixed(1)+' kWh/100km':'– kWh/100km';document.getElementById('teaser-cost100').textContent=ok?(p1*RATE).toFixed(2)+' €/100km':'–';document.getElementById('teaser-driven').textContent=ok?dr.toLocaleString('de-DE')+' km':'–';if(ok)localStorage.setItem('strom_km',ki.value);}}
const sv=localStorage.getItem('strom_km');if(sv){{ki.value=sv;ue();}}
ki.addEventListener('input',ue);
const st=localStorage.getItem('strom_tab');if(st){{const b=document.querySelectorAll('.tab-btn');const m=[['overview',0],['efficiency',1],['monthly',2],['sessions',3]].find(x=>x[0]===st);if(m)showTab(m[0],b[m[1]]);}}
</script>
</body>
</html>"""

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"✅ index.html geschrieben ({len(html):,} Zeichen)")
