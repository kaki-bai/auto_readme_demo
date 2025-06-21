# app.py
import os
import hmac
import hashlib
import base64
import re
from flask import Flask, request, abort
from github import Github
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET").encode()
PORT           = int(os.getenv("PORT", 3000))

if not GITHUB_TOKEN or not WEBHOOK_SECRET:
    print("Error: Please set GITHUB_TOKEN and WEBHOOK_SECRET in .env")
    exit(1)

# Initialize Flask app and PyGithub client
app = Flask(__name__)
gh  = Github(GITHUB_TOKEN)

def verify_signature(payload, signature):
    """
    Verify X-Hub-Signature-256 header
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

    # 2. Only process pull_request events for opened, reopened, or synchronize actions
    event  = request.headers.get("X-GitHub-Event", "")
    action = request.json.get("action", "")
    if event != "pull_request" or action not in ("opened", "reopened", "synchronize"):
        return "Ignored", 200

    # 3. Extract repository and file path information
    repo_info = request.json["repository"]
    owner     = repo_info["owner"]["login"]
    repo_name = repo_info["name"]
    pr_ref    = request.json["pull_request"]["head"]["ref"]
    path      = "README.md"

    try:
        repo = gh.get_repo(f"{owner}/{repo_name}")

        # 4. Retrieve current README content
        contents = repo.get_contents(path, ref=pr_ref)
        current  = base64.b64decode(contents.content).decode("utf-8")

        # 5. Update logic: insert or replace "Last PR: timestamp"
        import datetime
        ts = datetime.datetime.utcnow().isoformat() + "Z"
        if "Last PR:" in current:
            updated = re.sub(r"Last PR: .+", f"Last PR: {ts}", current)
        else:
            updated = current + f"\n\nLast PR: {ts}\n"

        # 6. Skip update if content is unchanged
        if updated == current:
            print("✅ README unchanged")
        else:
            repo.update_file(
                path,
                f"docs: update Last PR timestamp ({ts})",
                updated,
                contents.sha,
                branch=pr_ref
            )
            print("✅ README updated and submitted")
    except Exception as e:
        print("❌ Operation failed:", e)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
