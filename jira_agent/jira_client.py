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
    """Fetch valid issue type names for a specific project."""
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
    return ["Task", "Bug", "Story"]


def create_issue(domain: str, email: str, token: str, project_key: str, parsed: dict) -> dict:
    jira = _client(domain, email, token)
    fields = {
        "project":     {"key": project_key.strip().upper()},
        "summary":     parsed["summary"],
        "description": parsed.get("description", ""),
        "issuetype":   {"name": parsed.get("issuetype", "Task")},
        "priority":    {"name": parsed.get("priority", "Medium")},
    }
    if parsed.get("due_date"): fields["duedate"] = parsed["due_date"]
    if parsed.get("labels"): fields["labels"] = [str(l).replace(" ", "_") for l in parsed["labels"]]

    if assignee_name := parsed.get("assignee_name"):
        try:
            users = jira.search_users(query=assignee_name)
            if users: fields["assignee"] = {"accountId": users[0].accountId}
        except Exception: pass

    issue = jira.create_issue(fields=fields)
    return {"key": issue.key, "url": f"https://{domain.strip()}.atlassian.net/browse/{issue.key}"}

def get_issue(domain: str, email: str, token: str, issue_key: str) -> dict:
    jira = _client(domain, email, token)
    issue = jira.issue(issue_key)
    return {
        "key": issue.key,
        "summary": issue.fields.summary,
        "description": getattr(issue.fields, 'description', ''),
        "status": issue.fields.status.name,
        "priority": issue.fields.priority.name,
        "assignee_name": issue.fields.assignee.displayName if issue.fields.assignee else None,
        "url": f"https://{domain.strip()}.atlassian.net/browse/{issue.key}"
    }

def update_issue(domain: str, email: str, token: str, issue_key: str, parsed: dict) -> dict:
    jira = _client(domain, email, token)
    issue = jira.issue(issue_key)
    
    fields_to_update = {}
    if parsed.get("summary"): fields_to_update["summary"] = parsed["summary"]
    if parsed.get("description"): fields_to_update["description"] = parsed["description"]
    if parsed.get("priority"): fields_to_update["priority"] = {"name": parsed["priority"]}
    
    if parsed.get("assignee_name"):
        users = jira.search_users(query=parsed["assignee_name"])
        if users: fields_to_update["assignee"] = {"accountId": users[0].accountId}

    issue.update(fields=fields_to_update)
    return {"key": issue.key, "url": f"https://{domain.strip()}.atlassian.net/browse/{issue.key}"}

def delete_issue(domain: str, email: str, token: str, issue_key: str) -> bool:
    jira = _client(domain, email, token)
    issue = jira.issue(issue_key)
    issue.delete()
    return True

def search_issues(domain: str, email: str, token: str, jql: str) -> list[dict]:
    jira = _client(domain, email, token)
    issues = jira.search_issues(jql, maxResults=10)
    return [{
        "key": issue.key,
        "summary": issue.fields.summary,
        "status": issue.fields.status.name,
        "assignee_name": issue.fields.assignee.displayName if issue.fields.assignee else None,
        "url": f"https://{domain.strip()}.atlassian.net/browse/{issue.key}"
    } for issue in issues]

def add_comment(domain: str, email: str, token: str, issue_key: str, body: str) -> bool:
    jira = _client(domain, email, token)
    jira.add_comment(issue_key, body)
    return True

def get_comments(domain: str, email: str, token: str, issue_key: str) -> list[dict]:
    jira = _client(domain, email, token)
    issue = jira.issue(issue_key)
    return [{
        "author": c.author.displayName,
        "body": c.body,
        "created": c.created
    } for c in issue.fields.comment.comments[-5:]] # return last 5

def get_transitions(domain: str, email: str, token: str, issue_key: str) -> list[str]:
    jira = _client(domain, email, token)
    issue = jira.issue(issue_key)
    transitions = jira.transitions(issue)
    return [t['name'] for t in transitions]

def transition_issue(domain: str, email: str, token: str, issue_key: str, target_status_name: str) -> bool:
    jira = _client(domain, email, token)
    issue = jira.issue(issue_key)
    transitions = jira.transitions(issue)
    for t in transitions:
        if t['name'].lower() == target_status_name.lower():
            jira.transition_issue(issue, t['id'])
            return True
    raise ValueError(f"Transition '{target_status_name}' not found for {issue_key}")

def assign_issue(domain: str, email: str, token: str, issue_key: str, assignee_name: str) -> bool:
    jira = _client(domain, email, token)
    users = jira.search_users(query=assignee_name)
    if users:
        jira.assign_issue(issue_key, users[0].accountId)
        return True
    raise ValueError(f"User '{assignee_name}' not found")
