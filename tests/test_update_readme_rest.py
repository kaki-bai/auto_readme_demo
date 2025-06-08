import os
import sys
import pytest
import requests
from pathlib import Path
from update_readme_rest import (
    fetch_latest_commit_info,
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

def test_fetch_latest_commit_info_no_token(capsys):
    """When GITHUB_TOKEN is missing, the function should exit with an error."""
    with pytest.raises(SystemExit) as excinfo:
        fetch_latest_commit_info("owner", "repo")
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Error: GITHUB_TOKEN not set." in captured.out

def test_fetch_latest_commit_info_success(monkeypatch):
    """Simulate a successful GitHub API response and verify output parsing."""
    fake_iso = "2025-06-05T12:34:56Z"
    fake_msg = "Fix all the bugs\n\nDetailed description..."
    fake_json = {
        "commit": {
            "author": {"date": fake_iso},
            "message": fake_msg
        }
    }

    # Set a dummy token in the environment
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token")

    # Stub out requests.get to return our fake response
    def fake_get(url, headers):
        expected_url = f"{GITHUB_API}/repos/owner/repo/commits/main"
        assert url == expected_url
        assert headers["Authorization"].startswith("token ")
        return DummyResp(fake_json)

    monkeypatch.setattr(requests, "get", fake_get)

    # Call the function and verify it returns correctly formatted timestamp and message
    ts, msg = fetch_latest_commit_info("owner", "repo")
    assert ts == "2025-06-05 12:34:56"
    assert msg == "Fix all the bugs"

def test_update_file_with_github_info(monkeypatch, tmp_path):
    """End-to-end test of update_file_with_github_info with mocked commit info."""
    # 1. Create a temporary README.md file with the marker section
    readme = tmp_path / "README.md"
    readme.write_text(
        "Start\n"
        "<!-- AUTO_SECTION_START -->\n"
        "old content\n"
        "<!-- AUTO_SECTION_END -->\n"
        "End\n",
        encoding="utf-8"
    )

    # 2. Set a dummy token and stub fetch_latest_commit_info to return fixed values
    monkeypatch.setenv("GITHUB_TOKEN", "dummy_token")
    def fake_fetch(owner, repo):
        return "2000-01-01 00:00:00", "Initial commit"
    monkeypatch.setattr("update_readme_rest.fetch_latest_commit_info", fake_fetch)

    # 3. Run the update function
    update_file_with_github_info(readme, "owner", "repo")

    # 4. Verify that README.md contains the new timestamp and commit message
    updated = readme.read_text(encoding="utf-8")
    assert "- Last updated: 2000-01-01 00:00:00" in updated
    assert "- Commit message: Initial commit" in updated

    # 5. Verify that a backup file was created with the original content
    backup = tmp_path / "README.md.bak"
    assert backup.exists()
    assert "old content" in backup.read_text(encoding="utf-8")