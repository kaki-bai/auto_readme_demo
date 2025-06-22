# app.py
import os
import hmac
import hashlib
import base64
import re
import datetime
import random
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
    Verify the X-Hub-Signature-256 header matches our HMAC-SHA256 digest.
    """
    mac = hmac.new(WEBHOOK_SECRET, payload, hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, signature)

def generate_fake_data() -> dict:
    """
    Simulate fetching deployment info.
    Returns a dict with keys cluster, machine, queue.
    """
    clusters = ["alpha", "beta", "gamma", "delta"]
    machines = ["x1", "x2", "x3", "x4"]
    return {
        "cluster": random.choice(clusters),
        "machine": random.choice(machines),
        "queue": random.randint(0, 100)
    }

@app.route("/webhook", methods=["POST"])
def webhook():
    # 1. Verify that the request really came from GitHub
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(request.data, signature):
        abort(401, "Invalid signature")

    # 2. Only respond to pull_request opened/reopened/synchronize events
    event  = request.headers.get("X-GitHub-Event", "")
    action = request.json.get("action", "")
    if event != "pull_request" or action not in ("opened", "reopened", "synchronize"):
        return "Ignored", 200

    # 3. Extract repo info and PR branch/sha
    repo_info = request.json["repository"]
    owner     = repo_info["owner"]["login"]
    repo_name = repo_info["name"]
    pr        = request.json["pull_request"]
    pr_ref    = pr["head"]["ref"]
    head_sha  = pr["head"]["sha"]
    path      = "README.md"

    repo = gh.get_repo(f"{owner}/{repo_name}")

    # 4. Prevent infinite loop by skipping when our own commit triggered this
    try:
        last_commit = repo.get_commit(head_sha)
        if last_commit.commit.message.startswith("docs: update deploy"):
            print("⚠️ Skipping bot-generated commit")
            return "OK", 200
    except Exception:
        pass

    try:
        # 5. Retrieve current README from the PR branch
        contents = repo.get_contents(path, ref=pr_ref)
        current  = base64.b64decode(contents.content).decode("utf-8")

        print(f"🔔 Processing PR branch: {pr_ref}")

        # 6. Generate timestamp and fake deployment info
        now = datetime.datetime.utcnow().replace(microsecond=0)
        ts  = now.isoformat() + "Z"
        fake = generate_fake_data()

        # 7. Build new Markdown block
        deploy_block = "\n".join([
            "**Deploy Info**:",
            f"- cluster=`{fake['cluster']}`",
            f"- machine=`{fake['machine']}`",
            f"- queue=`{fake['queue']}`"
        ])
        last_pr_line = f"**Last PR**: {ts}"

        # 8. Replace or append the deploy block
        if "**Deploy Info**:" in current:
            # replace existing block (from Deploy Info: down to Last PR line)
            updated = re.sub(
                r"\*\*Deploy Info\*\*:[\s\S]*?\*\*Last PR\*\*:[^\n]*",
                f"{deploy_block}\n\n{last_pr_line}",
                current
            )
        else:
            # append at end
            updated = f"{current.rstrip()}\n\n{deploy_block}\n\n{last_pr_line}\n"

        print("    Preview of updated block:")
        for line in updated.splitlines()[-6:]:
            print("    ", line)

        # 9. Commit only if there is a real change
        if updated != current:
            repo.update_file(
                path=path,
                message=f"docs: update deploy info & Last PR ({ts})",
                content=updated,
                sha=contents.sha,
                branch=pr_ref
            )
            print("✅ README updated successfully")
        else:
            print("✅ No changes detected in README")

    except Exception as e:
        print("❌ Operation failed:", e)

    return "OK", 200

if __name__ == "__main__":
    # Launch the Flask development server
    app.run(host="0.0.0.0", port=PORT)
