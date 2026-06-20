import os
import json
import base64
import fitz
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key_env = os.getenv("GOOGLE_API_KEY", "")

SYSTEM_PROMPT = """You are an expert document analyst for a German staffing agency.
Your task is to determine whether the uploaded document authorizes the holder to work in Germany RIGHT NOW.

Today's date is 2026-06-20.

A document is VALID for work if ALL three are true:
1. It is a German residence/work permit (Aufenthaltstitel, Blaue Karte EU, Niederlassungserlaubnis, etc.)
2. The expiry date (Gültig bis) is after 2026-06-20
3. Employment is explicitly PERMITTED ("Erwerbstätigkeit gestattet" / "Beschäftigung gestattet")

Mark EXPIRED if it was a valid work permit but the date has passed.
Mark INVALID if employment is not permitted (e.g. student visa §16b with "nicht gestattet") or if it is the wrong document type entirely.

Respond ONLY with this exact JSON — no markdown, no explanation outside the JSON:
{
  "is_work_permit": true or false,
  "confidence_percent": 0-100,
  "verdict": "VALID" or "INVALID" or "EXPIRED" or "UNCERTAIN",
  "verdict_reason": "one clear sentence",
  "holder_name": "string or null",
  "permit_type": "string or null",
  "legal_basis": "string or null",
  "issuing_authority": "string or null",
  "valid_from": "DD.MM.YYYY or null",
  "valid_until": "DD.MM.YYYY or null",
  "days_remaining": integer or null,
  "nationality": "string or null",
  "employment_permitted": true or false or null,
  "employment_note": "exact text from remarks section or null",
  "red_flags": ["array of strings"],
  "summary": "2-3 sentences in plain English for a non-expert HR person"
}

Calculate days_remaining from 2026-06-20 to valid_until. Use negative number if expired."""


def extract_pdf(pdf_bytes: bytes) -> tuple[str, list]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    images = []
    for page in doc:
        text += page.get_text()
        pix = page.get_pixmap(dpi=150)
        images.append(base64.standard_b64encode(pix.tobytes("png")).decode())
    return text, images


