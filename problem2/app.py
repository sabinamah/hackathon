import os, json, io
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key_env = os.getenv("GOOGLE_API_KEY", "")

SYSTEM_PROMPT = """You are a smart shift replacement assistant for a German company.

You receive:
1. Info about a sick/absent employee (name, role, shift time, department, skills)
2. A list of available staff members with their details

Your job:
- Find the BEST replacement candidates from the available staff
- Consider: same role/skills, availability, not already working too many hours, willingness
- Rank top 3 candidates with explanation
- Suggest a contact message in German and English the manager can send

Respond ONLY with this JSON:
{
  "absent_employee": "string",
  "shift_summary": "string - brief description of the shift that needs covering",
  "top_candidates": [
    {
      "rank": 1,
      "name": "string",
      "role": "string",
      "match_score": integer 0-100,
      "reasons": ["reason1", "reason2"],
      "concerns": ["concern or empty list"],
      "contact_de": "German message the manager can send to this person",
      "contact_en": "English message the manager can send to this person"
    }
  ],
  "recommendation": "1-2 sentences on who to call first and why",
  "urgency": "LOW or MEDIUM or HIGH",
  "notes": "any additional advice for the manager or null"
}"""


def find_replacement(api_key: str, absent_info: str, staff_list: str, shift_details: str) -> dict:
    client = genai.Client(api_key=api_key)
    prompt = f"""ABSENT EMPLOYEE DETAILS:
{absent_info}

SHIFT TO COVER:
{shift_details}

AVAILABLE STAFF:
{staff_list}

Find the best replacement candidates."""
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
PRESET_ABSENT = """Name: Maria Schneider
Role: Cashier / Kassierer
Department: Checkout / Kasse
Shift: Today, 14:00 – 22:00 (8 hours)
Skills: POS system, customer service, cash handling, German & English
Reason for absence: Sick (called in at 11:30 AM)"""

PRESET_STAFF = """1. Thomas Becker | Role: Cashier | Dept: Checkout | Available today: YES | Hours this week: 28/40 | Skills: POS, cash handling, German | Phone: +49 151 1234 5678
2. Anna Müller | Role: Cashier | Dept: Checkout | Available today: YES | Hours this week: 35/40 | Skills: POS, customer service, German & French | Phone: +49 151 2345 6789
3. Klaus Weber | Role: Cashier Supervisor | Dept: Checkout | Available today: YES (afternoon) | Hours this week: 32/40 | Skills: POS, training, German & English | Phone: +49 151 3456 7890
4. Sophie Lang | Role: Shelf Stocker | Dept: Grocery | Available today: YES | Hours this week: 20/40 | Skills: Inventory, basic POS | Phone: +49 151 4567 8901
5. Felix Braun | Role: Cashier | Dept: Checkout | Available today: NO (already working 08:00–16:00) | Hours this week: 38/40 | Skills: POS, cash, German | Phone: +49 151 5678 9012
6. Laura Zimmermann | Role: Customer Service | Dept: Info Desk | Available today: YES | Hours this week: 30/40 | Skills: Customer service, POS, German & English | Phone: +49 151 6789 0123"""

