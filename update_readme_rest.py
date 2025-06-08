import os
import re
import sys
import requests
from datetime import datetime
from pathlib import Path

GITHUB_API = "https://api.github.com"

def fetch_latest_commit_info(owner: str, repo: str, branch: str = "main"):
    """
    Call GitHub REST API to get the latest commit's timestamp and message.
    Returns a tuple: (formatted_timestamp, commit_message_first_line).
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not set.")
        sys.exit(1)

    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits/{branch}"
    headers = {"Authorization": f"token {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    iso_ts = data["commit"]["author"]["date"]         # e.g. "2025-06-05T12:34:56Z"
    full_msg = data["commit"]["message"]              # full commit message, may contain newlines

    # parse and format
    dt = datetime.fromisoformat(iso_ts.rstrip("Z"))
    ts = dt.strftime("%Y-%m-%d %H:%M:%S")
    first_line = full_msg.splitlines()[0]             # take only the first line
    return ts, first_line

def update_file_with_github_info(path: Path, owner: str, repo: str):
    content = path.read_text(encoding="utf-8")
    pattern = r"(<!-- AUTO_SECTION_START -->)(.*?)(<!-- AUTO_SECTION_END -->)"
    if not re.search(pattern, content, flags=re.DOTALL):
        print("Warning: No AUTO_SECTION markers found.")
        sys.exit(1)

    timestamp, message = fetch_latest_commit_info(owner, repo)
    new_section = (
        "<!-- AUTO_SECTION_START -->\n"
        f"- Last updated: {timestamp}\n"
        f"- Commit message: {message}\n"
        "- Deployment status: ✅\n"
        "<!-- AUTO_SECTION_END -->"
    )
    updated = re.sub(pattern, new_section, content, flags=re.DOTALL)

    # backup original and write
    backup = path.with_suffix(path.suffix + ".bak")
    path.rename(backup)
    path.write_text(updated, encoding="utf-8")
    print(f"README.md updated with timestamp {timestamp} and message “{message}”")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python update_readme_rest.py <owner> <repo>")
        sys.exit(1)
    owner, repo = sys.argv[1], sys.argv[2]
    update_file_with_github_info(Path("README.md"), owner, repo)