import os, json
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key_env = os.getenv("GOOGLE_API_KEY", "")

SYSTEM_PROMPT = """You are a competitive intelligence analyst specializing in German OTC pharmacy and consumer health products.

You receive:
1. A company's own product portfolio (Allgäuer Latschenkiefer / Dr. Theiss)
2. Competitor products and positioning
3. Market context with need × format grid to analyse

Your method:
- Map both the company and competitors onto a NEED × FORMAT grid (needs: callus, dry skin, cold feet, heavy legs, spider veins, muscle pain, joint, recovery; formats: cream, gel, spray, bath, foam, balm, device, mask)
- Find cells where COMPETITORS ARE PRESENT but Allgäuer Latschenkiefer IS ABSENT → these are white-space gaps
- Rank gaps by: category size × margin potential × brand fit with natural/herbal positioning
- Recommend 5-8 concrete own-brand product ideas to fill those gaps
- Score each by market potential, entry difficulty, competitive risk

Respond ONLY with this JSON:
{
  "company_name": "string",
  "market_overview": "2-3 sentence summary of the competitive landscape",
  "competitor_strengths": [
    {"competitor": "string", "strong_areas": ["area1", "area2"], "threat_level": "HIGH or MEDIUM or LOW"}
  ],
  "white_space_gaps": [
    {
      "gap_id": 1,
      "gap_title": "string - short name for this gap",
      "description": "string - what is missing in the market",
      "target_audience": "string",
      "suggested_product": "string - concrete product idea",
      "market_potential": "HIGH or MEDIUM or LOW",
      "entry_difficulty": "EASY or MEDIUM or HARD",
      "competitive_risk": "LOW or MEDIUM or HIGH",
      "opportunity_score": integer 0-100
    }
  ],
  "top_recommendation": "string - the single best opportunity and why",
  "strategic_summary": "3-4 sentences of actionable strategic advice",
  "priority_actions": ["action1", "action2", "action3"]
}"""


def analyse(api_key: str, own_products: str, competitors: str, context: str) -> dict:
    client = genai.Client(api_key=api_key)
    prompt = f"""OWN PRODUCT PORTFOLIO:
{own_products}

COMPETITOR PRODUCTS & POSITIONING:
{competitors}

MARKET CONTEXT / TARGET CATEGORIES:
{context if context.strip() else "General consumer health and wellness products"}

Perform a full competitive gap analysis and identify white-space opportunities."""
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


# ── Presets ────────────────────────────────────────────────────────────────────
PRESET_OWN = """Company: Allgäuer Latschenkiefer (brand of Dr. Theiss Naturwaren GmbH, Homburg)
Hero ingredient: Allgäuer Latschenkiefernöl (dwarf mountain-pine oil)
Distribution: Pharmacies & pharmacy e-commerce, 60+ countries

FÜSSE (Foot care):
- Hornhaut Schälcreme (callus peeling cream)
- Hornhaut Reduziercreme Standard / extra stark / Multi-Aktiv / cremig (callus-reducing creams)
- Hornhaut Entferner Maske Plus (callus remover sock-mask)
- Hornhaut Reduzierer Fußpflegebad (callus foot bath)
- Fuß-Balsam wohlig & warm (warming foot balm, cold feet)
- Sole Fußbad (brine foot bath)
- Fuß Butter (rich foot butter, very dry feet)
- 10% Urea Fußcreme / Urea-Fußschaum / Urea-Cremegel (urea range)
- Schrunden Salbe / Schrunden Salbe Latschenkiefer-Orange (cracked-heel ointments)
- Fußpflege Deospray (foot deodorant spray)
- Fuß Balsam / Fuß Verwöhnbalsam (daily / pampering foot balms)

BEINE (Leg care):
- Bein Lotion (leg lotion, tired/heavy legs)
- 5 in 1 Beinlotion (multi-benefit leg lotion)
- Bein Balsam für die Nacht (overnight leg balm)
- Bein Frische Gel (refreshing leg gel)
- Bein Kühlbalsam (cooling leg balm)
- Besenreiser Pflegebalsam / Kältespray (spider-vein care balm / cold spray)

MUSKELN & GELENKE (Muscles & joints):
- Mobil Gel / Mobil Gel intensiv (muscle & joint gels)
- Mobil Einreibung Extra Stark (strong muscle rub)
- Mobil Latschenkiefer Gel (pine muscle gel)
- Arnika Einreibung / Arnika Vital Fluid (arnica rub / vital fluid)
- Mobil Eisspray akut (cold spray, acute)
- Schmerz Creme (pain cream)
- Mobil Schmerzfluid Franzbranntwein / Franzbranntwein (classic Franzbranntwein)
- Knie Spezialsalbe (knee special ointment)
- Kühlendes Aktiv Gel / Wärmendes Intensiv Gel (cooling/warming gels)
- Mobil Dusche klassik / Alpenglück Verwöhn-Dusche / Waldfrische Dusche (shower gels)

HUSTENBONBONS (Cough drops):
- Ur Bonbons (original cough drops)

Price range: €2.49 – €11.49
Target segments: Women 25–65, Active/Sport 25–55, Traditional 55+, Diabetic/dry skin"""