PRESET_SHIFT = """Date: Today (Saturday)
Time: 14:00 – 22:00
Duration: 8 hours
Location: Globus Markt, St. Wendel – Checkout Zone B
Required skills: POS system operation, cash handling, customer service
Minimum experience: 6 months
Notice: Less than 3 hours before shift starts (HIGH URGENCY)"""


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="ShiftReplace AI", page_icon="🔄", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, html, body { font-family: 'Inter', sans-serif !important; }
.main { background: #f0f4f9 !important; }
.block-container { padding: 2rem 3rem !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }

.topbar {
  background: linear-gradient(120deg, #1e3a5f 0%, #2563eb 100%);
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
  background: linear-gradient(135deg, #1e3a5f, #2563eb) !important;
  color: white !important; border: none !important;
  border-radius: 10px !important; font-weight: 600 !important;
  font-size: 0.95rem !important; padding: 0.65rem !important;
  width: 100% !important; box-shadow: 0 2px 8px rgba(37,99,235,0.3) !important;
}
.stButton > button:disabled { opacity: 0.35 !important; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
  border-radius: 9px !important; border: 1.5px solid #dde3ee !important;
  font-size: 0.88rem !important; background: #f8faff !important;
}
.urgency-high   { background:#fef2f2; border:1px solid #fecaca; color:#b91c1c; }
.urgency-medium { background:#fffbeb; border:1px solid #fde68a; color:#92400e; }
.urgency-low    { background:#f0fdf4; border:1px solid #86efac; color:#166534; }
.urgency-badge  {
  display:inline-flex; align-items:center; gap:6px;
  padding:7px 18px; border-radius:999px; font-size:0.84rem; font-weight:700; margin-bottom:16px;
}
.candidate-card {
  border-radius: 14px; border: 1.5px solid #e2e8f0;
  padding: 20px 22px; margin-bottom: 14px; background: white;
}
.rank-badge {
  display:inline-flex; align-items:center; justify-content:center;
  width:32px; height:32px; border-radius:50%; font-weight:800; font-size:0.9rem;
  margin-right:10px;
}
.rank-1 { background:#fef9c3; color:#854d0e; }
.rank-2 { background:#f1f5f9; color:#475569; }
.rank-3 { background:#fdf4ff; color:#7e22ce; }
.score-bar-bg { background:#e5e7eb; border-radius:999px; height:8px; margin:4px 0 2px; }
.tag-green { display:inline-block; background:#f0fdf4; color:#166534; border:1px solid #86efac; padding:3px 10px; border-radius:999px; font-size:0.75rem; font-weight:600; margin:2px; }
.tag-red   { display:inline-block; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; padding:3px 10px; border-radius:999px; font-size:0.75rem; font-weight:600; margin:2px; }
.msg-box {
  background:#f8faff; border:1px solid #dde3ee; border-radius:10px;
  padding:12px 15px; font-size:0.83rem; color:#374151; line-height:1.6;
  white-space:pre-wrap; margin-top:8px;
}
.rec-box {
  background:#eff6ff; border-left:4px solid #2563eb;
  border-radius:0 10px 10px 0; padding:13px 17px;
  font-size:0.88rem; color:#1e3a5f; line-height:1.6; margin-bottom:18px;
}
.placeholder {
  background:white; border:2px dashed #bfdbfe; border-radius:16px;
  padding:64px 40px; text-align:center;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="topbar">
  <div style="font-size:2.4rem">🔄</div>
  <div>
    <p class="topbar-title">ShiftReplace AI</p>
    <p class="topbar-sub">Last-Minute Shift Replacement Assistant · Powered by Google Gemini AI</p>
    <span class="topbar-pill">Problem 2 — Globus Group, St. Wendel</span>
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

    use_preset = st.checkbox("Use example data (Globus Cashier scenario)", value=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">🤒 Absent Employee</div>', unsafe_allow_html=True)
    absent_info = st.text_area("absent", value=PRESET_ABSENT if use_preset else "",
                               height=160, label_visibility="collapsed",
                               placeholder="Name, role, department, skills, reason for absence...")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">⏰ Shift Details</div>', unsafe_allow_html=True)
    shift_details = st.text_area("shift", value=PRESET_SHIFT if use_preset else "",
                                 height=140, label_visibility="collapsed",
                                 placeholder="Date, time, duration, location, required skills...")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">👥 Available Staff (one per line)</div>', unsafe_allow_html=True)
    staff_list = st.text_area("staff", value=PRESET_STAFF if use_preset else "",
                              height=220, label_visibility="collapsed",
                              placeholder="Name | Role | Department | Available | Hours | Skills | Phone")
    st.markdown('</div>', unsafe_allow_html=True)

    ready = bool(api_key and absent_info.strip() and staff_list.strip() and shift_details.strip())
    go = st.button("🔍  Find Replacement", disabled=not ready)

with right:
    if go and ready:
        with st.spinner("Analyzing staff and finding best replacements…"):
            try:
                r = find_replacement(api_key, absent_info, staff_list, shift_details)
                st.session_state["r2"] = r
            except Exception as e:
                st.error(f"Failed: {e}")

    if "r2" in st.session_state:
        r = st.session_state["r2"]
        urgency = r.get("urgency", "MEDIUM")
        urgency_cfg = {
            "HIGH":   ("🚨 HIGH URGENCY", "urgency-high"),
            "MEDIUM": ("⚠️ MEDIUM URGENCY", "urgency-medium"),
            "LOW":    ("✅ LOW URGENCY", "urgency-low"),
        }.get(urgency, ("⚠️ MEDIUM URGENCY", "urgency-medium"))

        st.markdown(f'<div class="urgency-badge {urgency_cfg[1]}">{urgency_cfg[0]}</div>', unsafe_allow_html=True)

        if r.get("shift_summary"):
            st.markdown(f'<div style="font-size:0.95rem;font-weight:700;color:#1e293b;margin-bottom:4px">📋 {r["shift_summary"]}</div>', unsafe_allow_html=True)

        if r.get("recommendation"):
            st.markdown(f'<div class="rec-box">💡 {r["recommendation"]}</div>', unsafe_allow_html=True)

        st.markdown('<div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#94a3b8;margin-bottom:12px">🏆 TOP REPLACEMENT CANDIDATES</div>', unsafe_allow_html=True)

        rank_colors = {"1": "#2563eb", "2": "#64748b", "3": "#9333ea"}
        for c in r.get("top_candidates", []):
            rank = str(c.get("rank", 1))
            score = c.get("match_score", 0)
            bar_color = "#16a34a" if score >= 75 else "#f59e0b" if score >= 50 else "#ef4444"
            reasons = c.get("reasons", [])
            concerns = c.get("concerns", [])
            color = rank_colors.get(rank, "#64748b")

            st.markdown(f"""
            <div class="candidate-card">
              <div style="display:flex;align-items:center;margin-bottom:12px">
                <span class="rank-badge rank-{rank}" style="background:{color}22;color:{color}">#{rank}</span>
                <div>
                  <div style="font-size:1.05rem;font-weight:800;color:#1e293b">{c.get('name','')}</div>
                  <div style="font-size:0.82rem;color:#64748b">{c.get('role','')}</div>
                </div>
                <div style="margin-left:auto;text-align:right">
                  <div style="font-size:1.1rem;font-weight:800;color:{bar_color}">{score}%</div>
                  <div style="font-size:0.72rem;color:#94a3b8">match</div>
                </div>
              </div>
              <div class="score-bar-bg"><div style="background:{bar_color};width:{score}%;height:8px;border-radius:999px"></div></div>
              <div style="margin:10px 0 6px">
                {''.join(f'<span class="tag-green">✓ {r}</span>' for r in reasons)}
                {''.join(f'<span class="tag-red">⚠ {w}</span>' for w in concerns)}
              </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"📱 Contact message for {c.get('name','')}"):
                st.markdown("**🇩🇪 German:**")
                st.markdown(f'<div class="msg-box">{c.get("contact_de","")}</div>', unsafe_allow_html=True)
                st.markdown("**🇬🇧 English:**")
                st.markdown(f'<div class="msg-box">{c.get("contact_en","")}</div>', unsafe_allow_html=True)

        if r.get("notes"):
            st.markdown(f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;font-size:0.84rem;color:#475569;margin-top:8px">📝 {r["notes"]}</div>', unsafe_allow_html=True)

        st.download_button(
            label="📥  Download Replacement Report (JSON)",
            data=json.dumps(r, indent=2, ensure_ascii=False),
            file_name="shift_replacement_report.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        st.markdown("""
        <div class="placeholder">
          <div style="font-size:3.5rem;margin-bottom:14px">🔄</div>
          <div style="font-size:1.05rem;font-weight:700;color:#374151;margin-bottom:8px">No shift entered yet</div>
          <div style="font-size:0.875rem;color:#94a3b8;max-width:320px;margin:0 auto;line-height:1.6">
            Enter the absent employee details, shift info, and available staff —
            the AI finds your best replacement in seconds.
          </div>
          <div style="margin-top:24px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
            <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">⚡ Instant matching</span>
            <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">📱 Contact messages</span>
            <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">🏆 Top 3 ranked</span>
            <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">🇩🇪 DE &amp; EN</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
