from groq import Groq
import json


def _build_system_prompt(valid_issue_types: list[str]) -> str:
    types_str = " | ".join(valid_issue_types) if valid_issue_types else "Task | Bug | Story"
    return f"""
You are an advanced Jira agent. Your job is to extract the user's intent into ONE of the following precise JSON action formats. 
Do not return markdown, reasoning, or anything other than the raw JSON object.

Valid Actions and their expected formats:

1. create_issue
{{"action": "create_issue", "params": {{"summary": "...", "description": "...", "priority": "Highest|High|Medium|Low|Lowest", "issuetype": "{types_str}", "due_date": "YYYY-MM-DD", "labels": ["..."], "assignee_name": "..."}}}}
*Note: description is required, keep it concise but helpful.*

2. update_issue
{{"action": "update_issue", "params": {{"issue_key": "PROJ-123", "summary": "...", "description": "...", "priority": "...", "assignee_name": "..."}}}}
*Note: only include fields in params that the user explicitly wants to update.*

3. get_issue
{{"action": "get_issue", "params": {{"issue_key": "PROJ-123"}}}}

4. search_issues  
{{"action": "search_issues", "params": {{"jql": "..."}}}}
*Note: write valid JQL. e.g. 'assignee = currentUser() AND status = Open'*

5. add_comment
{{"action": "add_comment", "params": {{"issue_key": "PROJ-123", "body": "..."}}}}

6. get_comments
{{"action": "get_comments", "params": {{"issue_key": "PROJ-123"}}}}

7. transition_issue
{{"action": "transition_issue", "params": {{"issue_key": "PROJ-123", "target_status_name": "In Progress"}}}}

8. get_transitions
{{"action": "get_transitions", "params": {{"issue_key": "PROJ-123"}}}}

9. assign_issue
{{"action": "assign_issue", "params": {{"issue_key": "PROJ-123", "assignee_name": "..."}}}}

10. delete_issue
{{"action": "delete_issue", "params": {{"issue_key": "PROJ-123"}}}}

CRITICAL RULES:
- Return ONLY the exact JSON shape for the chosen action. 
- No wrappers, no backticks, no comments.
- issue_key must be exactly like 'PROJ-123'.
""".strip()

def parse_task(user_input: str, api_key: str, valid_issue_types: list[str] | None = None) -> dict:
    client = Groq(api_key=api_key)
    system_prompt = _build_system_prompt(valid_issue_types or [])

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_input}
        ],
        temperature=0.2,
        max_tokens=400,
    )
    raw = response.choices[0].message.content.strip()
    
    # Strip markdown code blocks if the LLM accidentally includes them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("\n", 1)[0]
        
    parsed = json.loads(raw.strip())

    # Safety net for create_issue
    if parsed.get("action") == "create_issue":
        p = parsed.get("params", {})
        if valid_issue_types and p.get("issuetype") not in valid_issue_types:
            p["issuetype"] = valid_issue_types[0]

    return parsed
