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

from work_ocr.app import MainWindow, OcrWorker
from work_ocr import layout, postprocess

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
    @patch('work_ocr.app.postprocess.process_tsv')
    @patch('work_ocr.app.postprocess.load_config')
    @patch('work_ocr.app.layout.reconstruct_table')
    @patch('work_ocr.app.layout.reconstruct_text_with_postprocess')
    @patch('work_ocr.app.ocr_engine.OCREngine')
    def test_ocr_worker_table_mode_success(self, mock_ocr_engine_cls, mock_reconstruct_text_with_postprocess, mock_reconstruct_table, mock_load_config, mock_process_tsv):
        """
        Test that OcrWorker successfully processes a table in 'table' mode.
        Should call reconstruct_table and perform post-processing.
        """
        # 1. Setup Mocks
        mock_ocr = mock_ocr_engine_cls.return_value
        mock_ocr.recognize.return_value = "raw ocr result"
        mock_reconstruct_table.return_value = "reconstructed_table_tsv"
        mock_load_config.return_value = "dummy_settings"
        mock_process_tsv.return_value = "post_processed_table_data"

        # 2. Initialize and run the worker in 'table' mode
        worker = OcrWorker("dummy_path.png", "table", mock_ocr)
        finished_slot, error_slot, progress_slot = MagicMock(), MagicMock(), MagicMock()
        worker.finished.connect(finished_slot)
        worker.error.connect(error_slot)
        worker.progress.connect(progress_slot)
        
        worker.run()

        # 3. Assertions
        mock_ocr.recognize.assert_called_once_with("dummy_path.png")
        # Should NOT call detect_mode in 'table' mode
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
        mock_reconstruct_text_with_postprocess.assert_not_called() # Should not be called in table mode

    @patch('work_ocr.app.postprocess.process_tsv')
    @patch('work_ocr.app.postprocess.load_config')
    @patch('work_ocr.app.layout.reconstruct_table')
    @patch('work_ocr.app.layout.reconstruct_text_with_postprocess')
    @patch('work_ocr.app.ocr_engine.OCREngine')
    def test_ocr_worker_default_mode_with_text(self, mock_ocr_engine_cls, mock_reconstruct_text_with_postprocess, mock_reconstruct_table, mock_load_config, mock_process_tsv):
        """
        Test that OcrWorker processes plain text in 'default' mode.
        Should call reconstruct_text_with_postprocess and skip post-processing (no tabs in result).
        """
        # 1. Setup Mocks
        mock_ocr = mock_ocr_engine_cls.return_value
        mock_ocr.recognize.return_value = "raw ocr data"
        # Return plain text without tabs (not table data)
        mock_reconstruct_text_with_postprocess.return_value = "This is plain text\nwithout any table structure"

        # 2. Initialize and run the worker in 'default' mode
        worker = OcrWorker("dummy_path_text.png", "default", mock_ocr)
        finished_slot, error_slot, progress_slot = MagicMock(), MagicMock(), MagicMock()
        worker.finished.connect(finished_slot)
        worker.error.connect(error_slot)
        worker.progress.connect(progress_slot)
        
        worker.run()

        # 3. Assertions
        mock_ocr.recognize.assert_called_once_with("dummy_path_text.png")
        mock_reconstruct_text_with_postprocess.assert_called_once_with("raw ocr data")
        
        mock_load_config.assert_not_called() # Should not load config for plain text
        mock_process_tsv.assert_not_called() # Should not process TSV for plain text
        mock_reconstruct_table.assert_not_called() # Should not be called in default mode
        
        error_slot.assert_not_called()
        self.assertGreaterEqual(progress_slot.call_count, 4)
        
        finished_slot.assert_called_once_with(
            "This is plain text\nwithout any table structure", 
            "", # Post-processed result should be empty for plain text
            "default", 
            "dummy_path_text.png"
        )

    @patch('work_ocr.app.postprocess.process_tsv')
    @patch('work_ocr.app.postprocess.load_config')
    @patch('work_ocr.app.layout.reconstruct_table')
    @patch('work_ocr.app.layout.reconstruct_text_with_postprocess')
    @patch('work_ocr.app.ocr_engine.OCREngine')
    def test_ocr_worker_default_mode_no_auto_postprocess(self, mock_ocr_engine_cls, mock_reconstruct_text_with_postprocess, mock_reconstruct_table, mock_load_config, mock_process_tsv):
        """
        Test that OcrWorker does NOT auto post-process in 'default' mode.
        Even if result contains tabs (table data), post_result should be empty.
        User can view processed result on-demand by switching to Post-processed tab.
        """
        # 1. Setup Mocks
        mock_ocr = mock_ocr_engine_cls.return_value
        mock_ocr.recognize.return_value = "raw ocr data"
        # Return table data with tabs - but should NOT be auto-processed
        mock_reconstruct_text_with_postprocess.return_value = "col1\tcol2\nval1\tval2"

        # 2. Initialize and run the worker in 'default' mode
        worker = OcrWorker("dummy_path_table.png", "default", mock_ocr)
        finished_slot, error_slot, progress_slot = MagicMock(), MagicMock(), MagicMock()
        worker.finished.connect(finished_slot)
        worker.error.connect(error_slot)
        worker.progress.connect(progress_slot)
        
        worker.run()

        # 3. Assertions
        mock_ocr.recognize.assert_called_once_with("dummy_path_table.png")
        mock_reconstruct_text_with_postprocess.assert_called_once_with("raw ocr data")
        
        # Should NOT auto post-process in default mode
        mock_load_config.assert_not_called()
        mock_process_tsv.assert_not_called()
        mock_reconstruct_table.assert_not_called()
        
        error_slot.assert_not_called()
        self.assertGreaterEqual(progress_slot.call_count, 4)
        
        # Post-processed result should be empty - user can trigger it on-demand
        finished_slot.assert_called_once_with(
            "col1\tcol2\nval1\tval2", 
            "", # Post-processed result should be EMPTY in default mode
            "default", 
            "dummy_path_table.png"
        )

    @patch('work_ocr.app.ocr_engine.OCREngine')
    def test_ocr_worker_error_handling(self, mock_ocr_engine_cls):
        """
        Test that OcrWorker emits an error signal when an exception occurs.
        """
        # 1. Setup Mocks to raise an exception
        mock_ocr = mock_ocr_engine_cls.return_value
        mock_ocr.recognize.side_effect = ValueError("OCR engine failed")

        # 2. Initialize and run the worker
        worker = OcrWorker("dummy_path.png", "default", mock_ocr)
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
    @patch('work_ocr.app.tempfile.mkstemp', return_value=(0, 'mock_temp_path.png'))
    @patch('work_ocr.app.os.close')
    @patch('work_ocr.app.os.remove') 
    @patch.object(QPixmap, 'save', return_value=True) # Mock QPixmap.save
    @patch('work_ocr.app.capture.CaptureWindow')
    @patch('work_ocr.app.QApplication.processEvents') # Mock processEvents
    @patch('work_ocr.app.ocr_engine.OCREngine')
    def test_main_window_table_mode_auto_switch_tab(self, mock_ocr_cls, mock_process_events, mock_capture_window_cls, mock_pixmap_save, mock_os_remove, mock_os_close, mock_mkstemp):
        """
        Test that MainWindow auto-switches to Post-processed tab in 'table' mode.
        """
        window = MainWindow()
        window.mode_combo.setCurrentText("Table") # Start in table mode

        # Simulate the worker finishing by directly calling the connected slot
        window.on_processing_finished(
            layout_result="col1\tcol2\nval1\tval2",
            post_result="processed_col1\tprocessed_col2",
            detected_mode="table",
            image_path="dummy.png"
        )

        # Assert UI state is updated as expected
        self.assertEqual(window.ocr_result_text.toPlainText(), "col1\tcol2\nval1\tval2")
        self.assertEqual(window.postprocessed_text.toPlainText(), "processed_col1\tprocessed_col2")
        self.assertEqual(window.mode_combo.currentText(), "Table")
        self.assertEqual(window.tabs.currentIndex(), 1, "Should switch to post-processed tab for table mode")
        self.assertIsNone(window.worker, "Worker instance should be cleared after finishing")

    @patch('work_ocr.app.tempfile.mkstemp', return_value=(0, 'mock_temp_path.png'))
    @patch('work_ocr.app.os.close')
    @patch('work_ocr.app.os.remove') 
    @patch.object(QPixmap, 'save', return_value=True)
    @patch('work_ocr.app.capture.CaptureWindow')
    @patch('work_ocr.app.QApplication.processEvents')
    @patch('work_ocr.app.ocr_engine.OCREngine')
    def test_main_window_default_mode_no_auto_switch_tab(self, mock_ocr_cls, mock_process_events, mock_capture_window_cls, mock_pixmap_save, mock_os_remove, mock_os_close, mock_mkstemp):
        """
        Test that MainWindow does NOT auto-switch tab in 'default' mode.
        Even if the content looks like a table, should stay on OCR Result tab.
        """
        window = MainWindow()
        window.mode_combo.setCurrentText("Default") # Start in default mode

        # Simulate the worker finishing with table-like content
        window.on_processing_finished(
            layout_result="col1\tcol2\nval1\tval2",
            post_result="",
            detected_mode="default",
            image_path="dummy.png"
        )

        # Assert UI state - should stay on OCR Result tab (index 0)
        self.assertEqual(window.ocr_result_text.toPlainText(), "col1\tcol2\nval1\tval2")
        self.assertEqual(window.tabs.currentIndex(), 0, "Should stay on OCR Result tab in default mode")

    @patch('work_ocr.app.tempfile.mkstemp', return_value=(0, 'mock_temp_path.png'))
    @patch('work_ocr.app.os.close')
    @patch('work_ocr.app.os.remove') 
    @patch.object(QPixmap, 'save', return_value=True)
    @patch('work_ocr.app.capture.CaptureWindow')
    @patch('work_ocr.app.QApplication.processEvents')
    @patch('work_ocr.app.ocr_engine.OCREngine')
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
        # Mode should NOT be reset - preserve user's selection
        self.assertEqual(window.mode_combo.currentText(), "Table", "Mode should be preserved")

    @patch('work_ocr.app.tempfile.mkstemp', return_value=(0, 'mock_temp_path.png'))
    @patch('work_ocr.app.os.close')
    @patch('work_ocr.app.os.remove') 
    @patch.object(QPixmap, 'save', return_value=True)
    @patch('work_ocr.app.capture.CaptureWindow')
    @patch('work_ocr.app.QApplication.processEvents')
    @patch('work_ocr.app.ocr_engine.OCREngine')
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

    @patch('work_ocr.app.tempfile.mkstemp', return_value=(0, 'mock_temp_path.png'))
    @patch('work_ocr.app.os.close')
    @patch('work_ocr.app.os.remove') 
    @patch.object(QPixmap, 'save', return_value=True)
    @patch('work_ocr.app.capture.CaptureWindow')
    @patch('work_ocr.app.QApplication.processEvents')
    @patch('work_ocr.app.ocr_engine.OCREngine')
    def test_main_window_generate_button_in_default_mode(self, mock_ocr_cls, mock_process_events, mock_capture_window_cls, mock_pixmap_save, mock_os_remove, mock_os_close, mock_mkstemp):
        """
        Test that clicking Generate button in 'default' mode creates post-process preview.
        """
        from work_ocr import postprocess
        
        window = MainWindow()
        
        # Simulate having OCR result (as if user just recognized a table in default mode)
        window.original_ocr_result = "5.1k\t10nF\n1.5M\t2.2k"
        window.ocr_result_text.setPlainText("5.1k\t10nF\n1.5M\t2.2k")
        
        # Initially postprocessed_text should be empty (default mode doesn't auto-process)
        self.assertEqual(window.postprocessed_text.toPlainText(), "")
        
        # Click Generate button
        window.on_generate_postprocess()
        
        # Now postprocessed_text should have content (post-processing applied)
        processed_text = window.postprocessed_text.toPlainText()
        self.assertNotEqual(processed_text, "")
        # The content should be processed (tab-separated, possibly with unit conversion)
        self.assertIn("\t", processed_text)  # Should be tab-separated


if __name__ == '__main__':
    unittest.main(verbosity=2)