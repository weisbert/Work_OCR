# -*- coding: utf-8 -*-
"""
Unit tests for the main application (app.py).

These tests use mocking to isolate the application logic from the backend engines
(OCR, layout, etc.) to verify UI logic, state management, and orchestration.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock, ANY

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtCore import Qt # Needed for QPixmap.isNull()

# Ensure the app module can be found
sys.path.insert(0, '.')
from app import MainWindow, OcrWorker

class TestAppLogic(unittest.TestCase):
    """
    Tests the core logic of the application, including the OcrWorker and MainWindow state transitions.
    """
    qt_app = None

    @classmethod
    def setUpClass(cls):
        """Create a QApplication instance before any tests are run."""
        cls.qt_app = QApplication.instance()
        if not cls.qt_app:
            cls.qt_app = QApplication(sys.argv)

    @classmethod
    def tearDownClass(cls):
        """Clean up the QApplication instance."""
        cls.qt_app = None

    # Common patches for OcrWorker tests
    @patch('app.postprocess.process_tsv')
    @patch('app.postprocess.load_config')
    @patch('app.layout.reconstruct_table')
    @patch('app.layout.reconstruct_text')
    @patch('app.layout.detect_mode')
    @patch('app.ocr_engine.OCREngine')
    def test_ocr_worker_table_mode_success(self, mock_ocr_engine_cls, mock_detect_mode, mock_reconstruct_text, mock_reconstruct_table, mock_load_config, mock_process_tsv):
        """
        Test that OcrWorker successfully processes a table using functional calls.
        """
        # 1. Setup Mocks
        mock_ocr = mock_ocr_engine_cls.return_value
        mock_ocr.recognize.return_value = "raw ocr result"
        mock_detect_mode.return_value = "table"
        mock_reconstruct_table.return_value = "reconstructed_table_tsv"
        mock_load_config.return_value = "dummy_settings"
        mock_process_tsv.return_value = "post_processed_table_data"

        # 2. Initialize and run the worker
        worker = OcrWorker("dummy_path.png", "auto", mock_ocr)
        finished_slot, error_slot, progress_slot = MagicMock(), MagicMock(), MagicMock()
        worker.finished.connect(finished_slot)
        worker.error.connect(error_slot)
        worker.progress.connect(progress_slot)
        
        worker.run()

        # 3. Assertions
        mock_ocr.recognize.assert_called_once_with("dummy_path.png")
        mock_detect_mode.assert_called_once_with("raw ocr result")
        mock_reconstruct_table.assert_called_once_with("raw ocr result")
        mock_load_config.assert_called_once()
        mock_process_tsv.assert_called_once_with("reconstructed_table_tsv", "dummy_settings")
        
        error_slot.assert_not_called()
        self.assertGreaterEqual(progress_slot.call_count, 4)
        
        finished_slot.assert_called_once_with(
            "reconstructed_table_tsv", 
            "post_processed_table_data", 
            "table", 
            "dummy_path.png"
        )
        mock_reconstruct_text.assert_not_called() # Should not be called in table mode

    @patch('app.postprocess.process_tsv')
    @patch('app.postprocess.load_config')
    @patch('app.layout.reconstruct_table')
    @patch('app.layout.reconstruct_text_with_postprocess')
    @patch('app.layout.detect_mode')
    @patch('app.ocr_engine.OCREngine')
    def test_ocr_worker_text_mode_success(self, mock_ocr_engine_cls, mock_detect_mode, mock_reconstruct_text_with_postprocess, mock_reconstruct_table, mock_load_config, mock_process_tsv):
        """
        Test that OcrWorker successfully processes text mode using functional calls.
        """
        # 1. Setup Mocks
        mock_ocr = mock_ocr_engine_cls.return_value
        mock_ocr.recognize.return_value = "raw ocr data for text"
        mock_detect_mode.return_value = "text" # Force text mode
        mock_reconstruct_text_with_postprocess.return_value = "reconstructed plain text"

        # 2. Initialize and run the worker
        worker = OcrWorker("dummy_path_text.png", "auto", mock_ocr)
        finished_slot, error_slot, progress_slot = MagicMock(), MagicMock(), MagicMock()
        worker.finished.connect(finished_slot)
        worker.error.connect(error_slot)
        worker.progress.connect(progress_slot)
        
        worker.run()

        # 3. Assertions
        mock_ocr.recognize.assert_called_once_with("dummy_path_text.png")
        mock_detect_mode.assert_called_once_with("raw ocr data for text")
        mock_reconstruct_text_with_postprocess.assert_called_once_with("raw ocr data for text")
        
        mock_load_config.assert_not_called() # Should not load config for text
        mock_process_tsv.assert_not_called() # Should not process TSV for text
        mock_reconstruct_table.assert_not_called() # Should not be called in text mode
        
        error_slot.assert_not_called()
        self.assertGreaterEqual(progress_slot.call_count, 4)
        
        finished_slot.assert_called_once_with(
            "reconstructed plain text", 
            "", # Post-processed result should be empty for text mode
            "text", 
            "dummy_path_text.png"
        )

    @patch('app.ocr_engine.OCREngine')
    def test_ocr_worker_error_handling(self, mock_ocr_engine_cls):
        """
        Test that OcrWorker emits an error signal when an exception occurs.
        """
        # 1. Setup Mocks to raise an exception
        mock_ocr = mock_ocr_engine_cls.return_value
        mock_ocr.recognize.side_effect = ValueError("OCR engine failed")

        # 2. Initialize and run the worker
        worker = OcrWorker("dummy_path.png", "auto", mock_ocr)
        finished_slot = MagicMock()
        error_slot = MagicMock()
        worker.finished.connect(finished_slot)
        worker.error.connect(error_slot)
        
        worker.run()

        # 3. Assertions
        finished_slot.assert_not_called()
        error_slot.assert_called_once_with("An error occurred in the worker thread: OCR engine failed")

    # Common patches for MainWindow tests
    # Mock 'app.tempfile' and 'app.os' for temporary file handling in on_screenshot_captured
    @patch('app.tempfile.mkstemp', return_value=(0, 'mock_temp_path.png'))
    @patch('app.os.close')
    @patch('app.os.remove') 
    @patch.object(QPixmap, 'save', return_value=True) # Mock QPixmap.save
    @patch('app.capture.CaptureWindow')
    @patch('app.QApplication.processEvents') # Mock processEvents
    @patch('app.ocr_engine.OCREngine')
    def test_main_window_state_after_processing(self, mock_ocr_cls, mock_process_events, mock_capture_window_cls, mock_pixmap_save, mock_os_remove, mock_os_close, mock_mkstemp):
        """
        Test if the MainWindow correctly updates its state when the worker finishes.
        """
        window = MainWindow()
        window.mode_combo.setCurrentText("Auto") # Start in auto-detect mode

        # Simulate the worker finishing by directly calling the connected slot
        window.on_processing_finished(
            layout_result="final layout text",
            post_result="final post-processed text",
            detected_mode="table",
            image_path="dummy.png"
        )

        # Assert UI state is updated as expected
        self.assertEqual(window.ocr_result_text.toPlainText(), "final layout text")
        self.assertEqual(window.postprocessed_text.toPlainText(), "final post-processed text")
        self.assertEqual(window.mode_combo.currentText(), "Table", "Mode should be updated to detected mode")
        self.assertEqual(window.tabs.currentIndex(), 1, "Should switch to post-processed tab for tables")
        self.assertIsNone(window.worker, "Worker instance should be cleared after finishing")

    @patch('app.tempfile.mkstemp', return_value=(0, 'mock_temp_path.png'))
    @patch('app.os.close')
    @patch('app.os.remove') 
    @patch.object(QPixmap, 'save', return_value=True) # Mock QPixmap.save
    @patch('app.capture.CaptureWindow')
    @patch('app.QApplication.processEvents') # Mock processEvents
    @patch('app.ocr_engine.OCREngine')
    def test_main_window_clear_functionality(self, mock_ocr_cls, mock_process_events, mock_capture_window_cls, mock_pixmap_save, mock_os_remove, mock_os_close, mock_mkstemp):
        """
        Test the 'Clear' button logic.
        """
        window = MainWindow()
        
        # Set some initial state
        window.image_label.setPixmap(QPixmap(1,1)) # Needs a valid pixmap for isNull to work
        window.image_label.setText("some initial image text") # Set a non-default text to verify clear_results
        window.ocr_result_text.setPlainText("some text")
        window.postprocessed_text.setPlainText("some other text")
        window.log_text.appendPlainText("log message")
        window.progress_bar.setValue(50)
        window.mode_combo.setCurrentText("Table")

        # Call the method to be tested
        window.clear_all()

        # Assert that everything was cleared
        self.assertEqual(window.image_label.text(), "Screenshot will appear here")
        self.assertTrue(window.image_label.pixmap().isNull())
        self.assertEqual(window.ocr_result_text.toPlainText(), "")
        self.assertEqual(window.postprocessed_text.toPlainText(), "")
        self.assertEqual(window.log_text.toPlainText(), "", "Log should be cleared by clear_all")
        self.assertEqual(window.progress_bar.value(), 0)
        self.assertEqual(window.mode_combo.currentText(), "Auto", "Mode should reset to Auto")

    @patch('app.tempfile.mkstemp', return_value=(0, 'mock_temp_path.png'))
    @patch('app.os.close')
    @patch('app.os.remove') 
    @patch.object(QPixmap, 'save', return_value=True) # Mock QPixmap.save
    @patch('app.capture.CaptureWindow')
    @patch('app.QApplication.processEvents') # Mock processEvents
    @patch('app.ocr_engine.OCREngine')
    def test_main_window_copy_to_clipboard(self, mock_ocr_cls, mock_process_events, mock_capture_window_cls, mock_pixmap_save, mock_os_remove, mock_os_close, mock_mkstemp):
        """
        Test the 'Copy' button logic for both tabs.
        """
        window = MainWindow()
        clipboard = QGuiApplication.clipboard()

        # Test copying from the first tab
        window.tabs.setCurrentIndex(0)
        window.ocr_result_text.setPlainText("text from tab 1")
        window.copy_to_clipboard()
        self.assertEqual(clipboard.text(), "text from tab 1")

        # Test copying from the second tab
        window.tabs.setCurrentIndex(1)
        window.postprocessed_text.setPlainText("text from tab 2")
        window.copy_to_clipboard()
        self.assertEqual(clipboard.text(), "text from tab 2")


if __name__ == '__main__':
    unittest.main(verbosity=2)