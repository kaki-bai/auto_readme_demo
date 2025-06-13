import os
import sys
import re
import requests
from datetime import datetime
from pathlib import Path

GITHUB_GRAPHQL = "https://api.github.com/graphql"
CI_PREFIX = "ci: auto-update README"

def fetch_latest_user_commit_info_graphql(owner: str, repo: str, branch: str = "main", lookback: int = 10):
    """
    Call GitHub GraphQL API to fetch the most recent commit NOT starting with CI_PREFIX.
    Returns a tuple: (formatted_timestamp, commit_message_first_line).
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not set.")
        sys.exit(1)

    query = """
    query($owner:String!, $repo:String!, $branch:String!, $first:Int!) {
      repository(owner: $owner, name: $repo) {
        ref(qualifiedName: $branch) {
          target {
            ... on Commit {
              history(first: $first) {
                nodes {
                  committedDate
                  message
                }
              }
            }
          }
        }
      }
    }
    """
    variables = {
        "owner": owner,
        "repo": repo,
        "branch": f"refs/heads/{branch}",
        "first": lookback
    }
    headers = {"Authorization": f"bearer {token}"}
    resp = requests.post(GITHUB_GRAPHQL, json={"query": query, "variables": variables}, headers=headers)
    resp.raise_for_status()
    nodes = resp.json()["data"]["repository"]["ref"]["target"]["history"]["nodes"]

    # Iterate and skip CI commits
    for node in nodes:
        msg = node["message"].splitlines()[0]
        if not msg.startswith(CI_PREFIX):
            ts_iso = node["committedDate"]
            dt = datetime.fromisoformat(ts_iso.rstrip("Z"))
            return dt.strftime("%Y-%m-%d %H:%M:%S"), msg

    # Fallback to the very first one if all are CI commits
    node = nodes[0]
    ts_iso = node["committedDate"]
    dt = datetime.fromisoformat(ts_iso.rstrip("Z"))
    msg = node["message"].splitlines()[0]
    return dt.strftime("%Y-%m-%d %H:%M:%S"), msg

def update_file_with_github_info(path: Path, owner: str, repo: str):
    content = path.read_text(encoding="utf-8")
    pattern = r"(<!-- AUTO_SECTION_START -->)(.*?)(<!-- AUTO_SECTION_END -->)"
    if not re.search(pattern, content, flags=re.DOTALL):
        print("Warning: No AUTO_SECTION markers found.")
        sys.exit(1)

    timestamp, message = fetch_latest_user_commit_info_graphql(owner, repo)
    new_section = (
        "<!-- AUTO_SECTION_START -->\n"
        f"- Last updated: {timestamp}\n"
        f"- Commit message: {message}\n"
        "- Deployment status: ✅\n"
        "<!-- AUTO_SECTION_END -->"
    )
    updated = re.sub(pattern, new_section, content, flags=re.DOTALL)

    backup = path.with_suffix(path.suffix + ".bak")
    path.rename(backup)
    path.write_text(updated, encoding="utf-8")
    print(f"README.md updated with timestamp {timestamp} and message '{message}'")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python update_readme_graphql.py <owner> <repo>")
        sys.exit(1)
    owner, repo = sys.argv[1], sys.argv[2]
    update_file_with_github_info(Path("README.md"), owner, repo)