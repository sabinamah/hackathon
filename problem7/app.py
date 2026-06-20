import os, json, random
from datetime import date, timedelta
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key_env = os.getenv("GOOGLE_API_KEY", "")

# ── Product catalog from hackathon data pack §3 ────────────────────────────────
PRODUCTS = [
    {"sku":"ALK-FB-01","name":"Fuß Butter","line":"Feet","price":7.71,"peak":"Autumn–Winter","segment":"45+ dry-skin, women"},
    {"sku":"ALK-FB-02","name":"Sole Fußbad","line":"Feet","price":6.49,"peak":"Winter","segment":"Wellness, 50+"},
    {"sku":"ALK-FB-03","name":"Hornhaut Reduziercreme","line":"Feet","price":6.99,"peak":"Spring","segment":"Women 30–60"},
    {"sku":"ALK-FB-04","name":"Hornhaut Entferner Maske","line":"Feet","price":8.49,"peak":"Spring–Summer","segment":"Women 25–45"},
    {"sku":"ALK-FB-05","name":"10% Urea Fußcreme","line":"Feet","price":7.25,"peak":"All year","segment":"Diabetic / very dry skin"},
    {"sku":"ALK-FB-06","name":"Fußpflege Deospray","line":"Feet","price":6.10,"peak":"Summer","segment":"Active / men 20–45"},
    {"sku":"ALK-LG-01","name":"5 in 1 Beinlotion","line":"Legs","price":9.95,"peak":"Summer","segment":"Women 35–65"},
    {"sku":"ALK-LG-02","name":"Bein Frische Gel","line":"Legs","price":8.20,"peak":"Summer","segment":"Travel / standing jobs"},
    {"sku":"ALK-LG-03","name":"Besenreiser Pflegebalsam","line":"Legs","price":11.49,"peak":"Spring–Summer","segment":"Women 40–65"},
    {"sku":"ALK-MG-01","name":"Mobil Gel","line":"Muscles","price":5.83,"peak":"Autumn–Winter","segment":"Active 30+, 55+ joints"},
    {"sku":"ALK-MG-02","name":"Mobil Einreibung Extra Stark","line":"Muscles","price":8.90,"peak":"Winter / sport","segment":"Sport, 25–55"},
    {"sku":"ALK-MG-03","name":"Mobil Eisspray akut","line":"Muscles","price":9.40,"peak":"Sport season","segment":"Athletes, teams"},
    {"sku":"ALK-MG-04","name":"Franzbranntwein","line":"Muscles","price":6.75,"peak":"All year","segment":"Traditional 55+"},
    {"sku":"ALK-MG-05","name":"Wärmendes Intensiv Gel","line":"Muscles","price":8.30,"peak":"Winter","segment":"45+ tension/back"},
    {"sku":"ALK-CB-01","name":"Ur Bonbons","line":"Cough","price":2.49,"peak":"Cold season","segment":"Mass-market"},
]

PRODUCT_MAP = {p["sku"]: p for p in PRODUCTS}

SEGMENTS = ["Women 25–45","Women 35–65","Women 45–65","Active Men 20–45","Sport 25–55","Traditional 55+","Diabetic/Dry Skin","Wellness 50+"]
CHANNELS = ["Pharmacy","Online Pharmacy","DM","Rossmann","Amazon","Direct"]
REGIONS  = ["Bayern","NRW","Baden-Württemberg","Hessen","Niedersachsen","Saarland","Sachsen","Berlin"]
WEATHERS = ["cold","mild","warm","hot","rainy"]

