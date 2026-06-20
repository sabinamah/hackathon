import os, json, time, tempfile
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key_env = os.getenv("GOOGLE_API_KEY", "")

HERO_SKUS = [
    {"sku":"ALK-MG-01","name":"Mobil Gel","angle":"post-workout recovery, sport"},
    {"sku":"ALK-MG-03","name":"Mobil Eisspray akut","angle":"instant cold relief, athletes"},
    {"sku":"ALK-LG-01","name":"5 in 1 Beinlotion","angle":"summer legs, women after long day"},
    {"sku":"ALK-FB-02","name":"Sole Fußbad","angle":"winter wellness ritual, relaxation"},
    {"sku":"ALK-FB-01","name":"Fuß Butter","angle":"intense care, very dry feet"},
    {"sku":"ALK-FB-04","name":"Hornhaut Entferner Maske","angle":"before/after transformation, sandal season"},
    {"sku":"ALK-MG-05","name":"Wärmendes Intensiv Gel","angle":"tension & back pain, warming relief"},
    {"sku":"ALK-LG-03","name":"Besenreiser Pflegebalsam","angle":"spider vein care, women 40+"},
]

CONTENT_ANGLES = [
    "Ritual / ASMR (satisfying sounds, slow pour, texture)","Post-workout recovery (15-sec sport hook)",
    "Relatable hook: heavy legs after a long shift","Before / after transformation",
    "Ingredient origin story (Allgäu plantation → bottle)","Morning routine integration",
    "User testimonial / real person feel","Educational: how to use correctly",
]

PLATFORMS = ["TikTok + Instagram Reels (9:16, 1080×1920)","Instagram Reels only","TikTok only","YouTube Shorts"]

SYSTEM_PROMPT = """You are a senior social media content director and filmmaker specialising in German pharmacy/health brands.

You create complete video production briefs for short-form vertical reels for Allgäuer Latschenkiefer (Dr. Theiss Naturwaren GmbH).

CONTENT RULES — MANDATORY:
- EVERY shot must feature the specific product (packaging, texture, application, or result)
- Do NOT invent unrelated lifestyle scenes — no coffee shops, jungles, unrelated food, random outdoor sports unless directly tied to the product's use case
- The product is the HERO in every single shot — it must appear visually in at least 80% of shots
- Scenes must be realistic and achievable: bathroom, bedroom, kitchen counter, gym bag, outdoor trail (only for sport gels), sofa, balcony
- Concepts must directly connect to the product's purpose (e.g. foot cream → feet, leg lotion → legs, sport gel → post-workout)
- Do NOT use abstract or surreal concepts that have nothing to do with skincare or the product

SAFE ZONE SPECS for 1080×1920 (9:16):
- TOP safe zone: keep text/logo 140px from top (TikTok profile area)
- BOTTOM safe zone: keep 480–600px from bottom (caption bar + CTA buttons)
- RIGHT safe zone: keep 120–180px from right edge (action icons: like/comment/share)
- LEFT safe zone: ~40px from left
- MESSAGE-SAFE BAND: approximately y=140 to y=1320 (centre band is the prime creative area)

LEGAL GUARDRAILS (Heilmittelwerbegesetz / HWG):
- These are COSMETICS, not drugs — NO medical cure claims
- Say "pflegt" (cares for) not "heilt" (heals)
- Say "unterstützt" (supports) not "behandelt" (treats)
- No clinical efficacy claims without substantiation
- Allowed: sensory descriptions, ingredient origin, ritual feel, user experience

Produce a complete, production-ready video brief with shot-by-shot breakdown.

Respond ONLY with this JSON:
{
  "product": "string",
  "platform": "string",
  "content_angle": "string",
  "video_title": "string — attention-grabbing title",
  "hook_line": "string — first 1-2 seconds, must stop the scroll",
  "duration_seconds": integer,
  "caption": "string — full social media caption with hashtags (German + English mix)",
  "hashtags": ["#tag1","#tag2"],
  "music_vibe": "string — describe the music mood/tempo",
  "safe_zone_note": "string — reminder of where NOT to place overlays",
  "shots": [
    {
      "shot_number": 1,
      "timestamp": "0:00–0:03",
      "description": "string — what the camera shows",
      "text_overlay": "string or null — text on screen (must be in safe zone)",
      "overlay_position": "string or null — e.g. centre-screen, top-safe-zone",
      "voiceover": "string or null",
      "direction": "string — cinematography note (angle, movement, light)"
    }
  ],
  "cta": "string — call to action at end",
  "hwg_compliance_check": ["list of compliance points verified"],
  "production_tips": ["tip1","tip2","tip3"]
}"""


