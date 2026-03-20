import jira_client

def dispatch(action: str, params: dict, domain: str, email: str, token: str, project_key: str) -> str:
    """Route an action to jira_client and return a markdown string formatting the result."""
    try:
        if action == "create_issue":
            result = jira_client.create_issue(domain, email, token, project_key, params)
            return f"""✅ **Issue created successfully!**

| Field | Value |
|---|---|
| 🎫 **Key** | `{result['key']}` |
| 📝 **Summary** | {params.get('summary', '')} |
| 🚀 **Priority** | {params.get('priority', 'Medium')} |

🔗 [**Open {result['key']} in Jira ↗**]({result['url']})"""

        elif action == "update_issue":
            issue_key = params.pop("issue_key")
            result = jira_client.update_issue(domain, email, token, issue_key, params)
            return f"✅ **Updated {issue_key} successfully!** 🔗 [Open in Jira ↗]({result['url']})"

        elif action == "get_issue":
            result = jira_client.get_issue(domain, email, token, params["issue_key"])
            return f"""🔍 **Found {result['key']}**

| Field | Value |
|---|---|
| **Summary** | {result['summary']} |
| **Status** | {result['status']} |
| **Priority** | {result['priority']} |
| **Assignee** | {result.get('assignee_name') or 'Unassigned'} |

> {result['description']}

🔗 [**Open in Jira ↗**]({result['url']})"""

        elif action == "search_issues":
            results = jira_client.search_issues(domain, email, token, params["jql"])
            if not results:
                return "🔍 No issues found matching that search."
            
            md = f"🔍 **Found {len(results)} issues:**\n\n| Key | Summary | Status | Assignee |\n|---|---|---|---|\n"
            for r in results:
                md += f"| [{r['key']}]({r['url']}) | {r['summary']} | {r['status']} | {r['assignee_name'] or 'Unassigned'} |\n"
            return md

        elif action == "add_comment":
            jira_client.add_comment(domain, email, token, params["issue_key"], params["body"])
            return f"💬 **Added comment** to {params['issue_key']} successfully!"

        elif action == "get_comments":
            comments = jira_client.get_comments(domain, email, token, params["issue_key"])
            if not comments: return f"No comments found on {params['issue_key']}."
            
            md = f"💬 **Recent comments on {params['issue_key']}:**\n\n"
            for c in comments:
                md += f"**{c['author']}** ({c['created'][:10]}):\n> {c['body']}\n\n"
            return md

        elif action == "get_transitions":
            transitions = jira_client.get_transitions(domain, email, token, params["issue_key"])
            return f"🔄 **Available statuses for {params['issue_key']}:**\n\n" + "\n".join([f"- {t}" for t in transitions])

        elif action == "transition_issue":
            jira_client.transition_issue(domain, email, token, params["issue_key"], params["target_status_name"])
            return f"🚀 **Moved {params['issue_key']} to {params['target_status_name']}** successfully!"

        elif action == "assign_issue":
            jira_client.assign_issue(domain, email, token, params["issue_key"], params["assignee_name"])
            return f"👤 **Assigned {params['issue_key']} to {params['assignee_name']}** successfully!"

        elif action == "delete_issue":
            jira_client.delete_issue(domain, email, token, params["issue_key"])
            return f"🗑️ **Deleted {params['issue_key']}** forever. Hope you meant to do that!"

        else:
            return f"⚠️ **Unknown action:** {action}"

    except Exception as e:
        if "403" in str(e):
            return "🚫 **Permission Denied (403):** You do not have the right Jira permissions for this action."
        if "404" in str(e) or "Issue Does Not Exist" in str(e):
            return "🕵️‍♂️ **Not Found (404):** That issue or resource doesn't exist (or you can't view it)."
        return f"🚨 **Error executing `{action}`:**\n```\n{e}\n```"
