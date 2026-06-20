import os
import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

api_key_env = os.getenv("GOOGLE_API_KEY", "")

# ── Preset job descriptions from the hackathon test inputs ──────────────────

JOB_DESCRIPTIONS = {
    "Hiring Manager — People & Talent (MONA AI)": """
Role: Hiring Manager — People & Talent
Company: MONA AI GmbH — applied AI agents for enterprise
Location: Saarbrücken (hybrid, 2–3 days on-site)
Team: People & Talent · reports to Head of People
Type: Full-time, permanent

About the role:
We're hiring across engineering, GTM and operations and need a Hiring Manager who can run structured, fair
and fast processes. You'll partner with technical and commercial leads, design scorecards, and protect
candidate experience while keeping time-to-hire low.

What you'll do:
- Run full-cycle recruiting: intake, sourcing strategy, screening, scheduling, offer and close.
- Design structured interview kits and scorecards with hiring leads; standardise rubrics.
- Own the ATS, pipeline hygiene and weekly hiring metrics (funnel, time-to-fill, pass-through).
- Coach interviewers on bias-aware, competency-based interviewing.
- Manage employer-branding basics and an inclusive, GDPR-compliant candidate experience.

Must-have qualifications:
- 3+ years in-house recruiting or talent acquisition, ideally in tech/startups.
- Track record closing roles across functions (technical and non-technical).
- Hands-on with an ATS (e.g. Greenhouse, Personio, Join) and structured interviewing.
- Fluent German and English; strong written communication.
- Working knowledge of German labour-law basics and GDPR in recruiting.

Nice to have:
- Experience hiring AI/ML or data talent.
- Familiarity with competency frameworks and work-sample assessments.
- Comfort building simple hiring dashboards.

Tools & stack: Personio / Join ATS · LinkedIn Recruiter · structured-interview scorecards · spreadsheet or BI for funnel metrics · German employment-law & GDPR knowledge.

Success (first 6 months): A documented, repeatable interview process per function; median time-to-hire down; interviewer scorecard adoption above 80%; positive candidate-experience feedback.
""",
    "Go-to-Market (GTM) Engineer (MONA AI)": """
Role: Go-to-Market (GTM) Engineer
Company: MONA AI GmbH — applied AI agents for enterprise
Location: Saarbrücken / remote (EU time zones)
Team: Revenue · works across Sales, Marketing & Product
Type: Full-time, permanent

About the role:
A hybrid technical-commercial role. You'll automate the GTM motion end-to-end: enrich and route leads,
build outbound and lifecycle workflows, wire the data between CRM and product, and ship internal tools
(often AI-assisted) that make the revenue team faster.

What you'll do:
- Design and maintain lead enrichment, scoring and routing pipelines.
- Build outbound/lifecycle automations and integrations across CRM, product and billing data.
- Develop internal tools and lightweight apps (incl. LLM-powered workflows) for sales & CS.
- Instrument the funnel: event tracking, attribution, and revenue dashboards.
- Run experiments on messaging, sequencing and conversion; report what actually moves pipeline.

Must-have qualifications:
- 2+ years in GTM/RevOps/sales-engineering or software engineering touching go-to-market.
- Strong with APIs, webhooks and scripting (Python or JavaScript/TypeScript).
- Hands-on CRM automation (HubSpot or Salesforce) and data plumbing (SQL).
- Comfortable building with LLM APIs and prompt-based workflows.
- Clear communicator who can sit between technical and commercial teams.

Nice to have:
- Experience with iPaaS / workflow tools (Zapier, Make, n8n) and reverse-ETL.
- Familiarity with product-led growth instrumentation and attribution modelling.
- Prior startup 0→1 GTM tooling experience.

Tools & stack: Python / TypeScript · HubSpot or Salesforce · SQL & warehouse (BigQuery/Postgres) · REST/webhooks · LLM APIs · n8n/Make/Zapier · analytics (Looker/Metabase).

Success (first 6 months): Lead routing and enrichment fully automated; a working revenue dashboard the team trusts; at least two shipped internal tools that measurably cut manual sales work.
""",
    "Forward Deployed Engineer (FDE) (MONA AI)": """
Role: Forward Deployed Engineer (FDE)
Company: MONA AI GmbH — applied AI agents for enterprise
Location: Saarbrücken HQ + on-site at customers (travel up to ~30%)
Team: Delivery / Solutions Engineering · reports to Head of Delivery
Type: Full-time, permanent

About the role:
FDEs are senior engineers who deploy directly into customer environments, scope ambiguous problems, and
build and integrate AI-agent solutions against real data and systems. You own delivery from discovery to
production hand-off, and you're the technical face to the customer.

What you'll do:
- Scope customer problems on-site; translate vague requirements into a concrete technical plan.
- Build, integrate and deploy agentic workflows against customer data, APIs and internal systems.
- Design retrieval / RAG pipelines and evaluate LLM output quality with real test sets.
- Harden integrations: auth, error handling, observability, and security/PII handling.
- Run production hand-off, documentation and enablement; feed learnings back to Product.

Must-have qualifications:
- 4+ years software engineering with strong Python (and SQL); production systems experience.
- Built and shipped LLM/agent or data-integration systems against messy real-world data.
- Solid on APIs, cloud (AWS/GCP/Azure), containers, and CI/CD.
- Customer-facing maturity: can run a technical workshop and say 'no' diplomatically.
- Fluent English; German a strong plus for on-site work in DE.

Nice to have:
- Experience with RAG, vector databases, and LLM evaluation/guardrails.
- Background in regulated/enterprise environments (security, GDPR, audit).
- Prior consulting, solutions-engineering or FDE-style role.

Tools & stack: Python · SQL · LLM & agent frameworks · vector DBs (pgvector/Pinecone/Weaviate) · RAG & eval tooling · AWS/GCP/Azure · Docker · REST/gRPC · observability (logs/traces).

Success (first 6 months): At least one customer taken from discovery to production; a reusable integration pattern contributed back; measurable quality bar on agent outputs (eval pass-rate, not vibes).
""",
    "Custom — paste your own job description": "",
}