def generate_brief(api_key: str, product: str, angle: str, platform: str, duration: int, language: str, extra: str) -> dict:
    client = genai.Client(api_key=api_key)
    prompt = f"""Create a complete video production brief for:

PRODUCT: {product}
CONTENT ANGLE: {angle}
PLATFORM: {platform}
TARGET DURATION: {duration} seconds
LANGUAGE: {language}
ADDITIONAL NOTES: {extra or 'None'}

Brand: Allgäuer Latschenkiefer — natural, premium, Made in Germany, hero ingredient: Latschenkiefernöl (dwarf mountain-pine oil)

Generate a full shot-by-shot production brief respecting safe zones and HWG compliance."""
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


def _poll_operation(client, operation, max_wait=180):
    for _ in range(max_wait // 5):
        if operation.done:
            break
        time.sleep(5)
        operation = client.operations.get(operation)
    return operation


def generate_video(api_key: str, brief: dict, duration: int) -> list[bytes]:
    """Generate video clip(s) using Google Veo 2.
    Veo 2 hard limit is 8 seconds per clip.
    For durations > 8s we generate multiple 8s clips (one per ~8s chunk).
    Returns list of MP4 bytes (one per clip).
    """
    client = genai.Client(api_key=api_key)
    product = brief.get("product", "Allgäuer Latschenkiefer product")
    angle = brief.get("content_angle", "")
    hook = brief.get("hook_line", "")
    shots = brief.get("shots", [])
    music = brief.get("music_vibe", "")

    # Build a highly specific prompt from the brief's actual shot descriptions
    shot_descs = [s.get("description", "") for s in shots if s.get("description")]
    shot_text = ". ".join(shot_descs[:4])

    base_prompt = (
        f"Vertical 9:16 social media reel for '{product}' — a German natural cosmetics product. "
        f"Content angle: {angle}. "
        f"Opening hook: {hook}. "
        f"Shots: {shot_text}. "
        f"Music mood: {music}. "
        f"The PRODUCT PACKAGING must be visible and featured prominently. "
        f"Cinematic slow-motion close-ups of the product texture and application. "
        f"Soft warm natural lighting. Real skin textures. Alpine / Made-in-Germany feel. "
        f"No text overlays, no graphics. Professional cosmetics advertisement style."
    )

    # Veo 2 max per clip = 8s; calculate how many clips to generate
    clip_duration = 8
    num_clips = max(1, round(duration / clip_duration))

    results = []
    for i in range(num_clips):
        # Slightly vary each clip prompt to get different shots
        clip_prompt = base_prompt
        if i == 0:
            clip_prompt += " Opening scene — product reveal and hook moment."
        elif i == num_clips - 1:
            clip_prompt += " Closing scene — product held up, satisfied expression, call-to-action feel."
        else:
            clip_prompt += f" Middle scene {i} — product application, texture detail, result."
        try:
            op = client.models.generate_videos(
                model="veo-2.0-generate-001",
                prompt=clip_prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    duration_seconds=clip_duration,
                    number_of_videos=1,
                ),
            )
            op = _poll_operation(client, op)
            if op.done and op.response and op.response.generated_videos:
                video_bytes = client.files.download(file=op.response.generated_videos[0].video)
                results.append(bytes(video_bytes))
        except Exception:
            pass

    return results


