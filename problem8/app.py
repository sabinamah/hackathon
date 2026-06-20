import os, json
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key_env = os.getenv("GOOGLE_API_KEY", "")

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

SYSTEM_PROMPT = """You are a dynamic pricing engine for Allgäuer Latschenkiefer (Dr. Theiss Naturwaren GmbH), a German pharmacy health brand.

Rules:
- Base price is the anchor. You may adjust within ±12% maximum (pharmacy pricing / RPM rules)
- NEVER price-gouge health items — fairness floor: never below -12%, ceiling: never above +12%
- Each price change must have a logged rationale (auditability requirement)
- Consider: weather signals, seasonal events, sports fixtures, supply constraints, competitor activity

External signals you receive:
- Weather: affects demand (heat → leg/cooling products; cold → warming/bath products)
- Seasonal events: Christmas, Ramadan, Father's Day, sandal season (affects specific SKUs)
- Football fixtures: matchday → Mobil Eisspray / recovery products near venues
- Supply chain: shortages → margin protection (raise toward ceiling)
- Competitor pricing: undercut strategically or hold margin

For EACH product provided, output a pricing decision.

Respond ONLY with this JSON:
{
  "pricing_date": "string",
  "market_context": "2-3 sentence summary of current signals and their impact",
  "decisions": [
    {
      "sku": "string",
      "product_name": "string",
      "base_price": number,
      "recommended_price": number,
      "change_pct": number,
      "change_direction": "INCREASE or DECREASE or HOLD",
      "signal_drivers": ["signal1", "signal2"],
      "rationale": "one sentence audit log entry",
      "confidence": integer 0-100,
      "guardrail_applied": "string or null — any rule that capped the adjustment"
    }
  ],
  "top_opportunity": "string — which SKU has the best pricing opportunity today and why",
  "risk_flags": ["any pricing risks or ethical concerns to flag"],
  "audit_summary": "string — one paragraph suitable for compliance review"
}"""


