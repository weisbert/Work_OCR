# -*- coding: utf-8 -*-
"""Main GUI application for Work_OCR."""

from __future__ import annotations

import sys
import signal
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Fix Ctrl+C on Windows - must be done before importing paddle (via ocr_engine)
if sys.platform == "win32":
    signal.signal(signal.SIGINT, signal.default_int_handler)

from PySide6.QtCore import Qt, Slot, Signal, QThread, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QFont, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStyle,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QFormLayout,
    QDialog,
    QListWidget,
    QListWidgetItem,
)

# Import local modules
from . import capture, hotkey_manager, ocr_engine, layout, postprocess


class TextLogger:
    """Logger that writes to a QPlainTextEdit widget."""

    def __init__(self, widget: QPlainTextEdit):
        self.widget = widget

    def info(self, message: str) -> None:
        self.widget.appendPlainText(f"[INFO] {message}")

    def warning(self, message: str) -> None:
        self.widget.appendPlainText(f"[WARN] {message}")


class OcrWorker(QThread):
    """Worker thread for running OCR pipeline without freezing UI.
    
    Supports immediate cancellation via stop() method.
    When stopped, the worker continues running in background but results are discarded.
    """

    progress = Signal(str, int)  # message, percentage
    finished = Signal(str, str, str, str)  # layout_result, post_result, detected_mode, image_path
    error = Signal(str)
    stopped = Signal()

    def __init__(self, image_path: str, mode: str, ocr: ocr_engine.OCREngine):
        super().__init__()
        self.image_path = image_path
        self.mode = mode
        self.ocr = ocr
        self._is_cancelled = False

    def run(self):
        try:
            self.progress.emit("Initializing OCR engine...", 10)
            self.ocr.initialize()

            if self._is_cancelled:
                return  # Silently exit

            self.progress.emit("Running OCR recognition...", 30)
            ocr_result = self.ocr.recognize(self.image_path)

            if self._is_cancelled:
                return  # Silently exit, don't emit any signals

            self.progress.emit("Analyzing layout...", 50)
            detected_mode = layout.detect_mode(ocr_result)

            if self._is_cancelled:
                return

            self.progress.emit("Reconstructing layout...", 70)

            if self.mode == "table":
                layout_result = layout.reconstruct_table(ocr_result)
            else:
                layout_result = layout.reconstruct_text_with_postprocess(ocr_result)

            if self._is_cancelled:
                return

            self.progress.emit("Post-processing...", 90)
            settings = postprocess.load_config()

            if self.mode == "table":
                post_result = postprocess.process_tsv(layout_result, settings)
            else:
                post_result = layout_result

            if self._is_cancelled:
                return

            self.progress.emit("Completed!", 100)
            self.finished.emit(layout_result, post_result, self.mode, self.image_path)

        except ocr_engine.CancelledError:
            pass  # Silently exit on cancellation
        except Exception as exc:
            if not self._is_cancelled:
                self.error.emit(str(exc))

    def stop(self):
        """Cancel the OCR process immediately.
        
        This method returns immediately without blocking.
        The worker continues in background but results will be discarded.
        """
        self._is_cancelled = True
        if hasattr(self.ocr, 'cancel'):
            self.ocr.cancel()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Work_OCR - Screen OCR Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Worker thread
        self.worker: Optional[OcrWorker] = None

        # Screenshot temp file path
        self.current_screenshot_path: Optional[str] = None

        # Hotkey manager
        self.hotkey_manager: Optional[hotkey_manager.HotkeyManager] = None

        self._init_ui()
        self._init_hotkey()
        self._init_menu()

    def _init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left panel: Controls
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)

        # Right panel: Results
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)

        # Set splitter proportions
        main_splitter.setSizes([400, 800])

        # Layout
        layout_main = QHBoxLayout(central_widget)
        layout_main.addWidget(main_splitter)

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)

        # --- OCR Control Group ---
        ocr_group = QGroupBox("OCR Control")
        ocr_layout = QVBoxLayout(ocr_group)

        # Screenshot button
        self.screenshot_btn = QPushButton("📷 Take Screenshot (Ctrl+Alt+S)")
        self.screenshot_btn.setToolTip("Click to capture a screen region")
        self.screenshot_btn.clicked.connect(self.on_screenshot_clicked)
        ocr_layout.addWidget(self.screenshot_btn)

        # Retry button
        self.retry_button = QPushButton("🔄 Retry OCR")
        self.retry_button.setEnabled(False)
        self.retry_button.clicked.connect(self.on_retry_clicked)
        ocr_layout.addWidget(self.retry_button)

        # Stop button
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.on_stop_clicked)
        ocr_layout.addWidget(self.stop_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        ocr_layout.addWidget(self.progress_bar)

        panel_layout.addWidget(ocr_group)

        # --- OCR Settings Group ---
        settings_group = QGroupBox("OCR Settings")
        settings_layout = QFormLayout(settings_group)

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Table Mode", "Text Mode"])
        self.mode_combo.setToolTip("Select OCR output mode")
        settings_layout.addRow("Mode:", self.mode_combo)

        # Precision mode selection
        self.precision_mode_combo = QComboBox()
        self.precision_mode_combo.addItems(["High Precision", "Fast", "Super Fast"])
        self.precision_mode_combo.setToolTip(
            "High: Better accuracy with angle detection\n"
            "Fast: Good balance\n"
            "Super Fast: Maximum speed"
        )
        settings_layout.addRow("Speed:", self.precision_mode_combo)

        panel_layout.addWidget(settings_group)

        # --- Post-processing Settings Group ---
        post_group = QGroupBox("Post-processing (Table Mode)")
        post_layout = QVBoxLayout(post_group)

        # Load config once for initialization
        _config = postprocess.load_config()
        
        # Threshold settings
        self.threshold_check = QCheckBox("Apply Threshold Replacement")
        self.threshold_check.setChecked(_config.apply_threshold)
        post_layout.addWidget(self.threshold_check)

        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Value:"))
        self.threshold_value = QLineEdit(_config.threshold_value)
        self.threshold_value.setMaximumWidth(60)
        threshold_layout.addWidget(self.threshold_value)
        threshold_layout.addWidget(QLabel("Replace with:"))
        self.threshold_replace = QLineEdit(_config.threshold_replace_with)
        self.threshold_replace.setMaximumWidth(40)
        threshold_layout.addWidget(self.threshold_replace)
        threshold_layout.addStretch()
        post_layout.addLayout(threshold_layout)

        # Unit conversion
        self.unit_conv_check = QCheckBox("Convert to Target Unit")
        self.unit_conv_check.setChecked(_config.apply_unit_conversion)
        post_layout.addWidget(self.unit_conv_check)

        unit_layout = QHBoxLayout()
        unit_layout.addWidget(QLabel("Target prefix:"))
        self.target_unit = QComboBox()
        self.target_unit.addItems(["f", "p", "n", "u", "m", "k", "M", "G"])
        self.target_unit.setCurrentText(_config.target_unit_prefix if _config.target_unit_prefix else "u")
        unit_layout.addWidget(self.target_unit)
        unit_layout.addStretch()
        post_layout.addLayout(unit_layout)

        # Split value/unit
        self.split_check = QCheckBox("Split Value and Unit")
        self.split_check.setChecked(_config.split_value_unit)
        post_layout.addWidget(self.split_check)

        # Notation style
        notation_layout = QHBoxLayout()
        notation_layout.addWidget(QLabel("Notation:"))
        self.notation_combo = QComboBox()
        self.notation_combo.addItems(["None", "Scientific", "Engineering"])
        notation_map = {"none": 0, "scientific": 1, "engineering": 2}
        self.notation_combo.setCurrentIndex(
            notation_map.get(_config.notation_style, 0)
        )
        notation_layout.addWidget(self.notation_combo)
        notation_layout.addStretch()
        post_layout.addLayout(notation_layout)

        # Precision
        precision_layout = QHBoxLayout()
        precision_layout.addWidget(QLabel("Precision:"))
        self.precision_spin = QSpinBox()
        self.precision_spin.setRange(1, 15)
        self.precision_spin.setValue(_config.precision)
        precision_layout.addWidget(self.precision_spin)
        precision_layout.addStretch()
        post_layout.addLayout(precision_layout)

        # Copy strategy
        copy_layout = QHBoxLayout()
        copy_layout.addWidget(QLabel("Copy:"))
        self.copy_combo = QComboBox()
        self.copy_combo.addItems(["All", "Values Only", "Units Only"])
        copy_map = {"all": 0, "value_only": 1, "unit_only": 2}
        self.copy_combo.setCurrentIndex(
            copy_map.get(_config.copy_strategy, 0)
        )
        copy_layout.addWidget(self.copy_combo)
        copy_layout.addStretch()
        post_layout.addLayout(copy_layout)

        # Save button
        self.save_post_btn = QPushButton("💾 Save Settings")
        self.save_post_btn.clicked.connect(self.on_save_post_settings)
        post_layout.addWidget(self.save_post_btn)

        panel_layout.addWidget(post_group)

        # --- Log Panel ---
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_text)

        # Text logger for OCR engine
        self.text_logger = TextLogger(self.log_text)

        panel_layout.addWidget(log_group)

        # OCR control widget (shown during processing)
        self.ocr_control_widget = QWidget()
        ocr_control_layout = QVBoxLayout(self.ocr_control_widget)
        ocr_control_layout.setContentsMargins(0, 0, 0, 0)
        self.ocr_control_widget.setVisible(False)

        panel_layout.addStretch()
        return panel

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        # Image preview area
        self.image_label = QLabel("Click 'Take Screenshot' to capture an image")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(300)
        self.image_label.setStyleSheet("background-color: #f0f0f0; border: 1px dashed #999;")

        image_scroll = QScrollArea()
        image_scroll.setWidget(self.image_label)
        image_scroll.setWidgetResizable(True)
        panel_layout.addWidget(image_scroll, 1)

        # Results tabs
        self.results_tabs = QTabWidget()

        # Raw result tab
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(False)
        self.raw_text.setPlaceholderText("Raw OCR result will appear here...")
        self.results_tabs.addTab(self.raw_text, "📄 Raw Result")

        # Table result tab
        self.table_widget = QTableWidget()
        self.results_tabs.addTab(self.table_widget, "📊 Table View")

        # Post-processed tab
        self.post_text = QTextEdit()
        self.post_text.setReadOnly(False)
        self.post_text.setPlaceholderText("Post-processed result will appear here...")
        self.results_tabs.addTab(self.post_text, "✨ Post-processed")

        panel_layout.addWidget(self.results_tabs, 2)

        # Copy buttons
        btn_layout = QHBoxLayout()

        self.copy_raw_btn = QPushButton("📋 Copy Raw")
        self.copy_raw_btn.clicked.connect(lambda: self.copy_to_clipboard(self.raw_text.toPlainText()))
        btn_layout.addWidget(self.copy_raw_btn)

        self.copy_post_btn = QPushButton("📋 Copy Post-processed")
        self.copy_post_btn.clicked.connect(lambda: self.copy_to_clipboard(self.post_text.toPlainText()))
        btn_layout.addWidget(self.copy_post_btn)

        self.copy_table_btn = QPushButton("📋 Copy Table (TSV)")
        self.copy_table_btn.clicked.connect(self.copy_table_as_tsv)
        btn_layout.addWidget(self.copy_table_btn)

        panel_layout.addLayout(btn_layout)

        return panel

    def _init_hotkey(self):
        """Initialize global hotkey manager."""
        try:
            self.hotkey_manager = hotkey_manager.HotkeyManager()
            self.hotkey_manager.screenshot_hotkey_pressed.connect(self.on_screenshot_clicked)
            
            # Load saved hotkey or use default
            config = postprocess.load_config()
            hotkey = config.screenshot_hotkey
            
            if not self.hotkey_manager.register_hotkey(hotkey):
                self.log_text.appendPlainText(f"Warning: Failed to register hotkey '{hotkey}'")
            else:
                self.log_text.appendPlainText(f"Global hotkey registered: {hotkey}")
        except Exception as exc:
            self.log_text.appendPlainText(f"Hotkey manager not available: {exc}")
            self.hotkey_manager = None

    def _init_menu(self):
        """Initialize menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Image...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.on_open_image)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        hotkey_action = QAction("Configure Hotkey...", self)
        hotkey_action.triggered.connect(self.on_configure_hotkey)
        settings_menu.addAction(hotkey_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)

    @Slot()
    def on_screenshot_clicked(self):
        """Handle screenshot button click."""
        # Minimize window before capture
        self.showMinimized()

        # Small delay to let window minimize
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, self._start_capture)

    def _start_capture(self):
        """Start screen capture after delay."""
        self.capture_window = capture.CaptureWindow()
        self.capture_window.screenshot_completed.connect(self.on_screenshot_completed)
        self.capture_window.screenshot_cancelled.connect(self.on_screenshot_cancelled)
        self.capture_window.show()

    @Slot(QPixmap)
    def on_screenshot_completed(self, pixmap: QPixmap):
        """Handle completed screenshot."""
        self.restoreWindow()

        # Save to temp file
        if self.current_screenshot_path and os.path.exists(self.current_screenshot_path):
            try:
                os.remove(self.current_screenshot_path)
            except Exception:
                pass

        fd, self.current_screenshot_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        pixmap.save(self.current_screenshot_path)

        # Display
        self.image_label.setPixmap(
            pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        # Start OCR
        self.start_ocr(self.current_screenshot_path)

    @Slot()
    def on_screenshot_cancelled(self):
        """Handle cancelled screenshot."""
        self.restoreWindow()

    def restoreWindow(self):
        """Restore window from minimized state."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def start_ocr(self, image_path: str):
        """Start OCR processing on the given image."""
        # If a worker is still running, stop it and delay restart
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log_text.appendPlainText("Waiting for previous OCR to stop...")
            # Delay restart to allow old worker to clean up
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._start_ocr_safe(image_path))
            return
        
        self._start_ocr_safe(image_path)
    
    def _start_ocr_safe(self, image_path: str):
        """Actually start OCR - only call when no worker is running."""
        # Double-check worker is finished
        if self.worker and self.worker.isRunning():
            # Still running, delay again
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._start_ocr_safe(image_path))
            return
        
        self.log_text.clear()
        self.log_text.appendPlainText(f"Processing: {image_path}")

        current_mode = self.mode_combo.currentText().lower()
        ocr_params = self._get_ocr_params()
        engine = ocr_engine.OCREngine(**ocr_params)
        
        self.worker = OcrWorker(image_path, current_mode, engine)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error.connect(self.on_processing_error)
        self.worker.stopped.connect(self.on_processing_stopped)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.stopped.connect(self.worker.deleteLater)

        self.ocr_control_widget.setVisible(True)
        self.stop_button.setEnabled(True)
        self.retry_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.worker.start()

    def _get_ocr_params(self) -> dict:
        """Get OCR engine parameters based on the selected precision mode.
        
        Available models (in ~/.paddlex/official_models/):
        - PP-OCRv3_mobile_det/rec (lightweight, faster)
        - PP-OCRv5_server_det/rec (high accuracy, slower)
        """
        index = self.precision_mode_combo.currentIndex()
        mode_map = {0: "high", 1: "fast", 2: "superfast"}
        mode_str = mode_map.get(index, "high")

        self.log_text.appendPlainText(f"Precision Mode: {mode_str}")

        # Base parameters
        base_params = {
            "show_log": False,
            "logger": self.text_logger
        }
        
        if mode_str == "high":
            # High precision: PP-OCRv5_server + angle classification
            return {
                **base_params,
                "text_detection_model_name": "PP-OCRv5_server_det",
                "text_recognition_model_name": "PP-OCRv5_server_rec",
                "use_angle_cls": True,
            }
        
        if mode_str == "fast":
            # Fast: PP-OCRv5_server (no angle classification for speed)
            return {
                **base_params,
                "text_detection_model_name": "PP-OCRv5_server_det",
                "text_recognition_model_name": "PP-OCRv5_server_rec",
                "use_angle_cls": False,
            }
        
        if mode_str == "superfast":
            # Superfast: PP-OCRv3_mobile (lightweight models)
            return {
                **base_params,
                "text_detection_model_name": "PP-OCRv3_mobile_det",
                "text_recognition_model_name": "PP-OCRv3_mobile_rec",
                "use_angle_cls": False,
            }
        
        # Fallback: use server models
        return {
            **base_params,
            "text_detection_model_name": "PP-OCRv5_server_det",
            "text_recognition_model_name": "PP-OCRv5_server_rec",
            "use_angle_cls": True,
        }

    @Slot(str, int)
    def update_progress(self, message: str, value: int):
        self.log_text.appendPlainText(message)
        self.progress_bar.setValue(value)

    @Slot(str, str, str, str)
    def on_processing_finished(self, layout_result: str, post_result: str, detected_mode: str, image_path: str):
        """Handle the results from the OCR worker."""
        self.log_text.appendPlainText("Processing finished successfully.")
        self.worker = None
        self.stop_button.setEnabled(False)
        self.retry_button.setEnabled(True)

        # Update raw result
        self.raw_text.setPlainText(layout_result)

        # Update post-processed result
        self.post_text.setPlainText(post_result)

        # Update table view if in table mode
        if detected_mode == "table":
            self._update_table_view(post_result)
            self.results_tabs.setCurrentIndex(2)  # Switch to post-processed tab
        else:
            self.results_tabs.setCurrentIndex(0)  # Switch to raw result tab

    def _update_table_view(self, tsv_data: str):
        """Update table widget with TSV data."""
        lines = tsv_data.strip().split("\n")
        if not lines:
            return

        # Parse TSV
        rows = [line.split("\t") for line in lines]
        max_cols = max(len(row) for row in rows)

        # Set up table
        self.table_widget.clear()
        self.table_widget.setRowCount(len(rows))
        self.table_widget.setColumnCount(max_cols)

        # Fill data
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                item = QTableWidgetItem(cell)
                self.table_widget.setItem(i, j, item)

        # Resize columns
        self.table_widget.resizeColumnsToContents()

    @Slot(str)
    def on_processing_error(self, error_message: str):
        """Handle processing error."""
        self.log_text.appendPlainText(f"Error: {error_message}")
        self.worker = None
        self.stop_button.setEnabled(False)
        self.retry_button.setEnabled(True)

        QMessageBox.critical(self, "Processing Error", f"An error occurred in the worker thread: {error_message}")

    @Slot()
    def on_processing_stopped(self):
        """Handle stopped processing."""
        self.log_text.appendPlainText("Processing stopped.")
        self.worker = None
        self.stop_button.setEnabled(False)
        self.retry_button.setEnabled(True)

    @Slot()
    def on_retry_clicked(self):
        """Retry OCR on current image."""
        if self.current_screenshot_path and os.path.exists(self.current_screenshot_path):
            self.start_ocr(self.current_screenshot_path)
        else:
            QMessageBox.warning(self, "No Image", "No image to retry. Please take a screenshot first.")

    @Slot()
    def on_stop_clicked(self):
        """Stop current processing immediately."""
        if self.worker and self.worker.isRunning():
            self.log_text.appendPlainText("Stopping... (OCR will complete in background)")
            self.worker.stop()
            # Don't clear self.worker here - let stopped signal handle it
            self.stop_button.setEnabled(False)

    @Slot()
    def on_open_image(self):
        """Open an image file for OCR."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_path:
            # Display image
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(
                pixmap.scaled(
                    self.image_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
            self.current_screenshot_path = file_path
            self.start_ocr(file_path)

    @Slot()
    def on_save_post_settings(self):
        """Save post-processing settings."""
        notation_map = {0: "none", 1: "scientific", 2: "engineering"}
        copy_map = {0: "all", 1: "value_only", 2: "unit_only"}

        settings = postprocess.PostprocessSettings(
            apply_threshold=self.threshold_check.isChecked(),
            threshold_value=self.threshold_value.text(),
            threshold_replace_with=self.threshold_replace.text(),
            apply_unit_conversion=self.unit_conv_check.isChecked(),
            target_unit_prefix=self.target_unit.currentText(),
            split_value_unit=self.split_check.isChecked(),
            notation_style=notation_map.get(self.notation_combo.currentIndex(), "none"),
            precision=self.precision_spin.value(),
            copy_strategy=copy_map.get(self.copy_combo.currentIndex(), "all"),
        )

        postprocess.save_config(settings)
        self.log_text.appendPlainText("Post-processing settings saved.")

    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.log_text.appendPlainText("Copied to clipboard.")

    def copy_table_as_tsv(self):
        """Copy table content as TSV."""
        rows = []
        for i in range(self.table_widget.rowCount()):
            row = []
            for j in range(self.table_widget.columnCount()):
                item = self.table_widget.item(i, j)
                row.append(item.text() if item else "")
            rows.append("\t".join(row))

        tsv_text = "\n".join(rows)
        self.copy_to_clipboard(tsv_text)

    @Slot()
    def on_configure_hotkey(self):
        """Open hotkey configuration dialog."""
        dialog = HotkeyConfigDialog(self, self.hotkey_manager)
        if dialog.exec():
            new_hotkey = dialog.get_hotkey()
            if self.hotkey_manager:
                # Unregister old hotkey
                self.hotkey_manager.unregister_all()
                # Register new hotkey
                if self.hotkey_manager.register_hotkey(new_hotkey):
                    # Save to config
                    config = postprocess.load_config()
                    config.screenshot_hotkey = new_hotkey
                    postprocess.save_config(config)
                    self.log_text.appendPlainText(f"Hotkey changed to: {new_hotkey}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to register hotkey: {new_hotkey}")

    @Slot()
    def on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Work_OCR",
            "<h2>Work_OCR</h2>"
            "<p>A desktop OCR application for extracting text and tables from screenshots.</p>"
            "<p>Powered by PaddleOCR and PySide6.</p>"
        )

    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up temp files
        if self.current_screenshot_path and os.path.exists(self.current_screenshot_path):
            try:
                os.remove(self.current_screenshot_path)
            except Exception:
                pass

        # Stop worker
        if self.worker and self.worker.isRunning():
            self.worker.stop()

        # Unregister hotkeys
        if self.hotkey_manager:
            self.hotkey_manager.unregister_all()

        event.accept()


class HotkeyConfigDialog(QDialog):
    """Dialog for configuring global hotkey."""

    def __init__(self, parent=None, hotkey_manager=None):
        super().__init__(parent)
        self.hotkey_manager = hotkey_manager
        self.setWindowTitle("Configure Hotkey")
        self.setModal(True)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # Instructions
        layout.addWidget(QLabel("Enter a hotkey combination (e.g., 'ctrl+alt+s', 'f1'):"))

        # Hotkey input
        self.hotkey_input = QLineEdit()
        config = postprocess.load_config()
        self.hotkey_input.setText(config.screenshot_hotkey)
        layout.addWidget(self.hotkey_input)

        # Validation label
        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("color: red;")
        layout.addWidget(self.validation_label)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test")
        self.test_btn.clicked.connect(self.test_hotkey)
        btn_layout.addWidget(self.test_btn)
        
        btn_layout.addStretch()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.validate_and_accept)
        btn_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)

    def test_hotkey(self):
        """Test if hotkey format is valid."""
        hotkey = self.hotkey_input.text().strip()
        if self.hotkey_manager:
            is_valid = self.hotkey_manager.validate_hotkey(hotkey)
            if is_valid:
                self.validation_label.setText("✓ Valid hotkey format")
                self.validation_label.setStyleSheet("color: green;")
            else:
                self.validation_label.setText("✗ Invalid hotkey format")
                self.validation_label.setStyleSheet("color: red;")

    def validate_and_accept(self):
        """Validate hotkey and accept dialog."""
        hotkey = self.hotkey_input.text().strip()
        if not hotkey:
            self.validation_label.setText("Hotkey cannot be empty")
            return
        self.accept()

    def get_hotkey(self) -> str:
        """Get the configured hotkey."""
        return self.hotkey_input.text().strip()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Work_OCR")
    
    # Set application style
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
