import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import re
import pytest
from pathlib import Path
import tempfile
from update_readme import update_file, MarkerNotFoundError


@pytest.fixture
def single_marker(tmp_path):
    """
    Create a temporary README.md containing a single AUTO_SECTION marker.
    """
    readme = tmp_path / "README.md"
    content = """
# Project Title

Some intro text.

<!-- AUTO_SECTION_START -->
Old content that should be replaced.
<!-- AUTO_SECTION_END -->

Some closing text.
"""
    readme.write_text(content, encoding="utf-8")
    return readme


@pytest.fixture
def multiple_markers(tmp_path):
    """
    Create a temporary README.md containing two different markers: AUTO_SECTION and SECOND_MARKER.
    """
    readme = tmp_path / "README.md"
    content = """
# Project Title

<!-- AUTO_SECTION_START -->
Replace me once.
<!-- AUTO_SECTION_END -->

Middle section.

<!-- SECOND_MARKER_START -->
Replace me twice.
<!-- SECOND_MARKER_END -->

End section.
"""
    readme.write_text(content, encoding="utf-8")
    return readme


def test_update_single_marker(single_marker):
    """
    When update_file is called on a file with one AUTO_SECTION marker, it should:
    - Produce 'Last updated' and 'Deployment status' lines.
    - Create a backup file .bak.
    - Return the updated content.
    """
    # Run update_file
    updated_content = update_file(
        single_marker, status="TEST_STATUS", markers=["AUTO_SECTION"]
    )

    # Confirm backup exists
    backup_path = single_marker.with_suffix(".md.bak")
    assert backup_path.exists(), "Backup file was not created."

    # Check updated content contains the new 'Last updated' line and custom status
    # Use regex to match timestamp format and status
    assert re.search(
        r"<!-- AUTO_SECTION_START -->\s*- Last updated: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*- Deployment status: TEST_STATUS\s*<!-- AUTO_SECTION_END -->",
        updated_content,
        flags=re.DOTALL,
    )


def test_no_marker_raises(single_marker):
    """
    If the specified marker is not present, update_file should raise MarkerNotFoundError.
    """
    # Write a file without the marker
    no_marker_file = single_marker
    no_marker_file.write_text("# No markers here", encoding="utf-8")

    with pytest.raises(MarkerNotFoundError) as excinfo:
        update_file(no_marker_file, status="STATUS", markers=["AUTO_SECTION"])
    assert "No markers found for 'AUTO_SECTION'" in str(excinfo.value)


def test_update_multiple_markers(multiple_markers):
    """
    When update_file is called with multiple markers, it should replace each marker section in order.
    """
    # Run update_file with two markers
    updated_content = update_file(
        multiple_markers, status="STATUS_OK", markers=["AUTO_SECTION", "SECOND_MARKER"]
    )

    # Confirm backup exists
    backup_path = multiple_markers.with_suffix(".md.bak")
    assert backup_path.exists()

    # After first replacement, verify that AUTO_SECTION has correct format
    assert re.search(
        r"<!-- AUTO_SECTION_START -->\s*- Last updated: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*- Deployment status: STATUS_OK\s*<!-- AUTO_SECTION_END -->",
        updated_content,
        flags=re.DOTALL,
    )

    # After second replacement, verify that SECOND_MARKER has correct format
    assert re.search(
        r"<!-- SECOND_MARKER_START -->\s*- Last updated: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*- Deployment status: STATUS_OK\s*<!-- SECOND_MARKER_END -->",
        updated_content,
        flags=re.DOTALL,
    )


def test_backup_file_overwrite(single_marker):
    """
    If update_file is called twice on the same path, the second call should overwrite the previous .bak
    """
    # First update
    update_file(single_marker, status="FIRST", markers=["AUTO_SECTION"])
    bak1 = single_marker.with_suffix(".md.bak")
    assert bak1.exists()
    content_after_first = single_marker.read_text(encoding="utf-8")

    # Second update on the same path again (assuming .bak exists now)
    update_file(single_marker, status="SECOND", markers=["AUTO_SECTION"])
    bak2 = single_marker.with_suffix(".md.bak")
    assert bak2.exists()

    # The .bak file from the second run should contain the content after first update
    bak_content = bak2.read_text(encoding="utf-8")
    assert content_after_first == bak_content
