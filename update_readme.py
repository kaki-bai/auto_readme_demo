from pathlib import Path
import re
from datetime import datetime
import sys

# 1. Read the README.md file
readme_path = Path("README.md")
content = readme_path.read_text(encoding="utf-8")

# 2. Define the regex pattern to match the section between markers
pattern = r"(<!-- AUTO_SECTION_START -->)(.*?)(<!-- AUTO_SECTION_END -->)"

if not re.search(pattern, content, flags=re.DOTALL):
    print("Warning: No AUTO_SECTION markers found in README.md.")
    sys.exit(1)

# 3. Get the current date and time as a formatted string
now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")  # e.g., "2025-06-03 14:25:07"

# 4. Construct the new Markdown snippet with the dynamic timestamp
new_section = (
    "<!-- AUTO_SECTION_START -->\n"
    f"- Last updated: {timestamp}\n"
    "- Deployment status: ✅\n"
    "<!-- AUTO_SECTION_END -->"
)

# 5. Perform the replacement using re.sub (DOTALL so that '.' matches newlines)
updated_content = re.sub(pattern, new_section, content, flags=re.DOTALL)

# 6. Write the updated content back to README.md
readme_path.write_text(updated_content, encoding="utf-8")
print(f"README.md has been updated at {timestamp}")