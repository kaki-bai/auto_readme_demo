import os
import sys
import pytest
import requests
from pathlib import Path
from update_readme_rest import (
    fetch_latest_user_commit_info,
    update_file_with_github_info,
    GITHUB_API
)

class DummyResp:
    """A dummy response object for simulating requests.get responses."""
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        """Raise an HTTPError if the status code indicates a failure."""
        if not (200 <= self.status_code < 300):
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        """Return the JSON payload."""
        return self._json

@pytest.fixture(autouse=True)
def clear_token(monkeypatch):
    """Ensure GITHUB_TOKEN is not set in the environment before each test."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    yield
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

def test_fetch_latest_user_commit_info_skips_ci_commits(monkeypatch):
    """fetch_latest_user_commit_info should skip CI-generated commits."""
    # Prepare a list of commits: first two are CI, third is a real commit
    fake_commits = [
        {"commit": {"author": {"date": "2025-01-01T00:00:00Z"}, "message": "ci: auto-update README section"}},
        {"commit": {"author": {"date": "2025-02-02T00:00:00Z"}, "message": "ci: auto-update README section"}}, 
        {"commit": {"author": {"date": "2025-03-03T00:00:00Z"}, "message": "Add new feature"}}
    ]
    # Stub environment and requests.get
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token")
    def fake_get(url, headers, params):
        # Expect per_page=10, sha=main
        assert params["sha"] == "main" and params["per_page"] == 10
        return DummyResp(fake_commits)
    monkeypatch.setattr(requests, "get", fake_get)

    ts, msg = fetch_latest_user_commit_info("owner", "repo")
    # Should pick the third commit
    assert ts == "2025-03-03 00:00:00"
    assert msg == "Add new feature"

def test_fetch_latest_user_commit_info_all_ci(monkeypatch):
    """If all recent commits are CI commits, fallback to the very latest one."""
    fake_commits = [
        {"commit": {"author": {"date": "2025-04-04T12:00:00Z"}, "message": "ci: auto-update README section"}}
    ]
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token")
    def fake_get(url, headers, params):
        return DummyResp(fake_commits)
    monkeypatch.setattr(requests, "get", fake_get)

    ts, msg = fetch_latest_user_commit_info("owner", "repo")
    # Expect fallback to the only commit available
    assert ts == "2025-04-04 12:00:00"
    assert msg == "ci: auto-update README section"

def test_integration_with_rest(monkeypatch, tmp_path):
    """End-to-end test for update_file_with_github_info using REST logic."""
    # 1. Create temporary README.md
    readme = tmp_path / "README.md"
    readme.write_text(
        "Intro\n"
        "<!-- AUTO_SECTION_START -->\n"
        "old\n"
        "<!-- AUTO_SECTION_END -->\n",
        encoding="utf-8"
    )

    # 2. Stub fetch_latest_user_commit_info to return known timestamp/message
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token")
    def fake_user_info(owner, repo):
        return "1999-12-31 23:59:59", "Final commit"
    monkeypatch.setattr("update_readme_rest.fetch_latest_user_commit_info", fake_user_info)

    # 3. Call update function
    from update_readme_rest import update_file_with_github_info
    update_file_with_github_info(readme, "owner", "repo")

    # 4. Verify README.md content and backup
    updated = readme.read_text(encoding="utf-8")
    assert "- Last updated: 1999-12-31 23:59:59" in updated
    assert "- Commit message: Final commit" in updated
    bak = tmp_path / "README.md.bak"
    assert bak.exists() and "old" in bak.read_text(encoding="utf-8")