SYSTEM_PROMPT = """You are an expert hiring consultant helping a non-technical hiring manager conduct structured, fair interviews.

Given a job description, you will:
1. Generate 10 targeted interview questions tailored to the specific role, skills and responsibilities listed.
   - Mix: behavioral (past situations), technical/domain (role-specific knowledge), situational (hypotheticals), and culture/motivation questions.
   - Number each question and label its type in brackets, e.g. [Behavioral], [Technical], [Situational], [Motivation].
   - For technical questions a non-technical manager asks, include a brief "What a good answer sounds like" hint in italics beneath.

2. List 5–7 specific red flags to watch for during the interview, based on this role.
   - Each red flag should be concrete and observable (e.g. "Cannot name the ATS tools they claim to have used").
   - Include why it matters for THIS role.

3. Provide 3 "green flags" — positive signals that indicate a strong candidate for this specific role.

Format your response with clear markdown headers:
## Interview Questions
## Red Flags to Watch For
## Green Flags (Strong Candidate Signals)"""


def analyze_job(api_key: str, job_description: str) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    response = model.generate_content(
        f"Here is the job description:\n\n{job_description}\n\nPlease generate the interview support package."
    )
    return response.text



# ── Streamlit UI ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Interview Support Agent",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Interview Support Agent")
st.caption("For non-technical hiring managers · Powered by Claude AI · Problem 5 — Kohlpharma / MONA AI")

st.divider()

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Job Description")

    api_key = st.text_input(
        "Google API Key",
        type="password",
        value=api_key_env,
        help="Your Google AI API key. Get one at aistudio.google.com/apikey",
    )

    preset = st.selectbox(
        "Select a preset role or paste your own",
        options=list(JOB_DESCRIPTIONS.keys()),
    )

    if preset == "Custom — paste your own job description":
        job_text = st.text_area(
            "Paste job description here",
            height=400,
            placeholder="Paste the full job posting text...",
        )
    else:
        job_text = st.text_area(
            "Job description (editable)",
            value=JOB_DESCRIPTIONS[preset].strip(),
            height=400,
        )

    analyze_btn = st.button("🔍 Generate Interview Package", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Interview Package")

    if analyze_btn:
        if not api_key:
            st.error("Please enter your Anthropic API key.")
        elif not job_text.strip():
            st.error("Please enter a job description.")
        else:
            with st.spinner("Analyzing role and generating questions..."):
                try:
                    result = analyze_job(api_key, job_text)
                    st.session_state["result"] = result
                    st.session_state["role_name"] = preset
                except Exception as auth_err:
                    if "API_KEY" in str(auth_err).upper() or "401" in str(auth_err):
                        st.error("Invalid API key. Please check and try again.")
                    else:
                        st.error(f"Error: {auth_err}")

    if "result" in st.session_state:
        st.markdown(st.session_state["result"])
        st.divider()
        st.download_button(
            label="📥 Download as Markdown",
            data=f"# Interview Package: {st.session_state.get('role_name', 'Role')}\n\n{st.session_state['result']}",
            file_name="interview_package.md",
            mime="text/markdown",
            use_container_width=True,
        )
    else:
        st.info("Select a role and click **Generate Interview Package** to get started.")
        st.markdown("""
**What you'll get:**
- ✅ 10 tailored interview questions (behavioral, technical, situational, motivation)
- 🚩 5–7 red flags specific to this role
- ⭐ 3 green flags — signals of a strong candidate

**Tip:** You can edit the job description text before analyzing.
        """)
