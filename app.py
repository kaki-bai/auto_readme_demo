# app.py
import os
import hmac
import hashlib
import base64
import re
import datetime
from flask import Flask, request, abort
from github import Github
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").encode()
PORT           = int(os.getenv("PORT", 3000))

if not GITHUB_TOKEN or not WEBHOOK_SECRET:
    print("Error: Please set GITHUB_TOKEN and WEBHOOK_SECRET in .env")
    exit(1)

# Initialize Flask app and GitHub client
app = Flask(__name__)
gh  = Github(GITHUB_TOKEN)

def verify_signature(payload: bytes, signature: str) -> bool:
    """
    Verify the X-Hub-Signature-256 header against the HMAC-SHA256
    of the raw payload using our secret.
    """
    mac = hmac.new(WEBHOOK_SECRET, payload, hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route("/webhook", methods=["POST"])
def webhook():
    # 1. Verify request signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(request.data, signature):
        abort(401, "Invalid signature")

    # 2. Only handle pull_request events for open, reopen, or synchronize
    event  = request.headers.get("X-GitHub-Event", "")
    action = request.json.get("action", "")
    if event != "pull_request" or action not in ("opened", "reopened", "synchronize"):
        return "Ignored", 200

    # 3. Extract repository info and PR head branch
    repo_info = request.json["repository"]
    owner     = repo_info["owner"]["login"]
    repo_name = repo_info["name"]
    pr_ref    = request.json["pull_request"]["head"]["ref"]
    path      = "README.md"

    try:
        repo = gh.get_repo(f"{owner}/{repo_name}")

        # 4. Fetch current README content from the PR branch
        contents = repo.get_contents(path, ref=pr_ref)
        current  = base64.b64decode(contents.content).decode("utf-8")

        # Debug: log branch and existing Last PR line
        print(f"🔔 Processing PR branch: {pr_ref}")
        match_current = re.search(r"Last PR: .+", current)
        print(
            "    current Last PR line:",
            match_current.group(0) if match_current else "<none>"
        )

        # 5. Build a new timestamp without microseconds
        now = datetime.datetime.utcnow().replace(microsecond=0)
        ts  = now.isoformat() + "Z"

        # Replace or append the Last PR line
        if "Last PR:" in current:
            updated = re.sub(r"Last PR: .+", f"Last PR: {ts}", current)
        else:
            updated = current + f"\n\nLast PR: {ts}\n"

        # Debug: log new Last PR line (guard against None)
        match_updated = re.search(r"Last PR: .+", updated)
        print(
            "    updated Last PR line:",
            match_updated.group(0) if match_updated else "<none>"
        )

        # 6. Skip update if content has not changed
        if updated == current:
            print("✅ README unchanged")
        else:
            # 7. Commit the change back to the PR’s head branch
            repo.update_file(
                path=path,
                message=f"docs: update Last PR timestamp ({ts})",
                content=updated,
                sha=contents.sha,
                branch=pr_ref
            )
            print("✅ README updated and submitted")

    except Exception as e:
        # Log any unexpected error
        print("❌ Operation failed:", e)

    return "OK", 200

if __name__ == "__main__":
    # Start the Flask development server on all interfaces
    app.run(host="0.0.0.0", port=PORT)
