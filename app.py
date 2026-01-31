# -*- coding: utf-8 -*-
"""
Main application file for the Work OCR tool.

This module initializes the main window, orchestrates the different components
(capture, OCR, layout, post-processing), and handles user interactions.
"""

import sys
import time
import tempfile # Moved from on_screenshot_captured
import os       # Moved from on_screenshot_captured
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QTabWidget, QProgressBar,
    QPlainTextEdit, QComboBox, QSplitter, QMessageBox,
    QGroupBox, QCheckBox, QLineEdit, QGridLayout, QSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap, QGuiApplication

# Import project modules
import capture
import ocr_engine
import layout
import postprocess
import hotkey_manager


class OcrWorker(QThread):
    """
    A worker thread for running the entire OCR pipeline to avoid freezing the GUI.

    Signals:
        progress (str, int): Emits progress updates with a message and a percentage value.
        finished (str, str, str, str): Emits when processing is complete, sending
                                       layout_result, post_result, detected_mode, and image_path.
        error (str): Emits when an error occurs during processing.
    """
    progress = Signal(str, int)
    finished = Signal(str, str, str, str)
    error = Signal(str)

    def __init__(self, image_path: str, mode: str, ocr: ocr_engine.OCREngine):
        super().__init__()
        self.image_path = image_path
        self.mode = mode
        self.ocr = ocr

    def run(self):
        """Execute the OCR pipeline."""
        try:
            total_steps = 8
            start_time = time.time()

            def update_progress(step, message):
                self.progress.emit(f"({step}/{total_steps}) {message}", int(step / total_steps * 100))

            # Steps 1-2: Perform OCR
            update_progress(1, "Initializing OCR...")
            update_progress(2, "Performing OCR...")
            ocr_result = self.ocr.recognize(self.image_path)
            ocr_time = time.time()
            self.progress.emit(f"OCR finished in {ocr_time - start_time:.2f}s.", int(2 / total_steps * 100))

            # Steps 3-4: Analyze Layout
            update_progress(3, "Analyzing layout...")
            if self.mode == "auto":
                detected_mode = layout.detect_mode(ocr_result)
            else:
                detected_mode = self.mode

            if detected_mode == "table":
                layout_result = layout.reconstruct_table(ocr_result)
            else:
                layout_result = layout.reconstruct_text_with_postprocess(ocr_result)
            layout_time = time.time()
            self.progress.emit(f"Layout analysis finished in {layout_time - ocr_time:.2f}s.", int(4 / total_steps * 100))

            # Steps 5-6: Post-process Table
            post_result = ""
            if detected_mode == 'table':
                update_progress(5, "Loading post-processor settings...")
                settings = postprocess.load_config()
                update_progress(6, "Post-processing table...")
                post_result = postprocess.process_tsv(layout_result, settings)
                post_time = time.time()
                self.progress.emit(f"Post-processing finished in {post_time - layout_time:.2f}s.", int(6 / total_steps * 100))
            else:
                update_progress(6, "Skipping post-processing (not a table).")

            # Steps 7-8: Finalize
            update_progress(7, "Finalizing results...")
            end_time = time.time()
            update_progress(8, f"Total processing time: {end_time - start_time:.2f}s.")

            self.finished.emit(layout_result, post_result, detected_mode, self.image_path)

        except Exception as e:
            self.error.emit(f"An error occurred in the worker thread: {str(e)}")