SEASON_WEIGHTS = {
    "ALK-FB-01":[1,1,1,1,2,2,2,2,5,6,5,3],
    "ALK-FB-02":[4,3,2,1,1,1,1,1,2,3,4,5],
    "ALK-FB-03":[1,1,3,5,6,5,4,2,1,1,1,1],
    "ALK-FB-04":[1,1,2,4,6,6,5,3,1,1,1,1],
    "ALK-FB-05":[3,3,3,3,3,3,3,3,3,3,3,3],
    "ALK-FB-06":[1,1,1,2,4,6,6,4,2,1,1,1],
    "ALK-LG-01":[1,1,2,3,5,7,7,5,2,1,1,1],
    "ALK-LG-02":[1,1,2,3,5,7,7,5,2,1,1,1],
    "ALK-LG-03":[1,1,2,4,6,6,5,3,2,1,1,1],
    "ALK-MG-01":[4,3,2,2,2,2,2,2,3,5,6,5],
    "ALK-MG-02":[4,3,2,2,2,2,2,2,3,5,6,5],
    "ALK-MG-03":[2,2,3,4,5,5,5,5,4,3,2,2],
    "ALK-MG-04":[3,3,3,3,3,3,3,3,3,3,3,3],
    "ALK-MG-05":[5,4,2,2,1,1,1,1,2,4,5,6],
    "ALK-CB-01":[5,4,3,2,1,1,1,1,1,2,4,6],
}

SEG_SKU_AFFINITY = {
    "Women 25–45":      ["ALK-FB-03","ALK-FB-04","ALK-LG-01","ALK-LG-02"],
    "Women 35–65":      ["ALK-LG-01","ALK-LG-03","ALK-FB-01","ALK-FB-03"],
    "Women 45–65":      ["ALK-LG-03","ALK-FB-01","ALK-FB-02","ALK-MG-05"],
    "Active Men 20–45": ["ALK-FB-06","ALK-MG-03","ALK-MG-02"],
    "Sport 25–55":      ["ALK-MG-03","ALK-MG-02","ALK-MG-01","ALK-FB-06"],
    "Traditional 55+":  ["ALK-MG-04","ALK-MG-01","ALK-FB-02","ALK-CB-01"],
    "Diabetic/Dry Skin":["ALK-FB-05","ALK-FB-01","ALK-FB-03"],
    "Wellness 50+":     ["ALK-FB-02","ALK-FB-01","ALK-LG-03","ALK-MG-04"],
}


def generate_transactions(n=600):
    random.seed(42)
    rows = []
    start = date(2024, 1, 1)
    for i in range(n):
        seg  = random.choice(SEGMENTS)
        affi = SEG_SKU_AFFINITY.get(seg, [p["sku"] for p in PRODUCTS])
        sku  = random.choices(affi + [p["sku"] for p in PRODUCTS], weights=[4]*len(affi)+[1]*len(PRODUCTS), k=1)[0]
        month = random.choices(range(1,13), weights=SEASON_WEIGHTS.get(sku,[3]*12), k=1)[0]
        day   = random.randint(1, 28)
        txdate= date(random.choice([2024,2025]), month, day)
        qty   = random.choices([1,2,3], weights=[6,3,1])[0]
        price = round(PRODUCT_MAP[sku]["price"] * random.uniform(0.95, 1.05), 2)
        rows.append({
            "customer_id": f"C{random.randint(10000,99999)}",
            "segment": seg,
            "sku": sku,
            "product": PRODUCT_MAP[sku]["name"],
            "line": PRODUCT_MAP[sku]["line"],
            "date": txdate.isoformat(),
            "month": month,
            "qty": qty,
            "revenue": round(price * qty, 2),
            "channel": random.choices(CHANNELS, weights=[5,3,2,2,1,1])[0],
            "region": random.choice(REGIONS),
            "weather": random.choice(WEATHERS),
        })
    return rows


