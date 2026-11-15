# Auto-tests for Met Museum API

This project is intended to check the Metropolitan Museum of Art Collection API with Python,
Pytest, Requests and Pydantic 2.

Origin github repository: https://github.com/metmuseum/openaccess/

Official documentation: https://metmuseum.github.io/

### What this project tests:

- HTTP 200
- HTTP 404
- Pydantic-model
- Search for works by keyword
- No search results (for `objectIDs` is `null` or `[]`)
- Limiting the number of results (1, 5, 20, 100, 500)
- Absence of duplicate identifiers on adjacent pages
- Filtering by museum department, selected works, and dates
- Validation of erroneous data structures and parameters

The search returns only identifiers. To verify the filters, the tests additionally request the metadata for the found item.

### How to start

You need Python 3.10 or newer.
Recomended to connect Venv for the project requirements.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Then install the requirements:

```bash
python -m pip install -r requirements-dev.txt
```

After that simply run the tests:

```bash
python -m pytest
```

Also you can try other methods:

```bash
# Local tests
pytest -m "not integration"

# Only real HTTP-tests
pytest -m integration

# Style check and detailed output
ruff check .
pytest -v
```
