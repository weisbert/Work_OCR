# GEMINI.md

## Project Overview

This project is a desktop OCR (Optical Character Recognition) application for Windows, built with Python. Its primary purpose is to capture regions of the screen, recognize text within them, and be particularly effective at extracting tabular data (like from an Excel spreadsheet screenshot) into a machine-readable format.

The core of the application is the `ocr_engine.py`, which is a wrapper around the `PaddleOCR` library, configured for CPU-only execution. The project is designed to be a user-friendly tool for office and engineering workflows, allowing users to quickly convert images of text and tables into editable data.

The project requirements specify a multi-file structure, including a main application entry point (`app.py`), a screen capture module (`capture.py`), the OCR engine itself (`ocr_engine.py`), a layout analysis module for table reconstruction (`layout.py`), and a data post-processing module (`postprocess.py`).

## Building and Running

### Dependencies

The project's dependencies are listed in `requirements.txt`. To install them, run:

```bash
pip install -r requirements.txt
```

### Running the Application

The main entry point for the application is intended to be `app.py`. To run the application, use:

```bash
python app.py
```

*(Note: As of this writing, `app.py` has not been created yet.)*

### Running Tests

The project uses Python's built-in `unittest` framework for testing. The tests are located in the `tests/` directory. To run the tests, execute the following command from the project root:

```bash
python -m unittest discover tests
```

## Development Conventions

*   **Code Structure:** The project is structured into several modules, as detailed in `prompt/needs.txt`. This separation of concerns should be maintained.
    *   `app.py`: Main application and GUI.
    *   `capture.py`: Screen capture functionality.
    *   `ocr_engine.py`: OCR engine wrapper.
    *   `layout.py`: Table and text layout analysis.
    *   `postprocess.py`: Data post-processing and utility functions.
*   **Testing:** New functionality should be accompanied by tests in the `tests/` directory, using the `unittest` framework. The existing tests in `tests/test_ocr_engine.py` serve as a good example.
*   **Comments:** All code comments should be written in English.
*   **Environment:** The application is designed to run in a CPU-only environment. No GPU or CUDA dependencies should be introduced.