def build_summary(txs):
    from collections import defaultdict
    seg_rev  = defaultdict(float)
    seg_cnt  = defaultdict(int)
    sku_rev  = defaultdict(float)
    sku_cnt  = defaultdict(int)
    mon_rev  = defaultdict(float)
    seg_mon  = defaultdict(lambda: defaultdict(float))
    seg_line = defaultdict(lambda: defaultdict(int))

    for t in txs:
        seg_rev[t["segment"]]  += t["revenue"]
        seg_cnt[t["segment"]]  += 1
        sku_rev[t["sku"]]      += t["revenue"]
        sku_cnt[t["sku"]]      += 1
        mon_rev[t["month"]]    += t["revenue"]
        seg_mon[t["segment"]][t["month"]] += t["revenue"]
        seg_line[t["segment"]][t["line"]] += 1

    lines = ["=== TRANSACTION SUMMARY (600 synthetic purchases, 2024–2025) ===\n"]
    lines.append("TOP SEGMENTS BY REVENUE:")
    for seg, rev in sorted(seg_rev.items(), key=lambda x: -x[1]):
        lines.append(f"  {seg}: €{rev:.0f} ({seg_cnt[seg]} orders, avg €{rev/seg_cnt[seg]:.2f})")

    lines.append("\nTOP SKUs BY REVENUE:")
    for sku, rev in sorted(sku_rev.items(), key=lambda x: -x[1])[:8]:
        p = PRODUCT_MAP[sku]
        lines.append(f"  {sku} {p['name']} ({p['line']}): €{rev:.0f} ({sku_cnt[sku]} orders)")

    lines.append("\nMONTHLY REVENUE PATTERN:")
    month_names = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    for m in range(1,13):
        bar = "█" * int(mon_rev[m]/50)
        lines.append(f"  {month_names[m]:>3}: €{mon_rev[m]:>6.0f} {bar}")

    lines.append("\nSEGMENT × PRODUCT LINE AFFINITY:")
    for seg, lines_d in seg_line.items():
        top = sorted(lines_d.items(), key=lambda x: -x[1])
        lines.append(f"  {seg}: {', '.join(f'{l}({c})' for l,c in top)}")

    lines.append("\nSEGMENT PEAK MONTHS:")
    for seg, months in seg_mon.items():
        top3 = sorted(months.items(), key=lambda x: -x[1])[:3]
        lines.append(f"  {seg}: peak in {', '.join(month_names[m] for m,_ in top3)}")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a customer analytics and marketing intelligence agent for Allgäuer Latschenkiefer (Dr. Theiss Naturwaren GmbH).

You receive a summary of customer transaction data including revenue by segment, SKU performance, monthly patterns, and segment-product affinities.

Your job:
1. RFM Analysis: identify high-value vs at-risk segments
2. Category Affinity: which segments buy feet vs legs vs muscles products
3. Seasonal Timing: best months to advertise each product line to each segment
4. Targeting Signals: produce 5-7 specific campaign recommendations (segment × SKU × best month × channel × message angle)
5. Sales Lift Opportunity: estimate which campaigns would have highest uplift

Respond ONLY with this JSON:
{
  "executive_summary": "3-4 sentences summarising the key findings",
  "top_segments": [
    {"segment": "string", "value_tier": "HIGH or MEDIUM or LOW", "revenue_share": "string e.g. 28%", "key_products": ["sku1","sku2"], "rfm_profile": "string e.g. Frequent buyers, high AOV"}
  ],
  "category_affinities": [
    {"segment": "string", "primary_line": "Feet or Legs or Muscles or Cough", "affinity_score": integer 0-100, "insight": "string"}
  ],
  "seasonal_peaks": [
    {"product_line": "string", "peak_months": ["Jan","Feb"], "recommended_campaign_start": "string e.g. 2 weeks before peak", "reasoning": "string"}
  ],
  "campaign_recommendations": [
    {
      "campaign_id": 1,
      "title": "string",
      "target_segment": "string",
      "hero_sku": "string - SKU code",
      "hero_product": "string - product name",
      "best_months": ["string"],
      "channel": "string",
      "message_angle": "string - what to say",
      "estimated_uplift": "string e.g. +18% revenue in segment",
      "priority": "HIGH or MEDIUM or LOW"
    }
  ],
  "untapped_opportunities": ["string opportunity 1", "string opportunity 2"],
  "measurement_plan": "How to measure campaign lift — treatment vs control approach"
}"""


def analyse(api_key: str, summary: str) -> dict:
    client = genai.Client(api_key=api_key)
    prompt = f"""ALLGÄUER LATSCHENKIEFER — CUSTOMER ANALYTICS DATA

PRODUCT CATALOG:
{chr(10).join(f"  {p['sku']} | {p['name']} | {p['line']} | €{p['price']} | Peak: {p['peak']} | Segment: {p['segment']}" for p in PRODUCTS)}

{summary}

Generate targeting signals, campaign recommendations, and RFM insights."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    raw = response.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    result = json.loads(raw)
    if isinstance(result, list):
        result = result[0] if result else {}
    return result


