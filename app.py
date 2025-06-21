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
    Verify the X-Hub-Signature-256 header matches the HMAC-SHA256
    digest of the raw payload using our secret.
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

    # 2. Only handle pull_request events for opened, reopened, or synchronize
    event  = request.headers.get("X-GitHub-Event", "")
    action = request.json.get("action", "")
    if event != "pull_request" or action not in ("opened", "reopened", "synchronize"):
        return "Ignored", 200

    # 3. Extract repository info and PR head branch & SHA
    repo_info = request.json["repository"]
    owner     = repo_info["owner"]["login"]
    repo_name = repo_info["name"]
    pr         = request.json["pull_request"]
    pr_ref     = pr["head"]["ref"]
    head_sha   = pr["head"]["sha"]
    path       = "README.md"

    repo = gh.get_repo(f"{owner}/{repo_name}")

    # 4. Skip if this commit was our own bot update
    try:
        last_commit = repo.get_commit(head_sha)
        last_msg    = last_commit.commit.message
        if last_msg.startswith("docs: update Last PR timestamp"):
            print("⚠️ Skipping bot commit:", last_msg)
            return "OK", 200
    except Exception:
        # if anything goes wrong fetching commit, just continue
        pass

    try:
        # 5. Fetch current README content from the PR branch
        contents = repo.get_contents(path, ref=pr_ref)
        current  = base64.b64decode(contents.content).decode("utf-8")

        # Debug: log branch and any existing "Last PR:" line
        print(f"🔔 Processing PR branch: {pr_ref}")
        curr_match = re.search(r"Last PR: .+", current)
        print("    current Last PR line:", curr_match.group(0) if curr_match else "<none>")

        # 6. Build a new timestamp (seconds precision only)
        now = datetime.datetime.utcnow().replace(microsecond=0)
        ts  = now.isoformat() + "Z"

        # 7. Insert or replace "Last PR:" line
        if curr_match:
            updated = re.sub(r"Last PR: .+", f"Last PR: {ts}", current)
        else:
            updated = f"{current.rstrip()}\n\nLast PR: {ts}\n"

        # Debug: log the new "Last PR:" line
        new_match = re.search(r"Last PR: .+", updated)
        print("    updated Last PR line:", new_match.group(0) if new_match else "<none>")

        # 8. Commit only if something actually changed
        if updated == current:
            print("✅ README unchanged")
        else:
            repo.update_file(
                path=path,
                message=f"docs: update Last PR timestamp ({ts})",
                content=updated,
                sha=contents.sha,
                branch=pr_ref
            )
            print("✅ README updated and submitted")

    except Exception as e:
        print("❌ Operation failed:", e)

    return "OK", 200

if __name__ == "__main__":
    # Start the Flask dev server on all network interfaces
    app.run(host="0.0.0.0", port=PORT)
