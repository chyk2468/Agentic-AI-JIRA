from groq import Groq
import json


def _build_system_prompt(valid_issue_types: list[str], context_issues: list[dict] = None) -> str:
    types_str = " | ".join(valid_issue_types) if valid_issue_types else "Task | Bug | Story"
    
    context_str = ""
    if context_issues:
        context_str = "\n\n<ProjectContext>\nHere are some existing Jira tickets that might be relevant to the user's request. Use this to avoid duplicates, find issue keys, or answer questions:\n"
        for i, doc in enumerate(context_issues):
            context_str += f"- [{doc['key']}] ({doc['status']}) {doc['summary']}\n  Description: {doc['description'][:200]}...\n"
        context_str += "</ProjectContext>\n"

    return f"""
You are an advanced Jira agent. Your job is to extract the user's intent into an ARRAY of ONE OR MORE precise JSON action formats. 
Even if there is only one action, return it as a JSON array (e.g. `[ {{ ... }} ]`).
Do not return markdown, reasoning, or anything other than the raw JSON array.

Use the provided conversation history to resolve pronouns, references, or missing data. 
For example, if the user says "assign it to Yash", find the most recently discussed issue_key from the previous messages.{context_str}

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

11. answer_question
{{"action": "answer_question", "params": {{"answer": "Your detailed answer to the user's question..."}}}}
*Note: Use this if the user is just asking a question that you can answer using the <ProjectContext> above (e.g. "What is the status of the login bug?").*

CRITICAL RULES:
- Return ONLY the exact JSON array of actions `[ {{...}}, {{...}} ]`
- No wrappers, no backticks, no comments.
- issue_key must be exactly like 'PROJ-123'.
""".strip()

def parse_task(user_input: str, api_key: str, valid_issue_types: list[str] | None = None, chat_history: list[dict] | None = None, context_issues: list[dict] = None) -> dict:
    client = Groq(api_key=api_key)
    system_prompt = _build_system_prompt(valid_issue_types or [], context_issues)

    messages = [{"role": "system", "content": system_prompt}]
    
    # Inject conversational memory (last 6 messages to keep context window clean)
    if chat_history:
        for msg in chat_history[-6:]:
            # Omit the big intro message to save tokens if it's the very first
            if "Hi! I'm your **Jira AI Agent**" in msg["content"]:
                continue
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.2,
        max_tokens=400,
    )
    raw = response.choices[0].message.content.strip()
    
    # Strip markdown code blocks if the LLM accidentally includes them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("\n", 1)[0]
        
    raw = raw.strip()
    # Failsafe: if the LLM forgot to wrap in an array but returned valid JSON
    if not raw.startswith("["):
        # If it returned multiple dicts separated by newlines, this fix might fail but json.loads will catch it
        raw = f"[{raw}]"
        
    try:
        parsed_list = json.loads(raw)
    except json.JSONDecodeError as e:
        # Extreme failsafe: if multiple JSON objects are side-by-side without commas: }{
        raw = raw.replace("}\n{", "},{").replace("}{", "},{")
        if not raw.startswith("["): raw = f"[{raw}]"
        parsed_list = json.loads(raw)

    # Safety net for create_issue
    for parsed in parsed_list:
        if parsed.get("action") == "create_issue":
            p = parsed.get("params", {})
            if valid_issue_types and p.get("issuetype") not in valid_issue_types:
                p["issuetype"] = valid_issue_types[0]

    return parsed_list