PRESET_COMPETITORS = """1. Gehwol (Eduard Gerlach)
Overlaps: Feet (premium)
Positioning: Professional/podiatry foot care — cream, balm, bath, foam formats
Strength: Strong in pharmacies, podiatrist-recommended, premium perception

2. Scholl (Reckitt)
Overlaps: Feet — mass market
Positioning: Mass-market foot care, devices (electric file), creams
Strength: High brand awareness, drugstore dominance, device category

3. Allpresan (Neubourg Skin Care)
Overlaps: Feet (urea foam)
Positioning: Foam-format dry/diabetic feet specialist — unique foam delivery
Strength: Owns the foam format for foot care, diabetic-foot niche

4. Kneipp (Kneipp GmbH)
Overlaps: Feet, legs, bath
Positioning: Natural wellness, herbal baths, gift sets, whole-body ritual
Strength: Strong in bath/wellness ritual, gifting, younger audiences

5. tetesept (Merz)
Overlaps: Feet, bath
Positioning: Drugstore wellness/bath — affordable, wide range
Strength: DM/Rossmann shelf dominance, affordable price point

6. Hansaplast Foot Expert (Beiersdorf)
Overlaps: Feet
Positioning: Mass-market, devices & creams — blister care, insoles
Strength: Mass awareness, device cross-sell, pharmacy + drugstore

7. Doppelherz (Queisser Pharma)
Overlaps: Legs (vein), joints
Positioning: Supplements + topicals — vein health, joint support
Strength: Trusted health brand, oral + topical, vein segment

8. Voltaren / proff (GSK / Dr. Theiss)
Overlaps: Muscles & joints
Positioning: OTC pain (diclofenac) — fast relief, clinical credibility
Strength: Doctor-recommended, strong pain positioning

9. Pernaton (Gattlen Tritec)
Overlaps: Joints
Positioning: Green-lipped mussel — natural joint supplement + topical
Strength: Niche but loyal, natural joint care

10. Retterspitz / Pferdesalbe brands (Various)
Overlaps: Muscles
Positioning: Traditional herbal rubs — cult following, mass recognition
Strength: Heritage trust, broad appeal, pharmacy + online"""