# ── Page ───────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="TargetIQ Analytics", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, html, body { font-family: 'Inter', sans-serif !important; }
.main { background: #f0f4f9 !important; }
.block-container { padding: 2rem 3rem !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }
.topbar {
  background: linear-gradient(120deg, #0f172a 0%, #0369a1 100%);
  padding: 26px 40px; display: flex; align-items: center; gap: 18px;
  border-radius: 16px; margin-bottom: 28px;
}
.topbar-title { color: white; font-size: 1.7rem; font-weight: 800; margin: 0; }
.topbar-sub   { color: rgba(255,255,255,0.75); font-size: 0.88rem; margin: 3px 0 0; }
.topbar-pill  {
  display: inline-block; background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3); color: rgba(255,255,255,0.9);
  padding: 3px 13px; border-radius: 999px; font-size: 0.77rem; margin-top: 7px;
}
.panel {
  background: white; border-radius: 16px; border: 1px solid #e2e8f0;
  box-shadow: 0 2px 10px rgba(0,0,0,0.06); padding: 24px; margin-bottom: 18px;
}
.panel-label {
  font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: #94a3b8; margin-bottom: 12px;
}
.stButton > button {
  background: linear-gradient(135deg, #0f172a, #0369a1) !important;
  color: white !important; border: none !important;
  border-radius: 10px !important; font-weight: 600 !important;
  font-size: 0.95rem !important; padding: 0.65rem !important;
  width: 100% !important; box-shadow: 0 2px 8px rgba(3,105,161,0.3) !important;
}
.stButton > button:disabled { opacity: 0.35 !important; }
.stTextInput > div > div > input {
  border-radius: 9px !important; border: 1.5px solid #dde3ee !important;
  font-size: 0.9rem !important; padding: 10px 14px !important; background: #f8faff !important;
}
.metric-card {
  background: white; border-radius: 14px; border: 1px solid #e2e8f0;
  padding: 18px 20px; text-align: center;
}
.metric-val { font-size: 1.8rem; font-weight: 800; color: #0369a1; }
.metric-lbl { font-size: 0.75rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }
.seg-card {
  background: white; border-radius: 12px; border: 1.5px solid #e2e8f0;
  padding: 16px 18px; margin-bottom: 10px; display: flex; align-items: flex-start; gap: 14px;
}
.tier-badge {
  padding: 4px 12px; border-radius: 999px; font-size: 0.72rem; font-weight: 700;
}
.tier-HIGH   { background:#f0fdf4; color:#166534; border:1px solid #86efac; }
.tier-MEDIUM { background:#fffbeb; color:#92400e; border:1px solid #fde68a; }
.tier-LOW    { background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; }
.campaign-card {
  background: white; border-radius: 14px; border: 1.5px solid #e2e8f0;
  padding: 20px 22px; margin-bottom: 12px;
}
.priority-HIGH   { border-left: 4px solid #16a34a !important; }
.priority-MEDIUM { border-left: 4px solid #f59e0b !important; }
.priority-LOW    { border-left: 4px solid #94a3b8 !important; }
.month-chip {
  display: inline-block; background: #eff6ff; color: #1d4ed8;
  border: 1px solid #bfdbfe; padding: 2px 9px; border-radius: 999px;
  font-size: 0.72rem; font-weight: 600; margin: 2px;
}
.bar-wrap { background: #e5e7eb; border-radius: 999px; height: 8px; margin: 4px 0; }
.exec-box {
  background: #f0f9ff; border-left: 4px solid #0369a1;
  border-radius: 0 12px 12px 0; padding: 14px 18px;
  font-size: 0.88rem; color: #0c4a6e; line-height: 1.65; margin-bottom: 20px;
}
.opp-item {
  background: #f8faff; border: 1px solid #dde3ee; border-radius: 8px;
  padding: 9px 14px; font-size: 0.84rem; color: #1e293b; margin-bottom: 6px;
}
.placeholder {
  background: white; border: 2px dashed #bae6fd; border-radius: 16px;
  padding: 64px 40px; text-align: center;
}
[data-testid="stDownloadButton"] > button {
  background: white !important; color: #0369a1 !important;
  border: 1.5px solid #bae6fd !important; border-radius: 10px !important;
  font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="topbar">
  <div style="font-size:2.4rem">📊</div>
  <div>
    <p class="topbar-title">TargetIQ Analytics</p>
    <p class="topbar-sub">Customer Targeting & Campaign Intelligence · Powered by Google Gemini AI</p>
    <span class="topbar-pill">Problem 7 — Allgäuer Latschenkiefer / Dr. Theiss Naturwaren GmbH, Homburg</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar-style left column ──────────────────────────────────────────────────
left, right = st.columns([0.85, 1.15], gap="large")

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">🔑 API Key</div>', unsafe_allow_html=True)
    api_key = st.text_input("key", type="password", value=api_key_env,
                            placeholder="AIza...", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # Dataset preview
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">📦 Product Catalog (15 SKUs)</div>', unsafe_allow_html=True)
    for p in PRODUCTS:
        st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f8fafc;font-size:0.8rem"><span style="color:#1e293b;font-weight:600">{p["name"]}</span><span style="color:#94a3b8">{p["line"]} · €{p["price"]}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">👥 Customer Segments</div>', unsafe_allow_html=True)
    for s in SEGMENTS:
        st.markdown(f'<div style="padding:5px 0;border-bottom:1px solid #f8fafc;font-size:0.82rem;color:#374151">· {s}</div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.75rem;color:#94a3b8;margin-top:10px">600 synthetic transactions · 2024–2025</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    go = st.button("📊  Run Analytics & Generate Campaigns", disabled=not api_key)

# ── Right: results ─────────────────────────────────────────────────────────────
with right:
    if go and api_key:
        with st.spinner("Generating transactions & running AI analysis…"):
            try:
                txs = generate_transactions(600)
                summary = build_summary(txs)
                r = analyse(api_key, summary)
                st.session_state["r7"] = r
                st.session_state["r7_txs"] = txs
            except Exception as e:
                st.error(f"Analysis failed: {e}")

    if "r7" in st.session_state:
        r = st.session_state["r7"]
        txs = st.session_state.get("r7_txs", [])

        # KPI row
        total_rev = sum(t["revenue"] for t in txs)
        total_orders = len(txs)
        aov = total_rev / total_orders if total_orders else 0
        top_seg = max(set(t["segment"] for t in txs), key=lambda s: sum(t["revenue"] for t in txs if t["segment"]==s))

        c1, c2, c3, c4 = st.columns(4)
        for col, val, lbl in [
            (c1, f"€{total_rev:,.0f}", "Total Revenue"),
            (c2, str(total_orders), "Transactions"),
            (c3, f"€{aov:.2f}", "Avg Order Value"),
            (c4, len(SEGMENTS), "Segments"),
        ]:
            with col:
                st.markdown(f'<div class="metric-card"><div class="metric-val">{val}</div><div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Executive summary
        if r.get("executive_summary"):
            st.markdown(f'<div class="exec-box">📋 <strong>Executive Summary</strong><br><br>{r["executive_summary"]}</div>', unsafe_allow_html=True)

        # Monthly revenue chart
        mon_rev = {}
        month_names = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        for t in txs:
            m = int(t["date"][5:7])
            mon_rev[m] = mon_rev.get(m, 0) + t["revenue"]

        st.markdown('<div class="panel-label">📅 Monthly Revenue Pattern</div>', unsafe_allow_html=True)
        max_rev = max(mon_rev.values()) if mon_rev else 1
        cols = st.columns(12)
        for i, col in enumerate(cols, 1):
            rev = mon_rev.get(i, 0)
            pct = int((rev / max_rev) * 100)
            bar_color = "#0369a1" if pct >= 70 else "#38bdf8" if pct >= 40 else "#bae6fd"
            with col:
                st.markdown(f"""
                <div style="text-align:center">
                  <div style="height:60px;display:flex;align-items:flex-end;justify-content:center">
                    <div style="width:20px;background:{bar_color};height:{pct}%;border-radius:4px 4px 0 0;min-height:4px"></div>
                  </div>
                  <div style="font-size:0.65rem;color:#94a3b8;font-weight:600">{month_names[i]}</div>
                  <div style="font-size:0.6rem;color:#64748b">€{rev:.0f}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Segment value tiers
        segs = r.get("top_segments", [])
        if segs:
            st.markdown('<div class="panel-label">👥 Segment Value Analysis</div>', unsafe_allow_html=True)
            for s in segs:
                tier = s.get("value_tier","MEDIUM")
                st.markdown(f"""
                <div class="seg-card">
                  <div style="flex:1">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
                      <span style="font-weight:700;font-size:0.92rem;color:#1e293b">{s.get('segment','')}</span>
                      <span class="tier-badge tier-{tier}">{tier} VALUE</span>
                      <span style="margin-left:auto;font-size:0.8rem;font-weight:700;color:#0369a1">{s.get('revenue_share','')}</span>
                    </div>
                    <div style="font-size:0.8rem;color:#64748b;margin-bottom:4px">{s.get('rfm_profile','')}</div>
                    <div style="font-size:0.78rem;color:#475569">Top products: {', '.join(s.get('key_products',[]))}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # Campaign recommendations
        campaigns = r.get("campaign_recommendations", [])
        if campaigns:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="panel-label">🎯 Campaign Recommendations</div>', unsafe_allow_html=True)
            for c in sorted(campaigns, key=lambda x: {"HIGH":0,"MEDIUM":1,"LOW":2}.get(x.get("priority","LOW"),1)):
                pri = c.get("priority","MEDIUM")
                pri_color = {"HIGH":"#16a34a","MEDIUM":"#f59e0b","LOW":"#94a3b8"}.get(pri,"#f59e0b")
                months_html = "".join(f'<span class="month-chip">{m}</span>' for m in c.get("best_months",[]))
                st.markdown(f"""
                <div class="campaign-card priority-{pri}">
                  <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px">
                    <div>
                      <div style="font-size:1rem;font-weight:800;color:#1e293b">{c.get('title','')}</div>
                      <div style="font-size:0.8rem;color:#64748b;margin-top:2px">🎯 {c.get('target_segment','')} · 📦 {c.get('hero_product','')} · 📱 {c.get('channel','')}</div>
                    </div>
                    <span style="background:{pri_color}18;color:{pri_color};border:1px solid {pri_color}44;padding:3px 10px;border-radius:999px;font-size:0.72rem;font-weight:700;white-space:nowrap">{pri}</span>
                  </div>
                  <div style="font-size:0.84rem;color:#374151;margin-bottom:8px;background:#f8fafc;border-radius:8px;padding:8px 12px">
                    💬 {c.get('message_angle','')}
                  </div>
                  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
                    <div>{months_html}</div>
                    <span style="font-size:0.8rem;font-weight:700;color:#16a34a;margin-left:auto">📈 {c.get('estimated_uplift','')}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # Untapped opportunities
        opps = r.get("untapped_opportunities", [])
        if opps:
            st.markdown('<div class="panel-label" style="margin-top:8px">💡 Untapped Opportunities</div>', unsafe_allow_html=True)
            for o in opps:
                st.markdown(f'<div class="opp-item">💡 {o}</div>', unsafe_allow_html=True)

        # Measurement plan
        if r.get("measurement_plan"):
            st.markdown(f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:12px 16px;font-size:0.84rem;color:#166534;margin-top:8px">📏 <strong>Measurement Plan:</strong> {r["measurement_plan"]}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        export = {"analysis": r, "transactions_sample": txs[:20]}
        st.download_button(
            label="📥  Download Analytics Report (JSON)",
            data=json.dumps(export, indent=2, ensure_ascii=False),
            file_name="customer_analytics_report.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        st.markdown("""
        <div class="placeholder">
          <div style="font-size:3.5rem;margin-bottom:14px">📊</div>
          <div style="font-size:1.05rem;font-weight:700;color:#374151;margin-bottom:8px">Ready to analyse</div>
          <div style="font-size:0.875rem;color:#94a3b8;max-width:340px;margin:0 auto;line-height:1.6">
            Click the button — the AI generates 600 synthetic customer transactions,
            finds behavioural patterns, and recommends the best campaigns to run.
          </div>
          <div style="margin-top:24px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
            <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">📊 RFM analysis</span>
            <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">🎯 Targeting signals</span>
            <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">📅 Seasonal peaks</span>
            <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">📈 Campaign uplift</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
