import argparse
import re
import sys
import os
from pathlib import Path
from datetime import datetime


class MarkerNotFoundError(Exception):
    """Raised when the specified marker is not found in the file."""

    pass


def update_file(
    path: Path, status: str = "✅", markers: list = ["AUTO_SECTION"]
) -> str:
    """
    Read the file at `path`, replace each marker section with a new timestamp and status,
    back up the original file as <filename>.bak, then overwrite the original file.
    Returns the updated content as a string.

    :param path: Path to the file to update
    :param status: Deployment status string to insert (e.g., "✅", "❌")
    :param markers: List of marker prefixes (e.g., ["AUTO_SECTION", "ANOTHER_MARKER"])
    :raises MarkerNotFoundError: if any marker pair is not found
    :raises Exception: for other I/O or regex errors
    """
    content = path.read_text(encoding="utf-8")
    updated = content

    for marker in markers:
        start_marker = f"<!-- {marker}_START -->"
        end_marker = f"<!-- {marker}_END -->"
        # Escape markers to avoid regex injection
        pattern = rf"({re.escape(start_marker)})(.*?)({re.escape(end_marker)})"

        # Check if this marker exists
        if not re.search(pattern, updated, flags=re.DOTALL):
            raise MarkerNotFoundError(f"No markers found for '{marker}' in {path}")

        # Build replacement snippet
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_section = (
            f"{start_marker}\n"
            f"- Last updated: {now}\n"
            f"- Deployment status: {status}\n"
            f"{end_marker}"
        )

        # Perform replacement (DOTALL so '.' matches newlines)
        updated = re.sub(pattern, new_section, updated, flags=re.DOTALL)

    # Backup original file
    backup_path = path.with_suffix(path.suffix + ".bak")
    path.rename(backup_path)

    # Write updated content back
    path.write_text(updated, encoding="utf-8")
    return updated


def main():
    parser = argparse.ArgumentParser(
        description="Auto-update sections in README.md with timestamp and status"
    )
    parser.add_argument(
        "--status",
        default="✅",
        help="Deployment status string to insert (default: '✅')",
    )
    parser.add_argument(
        "--markers",
        default="AUTO_SECTION",
        help="Comma-separated list of marker prefixes (e.g., 'AUTO_SECTION,OTHER_MARKER')",
    )
    args = parser.parse_args()

    markers = [m.strip() for m in args.markers.split(",") if m.strip()]
    readme_path = Path("README.md")

    if not readme_path.is_file():
        print(f"Error: {readme_path} does not exist.")
        sys.exit(1)

    try:
        update_file(readme_path, status=args.status, markers=markers)
        print(f"README.md has been updated with markers {markers}.")
    except MarkerNotFoundError as e:
        print(f"Warning: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
