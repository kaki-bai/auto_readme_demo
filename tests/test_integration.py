import subprocess
from pathlib import Path
import sys

def test_cli_end_to_end(tmp_path):
    # 1. Create a sample README.md in the temp directory
    readme = tmp_path / "README.md"
    readme.write_text(
        "Header\n\n"
        "<!-- AUTO_SECTION_START -->\n"
        "old content\n"
        "<!-- AUTO_SECTION_END -->\n",
        encoding="utf-8"
    )

    # 2. Compute the path to the script in the project root
    script_path = Path(__file__).parent.parent / "update_readme.py"

    # 3. Execute the script using the same Python interpreter
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0

    # 4. Assert that README.md was updated and a backup exists
    updated = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Last updated:" in updated
    assert (tmp_path / "README.md.bak").exists()