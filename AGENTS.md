# Repository Guidelines

## Project Structure & Module Organization
- `prompt/` holds OCR prompt inputs and variants used during experiments.
- `test_pic/` contains sample images, spreadsheets, and expected output artifacts for manual checks.
- `README.md` is the minimal project overview; keep it updated as functionality grows.
- `.venv/` is a local Python environment; avoid relying on it as a source of truth.

## Build, Test, and Development Commands
There are no build or runtime scripts committed yet. If you add automation, document it here and keep commands runnable from the repo root. Example conventions:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ocr_engine
```

## Python and PKG version
Python use 3.11.7
PaddlePaddle use 3.2.0

## Coding Style & Naming Conventions
- Current repo has no source files; if you add Python, follow PEP 8 with 4‑space indentation.
- Prefer descriptive, domain‑specific names (e.g., `ocr_pipeline.py`, `extract_tables.py`).
- Keep data files in `test_pic/` and prompts in `prompt/` to avoid cluttering the root.

## Testing Guidelines
- No automated tests are present. If you introduce tests, place them in a `tests/` folder and name them `test_*.py` (or align with the language you introduce).
- Include a short “how to run” note in this file once a test runner is added.

## Commit & Pull Request Guidelines
- Git history only shows “Initial commit,” so no formal convention exists yet.
- Use short, imperative commit messages (e.g., `Add table OCR sample`).
- PRs should include a clear summary, input/output examples (files or screenshots), and any manual validation steps.

## Security & Data Handling
- Assume test assets may include sensitive data; sanitize or anonymize before committing.
- Avoid committing model weights or large binaries unless explicitly required and documented.