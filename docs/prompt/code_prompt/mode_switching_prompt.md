# Feature: OCR Precision Mode Switching

## 1. Objective

Implement a feature allowing the user to switch between a "High Precision" mode and a "Fast" mode for OCR. This will improve user experience on lower-end hardware by providing a faster, albeit slightly less accurate, option. This also includes laying the groundwork for a future "Super-fast" mode using lightweight models.

## 2. Implementation Plan

This will be a multi-phase implementation. The first phase focuses on parameter adjustment (Scheme 2), and the second phase (future work) will involve loading different models (Scheme 1).

### Phase 1: Parameter-based Fast Mode (Scheme 2)

**Files to Modify:** `src/work_ocr/app.py` and `src/work_ocr/ocr_engine.py`, and the configuration handling.

**`ocr_engine.py` Modifications:**

1.  The `OCREngine` class `__init__` should be updated to accept a dictionary of advanced parameters.
2.  The `initialize` method will pass these advanced parameters directly to the `PaddleOCR` constructor. This makes the engine flexible for future additions.
3.  The "Fast Mode" configuration will be: `use_angle_cls=False`. We can also experiment with `det_db_box_thresh=0.7`.
4.  The "High Precision Mode" will use the defaults: `use_angle_cls=True`.

**`app.py` Modifications:**

1.  **UI Change:** Add a `QCheckBox` to the main window's UI, labeled "快速模式" (Fast Mode).
2.  **Configuration Management:**
    *   The application's configuration loading/saving mechanism (likely handled via a JSON file) needs to be updated to include a `fast_mode` boolean setting.
    *   The state of the checkbox should be linked to this configuration setting, so it persists across sessions.
3.  **Logic:**
    *   When the application starts, read the `fast_mode` setting from the config and set the checkbox state.
    *   When the OCR process is initiated, check the state of the "Fast Mode" checkbox.
    *   Based on the mode, create the `OCREngine` instance with the correct parameters.
        *   **Fast Mode:** `OCREngine(lang="ch", use_angle_cls=False)`
        *   **High Precision Mode:** `OCREngine(lang="ch", use_angle_cls=True)`

### Phase 2: Lightweight Model "Super-fast" Mode (Scheme 1 - Future)

**This is for future planning and not to be implemented now.**

1.  **Model Management:** Add functionality to download and manage a separate set of lightweight "slim" models from PaddleOCR.
2.  **UI:** The UI control might be changed from a checkbox to a dropdown menu (e.g., "High", "Fast", "Fastest").
3.  **Logic:** Update `OCREngine` to accept `det_model_dir` and `rec_model_dir` to load the correct model files based on the selected mode.

## 3. Acceptance Criteria

*   A "Fast Mode" checkbox is present and functional in the UI.
*   The mode setting is saved and loaded correctly between application sessions.
*   When "Fast Mode" is enabled, OCR is noticeably faster, and it can be confirmed through logging or debugging that `OCREngine` is initialized with `use_angle_cls=False`.
*   The application remains stable and functions correctly in both modes.
