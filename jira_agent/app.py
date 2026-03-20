import re
import streamlit as st
from agent import parse_task
from jira_client import create_issue, fetch_projects, fetch_issue_types


def extract_domain(raw: str) -> str:
    """Extract bare Jira subdomain from a URL, full domain, or plain name."""
    raw = raw.strip()
    # e.g. https://mycompany.atlassian.net/... or mycompany.atlassian.net
    m = re.search(r'([\w-]+)\.atlassian\.net', raw)
    if m:
        return m.group(1)
    # plain word — return as-is
    return raw


def guess_domain_from_email(email: str) -> str:
    """Best-guess domain from email: john@mycompany.com → mycompany."""
    if "@" in email:
        host = email.split("@")[-1]          # mycompany.com
        return host.split(".")[0]            # mycompany
    return ""

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Jira AI Agent",
    page_icon="🤖",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #0f0c29 100%);
        min-height: 100vh;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b 0%, #12104a 100%);
        border-right: 1px solid rgba(139, 92, 246, 0.3);
    }
    [data-testid="stSidebar"] label { color: #c4b5fd !important; font-weight: 500 !important; }
    [data-testid="stSidebar"] input {
        background: rgba(139, 92, 246, 0.1) !important;
        border: 1px solid rgba(139, 92, 246, 0.4) !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] input:focus {
        border-color: #8b5cf6 !important;
        box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.25) !important;
    }

    /* Selectbox */
    [data-testid="stSelectbox"] div[data-baseweb="select"] {
        background: rgba(139, 92, 246, 0.1) !important;
        border: 1px solid rgba(139, 92, 246, 0.4) !important;
        border-radius: 8px !important;
    }

    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(139, 92, 246, 0.2) !important;
        border-radius: 14px !important;
        backdrop-filter: blur(10px);
        margin-bottom: 8px !important;
    }

    [data-testid="stChatInputTextArea"] {
        background: rgba(30, 27, 75, 0.8) !important;
        border: 1px solid rgba(139, 92, 246, 0.5) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
    }

    .stSpinner > div { border-top-color: #8b5cf6 !important; }
    p, li, span { color: #e2e8f0; }

    .brand-title {
        font-size: 1.6rem; font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; margin-bottom: 4px;
    }
    .brand-sub { color: #94a3b8; font-size: 0.8rem; margin-bottom: 20px; }
    hr { border-color: rgba(139, 92, 246, 0.2); }

    /* Fetch button */
    div[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(90deg, #7c3aed, #4f46e5);
        color: white; border: none; border-radius: 8px;
        width: 100%; font-weight: 600;
        transition: opacity 0.2s;
    }
    div[data-testid="stSidebar"] .stButton > button:hover { opacity: 0.85; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
if "projects" not in st.session_state:
    st.session_state.projects = []
if "issue_types" not in st.session_state:
    st.session_state.issue_types = []        # valid issue types for selected project
if "projects_error" not in st.session_state:
    st.session_state.projects_error = ""
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hi! I'm your **Jira AI Agent**.\n\n"
                "Describe a task in plain English and I'll parse it with **LLaMA 3.3 70B** "
                "and create a Jira issue instantly.\n\n"
                "_Fill in your credentials in the sidebar, then click **Fetch Projects** to load your projects._"
            ),
        }
    ]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand-title">🤖 Jira AI Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Powered by Groq × LLaMA 3.3 70B</div>', unsafe_allow_html=True)
    st.divider()

    st.subheader("⚙️ Credentials")

    groq_key   = st.text_input("Groq API Key",   type="password", placeholder="gsk_...")
    jira_email = st.text_input("Jira Email",      placeholder="you@example.com")
    jira_token = st.text_input("Jira API Token", type="password", placeholder="ATATT3...")

    # ── Auto-suggest domain from email ───────────────────────────────────────
    suggested = guess_domain_from_email(jira_email) if jira_email else ""
    raw_domain = st.text_input(
        "Jira Domain  *(auto-detected — edit if wrong)*",
        value=suggested,
        placeholder="e.g. mycompany  or paste your full Jira URL",
        help="We guessed this from your email. You can also paste the full URL like https://mycompany.atlassian.net",
    )
    jira_domain = extract_domain(raw_domain) if raw_domain.strip() else ""

    # reset projects if email/token changed
    prev_key = f"{jira_email}|{jira_token}|{jira_domain}"
    if st.session_state.get("_creds_key") != prev_key:
        st.session_state["_creds_key"] = prev_key
        st.session_state.projects = []
        st.session_state.projects_error = ""

    creds_ready = all([jira_email, jira_token, jira_domain])

    st.divider()

    # ── Fetch Projects button ─────────────────────────────────────────────────
    if st.button("🔍 Fetch My Projects", disabled=not creds_ready):
        with st.spinner("Connecting to Jira…"):
            try:
                st.session_state.projects = fetch_projects(
                    jira_domain.strip(), jira_email.strip(), jira_token.strip()
                )
                st.session_state.projects_error = ""
                if not st.session_state.projects:
                    st.session_state.projects_error = "No projects found. Check your credentials and domain."
            except Exception as e:
                st.session_state.projects = []
                msg = str(e)
                if "401" in msg:
                    st.session_state.projects_error = "❌ Auth failed — check email and API token."
                elif "404" in msg:
                    st.session_state.projects_error = "❌ Domain not found — check Jira domain."
                else:
                    st.session_state.projects_error = f"❌ {msg}"

    # ── Show fetch error ──────────────────────────────────────────────────────
    if st.session_state.projects_error:
        st.error(st.session_state.projects_error)

    # ── Project selectbox ─────────────────────────────────────────────────────
    selected_project_key = None
    if st.session_state.projects:
        st.success(f"✅ {len(st.session_state.projects)} project(s) loaded")
        options = [f"{p['name']}  [{p['key']}]" for p in st.session_state.projects]
        chosen = st.selectbox("📁 Select Project", options=options)
        # Extract the key from e.g. "My Project  [PROJ]"
        selected_project_key = chosen.split("[")[-1].rstrip("]").strip()

        # Fetch issue types when project changes
        prev_proj = st.session_state.get("_selected_proj")
        if prev_proj != selected_project_key:
            st.session_state["_selected_proj"] = selected_project_key
            with st.spinner("Loading issue types…"):
                st.session_state.issue_types = fetch_issue_types(
                    jira_domain, jira_email, jira_token, selected_project_key
                )

        if st.session_state.issue_types:
            st.caption(f"🗂 Valid types: {', '.join(st.session_state.issue_types)}")
    else:
        if creds_ready:
            st.info("👆 Click **Fetch My Projects** to load your Jira projects.")
        else:
            st.warning("⚠️ Fill in all credential fields above.")

    # ── Readiness check ───────────────────────────────────────────────────────
    is_ready = all([groq_key, jira_email, jira_token, jira_domain, selected_project_key])

    st.divider()
    with st.expander("ℹ️ How to get credentials", expanded=False):
        st.markdown("""
**Groq API Key**
Visit [console.groq.com](https://console.groq.com) → API Keys → Create Key

**Jira API Token**
Visit [Atlassian security settings](https://id.atlassian.com/manage-profile/security/api-tokens)
→ Create API token

**Jira Domain** *(auto-detected)*
We guess it from your email. If wrong, correct it or paste your full Jira URL like `https://mycompany.atlassian.net`.
        """)

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("## 🚀 Jira AI Agent")
st.markdown(
    "Describe any task in natural language — the agent extracts the details "
    "and creates a Jira ticket automatically."
)

if selected_project_key:
    st.info(f"🎯 Creating issues in **{selected_project_key}**")

st.divider()

# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
placeholder = (
    "Describe your task… e.g. 'Fix the login page crash on mobile — it's urgent'"
    if is_ready else
    "Fill credentials & fetch projects in the sidebar first…"
)

if prompt := st.chat_input(placeholder, disabled=not is_ready):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🧠 Parsing with LLaMA → 🔧 Creating Jira issue…"):
            try:
                parsed = parse_task(
                    prompt, groq_key,
                    valid_issue_types=st.session_state.issue_types or None,
                )
                result = create_issue(
                    jira_domain.strip(),
                    jira_email.strip(),
                    jira_token.strip(),
                    selected_project_key,
                    parsed,
                )
                key = result["key"]
                browse_url = result["url"]

                priority_emoji = {
                    "Highest": "🔴", "High": "🟠",
                    "Medium": "🟡", "Low": "🔵", "Lowest": "⚪"
                }.get(parsed.get("priority", "Medium"), "🟡")

                type_emoji = {
                    "Bug": "🐛", "Story": "📖",
                    "Task": "✅", "Improvement": "⚡"
                }.get(parsed.get("issuetype", "Task"), "✅")

                reply = f"""✅ **Issue created successfully!**

| Field | Value |
|---|---|
| 🎫 **Key** | `{key}` |
| 📝 **Summary** | {parsed.get('summary', '')} |
| {type_emoji} **Type** | {parsed.get('issuetype', 'Task')} |
| {priority_emoji} **Priority** | {parsed.get('priority', 'Medium')} |
{f"| 📅 **Due Date** | {parsed['due_date']} |" if parsed.get('due_date') else ""}
{f"| 🏷️ **Labels** | {', '.join(parsed['labels'])} |" if parsed.get('labels') else ""}
{f"| 👤 **Assignee** | {parsed['assignee_name']} |" if parsed.get('assignee_name') else ""}

> 📄 **Description**: {parsed.get('description', '_No description_') or '_No description_'}

🔗 [**Open {key} in Jira ↗**]({browse_url})
"""

            except Exception as e:
                msg = str(e)
                if "401" in msg:
                    hint = "Check your Jira email and API token."
                elif "404" in msg:
                    hint = "Check your domain and project key."
                elif "400" in msg:
                    hint = "Jira rejected the payload — try a different issue type or check project settings."
                else:
                    hint = "Check all configuration fields in the sidebar."
                reply = f"❌ **Error**: {msg}\n\n💡 **Hint**: {hint}"

        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='text-align:center; color:#475569; font-size:0.75rem;'>"
    "Jira AI Agent · Groq × LLaMA 3.3 70B · Jira REST API v3"
    "</p>",
    unsafe_allow_html=True,
)