def run_pricing(api_key: str, signals: dict, selected_skus: list) -> dict:
    client = genai.Client(api_key=api_key)
    products_text = "\n".join(
        f"  {p['sku']} | {p['name']} | Line: {p['line']} | Base price: €{p['price']} | Peak: {p['peak']} | Segment: {p['segment']}"
        for p in PRODUCTS if p["sku"] in selected_skus
    )
    prompt = f"""PRICING DATE: {signals['date']}

EXTERNAL SIGNALS:
- Weather: {signals['weather']} ({signals['temp']}°C)
- Season / Calendar event: {signals['season_event']}
- Football fixture today: {signals['football']}
- Supply chain status: {signals['supply']}
- Competitor activity: {signals['competitor']}
- Additional context: {signals['extra'] or 'None'}

PRODUCTS TO PRICE:
{products_text}

Generate pricing decisions for each product with full audit rationale."""
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
st.set_page_config(page_title="PriceSignal AI", page_icon="💹", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, html, body { font-family: 'Inter', sans-serif !important; }
.main { background: #f0f4f9 !important; }
.block-container { padding: 2rem 3rem !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }
.topbar {
  background: linear-gradient(120deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
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
  text-transform: uppercase; color: #94a3b8; margin-bottom: 10px;
}
.stButton > button {
  background: linear-gradient(135deg, #1a1a2e, #0f3460) !important;
  color: white !important; border: none !important; border-radius: 10px !important;
  font-weight: 600 !important; font-size: 0.95rem !important; padding: 0.65rem !important;
  width: 100% !important; box-shadow: 0 2px 8px rgba(15,52,96,0.4) !important;
}
.stButton > button:disabled { opacity: 0.35 !important; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {
  border-radius: 9px !important; border: 1.5px solid #dde3ee !important; background: #f8faff !important;
}
.price-card {
  background: white; border-radius: 14px; border: 1.5px solid #e2e8f0;
  padding: 16px 20px; margin-bottom: 10px; display: flex; align-items: center; gap: 16px;
}
.price-up   { border-left: 4px solid #16a34a !important; }
.price-down { border-left: 4px solid #2563eb !important; }
.price-hold { border-left: 4px solid #94a3b8 !important; }
.change-badge-up   { background:#f0fdf4; color:#166534; border:1px solid #86efac; }
.change-badge-down { background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; }
.change-badge-hold { background:#f8fafc; color:#64748b; border:1px solid #e2e8f0; }
.change-badge { display:inline-block; padding:3px 10px; border-radius:999px; font-size:0.78rem; font-weight:700; }
.signal-tag {
  display:inline-block; background:#faf5ff; color:#6d28d9;
  border:1px solid #ddd6fe; padding:2px 8px; border-radius:999px;
  font-size:0.71rem; font-weight:600; margin:2px;
}
.context-box {
  background:#f0f9ff; border-left:4px solid #0f3460;
  border-radius:0 12px 12px 0; padding:14px 18px;
  font-size:0.88rem; color:#0c4a6e; line-height:1.65; margin-bottom:18px;
}
.audit-box {
  background:#fafafa; border:1px solid #e2e8f0; border-radius:10px;
  padding:14px 18px; font-size:0.83rem; color:#374151; line-height:1.6;
}
.risk-tag {
  display:inline-block; background:#fef2f2; color:#b91c1c;
  border:1px solid #fecaca; padding:4px 12px; border-radius:999px;
  font-size:0.78rem; font-weight:600; margin:3px;
}
.placeholder {
  background:white; border:2px dashed #cbd5e1; border-radius:16px;
  padding:64px 40px; text-align:center;
}
[data-testid="stDownloadButton"] > button {
  background:white !important; color:#0f3460 !important;
  border:1.5px solid #cbd5e1 !important; border-radius:10px !important; font-weight:600 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="topbar">
  <div style="font-size:2.4rem">💹</div>
  <div>
    <p class="topbar-title">PriceSignal AI</p>
    <p class="topbar-sub">Signal-Driven Dynamic Pricing Engine · Pharmacy Guardrails · Powered by Google Gemini AI</p>
    <span class="topbar-pill">Problem 8 — Allgäuer Latschenkiefer / Dr. Theiss Naturwaren GmbH, Homburg</span>
  </div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 1.1], gap="large")

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">🔑 API Key</div>', unsafe_allow_html=True)
    api_key = st.text_input("key", type="password", value=api_key_env,
                            placeholder="AIza...", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">📅 Date & Weather Signals</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        pricing_date = st.date_input("Date", value=None, label_visibility="visible")
    with col2:
        temp = st.number_input("Temp (°C)", value=22, min_value=-10, max_value=42)
    weather = st.selectbox("Weather", ["sunny & warm","hot","cold & rainy","snowing","mild & cloudy","stormy"])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">📆 Seasonal & Event Signals</div>', unsafe_allow_html=True)
    season_event = st.selectbox("Calendar Event", [
        "No special event","Christmas / Weihnachten","New Year","Valentine's Day",
        "Easter / Ostern","Father's Day / Vatertag","Sandal season start (April)",
        "Summer holidays","Ramadan","Oktoberfest","Back-to-school","Halloween","Advent"
    ])
    football = st.selectbox("Football Fixture", [
        "No fixture today","Bundesliga matchday (local team)","Champions League tonight",
        "World Cup / Euro qualifier","DFB-Pokal match"
    ])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">⚠️ Supply & Competitor Signals</div>', unsafe_allow_html=True)
    supply = st.selectbox("Supply Chain Status", [
        "Normal — no issues","Minor shortage on Latschenkiefernöl",
        "Major shortage — key active low","Logistics delay (2-3 weeks)",
        "Oversupply — clear inventory"
    ])
    competitor = st.selectbox("Competitor Activity", [
        "No notable activity","Gehwol running 20% promo on foot care",
        "Scholl launched new device — stealing shelf space",
        "Kneipp heavy social campaign this week",
        "dm private label undercut by €1.50"
    ])
    extra = st.text_input("Extra context (optional)", placeholder="e.g. pharmacies in Bayern have 30% more foot traffic this week")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">📦 Select Products to Price</div>', unsafe_allow_html=True)
    all_skus = [p["sku"] for p in PRODUCTS]
    selected = st.multiselect(
        "skus", options=all_skus,
        default=["ALK-MG-03","ALK-LG-01","ALK-FB-02","ALK-MG-05","ALK-FB-06","ALK-MG-01"],
        format_func=lambda s: next(p["name"] for p in PRODUCTS if p["sku"]==s),
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    ready = bool(api_key and selected and pricing_date)
    go = st.button("💹  Run Pricing Engine", disabled=not ready)

with right:
    if go and ready:
        signals = {
            "date": str(pricing_date),
            "weather": weather,
            "temp": temp,
            "season_event": season_event,
            "football": football,
            "supply": supply,
            "competitor": competitor,
            "extra": extra,
        }
        with st.spinner("Analysing signals and computing optimal prices…"):
            try:
                r = run_pricing(api_key, signals, selected)
                st.session_state["r8"] = r
            except Exception as e:
                st.error(f"Pricing engine failed: {e}")

    if "r8" in st.session_state:
        r = st.session_state["r8"]

        # Context summary
        if r.get("market_context"):
            st.markdown(f'<div class="context-box">📡 <strong>Signal Analysis</strong><br><br>{r["market_context"]}</div>', unsafe_allow_html=True)

        # Top opportunity
        if r.get("top_opportunity"):
            st.markdown(f'<div style="background:#f0fdf4;border-left:4px solid #16a34a;border-radius:0 10px 10px 0;padding:12px 16px;font-size:0.88rem;color:#166534;margin-bottom:18px;line-height:1.5">🏆 <strong>Best Opportunity Today:</strong> {r["top_opportunity"]}</div>', unsafe_allow_html=True)

        # Price decisions
        decisions = r.get("decisions", [])
        if decisions:
            st.markdown('<div class="panel-label">💰 Pricing Decisions</div>', unsafe_allow_html=True)

            for d in decisions:
                direction = d.get("change_direction","HOLD")
                card_cls  = {"INCREASE":"price-up","DECREASE":"price-down","HOLD":"price-hold"}.get(direction,"price-hold")
                badge_cls = {"INCREASE":"change-badge-up","DECREASE":"change-badge-down","HOLD":"change-badge-hold"}.get(direction,"change-badge-hold")
                arrow     = {"INCREASE":"↑","DECREASE":"↓","HOLD":"→"}.get(direction,"→")
                base  = d.get("base_price", 0)
                new   = d.get("recommended_price", base)
                chg   = d.get("change_pct", 0)
                chg_str = f"{arrow} {abs(chg):.1f}%" if chg != 0 else "→ HOLD"
                signals_html = "".join(f'<span class="signal-tag">{s}</span>' for s in d.get("signal_drivers",[]))

                st.markdown(f"""
                <div class="price-card {card_cls}">
                  <div style="flex:1">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
                      <span style="font-weight:800;font-size:0.92rem;color:#1e293b">{d.get('product_name','')}</span>
                      <span style="font-size:0.72rem;color:#94a3b8">{d.get('sku','')}</span>
                      <span class="change-badge {badge_cls}" style="margin-left:auto">{chg_str}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                      <span style="font-size:0.85rem;color:#94a3b8;text-decoration:line-through">€{base:.2f}</span>
                      <span style="font-size:1.1rem;font-weight:800;color:#1e293b">€{new:.2f}</span>
                      <span style="font-size:0.75rem;color:#64748b">±12% band: €{base*0.88:.2f} – €{base*1.12:.2f}</span>
                    </div>
                    <div style="margin-bottom:6px">{signals_html}</div>
                    <div style="font-size:0.78rem;color:#64748b;font-style:italic">{d.get('rationale','')}</div>
                    {f'<div style="font-size:0.72rem;color:#f59e0b;margin-top:4px">⚠ Guardrail: {d["guardrail_applied"]}</div>' if d.get("guardrail_applied") else ""}
                  </div>
                  <div style="text-align:center;min-width:48px">
                    <div style="font-size:1rem;font-weight:800;color:{'#16a34a' if d.get('confidence',0)>=70 else '#f59e0b'}">{d.get('confidence',0)}%</div>
                    <div style="font-size:0.65rem;color:#94a3b8">conf.</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # Risk flags
        risks = r.get("risk_flags", [])
        if risks:
            st.markdown('<div class="panel-label" style="margin-top:8px">🚨 Risk Flags</div>', unsafe_allow_html=True)
            for risk in risks:
                st.markdown(f'<span class="risk-tag">⚠ {risk}</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # Audit summary
        if r.get("audit_summary"):
            st.markdown('<div class="panel-label">📋 Compliance Audit Log</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="audit-box">🔒 {r["audit_summary"]}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥  Download Pricing Report (JSON)",
            data=json.dumps(r, indent=2, ensure_ascii=False),
            file_name="dynamic_pricing_report.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        st.markdown("""
        <div class="placeholder">
          <div style="font-size:3.5rem;margin-bottom:14px">💹</div>
          <div style="font-size:1.05rem;font-weight:700;color:#374151;margin-bottom:8px">Configure signals to run pricing</div>
          <div style="font-size:0.875rem;color:#94a3b8;max-width:340px;margin:0 auto;line-height:1.6">
            Set the date, weather, seasonal events, and competitor activity —
            the AI adjusts prices within pharmacy guardrails with full audit log.
          </div>
          <div style="margin-top:24px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
            <span style="background:#f8fafc;color:#334155;border:1px solid #e2e8f0;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">🌤 Weather signals</span>
            <span style="background:#f8fafc;color:#334155;border:1px solid #e2e8f0;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">⚽ Sports fixtures</span>
            <span style="background:#f8fafc;color:#334155;border:1px solid #e2e8f0;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">📦 Supply chain</span>
            <span style="background:#f8fafc;color:#334155;border:1px solid #e2e8f0;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">🔒 ±12% guardrails</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
