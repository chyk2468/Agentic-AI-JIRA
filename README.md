# 🤖 Jira AI Agent

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/AI-Groq%20LLaMA%203.3-orange.svg)](https://groq.com/)
[![Jira](https://img.shields.io/badge/Integration-Jira%20Cloud-0052CC.svg)](https://www.atlassian.com/software/jira)

An intelligent, conversational interface for managing your Jira workspace. Powered by **Groq (LLaMA 3.3 70B)** and **ChromaDB**, this agent understands natural language commands to automate your Jira workflow.

---

## ✨ Key Features

*   **🗣️ Natural Language Processing**: Create, update, transition, and search Jira issues using plain English.
*   **🧠 Context-Aware (RAG)**: Syncs your project issues to a local **ChromaDB** vector store to answer questions about existing tickets accurately.
*   **🛡️ Human-in-the-Loop**: Preview and approve AI-generated actions before they are executed on Jira.
*   **📂 Multi-Project Support**: Dynamically fetch projects and issue types associated with your Jira account.
*   **💬 Conversational Memory**: Remembers previous interactions (e.g., "Assign *that* bug to me").
*   **🎨 Modern UI**: A sleek, dark-themed Streamlit interface with interactive feedback and real-time status updates.

---

## 🚀 Tech Stack

- **Frontend**: Streamlit (Custom CSS)
- **LLM**: Groq (LLaMA 3.3 70B Versatile)
- **Database**: ChromaDB (Vector Store for semantic search)
- **API**: Jira REST API v3
- **Language**: Python 3.10+

---

## 🛠️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/jira-ai-agent.git
cd jira-ai-agent
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory and add your credentials (optional, as you can also enter them in the UI):
```env
GROQ_API_KEY=your_groq_api_key
JIRA_EMAIL=your_email@example.com
JIRA_API_KEY=your_jira_api_token
JIRA_DOMAIN=your-subdomain
```
> **Note:** Generate your Jira API Token [here](https://id.atlassian.com/manage-profile/security/api-tokens).

### 4. Run the Application
```bash
streamlit run app.py
```

---

## 💡 How to Use

1.  **Connect**: Enter your Groq Key and Jira Credentials in the sidebar.
2.  **Fetch**: Click **"Fetch My Projects"** to load your accessible Jira boards.
3.  **Sync (Optional)**: Click **"Sync Project to AI Vector Memory"** to download recent tickets. This allows the AI to "know" about your existing work.
4.  **Chat**: Describe what you need in the chat box!

### 📝 Example Prompts

| Intent | Prompt |
| :--- | :--- |
| **Create** | "Create a high priority bug for the login page crash" |
| **Assign** | "Assign PROJ-123 to Yash" |
| **Transition**| "Move the payment issue to In Progress" |
| **Search** | "Find all open bugs assigned to me" |
| **Comment** | "Comment on PROJ-45: I have started working on this" |
| **Question** | "What is the current status of the database migration ticket?" |

---

## 🛠️ Architecture

- `app.py`: The Streamlit dashboard and UI logic.
- `agent.py`: Orchestrates the Groq LLM to parse intent into structured JSON actions.
- `actions.py`: The dispatcher that routes parsed actions to Jira functions.
- `jira_client.py`: Wrapper for the Jira REST API.
- `vector_store.py`: Handles local embeddings and semantic search using ChromaDB.

---

## 🔒 Security

This agent uses **Basic Auth** (Email + API Token) for Jira. Your credentials are used only to communicate with the official Atlassian API and are never stored outside your local environment or `.env` file.

---

<p align="center">
  Built with ❤️ for productive developers.
</p>
