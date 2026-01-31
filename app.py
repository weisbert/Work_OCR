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
    QPlainTextEdit, QComboBox, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap, QGuiApplication

# Import project modules
import capture
import ocr_engine
import layout
import postprocess


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
        self.setup_ui()
        self.connect_signals()
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
        controls_layout.addWidget(self.screenshot_button)
        controls_layout.addWidget(self.copy_button)
        controls_layout.addWidget(self.clear_button)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Mode:"))
        controls_layout.addWidget(self.mode_combo)

        # Results Tabs
        self.tabs = QTabWidget()
        self.ocr_result_text = QTextEdit()
        self.postprocessed_text = QTextEdit()
        self.ocr_result_text.setReadOnly(True)
        self.postprocessed_text.setReadOnly(True)
        self.tabs.addTab(self.ocr_result_text, "OCR Result")
        self.tabs.addTab(self.postprocessed_text, "Post-processed")

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

    def connect_signals(self):
        """Connect UI element signals to corresponding slots."""
        self.screenshot_button.clicked.connect(self.start_screenshot)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.clear_button.clicked.connect(self.clear_all)

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
        self.capture_window.show()

    @Slot(QPixmap)
    def on_screenshot_captured(self, pixmap: QPixmap):
        """Handles the QPixmap returned from the capture window, saves it, and starts OCR."""
        self.show() # Show the main window again
        if self.capture_window:
            self.capture_window.deleteLater() # Clean up the capture window
            self.capture_window = None

        if pixmap.isNull():
            self.log_text.appendPlainText("Screenshot cancelled or failed.")
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
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, QTextEdit):
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(current_tab.toPlainText())
            tab_name = self.tabs.tabText(self.tabs.currentIndex())
            self.log_text.appendPlainText(f"Copied content of '{tab_name}' to clipboard.")

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
        self.progress_bar.setValue(0)
        self.mode_combo.setCurrentIndex(0)  # Reset to "Auto"
    
    def resizeEvent(self, event):
        """Handle window resize to scale the image preview."""
        if isinstance(self.image_label.pixmap(), QPixmap) and not self.image_label.pixmap().isNull():
            self.image_label.setPixmap(self.image_label.pixmap().scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        super().resizeEvent(event)

    def closeEvent(self, event):
        """Ensure the worker thread is terminated before closing."""
        if self.worker and self.worker.isRunning():
            self.log_text.appendPlainText("Attempting to stop active processing...")
            self.worker.terminate()
            self.worker.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