class MainWindow(QMainWindow):
    """
    The main window of the application, responsible for UI and orchestrating modules.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Work OCR")
        self.setGeometry(100, 100, 1200, 800)

        self.worker = None
        self.capture_window = None
        self.original_ocr_result = ""  # Store raw OCR result for real-time preview
        self.current_settings = postprocess.PostprocessSettings()  # Current post-process settings
        self.hotkey_mgr = hotkey_manager.HotkeyManager()  # Global hotkey manager
        self.screenshot_hotkey = "ctrl+alt+s"  # Default hotkey
        
        self.setup_ui()
        self.connect_signals()
        self.load_settings()
        self.initialize_engines()

    def setup_ui(self):
        """Create and arrange all UI widgets."""
        main_splitter = QSplitter(Qt.Horizontal, self)

        # Left Panel: Image Preview
        self.image_label = QLabel("Screenshot will appear here")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumWidth(400)
        
        # Right Panel: Controls, Results, and Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Top Controls
        controls_layout = QHBoxLayout()
        self.screenshot_button = QPushButton("Screenshot")
        self.copy_button = QPushButton("Copy")
        self.clear_button = QPushButton("Clear")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Auto", "Table", "Text"])
        
        # Hotkey setting
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("e.g., ctrl+alt+s")
        self.hotkey_input.setMaximumWidth(120)
        self.hotkey_register_btn = QPushButton("Set Hotkey")
        self.hotkey_status_label = QLabel("(Global: None)")
        
        controls_layout.addWidget(self.screenshot_button)
        controls_layout.addWidget(self.copy_button)
        controls_layout.addWidget(self.clear_button)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Mode:"))
        controls_layout.addWidget(self.mode_combo)
        controls_layout.addWidget(QLabel("Hotkey:"))
        controls_layout.addWidget(self.hotkey_input)
        controls_layout.addWidget(self.hotkey_register_btn)
        controls_layout.addWidget(self.hotkey_status_label)

        # Results Tabs
        self.tabs = QTabWidget()
        self.ocr_result_text = QTextEdit()
        self.ocr_result_text.setReadOnly(True)
        self.tabs.addTab(self.ocr_result_text, "OCR Result")
        
        # Post-processed Tab with control panel and preview
        self.postprocess_widget = self._create_postprocess_tab()
        self.tabs.addTab(self.postprocess_widget, "Post-processed")

        # Bottom: Log and Progress Bar
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.progress_bar = QProgressBar()

        # Assemble Right Panel
        right_layout.addLayout(controls_layout)
        right_layout.addWidget(self.tabs)
        right_layout.addWidget(QLabel("Log"))
        right_layout.addWidget(self.log_text)
        right_layout.addWidget(QLabel("Progress"))
        right_layout.addWidget(self.progress_bar)

        # Assemble Main Splitter
        main_splitter.addWidget(self.image_label)
        main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([500, 700])
        self.setCentralWidget(main_splitter)

    def _create_postprocess_tab(self):
        """Create the Post-processed tab with control panel and preview."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Control Panel Group
        control_group = QGroupBox("Table Post-processing Settings")
        control_layout = QGridLayout(control_group)
        
        # Row 0: Threshold Replacement
        self.threshold_checkbox = QCheckBox("Enable Threshold Replacement")
        self.threshold_value_input = QLineEdit("5n")
        self.threshold_value_input.setPlaceholderText("e.g., 5n, 10u, 0.1m")
        self.threshold_replace_combo = QComboBox()
        self.threshold_replace_combo.addItems(["-", "0"])
        
        control_layout.addWidget(self.threshold_checkbox, 0, 0)
        control_layout.addWidget(QLabel("Threshold:"), 0, 1)
        control_layout.addWidget(self.threshold_value_input, 0, 2)
        control_layout.addWidget(QLabel("Replace with:"), 0, 3)
        control_layout.addWidget(self.threshold_replace_combo, 0, 4)
        
        # Row 1: Unit Conversion
        self.unit_conv_checkbox = QCheckBox("Enable Unit Unification")
        self.target_unit_combo = QComboBox()
        self.target_unit_combo.addItems(["f (1e-15)", "p (1e-12)", "n (1e-9)", "u (1e-6)", 
                                         "m (1e-3)", "base (1e0)", "k (1e3)", "M (1e6)", "G (1e9)"])
        self.target_unit_combo.setCurrentIndex(3)  # Default to 'u'
        
        control_layout.addWidget(self.unit_conv_checkbox, 1, 0)
        control_layout.addWidget(QLabel("Target Unit:"), 1, 1)
        control_layout.addWidget(self.target_unit_combo, 1, 2)
        
        # Row 2: Value/Unit Split and Notation
        self.split_checkbox = QCheckBox("Split Value and Unit")
        self.notation_combo = QComboBox()
        self.notation_combo.addItems(["None", "Scientific (e.g., 1.00E-05)", 
                                      "Engineering (e.g., 10.00E-06)"])
        
        control_layout.addWidget(self.split_checkbox, 2, 0)
        control_layout.addWidget(QLabel("Notation:"), 2, 1)
        control_layout.addWidget(self.notation_combo, 2, 2)
        
        # Precision setting
        self.precision_spinbox = QSpinBox()
        self.precision_spinbox.setRange(1, 15)
        self.precision_spinbox.setValue(6)
        self.precision_spinbox.setSuffix(" digits")
        control_layout.addWidget(QLabel("Precision:"), 2, 3)
        control_layout.addWidget(self.precision_spinbox, 2, 4)
        
        # Row 3: Copy Strategy and Buttons
        self.copy_strategy_combo = QComboBox()
        self.copy_strategy_combo.addItems(["Copy All", "Copy Values Only", "Copy Units Only"])
        self.apply_button = QPushButton("Apply & Save Settings")
        self.reset_button = QPushButton("Reset to Default")
        
        control_layout.addWidget(QLabel("Copy Strategy:"), 3, 0)
        control_layout.addWidget(self.copy_strategy_combo, 3, 1, 1, 2)
        control_layout.addWidget(self.apply_button, 3, 3)
        control_layout.addWidget(self.reset_button, 3, 4)
        
        # Set column stretch
        control_layout.setColumnStretch(2, 1)
        
        # Preview Text Area
        preview_label = QLabel("Preview:")
        self.postprocessed_text = QTextEdit()
        self.postprocessed_text.setReadOnly(True)
        
        layout.addWidget(control_group)
        layout.addWidget(preview_label)
        layout.addWidget(self.postprocessed_text, stretch=1)
        
        return widget

    def connect_signals(self):
        """Connect UI element signals to corresponding slots."""
        self.screenshot_button.clicked.connect(self.start_screenshot)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.clear_button.clicked.connect(self.clear_all)
        
        # Hotkey signals
        self.hotkey_register_btn.clicked.connect(self.on_register_hotkey)
        self.hotkey_mgr.screenshot_hotkey_pressed.connect(self.on_hotkey_screenshot)
        
        # Post-processing control signals
        self.apply_button.clicked.connect(self.on_apply_postprocess_settings)
        self.reset_button.clicked.connect(self.on_reset_postprocess_settings)
        
        # Real-time preview on any control change
        self.threshold_checkbox.stateChanged.connect(self.on_postprocess_changed)
        self.threshold_value_input.textChanged.connect(self.on_postprocess_changed)
        self.threshold_replace_combo.currentIndexChanged.connect(self.on_postprocess_changed)
        self.unit_conv_checkbox.stateChanged.connect(self.on_postprocess_changed)
        self.target_unit_combo.currentIndexChanged.connect(self.on_postprocess_changed)
        self.split_checkbox.stateChanged.connect(self.on_postprocess_changed)
        self.notation_combo.currentIndexChanged.connect(self.on_postprocess_changed)
        self.precision_spinbox.valueChanged.connect(self.on_postprocess_changed)
        self.copy_strategy_combo.currentIndexChanged.connect(self.on_postprocess_changed)

    def initialize_engines(self):
        """Initialize backend modules."""
        self.log_text.appendPlainText("Initializing engines...")
        QApplication.processEvents()
        try:
            self.ocr_engine = ocr_engine.OCREngine()
            self.log_text.appendPlainText("Engines initialized successfully.")
        except Exception as e:
            self.log_text.appendPlainText(f"Error initializing engines: {e}")
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize engines: {e}")

    @Slot()
    def start_screenshot(self):
        """Hides the main window and shows the capture window."""
        self.log_text.appendPlainText("Waiting for screenshot...")
        self.hide()
        # Give time for the main window to hide completely before showing the capture window.
        QApplication.processEvents()
        QThread.msleep(200) 

        self.capture_window = capture.CaptureWindow()
        self.capture_window.screenshot_completed.connect(self.on_screenshot_captured)
        self.capture_window.screenshot_cancelled.connect(self.on_screenshot_cancelled)
        self.capture_window.show()

    @Slot()
    def on_screenshot_cancelled(self):
        """Handles when user cancels the screenshot (presses Esc or selects too small area)."""
        self.show()  # Show the main window again
        if self.capture_window:
            self.capture_window.deleteLater()  # Clean up the capture window
            self.capture_window = None
        self.log_text.appendPlainText("Screenshot cancelled by user.")

    @Slot(QPixmap)
    def on_screenshot_captured(self, pixmap: QPixmap):
        """Handles the QPixmap returned from the capture window, saves it, and starts OCR."""
        self.show() # Show the main window again
        if self.capture_window:
            self.capture_window.deleteLater() # Clean up the capture window
            self.capture_window = None

        if pixmap.isNull():
            self.log_text.appendPlainText("Screenshot capture failed (null pixmap).")
            return

        # Save the QPixmap to a temporary file, then pass the path to the original on_screenshot_finished
        import tempfile
        import os
        try:
            # mkstemp returns (fd, name)
            fd, temp_image_path = tempfile.mkstemp(suffix=".png")
            os.close(fd) # Close the file descriptor immediately

            if pixmap.save(temp_image_path, "PNG"):
                self.on_screenshot_finished(temp_image_path)
                # The temp file will be processed and then deleted by the caller (or when app exits)
            else:
                self.log_text.appendPlainText("Failed to save temporary screenshot file.")
                os.remove(temp_image_path) # Clean up failed save
        except Exception as e:
            self.log_text.appendPlainText(f"Error saving screenshot: {e}")

    @Slot(str)
    def on_screenshot_finished(self, image_path: str):
        """Callback slot for when screen capture is finished."""
        if image_path and self.worker is None:
            self.log_text.appendPlainText(f"Screenshot saved to {image_path}")
            self.clear_results()
            
            pixmap = QPixmap(image_path)
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

            current_mode = self.mode_combo.currentText().lower()

            self.worker = OcrWorker(
                image_path, current_mode, self.ocr_engine
            )
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.on_processing_finished)
            self.worker.error.connect(self.on_processing_error)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker.start()
        elif self.worker is not None and self.worker.isRunning():
             self.log_text.appendPlainText("Processing is already in progress.")

    @Slot(str, int)
    def update_progress(self, message: str, value: int):
        """Update the log text and progress bar."""
        self.log_text.appendPlainText(message)
        self.progress_bar.setValue(value)

    @Slot(str, str, str, str)
    def on_processing_finished(self, layout_result: str, post_result: str, detected_mode: str, image_path: str):
        """Handle the results from the OCR worker."""
        self.log_text.appendPlainText("Processing finished successfully.")
        self.worker = None
        
        # Store the original OCR result for real-time post-processing preview
        self.original_ocr_result = layout_result
        
        self.ocr_result_text.setPlainText(layout_result)
        self.postprocessed_text.setPlainText(post_result)

        if self.mode_combo.currentText().lower() == 'auto':
            if detected_mode == 'table':
                self.mode_combo.setCurrentIndex(1)  # "Table"
            else:
                self.mode_combo.setCurrentIndex(2)  # "Text"

        if detected_mode == 'table' and post_result:
            self.tabs.setCurrentIndex(1)
        else:
            self.tabs.setCurrentIndex(0)

    @Slot(str)
    def on_processing_error(self, error_message: str):
        """Handle errors reported by the worker."""
        self.worker = None
        self.progress_bar.setValue(0)
        self.log_text.appendPlainText(f"ERROR: {error_message}")
        QMessageBox.critical(self, "Processing Error", error_message)

    @Slot()
    def copy_to_clipboard(self):
        """Copy the content of the currently visible tab to the clipboard."""
        current_idx = self.tabs.currentIndex()
        tab_name = self.tabs.tabText(current_idx)
        clipboard = QGuiApplication.clipboard()
        
        # Check if we're on the Post-processed tab and need to apply copy strategy
        if current_idx == 1 and self.current_settings.copy_strategy != "all":  # Post-processed tab
            text_to_copy = self._get_postprocess_copy_text()
            clipboard.setText(text_to_copy)
            strategy_desc = {
                "value_only": "values only",
                "unit_only": "units only",
                "all": "all content"
            }.get(self.current_settings.copy_strategy, "all content")
            self.log_text.appendPlainText(f"Copied {strategy_desc} from '{tab_name}' to clipboard.")
        elif current_idx == 0:  # OCR Result tab
            clipboard.setText(self.ocr_result_text.toPlainText())
            self.log_text.appendPlainText(f"Copied content of '{tab_name}' to clipboard.")
        elif current_idx == 1:  # Post-processed tab with "all" strategy
            clipboard.setText(self.postprocessed_text.toPlainText())
            self.log_text.appendPlainText(f"Copied content of '{tab_name}' to clipboard.")

    def _get_postprocess_copy_text(self) -> str:
        """Get text to copy based on copy_strategy setting.
        When split_value_unit is True, the last column is the unit column.
        """
        text = self.postprocessed_text.toPlainText()
        if not text or self.current_settings.copy_strategy == "all":
            return text
        
        lines = text.strip().split('\n')
        result_lines = []
        
        for line in lines:
            cells = line.split('\t')
            if not cells:
                result_lines.append('')
                continue
                
            if self.current_settings.copy_strategy == "value_only":
                # Exclude the last column (unit column) if split_value_unit was applied
                if self.current_settings.split_value_unit and len(cells) > 1:
                    result_lines.append('\t'.join(cells[:-1]))
                else:
                    result_lines.append(line)
            elif self.current_settings.copy_strategy == "unit_only":
                # Only copy the last column (unit column) if split_value_unit was applied
                if self.current_settings.split_value_unit and len(cells) > 1:
                    result_lines.append(cells[-1])
                else:
                    result_lines.append('')  # No unit column available
        
        return '\n'.join(result_lines)

    @Slot()
    def clear_all(self):
        """Clear all output areas, including the log."""
        self.log_text.appendPlainText("Clearing all fields.")
        self.clear_results()
        self.log_text.clear()

    def clear_results(self):
        """Clear only the result fields, not the log."""
        self.image_label.setPixmap(QPixmap()) # Clear pixmap first
        self.image_label.setText("Screenshot will appear here") # Then set text
        self.ocr_result_text.clear()
        self.postprocessed_text.clear()
        self.original_ocr_result = ""  # Clear stored OCR result
        self.progress_bar.setValue(0)
        self.mode_combo.setCurrentIndex(0)  # Reset to "Auto"

    # ========== Hotkey Methods ==========

    def load_hotkey_settings(self):
        """Load hotkey settings from config file and register the hotkey."""
        config_path = "config.json"
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                hotkey = data.get('screenshot_hotkey', 'ctrl+alt+s')
        except (FileNotFoundError, json.JSONDecodeError):
            hotkey = 'ctrl+alt+s'
        
        self.screenshot_hotkey = hotkey
        self.hotkey_input.setText(hotkey)
        self._register_hotkey_internal(hotkey)

    def save_hotkey_settings(self):
        """Save hotkey settings to config file."""
        config_path = "config.json"
        try:
            import json
            # Load existing config first
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}
            
            # Update hotkey
            data['screenshot_hotkey'] = self.screenshot_hotkey
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.log_text.appendPlainText(f"Failed to save hotkey settings: {e}")

    def _register_hotkey_internal(self, hotkey_str: str) -> bool:
        """Internal method to register the hotkey."""
        if not hotkey_str or hotkey_str.strip() == '':
            self.hotkey_status_label.setText("(Global: None)")
            return False
        
        success = self.hotkey_mgr.register_screenshot_hotkey(hotkey_str)
        if success:
            formatted = hotkey_manager.HotkeyManager.format_hotkey_display(hotkey_str)
            self.hotkey_status_label.setText(f"(Global: {formatted})")
            self.log_text.appendPlainText(f"Global hotkey registered: {formatted}")
            return True
        else:
            self.hotkey_status_label.setText("(Global: Failed)")
            QMessageBox.warning(self, "Hotkey Error", 
                f"Failed to register hotkey '{hotkey_str}'.\n"
                "Please try a different combination (e.g., ctrl+alt+s, f1, ctrl+f12).")
            return False

    @Slot()
    def on_register_hotkey(self):
        """Handle the Set Hotkey button click."""
        hotkey_str = self.hotkey_input.text().strip()
        
        if not hotkey_str:
            # Unregister if empty
            self.hotkey_mgr.unregister_all()
            self.screenshot_hotkey = ""
            self.hotkey_status_label.setText("(Global: None)")
            self.save_hotkey_settings()
            self.log_text.appendPlainText("Global hotkey unregistered.")
            return
        
        # Validate hotkey format
        if not hotkey_manager.HotkeyManager.validate_hotkey(hotkey_str):
            QMessageBox.warning(self, "Invalid Hotkey", 
                f"Invalid hotkey format: '{hotkey_str}'\n"
                "Examples: ctrl+alt+s, f1, ctrl+shift+a")
            return
        
        # Register the hotkey
        if self._register_hotkey_internal(hotkey_str):
            self.screenshot_hotkey = hotkey_str
            self.save_hotkey_settings()

    @Slot()
    def on_hotkey_screenshot(self):
        """Handle global hotkey press for screenshot."""
        # Bring window to front if minimized
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        
        self.log_text.appendPlainText("Global hotkey triggered: Screenshot")
        self.start_screenshot()

    # ========== Post-processing Methods ==========

    def load_postprocess_settings(self):
        """Load post-process settings from config file and update UI."""
        self.current_settings = postprocess.load_config()
        settings = self.current_settings
        
        # Update UI controls
        self.threshold_checkbox.setChecked(settings.apply_threshold)
        self.threshold_value_input.setText(settings.threshold_value)
        replace_idx = 0 if settings.threshold_replace_with == "-" else 1
        self.threshold_replace_combo.setCurrentIndex(replace_idx)
        
        self.unit_conv_checkbox.setChecked(settings.apply_unit_conversion)
        # Map prefix to combo index: f,p,n,u,m,base,k,M,G -> 0,1,2,3,4,5,6,7,8
        prefix_to_idx = {'f': 0, 'p': 1, 'n': 2, 'u': 3, 'm': 4, '': 5, 'k': 6, 'M': 7, 'G': 8}
        unit_idx = prefix_to_idx.get(settings.target_unit_prefix, 5)
        self.target_unit_combo.setCurrentIndex(unit_idx)
        
        self.split_checkbox.setChecked(settings.split_value_unit)
        # Map notation style: "none", "scientific", "engineering"
        notation_map = {'none': 0, 'scientific': 1, 'engineering': 2}
        notation_idx = notation_map.get(settings.notation_style, 0)
        self.notation_combo.setCurrentIndex(notation_idx)
        
        # Precision setting
        self.precision_spinbox.setValue(settings.precision)
        
        # Map copy strategy: "all", "value_only", "unit_only"
        strategy_map = {'all': 0, 'value_only': 1, 'unit_only': 2}
        strategy_idx = strategy_map.get(settings.copy_strategy, 0)
        self.copy_strategy_combo.setCurrentIndex(strategy_idx)
        
        self.log_text.appendPlainText("Post-process settings loaded.")

    def load_settings(self):
        """Load all settings including hotkey and post-process settings."""
        self.load_hotkey_settings()
        self.load_postprocess_settings()

    def get_settings_from_ui(self) -> postprocess.PostprocessSettings:
        """Extract settings from UI controls."""
        settings = postprocess.PostprocessSettings()
        
        settings.apply_threshold = self.threshold_checkbox.isChecked()
        settings.threshold_value = self.threshold_value_input.text()
        settings.threshold_replace_with = self.threshold_replace_combo.currentText()
        
        settings.apply_unit_conversion = self.unit_conv_checkbox.isChecked()
        # Map combo index to prefix
        idx_to_prefix = {0: 'f', 1: 'p', 2: 'n', 3: 'u', 4: 'm', 5: '', 6: 'k', 7: 'M', 8: 'G'}
        settings.target_unit_prefix = idx_to_prefix.get(self.target_unit_combo.currentIndex(), '')
        
        settings.split_value_unit = self.split_checkbox.isChecked()
        # Map notation combo index to style (0: none, 1: scientific, 2: engineering)
        notation_styles = {0: 'none', 1: 'scientific', 2: 'engineering'}
        settings.notation_style = notation_styles.get(self.notation_combo.currentIndex(), 'none')
        settings.apply_notation_conversion = (settings.notation_style != 'none')
        
        # Precision setting
        settings.precision = self.precision_spinbox.value()
        
        # Map copy strategy combo index
        copy_strategies = {0: 'all', 1: 'value_only', 2: 'unit_only'}
        settings.copy_strategy = copy_strategies.get(self.copy_strategy_combo.currentIndex(), 'all')
        
        return settings

    def update_postprocess_preview(self):
        """Update the post-process preview based on current settings and original OCR result."""
        if not self.original_ocr_result:
            return
        
        settings = self.get_settings_from_ui()
        self.current_settings = settings
        
        # Only process if it's a table (contains tabs)
        if '\t' in self.original_ocr_result:
            try:
                processed = postprocess.process_tsv(self.original_ocr_result, settings)
                self.postprocessed_text.setPlainText(processed)
            except Exception as e:
                self.log_text.appendPlainText(f"Post-processing preview error: {e}")
        else:
            # For text mode, just show original
            self.postprocessed_text.setPlainText(self.original_ocr_result)

    @Slot()
    def on_postprocess_changed(self):
        """Handle any post-processing control change - update preview in real-time."""
        self.update_postprocess_preview()

    @Slot()
    def on_apply_postprocess_settings(self):
        """Apply current settings and save to config file."""
        self.current_settings = self.get_settings_from_ui()
        try:
            postprocess.save_config(self.current_settings)
            self.log_text.appendPlainText("Post-process settings saved.")
            self.update_postprocess_preview()
        except Exception as e:
            self.log_text.appendPlainText(f"Failed to save settings: {e}")
            QMessageBox.warning(self, "Save Error", f"Failed to save settings: {e}")

    @Slot()
    def on_reset_postprocess_settings(self):
        """Reset post-process settings to default."""
        self.current_settings = postprocess.PostprocessSettings()
        try:
            postprocess.save_config(self.current_settings)
            self.load_postprocess_settings()
            self.update_postprocess_preview()
            self.log_text.appendPlainText("Post-process settings reset to default.")
        except Exception as e:
            self.log_text.appendPlainText(f"Failed to reset settings: {e}")
    
    def resizeEvent(self, event):
        """Handle window resize to scale the image preview."""
        if isinstance(self.image_label.pixmap(), QPixmap) and not self.image_label.pixmap().isNull():
            self.image_label.setPixmap(self.image_label.pixmap().scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        super().resizeEvent(event)

    def closeEvent(self, event):
        """Ensure the worker thread is terminated and hotkeys are unregistered before closing."""
        if self.worker and self.worker.isRunning():
            self.log_text.appendPlainText("Attempting to stop active processing...")
            self.worker.terminate()
            self.worker.wait()
        
        # Unregister global hotkeys
        self.hotkey_mgr.stop()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
