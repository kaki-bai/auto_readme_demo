import os
import sys
import pytest
import requests
from pathlib import Path
from update_readme_graphql import (
    fetch_latest_user_commit_info_graphql,
    update_file_with_github_info,
    GITHUB_GRAPHQL,
    CI_PREFIX
)

class DummyResponse:
    """A dummy response object for simulating requests.post."""
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        """Raise an HTTPError if the status indicates failure."""
        if not (200 <= self.status_code < 300):
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        """Return the JSON payload."""
        return self._json

@pytest.fixture(autouse=True)
def clear_token(monkeypatch):
    """Ensure GITHUB_TOKEN is unset before each test."""
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    yield
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)

def test_fetch_latest_user_commit_info_skips_ci(monkeypatch):
    """Should skip commits starting with CI_PREFIX."""
    # Prepare nodes: two CI commits, one user commit
    nodes = [
        {'committedDate': '2025-01-01T00:00:00Z', 'message': CI_PREFIX + ' section'},
        {'committedDate': '2025-02-02T00:00:00Z', 'message': CI_PREFIX + ' section again'},
        {'committedDate': '2025-03-03T12:34:56Z', 'message': 'New feature added'}
    ]
    fake_json = {'data': {'repository': {'ref': {'target': {'history': {'nodes': nodes}}}}}}

    # Set dummy token
    monkeypatch.setenv('GITHUB_TOKEN', 'dummy')

    # Stub requests.post
    def fake_post(url, json, headers):
        assert url == GITHUB_GRAPHQL
        assert headers['Authorization'].startswith('bearer ')
        # Ensure variables included
        assert json['variables']['first'] == 10
        return DummyResponse(fake_json)
    monkeypatch.setattr(requests, 'post', fake_post)

    ts, msg = fetch_latest_user_commit_info_graphql('owner', 'repo')
    assert ts == '2025-03-03 12:34:56'
    assert msg == 'New feature added'


def test_fetch_latest_user_commit_info_all_ci(monkeypatch):
    """If all commits are CI, fallback to first node."""
    nodes = [
        {'committedDate': '2025-04-04T11:11:11Z', 'message': CI_PREFIX + ' update'}
    ]
    fake_json = {'data': {'repository': {'ref': {'target': {'history': {'nodes': nodes}}}}}}

    monkeypatch.setenv('GITHUB_TOKEN', 'dummy')
    monkeypatch.setattr(requests, 'post', lambda url, json, headers: DummyResponse(fake_json))

    ts, msg = fetch_latest_user_commit_info_graphql('owner', 'repo')
    assert ts == '2025-04-04 11:11:11'
    assert msg == CI_PREFIX + ' update'


def test_update_file_with_github_info_graphql(monkeypatch, tmp_path):
    """Integration-like test for update_file_with_github_info using GraphQL logic."""
    # Create temporary README.md with marker
    readme = tmp_path / 'README.md'
    readme.write_text(
        'Header\n'
        '<!-- AUTO_SECTION_START -->\n'
        'old content\n'
        '<!-- AUTO_SECTION_END -->\n'
        'Footer\n',
        encoding='utf-8'
    )

    # Stub fetch_latest_user_commit_info_graphql
    monkeypatch.setenv('GITHUB_TOKEN', 'dummy')
    def fake_fetch(owner, repo):
        return '1999-09-09 09:09:09', 'Test commit message'
    monkeypatch.setattr('update_readme_graphql.fetch_latest_user_commit_info_graphql', fake_fetch)

    # Call update
    update_file_with_github_info(readme, 'owner', 'repo')

    updated = readme.read_text(encoding='utf-8')
    assert '- Last updated: 1999-09-09 09:09:09' in updated
    assert '- Commit message: Test commit message' in updated

    # Backup file exists
    bak = tmp_path / 'README.md.bak'
    assert bak.exists()
    assert 'old content' in bak.read_text(encoding='utf-8')