<!-- AUTO_SECTION_START -->
- Last updated: 2025-06-10 02:08:31
- Commit message: Merge pull request #9 from kaki-bai/test/pr-trigger
- Deployment status: ✅
<!-- AUTO_SECTION_END -->

# Auto README Updater

- Auto-update designated sections in `README.md` with the current timestamp and deployment status via `update_readme.py`.  
- Includes a GitHub Actions workflow that runs on `PRs` and on pushes to `main` to keep those sections up to date.

---

## Project Structure

```
auto_readme/
├── update_readme.py                # Main script to auto-update README markers
├── README.md                       # Project README (this file)
├── requirements.txt                # List of Python dependencies
├── .github/
│   └── workflows/
│       └── auto_update_readme.yml  # GitHub Actions workflow
└── tests/
│   └── test_update_readme.py       # Pytest unit tests for update_readme.py
```

- **`update_readme.py`**  
  Python script that:
  1. Finds one or more marker sections in `README.md`.
  2. Retrieves the current date & time.
  3. Inserts a “Last updated” line and a “Deployment status” line within each marker section.
  4. Backs up the original `README.md` as `README.md.bak`.
  5. Overwrites `README.md` with the updated content.

- **`.github/workflows/auto_update_readme.yml`**  
  GitHub Actions workflow that runs on pull requests (via `pull_request_target`) and, optionally, on pushes to `main`. It:
  1. Checks out the repository with full history and write permissions.
  2. Sets up Python 3.9.
  3. Installs dependencies from `requirements.txt`.
  4. Runs `update_readme.py`.
  5. Commits and pushes any changes to `README.md` back to the PR branch (or `main`).

- **`tests/test_update_readme.py`**  
  Pytest-based unit tests covering:
  1. Single-marker replacement.
  2. Handling missing markers (`MarkerNotFoundError`).
  3. Multiple-marker replacement.
  4. Backup file behavior.

---

## Prerequisites

- **Python 3.9+**  
- **Git** (for version control)  
- **Virtual Environment** (strongly recommended)  

---

## Installation

1. Clone this repository
   ```bash
   git clone https://github.com/your-username/auto_readme_demo.git
   cd auto_readme_demo
   ```

2. Create and activate a virtual environment
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   - The only runtime dependency is:
   ```bash
   pytest>=7.1.1  # for running unit tests
   ```

---

## Usage

### Basic Example

1. Ensure your `README.md` has a marker section in the following format:

   ```markdown
   # Project Title

   Some introductory text.

   <!-- AUTO_SECTION_START -->
- Last updated: 2025-06-10 02:08:31
- Commit message: Merge pull request #9 from kaki-bai/test/pr-trigger
- Deployment status: ✅
<!-- AUTO_SECTION_END -->

   Some concluding text.
   ```

2. Run the script from the project root:
   ```bash
   python3 update_readme.py
   ```

3. Open README.md and verify that the marker section has been replaced with something like:

   ```markdown
   <!-- AUTO_SECTION_START -->
- Last updated: 2025-06-10 02:08:31
- Commit message: Merge pull request #9 from kaki-bai/test/pr-trigger
- Deployment status: ✅
<!-- AUTO_SECTION_END -->
   ```

---

### Command-Line Options

`update_readme.py` supports the following optional arguments:

- `status`
  - Description: Custom deployment status string to be inserted.
  - Default: ✅
  - Example:
     ```bash
     python3 update_readme.py --status "⚙️ In Progress"
     ```

- `markers`
  - Description: Comma-separated list of marker prefixes. Each prefix generates a pair of markers:
`<!-- <PREFIX>_START --> … <!-- <PREFIX>_END -->`.
  - Default: "AUTO_SECTION"
  - Example (two markers):
     ```bash
     python3 update_readme.py --markers "AUTO_SECTION,SECOND_MARKER"
     ```

Full invocation example:
```bash
python3 update_readme.py --status "❌ Failed" --markers "AUTO_SECTION,SECOND_MARKER"
```

---

### Marker Format in README.md

The script looks for marker pairs in this format:

```markdown
<!-- <PREFIX>_START -->
(any content here will be replaced)
<!-- <PREFIX>_END -->
```

- `<PREFIX>` can be any uppercase identifier (e.g., AUTO_SECTION, SECOND_MARKER).
- For each `<PREFIX>`, the script will:
	1. Replace everything between `<PREFIX>_START` and `<PREFIX>_END` (inclusive) with:
   ```markdown
   <!-- <PREFIX>_START -->
   - Last updated: YYYY-MM-DD HH:MM:SS
   - Deployment status: <STATUS>
   <!-- <PREFIX>_END -->
   ```

	2. Create a backup of the original file named README.md.bak.