PRESET_CONTEXT = """Market: DACH (Germany, Austria, Switzerland)
Distribution: Pharmacies & pharmacy e-commerce (primary)

Categories to analyse (need × format grid):
NEEDS: callus removal, dry skin / cracked heels, cold feet/warming, heavy legs / tired legs, spider veins, muscle pain, joint pain, sport recovery
FORMATS: cream, gel, spray, bath, foam, balm, device, mask, supplement

White-space hypotheses from brief (validate, don't assume):
- Men-targeted recovery line (currently almost all SKUs target women 35+)
- Cooling sports-team sprays — compete vs Scholl/Hansaplast in sport/team context
- Subscription/refill for repeat foot-care SKUs
- Sustainability-forward / refill packaging
- Diabetic-foot specialist sub-brand (Allpresan owns foam but cream/balm gap exists)
- App/QR usage guidance for product routines

Goal: Surface cells in the need × format grid where competitors are present but Allgäuer Latschenkiefer is absent.
Rank opportunities by: category size × margin potential × brand fit with Latschenkiefernöl heritage."""


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="GapScout AI", page_icon="🔍", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, html, body { font-family: 'Inter', sans-serif !important; }
.main { background: #f0f4f9 !important; }
.block-container { padding: 2rem 3rem !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }

.topbar {
  background: linear-gradient(120deg, #4c1d95 0%, #7c3aed 100%);
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
  background: linear-gradient(135deg, #4c1d95, #7c3aed) !important;
  color: white !important; border: none !important;
  border-radius: 10px !important; font-weight: 600 !important;
  font-size: 0.95rem !important; padding: 0.65rem !important;
  width: 100% !important; box-shadow: 0 2px 8px rgba(124,58,237,0.3) !important;
}
.stButton > button:disabled { opacity: 0.35 !important; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
  border-radius: 9px !important; border: 1.5px solid #dde3ee !important;
  font-size: 0.85rem !important; background: #f8faff !important;
}
.gap-card {
  background: white; border-radius: 14px; border: 1.5px solid #e2e8f0;
  padding: 20px 22px; margin-bottom: 14px;
}
.gap-score-ring {
  width: 54px; height: 54px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 800; flex-shrink: 0;
}
.badge {
  display: inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: 0.72rem; font-weight: 700; margin: 2px;
}
.badge-green  { background:#f0fdf4; color:#166534; border:1px solid #86efac; }
.badge-yellow { background:#fffbeb; color:#92400e; border:1px solid #fde68a; }
.badge-red    { background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; }
.badge-blue   { background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; }
.badge-purple { background:#f5f3ff; color:#6d28d9; border:1px solid #ddd6fe; }
.rec-box {
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  border-left: 4px solid #7c3aed; border-radius: 0 12px 12px 0;
  padding: 16px 20px; font-size: 0.9rem; color:#4c1d95;
  line-height: 1.6; margin-bottom: 20px; font-weight: 500;
}
.overview-box {
  background: #fafafa; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 14px 18px; font-size: 0.88rem; color: #374151;
  line-height: 1.65; margin-bottom: 18px;
}
.threat-card {
  display: flex; align-items: flex-start; gap: 12px;
  background: white; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 12px 16px; margin-bottom: 8px;
}
.action-item {
  display: flex; align-items: flex-start; gap: 10px;
  background: #f8faff; border-radius: 8px; padding: 10px 14px; margin-bottom: 6px;
  font-size: 0.86rem; color: #1e293b;
}
.placeholder {
  background: white; border: 2px dashed #ddd6fe; border-radius: 16px;
  padding: 64px 40px; text-align: center;
}
[data-testid="stDownloadButton"] > button {
  background: white !important; color: #6d28d9 !important;
  border: 1.5px solid #ddd6fe !important; border-radius: 10px !important;
  font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="topbar">
  <div style="font-size:2.4rem">🔍</div>
  <div>
    <p class="topbar-title">GapScout AI</p>
    <p class="topbar-sub">Competitive Product-Gap Analysis · White-Space Intelligence · Powered by Google Gemini AI</p>
    <span class="topbar-pill">Problem 9 — Allgäuer Latschenkiefer / Dr. Theiss Naturwaren GmbH, Homburg</span>
  </div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 1.15], gap="large")

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">🔑 API Key</div>', unsafe_allow_html=True)
    api_key = st.text_input("key", type="password", value=api_key_env,
                            placeholder="AIza...", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    use_preset = st.checkbox("Use Dr. Theiss example data", value=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">🏢 Your Product Portfolio</div>', unsafe_allow_html=True)
    own_products = st.text_area("own", value=PRESET_OWN if use_preset else "",
                                height=220, label_visibility="collapsed",
                                placeholder="List your company name and all your current products with formats, sizes, price range, channels...")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">⚔️ Competitor Products</div>', unsafe_allow_html=True)
    competitors = st.text_area("comp", value=PRESET_COMPETITORS if use_preset else "",
                               height=260, label_visibility="collapsed",
                               placeholder="List competitors and their products, positioning, price range, strengths...")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">🎯 Market Context & Goals</div>', unsafe_allow_html=True)
    context = st.text_area("ctx", value=PRESET_CONTEXT if use_preset else "",
                           height=160, label_visibility="collapsed",
                           placeholder="Target market, trends, categories to focus on, goals...")
    st.markdown('</div>', unsafe_allow_html=True)

    ready = bool(api_key and own_products.strip() and competitors.strip())
    go = st.button("🔍  Run Gap Analysis", disabled=not ready)

with right:
    if go and ready:
        with st.spinner("Analysing competitive landscape and finding white-space gaps…"):
            try:
                r = analyse(api_key, own_products, competitors, context)
                st.session_state["r9"] = r
            except Exception as e:
                st.error(f"Analysis failed: {e}")

    if "r9" in st.session_state:
        r = st.session_state["r9"]

        # Market overview
        if r.get("market_overview"):
            st.markdown(f'<div class="overview-box">🌍 <strong>Market Overview</strong><br>{r["market_overview"]}</div>', unsafe_allow_html=True)

        # Top recommendation
        if r.get("top_recommendation"):
            st.markdown(f'<div class="rec-box">🏆 <strong>Top Opportunity:</strong> {r["top_recommendation"]}</div>', unsafe_allow_html=True)

        # Competitor threats
        threats = r.get("competitor_strengths", [])
        if threats:
            st.markdown('<div class="panel-label" style="margin-bottom:10px">⚔️ Competitor Threat Map</div>', unsafe_allow_html=True)
            for t in threats:
                lvl = t.get("threat_level", "MEDIUM")
                col = {"HIGH": "#b91c1c", "MEDIUM": "#92400e", "LOW": "#166534"}.get(lvl, "#92400e")
                bg  = {"HIGH": "#fef2f2", "MEDIUM": "#fffbeb", "LOW": "#f0fdf4"}.get(lvl, "#fffbeb")
                icon= {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(lvl, "🟡")
                areas = " · ".join(t.get("strong_areas", []))
                st.markdown(f"""
                <div class="threat-card">
                  <span style="font-size:1.3rem">{icon}</span>
                  <div style="flex:1">
                    <div style="font-weight:700;color:#1e293b;font-size:0.9rem">{t.get('competitor','')}</div>
                    <div style="font-size:0.8rem;color:#64748b;margin-top:2px">{areas}</div>
                  </div>
                  <span style="background:{bg};color:{col};border:1px solid {col}33;padding:3px 10px;border-radius:999px;font-size:0.72rem;font-weight:700">{lvl}</span>
                </div>
                """, unsafe_allow_html=True)

        # White space gaps
        gaps = r.get("white_space_gaps", [])
        if gaps:
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('<div class="panel-label" style="margin-bottom:12px">💡 White-Space Gaps & Opportunities</div>', unsafe_allow_html=True)

            pot_badge = {"HIGH": "badge-green", "MEDIUM": "badge-yellow", "LOW": "badge-red"}
            diff_badge = {"EASY": "badge-green", "MEDIUM": "badge-yellow", "HARD": "badge-red"}
            risk_badge = {"LOW": "badge-green", "MEDIUM": "badge-yellow", "HIGH": "badge-red"}

            for g in sorted(gaps, key=lambda x: -x.get("opportunity_score", 0)):
                score = g.get("opportunity_score", 0)
                ring_color = "#16a34a" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
                pot   = g.get("market_potential", "MEDIUM")
                diff  = g.get("entry_difficulty", "MEDIUM")
                risk  = g.get("competitive_risk", "MEDIUM")

                st.markdown(f"""
                <div class="gap-card">
                  <div style="display:flex;align-items:flex-start;gap:14px">
                    <div class="gap-score-ring" style="background:{ring_color}18;border:2.5px solid {ring_color};color:{ring_color}">
                      {score}
                    </div>
                    <div style="flex:1">
                      <div style="font-size:1rem;font-weight:800;color:#1e293b">{g.get('gap_title','')}</div>
                      <div style="font-size:0.8rem;color:#64748b;margin:3px 0 8px">{g.get('target_audience','')}</div>
                      <div style="font-size:0.84rem;color:#374151;margin-bottom:10px">{g.get('description','')}</div>
                      <div style="background:#f5f3ff;border-radius:8px;padding:8px 12px;font-size:0.83rem;color:#4c1d95;margin-bottom:10px">
                        💡 <strong>Product idea:</strong> {g.get('suggested_product','')}
                      </div>
                      <div>
                        <span class="badge {pot_badge.get(pot,'badge-yellow')}">📈 Potential: {pot}</span>
                        <span class="badge {diff_badge.get(diff,'badge-yellow')}">🚀 Entry: {diff}</span>
                        <span class="badge {risk_badge.get(risk,'badge-yellow')}">🛡 Risk: {risk}</span>
                      </div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # Strategic summary
        if r.get("strategic_summary"):
            st.markdown(f'<div class="overview-box" style="margin-top:8px">📊 <strong>Strategic Summary</strong><br>{r["strategic_summary"]}</div>', unsafe_allow_html=True)

        # Priority actions
        actions = r.get("priority_actions", [])
        if actions:
            st.markdown('<div class="panel-label" style="margin:12px 0 8px">✅ Priority Actions</div>', unsafe_allow_html=True)
            for i, a in enumerate(actions, 1):
                st.markdown(f'<div class="action-item"><span style="font-weight:800;color:#7c3aed;min-width:22px">{i}.</span>{a}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥  Download Gap Analysis Report (JSON)",
            data=json.dumps(r, indent=2, ensure_ascii=False),
            file_name="competitive_gap_analysis.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        st.markdown("""
        <div class="placeholder">
          <div style="font-size:3.5rem;margin-bottom:14px">🔍</div>
          <div style="font-size:1.05rem;font-weight:700;color:#374151;margin-bottom:8px">No analysis yet</div>
          <div style="font-size:0.875rem;color:#94a3b8;max-width:320px;margin:0 auto;line-height:1.6">
            Enter your product portfolio and competitor data — the AI finds white-space gaps
            and ranks opportunities by market potential.
          </div>
          <div style="margin-top:24px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
            <span style="background:#f5f3ff;color:#6d28d9;border:1px solid #ddd6fe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">💡 White-space gaps</span>
            <span style="background:#f5f3ff;color:#6d28d9;border:1px solid #ddd6fe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">🏆 Scored opportunities</span>
            <span style="background:#f5f3ff;color:#6d28d9;border:1px solid #ddd6fe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">⚔️ Threat map</span>
            <span style="background:#f5f3ff;color:#6d28d9;border:1px solid #ddd6fe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">✅ Action plan</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
