# Work_OCR - AI Coding Agent Guide

## Project Overview

Work_OCR is a desktop OCR (Optical Character Recognition) application designed for Windows 11 + CPU-only environments. It captures screen regions, recognizes text using PaddleOCR, and excels at extracting tabular data from screenshots (like Excel tables) into machine-readable TSV format.

### Key Features
- Screenshot region selection (Snipaste-like interaction)
- Table mode: outputs TSV format that can be directly pasted into Excel
- Text mode: preserves layout with line breaks and indentation
- Table post-processing: threshold replacement, unit conversion, engineering notation conversion
- Real-time progress display and logging

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11 |
| GUI Framework | PySide6 |
| OCR Engine | PaddleOCR 3.4.0 + PaddlePaddle 3.2.0 (CPU) |
| Image Processing | OpenCV (cv2), PIL/Pillow |
| Testing | unittest, pytest, pytest-qt |

### Key Dependencies
- `paddlepaddle==3.2.0` - Deep learning framework (CPU-only)
- `paddleocr==3.4.0` - OCR toolkit
- `PySide6` - Qt bindings for Python GUI
- `opencv-contrib-python` - Image processing
- `numpy`, `pandas` - Numerical and data manipulation

## Project Structure

```
Work_OCR/
├── app.py              # Main application entry point, GUI (MainWindow, OcrWorker)
├── capture.py          # Screen capture functionality (CaptureWindow)
├── ocr_engine.py       # PaddleOCR wrapper (OCREngine class)
├── layout.py           # Layout analysis: table reconstruction & text layout
├── postprocess.py      # Data post-processing: threshold, unit conversion, notation
├── manual_test.py      # Standalone manual test script for OCR engine
├── requirements.txt    # Python dependencies
├── tests/              # Unit tests
│   ├── test_app.py
│   ├── test_capture.py
│   ├── test_layout.py
│   ├── test_ocr_engine.py
│   └── test_postprocess.py
├── test_pic/           # Test images
│   ├── test_pic1_data_table.png
│   ├── test_pic1_data_table_anwser.txt
│   └── current_data.xlsx
└── prompt/             # Requirements documentation (Chinese)
    └── needs.txt
```

## Module Responsibilities

### `app.py`
- `MainWindow`: Main GUI window with image preview, results tabs, and controls
- `OcrWorker`: QThread subclass for running OCR pipeline without freezing UI
- Orchestrates capture → OCR → layout → post-processing pipeline

### `capture.py`
- `CaptureWindow`: Full-screen semi-transparent overlay for region selection
- Emits `screenshot_completed` signal with captured QPixmap
- Supports mouse drag selection and Escape key cancellation

### `ocr_engine.py`
- `OCREngine`: Wrapper around PaddleOCR
- Handles model initialization, image preprocessing (padding), and recognition
- Configured for CPU-only execution with MKL-DNN disabled
- Returns OCR result as list of tuples: `[(bbox, text, score), ...]`

### `layout.py`
- `detect_mode()`: Heuristic detection of table vs text layout
- `reconstruct_table()`: Converts OCR results to TSV format using row/column clustering
- `reconstruct_text()`: Preserves text layout with spacing
- `normalize_bbox()`: Normalizes bounding box formats

### `postprocess.py`
- `ParsedValue`: Dataclass for parsed numeric values with engineering prefixes
- `PostprocessSettings`: Configuration dataclass for post-processing options
- `parse_cell()`: Parses values like "5.1k", "10nF", "1.23e-4"
- `apply_threshold()`, `convert_unit()`, `process_tsv()`: Processing functions
- Supports engineering prefixes: f, p, n, u, m, k, M, G

## Build and Run Commands

### Setup Environment
```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run Application
```bash
python app.py
```

### Run Tests
```bash
# Run all tests with unittest
python -m unittest discover tests

# Run all tests with pytest
pytest

# Run specific test file
pytest tests/test_layout.py

# Run with verbose output
pytest -v
```

### Manual Testing
```bash
# Run manual OCR test on test image
python manual_test.py
```

## Testing Strategy

### Test Framework
- **unittest**: Standard library testing for logic modules (`test_layout.py`, `test_postprocess.py`, `test_ocr_engine.py`)
- **pytest + pytest-qt**: For Qt-related testing (`test_capture.py`, `test_app.py`)

### Test Categories
1. **Unit Tests**: Individual function testing (bbox normalization, cell parsing)
2. **Integration Tests**: OCR pipeline testing with mocked dependencies
3. **GUI Tests**: Qt widget behavior using qtbot fixture

### Running Tests Requirements
- For `test_capture.py` and `test_app.py`: Requires display/GUI environment
- For `test_ocr_engine.py`: Downloads PaddleOCR models on first run (may be slow)

## Development Conventions

### Code Style
- **Comments**: All code comments must be written in English
- **Type Hints**: Use Python type hints where applicable
- **Docstrings**: Use triple-quoted docstrings for classes and functions

### CPU-Only Constraint
- **CRITICAL**: The application is designed for CPU-only execution
- Environment variables are set at the top of `ocr_engine.py` to disable GPU/MKL features:
  ```python
  os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
  os.environ.setdefault("FLAGS_use_mkldnn", "0")
  os.environ.setdefault("FLAGS_enable_onednn", "0")
  ```
- Do NOT introduce CUDA or GPU dependencies

### File Organization
- Keep code organized into the 5 main modules as specified
- New functionality should fit into existing module structure
- Configuration persistence uses `config.json` (created at runtime)

### Error Handling
- Custom exceptions: `OCREngineError` for OCR-related errors
- Graceful degradation when optional dependencies are missing
- Worker thread emits error signals for GUI display

## Security Considerations

1. **Input Validation**: Image paths are converted to strings before passing to OpenCV
2. **Temporary Files**: Screenshots are saved to temporary files using `tempfile.mkstemp()`
3. **Environment Variables**: Paddle flags are set before importing paddle modules
4. **No Network**: Application works offline; models are downloaded once by PaddleOCR

## Configuration

The application uses a `config.json` file for persisting user settings:
- Threshold values and replacement strings
- Unit conversion target prefix
- Notation style preferences
- Copy strategy settings

Default config is created automatically if missing.

## Troubleshooting

### Common Issues

1. **PaddleOCR Model Download**: First run may take time to download models
2. **MKL-DNN Warnings**: Suppressed via environment variables in `ocr_engine.py`
3. **Qt Platform Plugin**: Ensure PySide6 is properly installed on Windows

### Debug Mode
- Check the log panel in the GUI for processing stage information
- Use `manual_test.py` to test OCR without GUI complications
- Set logger in `OCREngine` for detailed initialization timing
