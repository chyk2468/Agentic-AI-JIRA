import os
import chromadb

# Initialize the Chroma client pointing to a local directory
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_PATH)

def _get_collection(project_key: str):
    """Get or create a Chroma collection for a specific Jira project."""
    # Collections must start/end with auth num/letter, length 3-63.
    safe_name = f"jira_{project_key.lower()}"
    return client.get_or_create_collection(
        name=safe_name,
        metadata={"hnsw:space": "cosine"} # Use cosine similarity for text
    )

def sync_project_issues(project_key: str, issues: list[dict]) -> int:
    """
    Ingest a list of Jira issues into the vector database.
    Expects issues in format: [{"key": "PROJ-1", "summary": "...", "description": "...", ...}]
    """
    if not issues:
        return 0

    collection = _get_collection(project_key)
    
    documents = []
    metadatas = []
    ids = []

    for issue in issues:
        # Create a rich text document for the embedding model
        # Combines summary and description so both are searchable
        doc_text = f"Ticket: {issue['key']}\nSummary: {issue['summary']}\nDescription: {issue.get('description', '')}"
        
        documents.append(doc_text)
        metadatas.append({
            "key": issue["key"],
            "summary": issue["summary"],
            "status": issue.get("status", "Unknown"),
            "assignee": issue.get("assignee_name") or "Unassigned"
        })
        ids.append(issue["key"])

    # Upsert means insert, or update if the ID already exists
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    return len(issues)

def search_similar_issues(project_key: str, query: str, n_results: int = 3) -> list[dict]:
    """
    Search the vector DB for tickets matching the query conceptually.
    Returns a list of metadata dicts containing key, summary, status.
    """
    try:
        collection = _get_collection(project_key)
        # Check if collection is empty
        if collection.count() == 0:
            return []
            
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count())
        )
        
        # results["metadatas"] is a list of lists. We only queried 1 text, so take [0]
        if results and results.get("metadatas") and len(results["metadatas"][0]) > 0:
            return results["metadatas"][0]
        return []
    except Exception as e:
        print(f"Chroma search error: {e}")
        return []
