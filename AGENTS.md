# Work_OCR - AI Coding Agent Guide

## Project Overview

Work_OCR is a desktop OCR (Optical Character Recognition) application designed for Windows 11 + CPU-only environments. It captures screen regions, recognizes text using PaddleOCR, and excels at extracting tabular data from screenshots (like Excel tables) into machine-readable TSV format.

### Key Features
- Screenshot region selection with Snipaste-like interaction (drag to select, Esc to cancel)
- Table mode: outputs TSV format that can be directly pasted into Excel
- Text mode: preserves layout with line breaks and indentation
- Table post-processing: threshold replacement, unit conversion, engineering notation conversion
- Real-time progress display and logging
- Global hotkey support for quick screenshot capture (default: `Ctrl+Alt+S`)
- Copy strategies: All / Values Only / Units Only
- Three precision modes: PP-OCRv4 Server (High Precision) / PP-OCRv4 Server (Fast) / PP-OCRv4 Mobile (Super Fast)

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| GUI Framework | PySide6 |
| OCR Engine | PaddleOCR 3.4.0 + PaddlePaddle 3.2.0 (CPU) |
| Image Processing | OpenCV (cv2), PIL/Pillow |
| Global Hotkey | keyboard |
| Testing | unittest, pytest, pytest-qt |

### Key Dependencies
- `paddlepaddle==3.2.0` - Deep learning framework (CPU-only)
- `paddleocr==3.4.0` - OCR toolkit
- `PySide6>=6.0` - Qt bindings for Python GUI
- `keyboard>=0.13` - Global hotkey registration
- `opencv-contrib-python>=4.0` - Image processing
- `numpy>=1.20`, `pandas>=1.3` - Numerical and data manipulation

## Project Structure

```
Work_OCR/
├── src/
│   └── work_ocr/           # Main application package
│       ├── __init__.py     # Package initialization with public exports
│       ├── __main__.py     # Module entry point (python -m work_ocr)
│       ├── app.py          # Main GUI (MainWindow, OcrWorker)
│       ├── capture.py      # Screen capture (CaptureWindow)
│       ├── hotkey_manager.py  # Global hotkey management
│       ├── ocr_engine.py   # PaddleOCR wrapper (OCREngine)
│       ├── layout.py       # Layout analysis & reconstruction
│       └── postprocess.py  # Data post-processing pipeline
│
├── tests/                  # Unit tests
│   ├── test_app.py         # Main window and OcrWorker tests (pytest-qt)
│   ├── test_capture.py     # Capture window tests (pytest-qt)
│   ├── test_hotkey_manager.py  # Hotkey validation tests
│   ├── test_layout.py      # Layout reconstruction tests
│   ├── test_ocr_engine.py  # OCR engine tests
│   ├── test_ocr_accuracy.py  # OCR accuracy validation
│   └── test_postprocess.py  # Post-processing pipeline tests
│
├── scripts/                # Utility scripts
│   └── manual_test.py      # Standalone OCR test script
│
├── assets/                 # Project assets
│   └── test_images/        # Test images and expected outputs
│       ├── test_pic1_data_table.png
│       ├── test_pic1_data_table_anwser.txt
│       ├── test_pic2_code.png
│       ├── test_pic2_code.txt
│       └── current_data.xlsx
│
├── docs/                   # Documentation
│   └── prompt/             # Requirements (Chinese)
│       ├── needs.txt       # PRD + SRS document
│       └── code_prompt/    # Development prompts
│
├── pyproject.toml          # Project configuration (setuptools)
├── requirements.txt        # Python dependencies
├── config.json             # User configuration (auto-generated)
├── compare_ocr.py          # OCR result comparison utility
├── README.md               # User documentation (Chinese)
└── AGENTS.md               # This file
```

## Module Responsibilities

### `src/work_ocr/app.py`
- `MainWindow`: Main GUI window with image preview, results tabs, and controls
- `OcrWorker`: QThread subclass for running OCR pipeline without freezing UI
- Orchestrates capture → OCR → layout → post-processing pipeline
- Manages post-processing settings UI and real-time preview updates
- Handles clipboard operations with copy strategy support
- Supports three precision modes: high (server model + angle cls), fast (server model), superfast (mobile model)

### `src/work_ocr/capture.py`
- `CaptureWindow`: Full-screen semi-transparent overlay for region selection
- Emits `screenshot_completed` signal with captured QPixmap
- Emits `screenshot_cancelled` signal when user presses Escape or selects too small area
- Supports mouse drag selection and multi-monitor setups via virtual geometry
- Handles high-DPI displays with devicePixelRatio scaling

