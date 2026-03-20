from groq import Groq
import json


def _build_system_prompt(valid_issue_types: list[str]) -> str:
    types_str = " | ".join(valid_issue_types) if valid_issue_types else "Task | Bug | Story"
    return f"""
You are a Jira task parser. Extract and return ONLY a JSON object with these fields:

- summary: string (max 100 chars, concise title)
- description: string (REQUIRED — always write 2-3 sentences explaining the task context, goal, and any details mentioned. Never leave this empty.)
- priority: one of Highest | High | Medium | Low | Lowest
- issuetype: one of {types_str}
- due_date: string in YYYY-MM-DD format if a date or deadline is mentioned, otherwise null
- labels: array of short label strings (snake_case) relevant to the task, max 3 items, empty array if none
- assignee_name: string — first name or full name of the person to assign to if mentioned (e.g. "John", "Yash"), otherwise null

Return ONLY raw JSON. No markdown. No explanation. No backticks. No extra keys.
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
    parsed = json.loads(raw)

    # Safety net: if Groq still returned an invalid type, fall back to first valid
    if valid_issue_types and parsed.get("issuetype") not in valid_issue_types:
        parsed["issuetype"] = valid_issue_types[0]

    return parsed