def validate_permit(api_key: str, pdf_bytes: bytes, filename: str) -> dict:
    text, images = extract_pdf(pdf_bytes)
    client = genai.Client(api_key=api_key)
    parts = [types.Part.from_text(
        text=f"Filename: {filename}\n\nExtracted text:\n{text}\n\nValidate this document."
    )]
    for img_b64 in images[:3]:
        parts.append(types.Part.from_bytes(data=base64.b64decode(img_b64), mime_type="image/png"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    raw = response.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    return json.loads(raw)


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Work Permit Validator", page_icon="🇩🇪", layout="wide")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main { background-color: #f8f9fb; }
  .block-container { padding-top: 2rem; max-width: 1100px; }
  h1 { color: #1a1a2e; font-size: 2rem !important; }
  .stButton > button {
    background-color: #1a3c6e; color: white;
    border-radius: 8px; font-size: 1rem;
    padding: 0.6rem 1.2rem; border: none;
  }
  .stButton > button:hover { background-color: #14305a; }
  .verdict-box {
    padding: 20px 24px; border-radius: 12px;
    margin-bottom: 16px; font-size: 1.1rem;
  }
  .detail-card {
    background: white; border-radius: 12px;
    padding: 20px 24px; margin-top: 12px;
    border: 1px solid #e0e4ea;
  }
  .detail-row {
    display: flex; justify-content: space-between;
    padding: 8px 0; border-bottom: 1px solid #f0f0f0;
    font-size: 0.95rem;
  }
  .detail-label { color: #666; font-weight: 500; }
  .detail-value { color: #1a1a2e; font-weight: 600; text-align: right; }
  .flag-item {
    background: #fff8e1; border-left: 4px solid #f0a500;
    padding: 8px 14px; border-radius: 6px; margin: 6px 0;
    font-size: 0.9rem; color: #5a4000;
  }
  .info-box {
    background: #eef3fb; border-radius: 10px;
    padding: 18px 22px; border: 1px solid #c8d8f0;
    font-size: 0.95rem; color: #2c3e6b;
  }
  .step-chip {
    display: inline-block; background: #1a3c6e; color: white;
    border-radius: 50%; width: 26px; height: 26px;
    text-align: center; line-height: 26px;
    font-weight: bold; margin-right: 8px; font-size: 0.85rem;
  }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:16px;margin-bottom:8px">
  <div style="font-size:2.8rem">🇩🇪</div>
  <div>
    <h1 style="margin:0;font-size:1.9rem;color:#1a1a2e">Work Permit Validation Agent</h1>
    <p style="margin:0;color:#666;font-size:0.95rem">
      Instantly verify any German residence or work permit — valid, expired, or restricted.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

left, right = st.columns([1, 1], gap="large")

# ── Left panel ────────────────────────────────────────────────────────────────
with left:
    st.markdown("### Upload & Validate")

    api_key = st.text_input(
        "Google API Key",
        type="password",
        value=api_key_env,
        placeholder="Paste your Google AI API key here",
        help="Free key at aistudio.google.com/apikey",
    )

    uploaded = st.file_uploader(
        "Upload permit document (PDF)",
        type=["pdf"],
        help="Works with any German Aufenthaltstitel, Blaue Karte EU, or residence permit PDF",
    )

    if uploaded:
        st.markdown(f"""
        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:10px 14px;font-size:0.9rem;color:#166534">
          ✓ <strong>{uploaded.name}</strong> &nbsp;·&nbsp; {uploaded.size/1024:.1f} KB ready
        </div>""", unsafe_allow_html=True)

    st.markdown("")
    validate_btn = st.button("🔍 &nbsp; Validate Permit", type="primary", use_container_width=True, disabled=not uploaded)

    st.markdown("---")
    st.markdown("""
    <div class="info-box">
      <strong>How it works</strong><br><br>
      <span class="step-chip">1</span> Upload any German work or residence permit PDF<br><br>
      <span class="step-chip">2</span> AI reads and analyses the document<br><br>
      <span class="step-chip">3</span> Get an instant verdict with full details<br><br>
      <strong>What it checks:</strong><br>
      ✅ &nbsp;Is it a valid German permit?<br>
      📅 &nbsp;Has it expired?<br>
      👷 &nbsp;Is employment actually permitted?<br>
      🚩 &nbsp;Any restrictions or red flags?<br><br>
      <em style="font-size:0.85rem;color:#4a5f8a">
        Works on any German Aufenthaltstitel, Blaue Karte EU, Niederlassungserlaubnis,
        or similar document — not limited to specific templates.
      </em>
    </div>
    """, unsafe_allow_html=True)

# ── Right panel ───────────────────────────────────────────────────────────────
with right:
    st.markdown("### Validation Result")

    if validate_btn and uploaded:
        if not api_key:
            st.error("Please enter your Google API key.")
        else:
            with st.spinner("Reading document and analysing with AI..."):
                try:
                    result = validate_permit(api_key, uploaded.read(), uploaded.name)
                    st.session_state["result"] = result
                    st.session_state["filename"] = uploaded.name
                except Exception as e:
                    st.error(f"Something went wrong: {e}")

    if "result" in st.session_state:
        r = st.session_state["result"]
        verdict = r.get("verdict", "UNCERTAIN")
        confidence = r.get("confidence_percent", 0)

        # Verdict banner
        cfg = {
            "VALID":     ("#d1fae5", "#065f46", "#10b981", "✅", "Employment Permitted"),
            "EXPIRED":   ("#fef3c7", "#92400e", "#f59e0b", "⏰", "Permit Expired"),
            "INVALID":   ("#fee2e2", "#991b1b", "#ef4444", "❌", "Not Valid for Work"),
            "UNCERTAIN": ("#f3f4f6", "#374151", "#9ca3af", "❓", "Could Not Determine"),
        }
        bg, text_c, border_c, icon, label = cfg.get(verdict, cfg["UNCERTAIN"])
        st.markdown(f"""
        <div style="background:{bg};border-left:6px solid {border_c};border-radius:10px;padding:18px 22px;margin-bottom:16px">
          <div style="font-size:2rem;display:inline">{icon}</div>
          <span style="font-size:1.5rem;font-weight:700;color:{text_c};margin-left:10px">{verdict}</span>
          <span style="font-size:0.95rem;color:{text_c};margin-left:8px;opacity:0.8">— {label}</span>
        </div>""", unsafe_allow_html=True)

        # Confidence bar
        bar_color = "#10b981" if confidence >= 75 else "#f59e0b" if confidence >= 50 else "#ef4444"
        st.markdown(f"""
        <div style="margin-bottom:4px;font-size:0.85rem;color:#666">AI Confidence</div>
        <div style="background:#e5e7eb;border-radius:999px;height:18px;margin-bottom:14px">
          <div style="background:{bar_color};width:{confidence}%;height:18px;border-radius:999px;
               text-align:center;color:white;font-size:12px;font-weight:600;line-height:18px">
            {confidence}%
          </div>
        </div>""", unsafe_allow_html=True)

        if r.get("verdict_reason"):
            st.markdown(f"<div style='color:#444;font-size:0.95rem;margin-bottom:12px'>📋 {r['verdict_reason']}</div>", unsafe_allow_html=True)

        if r.get("summary"):
            st.info(r["summary"])

        # Details card
        days = r.get("days_remaining")
        days_color = "#10b981" if days and days > 60 else "#f59e0b" if days and days > 0 else "#ef4444"
        days_str = f"<span style='color:{days_color};font-weight:700'>{days} days</span>" if days is not None else "—"
        emp = r.get("employment_permitted")
        emp_str = "✅ Yes" if emp is True else "❌ No" if emp is False else "—"

        fields = [
            ("Holder Name",       r.get("holder_name")),
            ("Nationality",       r.get("nationality")),
            ("Permit Type",       r.get("permit_type")),
            ("Legal Basis",       r.get("legal_basis")),
            ("Issuing Authority", r.get("issuing_authority")),
            ("Valid From",        r.get("valid_from")),
            ("Valid Until",       r.get("valid_until")),
            ("Days Remaining",    days_str if days is not None else None),
            ("Employment",        emp_str),
            ("Restrictions",      r.get("employment_note")),
        ]

        rows_html = "".join(
            f'<div class="detail-row"><span class="detail-label">{lbl}</span>'
            f'<span class="detail-value">{val}</span></div>'
            for lbl, val in fields if val
        )
        st.markdown(f'<div class="detail-card">{rows_html}</div>', unsafe_allow_html=True)

        # Red flags
        flags = r.get("red_flags", [])
        if flags:
            st.markdown("<br>**🚩 Red Flags**", unsafe_allow_html=True)
            for f in flags:
                st.markdown(f'<div class="flag-item">⚠️ {f}</div>', unsafe_allow_html=True)

        # Download
        st.markdown("")
        st.download_button(
            label="📥 Download Full Report (JSON)",
            data=json.dumps(r, indent=2, ensure_ascii=False),
            file_name=f"permit_check_{st.session_state.get('filename','report')}.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        st.markdown("""
        <div style="background:#f8f9fb;border:2px dashed #d1d5db;border-radius:12px;
             padding:48px 32px;text-align:center;color:#9ca3af;margin-top:16px">
          <div style="font-size:3rem;margin-bottom:12px">📄</div>
          <div style="font-size:1rem;font-weight:600;color:#6b7280">No document uploaded yet</div>
          <div style="font-size:0.875rem;margin-top:6px">
            Upload a PDF on the left to get an instant validation result
          </div>
        </div>""", unsafe_allow_html=True)
