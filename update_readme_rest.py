import os
import re
import sys
import requests
from datetime import datetime
from pathlib import Path

GITHUB_API = "https://api.github.com"

def fetch_latest_user_commit_info(owner: str, repo: str, branch: str = "main"):
    """
    Fetch the most recent commit on `branch` whose message does NOT
    start with 'ci: auto-update README'. Returns (timestamp, message).
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not set.")
        sys.exit(1)

    # Fetch the latest 10 commits on the branch
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    params = {"sha": branch, "per_page": 10}
    headers = {"Authorization": f"token {token}"}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    commits = resp.json()

    for commit in commits:
        msg = commit["commit"]["message"].splitlines()[0]
        # Skip CI auto-update commits
        if not msg.startswith("ci: auto-update README"):
            # Parse timestamp
            iso_ts = commit["commit"]["author"]["date"]
            dt = datetime.fromisoformat(iso_ts.rstrip("Z"))
            ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            return ts, msg

    # Fallback to the very latest if all are CI commits
    latest = commits[0]
    iso_ts = latest["commit"]["author"]["date"]
    dt = datetime.fromisoformat(iso_ts.rstrip("Z"))
    ts = dt.strftime("%Y-%m-%d %H:%M:%S")
    msg = latest["commit"]["message"].splitlines()[0]
    return ts, msg

def update_file_with_github_info(path: Path, owner: str, repo: str):
    content = path.read_text(encoding="utf-8")
    pattern = r"(<!-- AUTO_SECTION_START -->)(.*?)(<!-- AUTO_SECTION_END -->)"
    if not re.search(pattern, content, flags=re.DOTALL):
        print("Warning: No AUTO_SECTION markers found.")
        sys.exit(1)

    timestamp, message = fetch_latest_user_commit_info(owner, repo)
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