# ── Page ───────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="ReelDirector AI", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, html, body { font-family: 'Inter', sans-serif !important; color: #1e293b !important; }
.main { background: #f0f4f9 !important; }
.block-container { padding: 2rem 3rem !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }
.topbar {
  background: white;
  border: 1.5px solid #e2e8f0; padding: 20px 32px; display: flex; align-items: center; gap: 18px;
  border-radius: 16px; margin-bottom: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.topbar-title { color: #0f172a; font-size: 1.7rem; font-weight: 800; margin: 0; }
.topbar-sub   { color: #64748b; font-size: 0.88rem; margin: 3px 0 0; }
.topbar-pill  {
  display: inline-block; background: #fff7ed;
  border: 1px solid #fed7aa; color: #9a3412;
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
  background: linear-gradient(135deg, #e65c00, #f59e0b) !important;
  color: white !important; border: none !important; border-radius: 10px !important;
  font-weight: 700 !important; font-size: 0.95rem !important; padding: 0.65rem !important;
  width: 100% !important;
}
.stButton > button:disabled { opacity: 0.35 !important; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
  border-radius: 9px !important; border: 1.5px solid #dde3ee !important;
  background: #f8faff !important; color: #1e293b !important;
}

/* Phone mockup */
.phone-frame {
  width: 200px; height: 355px; background: #1a1a2e; border-radius: 24px;
  border: 3px solid #334155; position: relative; overflow: hidden;
  margin: 0 auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.phone-screen { width:100%; height:100%; background:#0f172a; position:relative; }
.safe-top    { position:absolute; top:0; left:0; right:0; height:14%; background:rgba(239,68,68,0.2); border-bottom:1px dashed #ef4444; }
.safe-bottom { position:absolute; bottom:0; left:0; right:0; height:27%; background:rgba(239,68,68,0.2); border-top:1px dashed #ef4444; }
.safe-right  { position:absolute; top:0; right:0; bottom:0; width:13%; background:rgba(245,158,11,0.15); border-left:1px dashed #f59e0b; }
.safe-left   { position:absolute; top:0; left:0; bottom:0; width:4%; background:rgba(245,158,11,0.08); }
.safe-zone   { position:absolute; top:15%; left:5%; right:14%; bottom:28%; border:2px dashed #22c55e; border-radius:4px; display:flex;align-items:center;justify-content:center; }
.safe-label  { color:#22c55e; font-size:0.45rem; font-weight:700; text-align:center; }

.shot-card {
  background: #f8faff; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 16px 18px; margin-bottom: 10px; border-left: 3px solid #e65c00;
}
.overlay-badge {
  display:inline-block; background:#fff7ed; color:#9a3412;
  border:1px solid #fed7aa; padding:2px 8px; border-radius:4px;
  font-size:0.72rem; font-family:monospace; margin-top:4px;
}
.compliance-item {
  display:flex; align-items:flex-start; gap:8px;
  color:#166534; font-size:0.82rem; padding:4px 0;
}
.caption-box {
  background:#f8faff; border:1px solid #e2e8f0; border-radius:10px;
  padding:14px 16px; font-size:0.84rem; color:#1e293b;
  white-space:pre-wrap; line-height:1.65;
}
.hook-box {
  background: linear-gradient(135deg,#fff7ed,#fef3c7);
  border:1px solid #fed7aa; border-radius:10px;
  padding:14px 18px; font-size:1rem; font-weight:700;
  color:#9a3412; text-align:center; margin-bottom:16px;
}
[data-testid="stDownloadButton"] > button {
  background: white !important; color: #e65c00 !important;
  border: 1.5px solid #fed7aa !important; border-radius: 10px !important; font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="topbar">
  <div style="font-size:2.4rem">🎬</div>
  <div>
    <p class="topbar-title">ReelDirector AI</p>
    <p class="topbar-sub">Studio-Quality Reel Production Brief · TikTok & Instagram Safe Zones · HWG Compliant</p>
    <span class="topbar-pill">Problem 6 — Allgäuer Latschenkiefer / Dr. Theiss Naturwaren GmbH</span>
  </div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 1.1], gap="large")

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label" style="color:#666">🔑 API Key</div>', unsafe_allow_html=True)
    api_key = st.text_input("key", type="password", value=api_key_env,
                            placeholder="AIza...", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label" style="color:#666">📦 Hero Product</div>', unsafe_allow_html=True)
    sku_labels = {f"{p['name']} ({p['sku']})": p for p in HERO_SKUS}
    selected_label = st.selectbox("product", list(sku_labels.keys()), label_visibility="collapsed")
    selected_product = sku_labels[selected_label]
    st.markdown(f'<div style="font-size:0.78rem;color:#666;margin-top:4px">💡 Suggested angle: {selected_product["angle"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label" style="color:#666">🎭 Content</div>', unsafe_allow_html=True)
    angle = st.selectbox("angle", CONTENT_ANGLES, label_visibility="collapsed")
    platform = st.selectbox("platform", PLATFORMS, label_visibility="collapsed")
    col1, col2 = st.columns(2)
    with col1:
        duration = st.selectbox("Duration", [15, 30, 45, 60], index=1, label_visibility="visible")
    with col2:
        language = st.selectbox("Script language", ["English","German","German + English mix"], label_visibility="visible")
    extra = st.text_area("Extra notes", height=70, label_visibility="visible",
                         placeholder="e.g. target women 35–50, show product texture close-up, alpine scenery...")
    st.markdown('</div>', unsafe_allow_html=True)

    # Safe zone visual
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label" style="color:#666">📱 Safe Zone Map (1080×1920)</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="phone-frame">
      <div class="phone-screen">
        <div class="safe-top"><span style="color:#ef4444;font-size:0.38rem;padding:2px 4px;font-weight:700">⛔ DANGER ZONE — Profile/UI (140px)</span></div>
        <div class="safe-bottom"><span style="color:#ef4444;font-size:0.38rem;padding:2px 4px;font-weight:700">⛔ DANGER ZONE — Caption/CTA (480–600px)</span></div>
        <div class="safe-right"><span style="color:#f59e0b;font-size:0.35rem;writing-mode:vertical-rl;padding:4px 2px;font-weight:700">⚠ Icons</span></div>
        <div class="safe-zone"><div class="safe-label">✅ MESSAGE<br>SAFE BAND<br><br>Place all text<br>& overlays here</div></div>
      </div>
    </div>
    <div style="margin-top:10px;font-size:0.75rem;color:#666;line-height:1.6">
      <span style="color:#ef4444">■</span> Top 140px — avoid (profile pic/name)<br>
      <span style="color:#ef4444">■</span> Bottom 480–600px — avoid (caption/CTA bar)<br>
      <span style="color:#f59e0b">■</span> Right 120–180px — avoid (like/share icons)<br>
      <span style="color:#22c55e">■</span> Centre band — prime creative area
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    ready = bool(api_key)
    go = st.button("🎬  Generate Production Brief", disabled=not ready)

with right:
    if go and ready:
        with st.spinner("Directing your reel…"):
            try:
                product_str = f"{selected_product['name']} — {selected_product['angle']}"
                r = generate_brief(api_key, product_str, angle, platform, duration, language, extra)
                st.session_state["r6"] = r
            except Exception as e:
                st.error(f"Generation failed: {e}")

    if "r6" in st.session_state:
        r = st.session_state["r6"]

        # Hook
        st.markdown(f'<div class="hook-box">🎯 SCROLL-STOPPER HOOK<br><br>"{r.get("hook_line","")}"</div>', unsafe_allow_html=True)

        # Meta row
        c1, c2, c3 = st.columns(3)
        for col, lbl, val in [
            (c1, "Product", r.get("product","")),
            (c2, "Duration", f"{r.get('duration_seconds',30)}s"),
            (c3, "Music vibe", r.get("music_vibe",""))
        ]:
            with col:
                st.markdown(f'<div style="background:white;border:1.5px solid #e2e8f0;border-radius:10px;padding:10px 14px;text-align:center"><div style="font-size:0.65rem;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.05em">{lbl}</div><div style="font-size:0.85rem;font-weight:700;color:#e65c00;margin-top:4px">{val}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Shot list
        shots = r.get("shots", [])
        if shots:
            st.markdown('<div class="panel-label" style="color:#666">🎥 Shot-by-Shot Breakdown</div>', unsafe_allow_html=True)
            for shot in shots:
                overlay_html = f'<div class="overlay-badge">📝 "{shot["text_overlay"]}" → {shot.get("overlay_position","centre")}</div>' if shot.get("text_overlay") else ""
                vo_html = f'<div style="font-size:0.78rem;color:#64748b;margin-top:4px;font-style:italic">🎙 {shot["voiceover"]}</div>' if shot.get("voiceover") else ""
                st.markdown(f"""
                <div class="shot-card">
                  <div style="display:flex;gap:12px;align-items:flex-start">
                    <div style="background:#f59e0b;color:black;border-radius:6px;padding:4px 8px;font-size:0.78rem;font-weight:800;min-width:36px;text-align:center">#{shot.get('shot_number',1)}</div>
                    <div style="flex:1">
                      <div style="font-size:0.72rem;color:#666;margin-bottom:3px">{shot.get('timestamp','')}</div>
                      <div style="font-size:0.86rem;color:#1e293b;font-weight:600">{shot.get('description','')}</div>
                      <div style="font-size:0.78rem;color:#64748b;margin-top:3px">🎬 {shot.get('direction','')}</div>
                      {overlay_html}
                      {vo_html}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # CTA
        if r.get("cta"):
            st.markdown(f'<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px 16px;font-size:0.88rem;color:#9a3412;margin:8px 0"><strong>📣 CTA:</strong> {r["cta"]}</div>', unsafe_allow_html=True)

        # Caption
        if r.get("caption"):
            st.markdown('<div class="panel-label" style="color:#666;margin-top:12px">📝 Social Caption</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="caption-box">{r["caption"]}</div>', unsafe_allow_html=True)

        # HWG compliance
        compliance = r.get("hwg_compliance_check", [])
        if compliance:
            st.markdown('<div class="panel-label" style="color:#666;margin-top:12px">⚖️ HWG Compliance Check</div>', unsafe_allow_html=True)
            for item in compliance:
                st.markdown(f'<div class="compliance-item">✅ {item}</div>', unsafe_allow_html=True)

        # Safe zone note
        if r.get("safe_zone_note"):
            st.markdown(f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:12px 16px;font-size:0.82rem;color:#166534;margin-top:8px">📱 <strong>Safe Zone Reminder:</strong> {r["safe_zone_note"]}</div>', unsafe_allow_html=True)

        # Production tips
        tips = r.get("production_tips", [])
        if tips:
            st.markdown('<div class="panel-label" style="color:#666;margin-top:12px">💡 Production Tips</div>', unsafe_allow_html=True)
            for tip in tips:
                st.markdown(f'<div style="background:#f8faff;border-radius:8px;padding:8px 14px;font-size:0.82rem;color:#374151;margin-bottom:5px">· {tip}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Video generation ──────────────────────────────────────────────────
        st.markdown('<div class="panel-label" style="color:#666;margin-bottom:10px">🎬 Generate Video Clips (Google Veo 2)</div>', unsafe_allow_html=True)
        num_clips = max(1, round(duration / 8))
        st.markdown(f'<div style="background:#f8faff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;font-size:0.8rem;color:#64748b;margin-bottom:12px">⚠️ <strong>Google Veo 2 API limit: max 8 seconds per clip.</strong> For your {duration}s reel, this will generate <strong>{num_clips} clip{"s" if num_clips>1 else ""} × 8s</strong> — each matched to a different part of the brief. Each clip takes ~2–3 min.</div>', unsafe_allow_html=True)

        if st.button("🎥  Generate Video Clips with Veo", use_container_width=True):
            with st.spinner(f"Generating {num_clips} clip(s) with Veo 2… ~{num_clips*2}–{num_clips*3} minutes total ⏳"):
                clips = generate_video(api_key, r, duration)
            if clips:
                st.session_state["r6_clips"] = clips
                st.success(f"✅ {len(clips)} clip(s) generated!")
            else:
                st.warning("⚠️ Video generation failed or Veo API access not available on your key.")

        if "r6_clips" in st.session_state:
            clips = st.session_state["r6_clips"]
            for idx, clip_bytes in enumerate(clips):
                st.markdown(f'<div style="font-size:0.78rem;font-weight:700;color:#64748b;margin:10px 0 4px">Clip {idx+1} of {len(clips)}</div>', unsafe_allow_html=True)
                # Constrain video width so it's not full-screen
                col_vid, col_spacer = st.columns([1, 2])
                with col_vid:
                    st.video(clip_bytes)
                st.download_button(
                    label=f"📥  Download Clip {idx+1} (MP4)",
                    data=clip_bytes,
                    file_name=f"reel_{r.get('product','product').replace(' ','_')}_clip{idx+1}.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                    key=f"dl_clip_{idx}",
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥  Download Production Brief (JSON)",
            data=json.dumps(r, indent=2, ensure_ascii=False),
            file_name=f"reel_brief_{r.get('product','product').replace(' ','_')}.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        st.markdown("""
        <div style="background:white;border:1.5px solid #e2e8f0;border-radius:16px;padding:48px 32px;text-align:center">
          <div style="font-size:3.5rem;margin-bottom:14px">🎬</div>
          <div style="font-size:1.05rem;font-weight:700;color:#1e293b;margin-bottom:8px">Select a product & angle</div>
          <div style="font-size:0.875rem;color:#64748b;max-width:320px;margin:0 auto;line-height:1.6">
            Generate a complete shot-by-shot production brief for TikTok & Instagram reels,
            with safe zones and HWG compliance built in.
          </div>
          <div style="margin-top:24px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
            <span style="background:#fff7ed;color:#9a3412;border:1px solid #fed7aa;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">🎥 Shot breakdown</span>
            <span style="background:#f0f9ff;color:#0369a1;border:1px solid #bae6fd;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">📱 Safe zones</span>
            <span style="background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">⚖️ HWG compliant</span>
            <span style="background:#faf5ff;color:#6b21a8;border:1px solid #e9d5ff;padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600">📝 Caption + hashtags</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
