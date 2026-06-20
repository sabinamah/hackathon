import os
import json
import base64
import io
import fitz
from PIL import Image
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key_env = os.getenv("GOOGLE_API_KEY", "")

SYSTEM_PROMPT = """You are an expert document authentication analyst for a European HR and staffing company.
Your job is to analyse any certificate, diploma, degree, license, or qualification document and assess its authenticity and validity.

Today's date is 2026-06-20.

You must handle any document type including:
- University degrees (Bachelor, Master, PhD, LL.M., M.A., M.Sc., etc.)
- Professional certificates (ISACA, TÜV, IHK, TQCert, AZWV, LinkedIn Learning, etc.)
- Government-issued licenses (EU transport, trade, operator licenses, etc.)
- Training completion certificates
- Language certificates (Goethe, IELTS, TOEFL, DELF, etc.)
- Any other qualification document

For each document analyse:
1. AUTHENTICITY — Does it look genuine? Check for: official logos, seals/stamps, signatures, registration numbers, proper formatting, consistent fonts, official letterhead
2. VALIDITY — Is it still valid today (2026-06-20)? Check expiry dates. If no expiry stated, mark as "No expiry stated"
3. CONTENT — Extract all key information accurately
4. RISK — Flag anything suspicious

Respond ONLY with this JSON — no text outside the JSON:
{
  "document_type": "e.g. Master Degree / Professional Certificate / EU License / Training Certificate",
  "issuing_institution": "full name of issuing body",
  "issuing_country": "country or null",
  "holder_name": "full name of certificate holder",
  "qualification_title": "exact title of the qualification or certificate",
  "issued_date": "DD.MM.YYYY or null",
  "expiry_date": "DD.MM.YYYY or 'No expiry stated' or null",
  "days_remaining": integer or null,
  "registration_number": "certificate or registration number if present or null",
  "authenticity_score": integer 0-100,
  "authenticity_verdict": "AUTHENTIC" or "LIKELY_AUTHENTIC" or "SUSPICIOUS" or "LIKELY_FAKE" or "CANNOT_DETERMINE",
  "validity_status": "VALID" or "EXPIRED" or "NO_EXPIRY" or "UNKNOWN",
  "authenticity_signals": ["list of positive authenticity indicators found"],
  "red_flags": ["list of suspicious or missing elements"],
  "additional_info": "grades, modules, specialisations or other key details, or null",
  "summary": "3-4 sentences in plain English for an HR manager who is not a document expert"
}

Scoring: 90-100 fully genuine, 70-89 likely genuine minor questions, 50-69 needs verification, below 50 suspicious.
Calculate days_remaining from 2026-06-20. Negative = expired."""


def pdf_to_images(pdf_bytes: bytes) -> list[bytes]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [page.get_pixmap(dpi=180).tobytes("png") for page in doc]


def image_file_to_bytes(uploaded_file) -> bytes:
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def analyse_document(api_key: str, image_bytes_list: list[bytes], filename: str) -> dict:
    client = genai.Client(api_key=api_key)
    parts = [types.Part.from_text(text=f"Filename: {filename}\n\nAuthenticate and validate this document.")]
    for img_bytes in image_bytes_list[:4]:
        mime = "image/png" if img_bytes[:4] == b"\x89PNG" else "image/jpeg"
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))
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


# ─── Page ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocVerify AI",
    page_icon="🔏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, html, body { font-family: 'Inter', sans-serif !important; }

