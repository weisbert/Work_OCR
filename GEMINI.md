# GEMINI.md

## Project Overview

This project is a desktop OCR (Optical Character Recognition) application for Windows, built with Python. Its primary purpose is to capture regions of the screen, recognize text within them, and be particularly effective at extracting tabular data (like from an Excel spreadsheet screenshot) into a machine-readable format.

The application uses **PySide6** for its graphical user interface and a **PaddleOCR** wrapper for the core recognition engine, configured specifically for CPU-only execution. This makes it accessible for systems without a dedicated GPU.

The project is structured into several key modules to separate concerns:
*   `app.py`: The main application entry point, handling the GUI and overall orchestration.
*   `capture.py`: Manages screen capture functionality, including a Snipaste-like overlay for region selection.
*   `ocr_engine.py`: A wrapper around the `PaddleOCR` library.
*   `layout.py`: Handles the analysis of OCR results to reconstruct table structures (TSV format) or preserve text formatting.
*   `postprocess.py`: Provides tools for post-processing extracted data, such as unit conversion and thresholding for tabular data.
*   `hotkey_manager.py`: Manages global hotkeys for triggering screen captures.

## Building and Running

### Dependencies

The project's dependencies are listed in `requirements.txt`. To install them, it is recommended to first create a virtual environment, and then run:

```bash
pip install -r requirements.txt
```

To install development dependencies for running tests, use:
```bash
pip install -r requirements.txt -e .[dev]
```

### Running the Application

The application can be run in two ways after installation:

1.  **As a module:**
    ```bash
    python -m work_ocr
    ```

2.  **Using the script entry point** (after `pip install -e .`):
    ```bash
    work-ocr
    ```

### Running Tests

The project uses `pytest` for testing. The tests are located in the `tests/` directory. To run the tests, execute the following command from the project root:

```bash
pytest
```

## Development Conventions

*   **Code Structure:** The project is modular, with responsibilities divided among the files in `src/work_ocr/`. This separation of concerns should be maintained.
*   **Testing:** New functionality should be accompanied by tests in the `tests/` directory, using the `pytest` framework. The existing tests serve as a good example.
*   **Environment:** The application is designed to run in a **CPU-only** environment. No GPU or CUDA dependencies should be introduced.
*   **Configuration:** User settings are stored in a `config.json` file, which is generated at runtime.
*   **Comments:** All code comments should be written in English.