### `src/work_ocr/hotkey_manager.py`
- `HotkeyManager`: Manages global hotkey registration using the `keyboard` library
- Emits `screenshot_hotkey_pressed` signal when hotkey is triggered
- Provides hotkey validation and display formatting utilities
- Runs keyboard listener in a separate daemon thread

### `src/work_ocr/ocr_engine.py`
- `OCREngine`: Wrapper around PaddleOCR
- Handles model initialization, image preprocessing (padding), and recognition
- Configured for CPU-only execution with MKL-DNN disabled via environment variables
- Returns OCR result as list of tuples: `[(bbox, (text, score)), ...]`
- Custom exception: `OCREngineError`
- Supports multiple model configurations (server/mobile, angle classification)

### `src/work_ocr/layout.py`
- `detect_mode()`: Heuristic detection of table vs text layout based on vertical alignment
- `reconstruct_table()`: Converts OCR results to TSV format using row/column clustering with vertical projection histogram
- `reconstruct_text()`: Preserves text layout with spacing based on character width
- `reconstruct_text_with_postprocess()`: Enhanced text reconstruction with post-processing
- `post_process_text()`: Fixes common OCR issues (Markdown headers, punctuation spacing)
- `normalize_bbox()`: Normalizes bounding box formats (polygon or rectangle)

### `src/work_ocr/postprocess.py`
- `ParsedValue`: Dataclass for parsed numeric values with engineering prefixes
- `PostprocessSettings`: Configuration dataclass for post-processing options
- `parse_cell()`: Parses values like "5.1k", "10nF", "1.23e-4"
- `apply_threshold()`: Replaces values below threshold with specified string
- `convert_unit()`: Converts between engineering prefixes (f, p, n, u, m, k, M, G)
- `to_scientific()`: Converts to scientific notation (e.g., 1.00E-05)
- `to_engineering()`: Converts to engineering notation (e.g., 10.00E-06)
- `sci_to_prefix()`: Converts scientific notation to best engineering prefix
- `format_decimal()`: Formats Decimal values without scientific notation
- `process_tsv()`: Main pipeline processing TSV data with all enabled transformations
- `load_config()` / `save_config()`: Configuration persistence

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
# Method 1: Run as a module (recommended)
python -m work_ocr

# Method 2: Install in editable mode and use entry point
pip install -e .
work-ocr
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

# Run specific test class
pytest tests/test_postprocess.py::TestPostprocess
```

### Manual Testing
```bash
# Run manual OCR test on test image
python scripts/manual_test.py --image-path assets/test_images/test_pic1_data_table.png

# Run in fast mode
python scripts/manual_test.py --image-path assets/test_images/test_pic1_data_table.png --fast
```

## Testing Strategy

### Test Framework
- **unittest**: Standard library testing for logic modules (`test_layout.py`, `test_postprocess.py`, `test_ocr_engine.py`, `test_hotkey_manager.py`)
- **pytest + pytest-qt**: For Qt-related testing (`test_capture.py`, `test_app.py`)

### Test Categories
1. **Unit Tests**: Individual function testing (bbox normalization, cell parsing, hotkey validation)
2. **Integration Tests**: OCR pipeline testing with mocked dependencies
3. **GUI Tests**: Qt widget behavior using qtbot fixture
4. **Accuracy Tests**: OCR output validation against expected results (`test_ocr_accuracy.py`)

### Running Tests Requirements
- For `test_capture.py` and `test_app.py`: Requires display/GUI environment
- For `test_ocr_engine.py`: Downloads PaddleOCR models on first run (may be slow)
- For `test_hotkey_manager.py`: Tests hotkey validation logic without actual registration

## Development Conventions

### Code Style
- **Comments**: All code comments must be written in English
- **Type Hints**: Use Python type hints where applicable
- **Docstrings**: Use triple-quoted docstrings for classes and functions
- **File Encoding**: UTF-8 encoding declaration `# -*- coding: utf-8 -*-` at the top

### CPU-Only Constraint
- **CRITICAL**: The application is designed for CPU-only execution
- Environment variables are set at the top of `ocr_engine.py` to disable GPU/MKL features:
  ```python
  os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
  os.environ.setdefault("FLAGS_use_mkldnn", "0")
  os.environ.setdefault("FLAGS_enable_onednn", "0")
  os.environ.setdefault("FLAGS_enable_pir_api", "0")
  os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")
  ```
- Do NOT introduce CUDA or GPU dependencies

### File Organization
- Source code is organized under `src/work_ocr/` package
- Use relative imports within the package (e.g., `from . import ocr_engine`)
- Tests remain in `tests/` directory at project root
- Utility scripts go in `scripts/` directory
- Test images and assets go in `assets/test_images/`
- Configuration persistence uses `config.json` (created at runtime)

