from jira import JIRA


def _client(domain: str, email: str, token: str) -> JIRA:
    """Return an authenticated JIRA client."""
    return JIRA(
        server=f"https://{domain.strip()}.atlassian.net",
        basic_auth=(email.strip(), token.strip()),
    )


def fetch_projects(domain: str, email: str, token: str) -> list[dict]:
    """Fetch all Jira projects the user has access to."""
    jira = _client(domain, email, token)
    projects = jira.projects()
    return [{"key": p.key, "name": p.name} for p in sorted(projects, key=lambda p: p.name)]


def fetch_issue_types(domain: str, email: str, token: str, project_key: str) -> list[str]:
    """
    Fetch valid issue type names for a specific project.
    Returns e.g. ['Task', 'Bug', 'Epic', 'Subtask']
    """
    jira = _client(domain, email, token)
    try:
        meta = jira.createmeta(
            projectKeys=project_key.strip().upper(),
            expand="projects.issuetypes",
        )
        projects = meta.get("projects", [])
        if projects:
            return [it["name"] for it in projects[0].get("issuetypes", [])]
    except Exception:
        pass
    return ["Task", "Bug", "Story"]   # safe fallback


def create_issue(domain: str, email: str, token: str, project_key: str, parsed: dict) -> dict:
    """
    Create a Jira issue and return a dict with 'key' and 'url'.
    """
    jira = _client(domain, email, token)

    fields = {
        "project":     {"key": project_key.strip().upper()},
        "summary":     parsed["summary"],
        "description": parsed.get("description", "") or "",
        "issuetype":   {"name": parsed.get("issuetype", "Task")},
        "priority":    {"name": parsed.get("priority", "Medium")},
    }

    # ── Optional: due date ────────────────────────────────────────────────────
    if parsed.get("due_date"):
        fields["duedate"] = parsed["due_date"]          # YYYY-MM-DD

    # ── Optional: labels ──────────────────────────────────────────────────────
    labels = parsed.get("labels") or []
    if labels:
        fields["labels"] = [str(l).replace(" ", "_") for l in labels]

    # ── Optional: assignee (lookup by name) ───────────────────────────────────
    assignee_name = parsed.get("assignee_name")
    if assignee_name:
        try:
            users = jira.search_users(query=assignee_name)
            if users:
                fields["assignee"] = {"accountId": users[0].accountId}
        except Exception:
            pass  # silently skip if not found or no permission

    issue = jira.create_issue(fields=fields)

    return {
        "key": issue.key,
        "url": f"https://{domain.strip()}.atlassian.net/browse/{issue.key}",
    }