/* Background */
.main, .block-container { background: #f0f4f9 !important; }
.block-container { padding: 2rem 3rem !important; max-width: 100% !important; }

/* Hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Topbar */
.topbar {
  background: linear-gradient(120deg, #0f2645 0%, #1e4d8c 100%);
  padding: 28px 56px 24px 56px;
  display: flex; align-items: center; gap: 20px;
  margin-bottom: 0;
}
.topbar-icon { font-size: 2.6rem; }
.topbar-title { color: white; font-size: 1.75rem; font-weight: 800; margin: 0; line-height: 1.2; }
.topbar-sub   { color: rgba(255,255,255,0.72); font-size: 0.88rem; margin: 4px 0 0 0; }
.topbar-pill  {
  display: inline-block; background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3); color: rgba(255,255,255,0.9);
  padding: 3px 14px; border-radius: 999px; font-size: 0.78rem;
  margin-top: 8px; font-weight: 500;
}

/* Content wrapper */
.content { padding: 36px 56px; }

/* Panel card */
.panel {
  background: white; border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
  padding: 32px 32px; height: 100%;
}
.panel-label {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: #94a3b8; margin-bottom: 14px;
}

/* Upload area */
[data-testid="stFileUploaderDropzone"] {
  background: #f8faff !important;
  border: 2px dashed #bdd0f0 !important;
  border-radius: 12px !important;
  padding: 20px !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] { color: #64748b !important; }

/* Primary button */
.stButton > button {
  background: linear-gradient(135deg, #0f2645, #1e4d8c) !important;
  color: white !important; border: none !important;
  border-radius: 10px !important; font-weight: 600 !important;
  font-size: 0.95rem !important; padding: 0.65rem 1.2rem !important;
  width: 100% !important; letter-spacing: 0.01em;
  box-shadow: 0 2px 8px rgba(15,38,69,0.3) !important;
  transition: all 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }
.stButton > button:disabled { opacity: 0.35 !important; }

/* Text input */
.stTextInput > div > div > input {
  border-radius: 9px !important;
  border: 1.5px solid #dde3ee !important;
  font-size: 0.9rem !important;
  padding: 10px 14px !important;
  background: #f8faff !important;
}
.stTextInput > label { color: #475569 !important; font-weight: 600 !important; font-size: 0.85rem !important; }

/* Success file confirm */
.file-ok {
  background: #f0fdf4; border: 1px solid #86efac;
  border-radius: 9px; padding: 10px 14px;
  font-size: 0.85rem; color: #166534; margin-top: 8px;
  display: flex; align-items: center; gap: 8px;
}

/* Verdict */
.verdict-wrap {
  border-radius: 14px; padding: 22px 24px;
  display: flex; align-items: center; gap: 22px;
  margin-bottom: 18px;
}
.score-circle {
  width: 80px; height: 80px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.55rem; font-weight: 800; color: white;
  flex-shrink: 0; box-shadow: 0 4px 14px rgba(0,0,0,0.2);
}
.verdict-label { font-size: 1.35rem; font-weight: 800; margin: 0; }
.verdict-sub   { font-size: 0.85rem; color: #64748b; margin: 5px 0 0 0; }

/* Summary box */
.summary-box {
  background: #f8faff; border-left: 4px solid #3b82f6;
  border-radius: 0 10px 10px 0;
  padding: 14px 18px; font-size: 0.9rem;
  color: #1e3a5f; line-height: 1.6; margin-bottom: 20px;
}

/* Detail grid */
.detail-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 0; border: 1px solid #f1f5f9; border-radius: 12px;
  overflow: hidden;
}
.detail-cell {
  padding: 11px 16px; border-bottom: 1px solid #f1f5f9;
  display: flex; flex-direction: column; gap: 2px;
}
.detail-cell:nth-child(odd)  { border-right: 1px solid #f1f5f9; background: #fafbff; }
.detail-cell:nth-child(even) { background: white; }
.detail-cell:nth-last-child(-n+2) { border-bottom: none; }
.dc-label { font-size: 0.72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.dc-value { font-size: 0.9rem; font-weight: 600; color: #1e293b; }

/* Tags */
.tag-green {
  display: inline-block; background: #dcfce7; color: #15803d;
  border: 1px solid #bbf7d0; padding: 4px 11px;
  border-radius: 999px; font-size: 0.78rem;
  font-weight: 500; margin: 3px 3px 3px 0;
}
.tag-red {
  display: inline-block; background: #fee2e2; color: #b91c1c;
  border: 1px solid #fecaca; padding: 4px 11px;
  border-radius: 999px; font-size: 0.78rem;
  font-weight: 500; margin: 3px 3px 3px 0;
}

/* Validity badge */
.vbadge {
  display: inline-block; padding: 4px 13px;
  border-radius: 999px; font-size: 0.8rem; font-weight: 700;
}
.vb-valid   { background: #dcfce7; color: #15803d; }
.vb-expired { background: #fee2e2; color: #b91c1c; }
.vb-noexp   { background: #dbeafe; color: #1d4ed8; }
.vb-unknown { background: #f1f5f9; color: #475569; }

/* Section heading inside result */
.sec-head {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: #94a3b8;
  margin: 20px 0 10px 0;
  display: flex; align-items: center; gap: 6px;
}

/* Placeholder */
.placeholder {
  background: white; border: 2px dashed #cbd5e1;
  border-radius: 16px; padding: 64px 40px;
  text-align: center; height: 100%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.ph-icon { font-size: 4rem; margin-bottom: 16px; }
.ph-title { font-size: 1.05rem; font-weight: 700; color: #475569; margin-bottom: 8px; }
.ph-sub   { font-size: 0.875rem; color: #94a3b8; max-width: 300px; line-height: 1.6; }
.ph-types {
  display: flex; gap: 20px; margin-top: 28px;
  flex-wrap: wrap; justify-content: center;
}
.ph-chip {
  background: #f1f5f9; border-radius: 999px;
  padding: 6px 16px; font-size: 0.8rem;
  color: #64748b; font-weight: 500;
}

/* Info checklist */
.checklist { list-style: none; padding: 0; margin: 0; }
.checklist li {
  padding: 9px 0; border-bottom: 1px solid #f1f5f9;
  font-size: 0.875rem; color: #374151;
  display: flex; align-items: flex-start; gap: 10px;
}
.checklist li:last-child { border-bottom: none; }
.cl-icon { font-size: 1rem; flex-shrink: 0; margin-top: 1px; }
.cl-bold { font-weight: 600; color: #1e293b; }

/* download btn override */
[data-testid="stDownloadButton"] > button {
  background: white !important;
  color: #1e3a5f !important;
  border: 1.5px solid #bdd0f0 !important;
  border-radius: 10px !important;
  font-weight: 600 !important; font-size: 0.88rem !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div class="topbar-icon">🔏</div>
  <div>
    <p class="topbar-title">DocVerify AI</p>
    <p class="topbar-sub">Certificate &amp; Document Authentication &nbsp;·&nbsp; Powered by Google Gemini AI</p>
    <span class="topbar-pill">Problem 4 — Persowerk Deutschland GmbH, Saarbrücken</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="content">', unsafe_allow_html=True)

left, right = st.columns([0.9, 1.1], gap="large")
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ─── LEFT PANEL ──────────────────────────────────────────────────────────────
with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    # API Key
    st.markdown('<div class="panel-label">🔑 API Configuration</div>', unsafe_allow_html=True)
    api_key = st.text_input(
        "Google AI API Key",
        type="password",
        value=api_key_env,
        placeholder="AIza...",
        label_visibility="collapsed",
    )
    st.markdown('<p style="font-size:0.76rem;color:#94a3b8;margin:-6px 0 20px 2px">Free key at <strong>aistudio.google.com/apikey</strong></p>', unsafe_allow_html=True)

    # Upload
    st.markdown('<div class="panel-label">📎 Upload Document</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "drop",
        type=["pdf", "jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )
    if uploaded:
        st.markdown(f'<div class="file-ok">✓ &nbsp;<strong>{uploaded.name}</strong> &nbsp;·&nbsp; {uploaded.size/1024:.1f} KB</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    go = st.button("🔍 &nbsp; Authenticate Document", disabled=not uploaded)

    # Divider
    st.markdown('<hr style="border:none;border-top:1px solid #f1f5f9;margin:24px 0">', unsafe_allow_html=True)

    # Checklist
    st.markdown('<div class="panel-label">✦ What DocVerify checks</div>', unsafe_allow_html=True)
    st.markdown("""
    <ul class="checklist">
      <li><span class="cl-icon">🎓</span><div><span class="cl-bold">University degrees</span><br>Bachelor, Master, PhD, LL.M., M.A., M.Sc.</div></li>
      <li><span class="cl-icon">📜</span><div><span class="cl-bold">Professional certificates</span><br>ISACA, TÜV, IHK, TQCert, AZWV, LinkedIn Learning</div></li>
      <li><span class="cl-icon">🪪</span><div><span class="cl-bold">Government licenses</span><br>EU transport, trade, operator licenses</div></li>
      <li><span class="cl-icon">🌍</span><div><span class="cl-bold">Language certificates</span><br>Goethe, IELTS, TOEFL, DELF, Cambridge</div></li>
      <li><span class="cl-icon">📋</span><div><span class="cl-bold">Training completions</span><br>Any course or qualification document</div></li>
    </ul>
    <p style="font-size:0.76rem;color:#94a3b8;margin:16px 0 0 0">
      Supports <strong>PDF · JPG · PNG · WebP</strong> &nbsp;·&nbsp; Any language &nbsp;·&nbsp; Any country
    </p>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # /panel

# ─── RIGHT PANEL ─────────────────────────────────────────────────────────────
with right:

    if go and uploaded:
        if not api_key:
            st.error("Please enter your Google API key.")
        else:
            with st.spinner("Authenticating document with AI…"):
                try:
                    ext = uploaded.name.rsplit(".", 1)[-1].lower()
                    imgs = pdf_to_images(uploaded.read()) if ext == "pdf" else [image_file_to_bytes(uploaded)]
                    result = analyse_document(api_key, imgs, uploaded.name)
                    st.session_state["r4"] = result
                    st.session_state["r4fn"] = uploaded.name
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

    if "r4" in st.session_state:
        r = st.session_state["r4"]

        verdict = r.get("authenticity_verdict", "CANNOT_DETERMINE")
        score   = r.get("authenticity_score", 0)
        vs      = r.get("validity_status", "UNKNOWN")

        vcfg = {
            "AUTHENTIC":        ("#ecfdf5","#10b981","#065f46","✅","Authentic"),
            "LIKELY_AUTHENTIC": ("#f0fdf4","#34d399","#065f46","✅","Likely Authentic"),
            "SUSPICIOUS":       ("#fff7ed","#f59e0b","#92400e","⚠️","Suspicious — Verify Manually"),
            "LIKELY_FAKE":      ("#fef2f2","#ef4444","#991b1b","❌","Likely Fraudulent"),
            "CANNOT_DETERMINE": ("#f8fafc","#94a3b8","#334155","❓","Cannot Determine"),
        }
        vbg, vring, vtxt, vicon, vlabel = vcfg.get(verdict, vcfg["CANNOT_DETERMINE"])

        # ── Verdict banner ──
        st.markdown(f"""
        <div class="verdict-wrap" style="background:{vbg}">
          <div class="score-circle" style="background:{vring}">{score}</div>
          <div>
            <p class="verdict-label" style="color:{vtxt}">{vicon} {vlabel}</p>
            <p class="verdict-sub">{r.get('document_type','Document')} &nbsp;·&nbsp; Authenticity score: <strong>{score}/100</strong></p>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Summary ──
        if r.get("summary"):
            st.markdown(f'<div class="summary-box">{r["summary"]}</div>', unsafe_allow_html=True)

        # ── Detail grid ──
        days = r.get("days_remaining")
        days_html = ""
        if days is not None:
            c = "#15803d" if days > 60 else "#b45309" if days > 0 else "#b91c1c"
            days_html = f" <span style='color:{c};font-size:0.8rem'>({days} days)</span>"

        vb_cls  = {"VALID":"vb-valid","EXPIRED":"vb-expired","NO_EXPIRY":"vb-noexp"}.get(vs,"vb-unknown")
        vb_text = {"VALID":"✅ Valid","EXPIRED":"⏰ Expired","NO_EXPIRY":"∞ No Expiry","UNKNOWN":"❓ Unknown"}.get(vs,vs)

        def cell(label, value):
            return f'<div class="detail-cell"><span class="dc-label">{label}</span><span class="dc-value">{value or "—"}</span></div>'

        st.markdown('<div class="sec-head">📋 Document Details</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="detail-grid">
          {cell("Holder", r.get("holder_name"))}
          {cell("Document Type", r.get("document_type"))}
          {cell("Qualification", r.get("qualification_title"))}
          {cell("Issued by", r.get("issuing_institution"))}
          {cell("Country", r.get("issuing_country"))}
          {cell("Reg. / Cert. No.", r.get("registration_number"))}
          {cell("Issue Date", r.get("issued_date"))}
          <div class="detail-cell">
            <span class="dc-label">Expiry</span>
            <span class="dc-value">{r.get("expiry_date") or "—"}{days_html}</span>
          </div>
          <div class="detail-cell" style="grid-column:span 2">
            <span class="dc-label">Validity Status</span>
            <span class="dc-value"><span class="vbadge {vb_cls}">{vb_text}</span></span>
          </div>
        </div>
        {f'<p style="font-size:0.83rem;color:#475569;margin:10px 4px 0">{r["additional_info"]}</p>' if r.get("additional_info") else ""}
        """, unsafe_allow_html=True)

        # ── Signals + Red Flags ──
        signals = r.get("authenticity_signals", [])
        flags   = r.get("red_flags", [])

        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown('<div class="sec-head">🔐 Authenticity Signals</div>', unsafe_allow_html=True)
            if signals:
                st.markdown("".join(f'<span class="tag-green">✓ {s}</span>' for s in signals), unsafe_allow_html=True)
            else:
                st.markdown('<span style="color:#94a3b8;font-size:0.85rem">None detected</span>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="sec-head">🚩 Red Flags</div>', unsafe_allow_html=True)
            if flags:
                st.markdown("".join(f'<span class="tag-red">⚠ {f}</span>' for f in flags), unsafe_allow_html=True)
            else:
                st.markdown('<span style="color:#94a3b8;font-size:0.85rem">None detected</span>', unsafe_allow_html=True)

        # ── Download ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥  Download Full Report (JSON)",
            data=json.dumps(r, indent=2, ensure_ascii=False),
            file_name=f"docverify_{st.session_state.get('r4fn','report')}.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        st.markdown("""
        <div class="placeholder">
          <div class="ph-icon">🔏</div>
          <div class="ph-title">Ready to authenticate</div>
          <div class="ph-sub">
            Upload any certificate, diploma, degree or license on the left
            to get an instant AI-powered authenticity report.
          </div>
          <div class="ph-types">
            <span class="ph-chip">🎓 Degrees</span>
            <span class="ph-chip">📜 Certificates</span>
            <span class="ph-chip">🪪 Licenses</span>
            <span class="ph-chip">🌍 Any Language</span>
            <span class="ph-chip">📋 Any Country</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # /content