### Error Handling
- Custom exceptions: `OCREngineError` for OCR-related errors
- Graceful degradation when optional dependencies are missing
- Worker thread emits error signals for GUI display

## Configuration

The application uses a `config.json` file for persisting user settings:

```json
{
    "screenshot_hotkey": "ctrl+alt+s",
    "apply_threshold": true,
    "threshold_value": "5n",
    "threshold_replace_with": "0",
    "apply_unit_conversion": true,
    "target_unit_prefix": "u",
    "split_value_unit": true,
    "notation_style": "none",
    "precision": 3,
    "copy_strategy": "all",
    "fast_mode": false,
    "precision_mode": "high"
}
```

### Configuration Fields
- `screenshot_hotkey`: Global hotkey for screenshot (e.g., "ctrl+alt+s", "f1")
- `apply_threshold`: Enable threshold replacement feature
- `threshold_value`: Threshold value with unit prefix (e.g., "5n", "10u")
- `threshold_replace_with`: "-" or "0"
- `apply_unit_conversion`: Enable unit unification
- `target_unit_prefix`: Target engineering prefix (f, p, n, u, m, k, M, G)
- `split_value_unit`: Split numeric values and units into separate columns
- `notation_style`: "none", "scientific", or "engineering"
- `precision`: Number of significant digits (1-15)
- `copy_strategy`: "all", "value_only", or "unit_only"
- `precision_mode`: "high", "fast", or "superfast"

Default config is created automatically if missing.

## Security Considerations

1. **Input Validation**: Image paths are converted to strings before passing to OpenCV
2. **Temporary Files**: Screenshots are saved to temporary files using `tempfile.mkstemp()`
3. **Environment Variables**: Paddle flags are set before importing paddle modules
4. **No Network**: Application works offline; models are downloaded once by PaddleOCR

## Troubleshooting

### Common Issues

1. **PaddleOCR Model Download**: First run may take time to download models (~100MB)
2. **MKL-DNN Warnings**: Suppressed via environment variables in `ocr_engine.py`
3. **Qt Platform Plugin**: Ensure PySide6 is properly installed on Windows
4. **Global Hotkey Registration**: May fail if hotkey is already in use by another application

### Debug Mode
- Check the log panel in the GUI for processing stage information
- Use `scripts/manual_test.py` to test OCR without GUI complications
- Set logger in `OCREngine` for detailed initialization timing

## OCR Processing Pipeline

The application follows this processing flow:

1. **Capture**: User selects screen region → `CaptureWindow` emits `screenshot_completed`
2. **OCR**: `OcrWorker` runs OCR → `ocr_engine.OCREngine.recognize()`
3. **Layout Detection**: Based on selected mode (Default/Table)
4. **Layout Reconstruction**: 
   - Table: `layout.reconstruct_table()` → TSV format
   - Text: `layout.reconstruct_text_with_postprocess()` → formatted text
5. **Post-processing** (tables only): `postprocess.process_tsv()` applies threshold, unit conversion, notation
6. **Display**: Results shown in respective tabs, post-processed tab updated in real-time

## Engineering Prefix Support

The post-processing module supports standard engineering prefixes:

| Prefix | Value | Example Input | Base Value |
|--------|-------|---------------|------------|
| f | 10⁻¹⁵ | 5f | 0.000000000000005 |
| p | 10⁻¹² | 3p | 0.000000000003 |
| n | 10⁻⁹ | 10n | 0.00000001 |
| u | 10⁻⁶ | 100u | 0.0001 |
| m | 10⁻³ | 50m | 0.05 |
| (none) | 10⁰ | 123 | 123 |
| k | 10³ | 1.5k | 1500 |
| M | 10⁶ | 2.2M | 2200000 |
| G | 10⁹ | 0.1G | 100000000 |

Note: The application uses 'u' instead of 'μ' for micro (10⁻⁶).

## Additional Notes

### WorkOCR_Core Directory
The `WorkOCR_Core/` directory appears to be a duplicate of the main source code structure. For development purposes, use the main `src/work_ocr/` directory.

### OCR Accuracy Comparison
The `compare_ocr.py` file provides a utility to compare OCR output against ground truth data. This is used for validating OCR accuracy during development.

### Precision Modes
The application supports three OCR precision modes:
1. **PP-OCRv4 Server (精准/High Precision)**: Uses server models with angle classification enabled
2. **PP-OCRv4 Server (快速/Fast)**: Uses server models with angle classification disabled
3. **PP-OCRv4 Mobile (超快/Super Fast)**: Uses mobile models for maximum speed

Users can switch between modes via the precision mode dropdown in the UI.
