# -*- coding: utf-8 -*-
import unittest
import os
import sys

from work_ocr.layout import (
    normalize_bbox,
    detect_mode,
    reconstruct_table,
    reconstruct_text,
    OcrResult
)

class TestLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up mock OCR data for testing."""
        # Mock data representing a simple 2x2 table
        cls.table_ocr_result: OcrResult = [
            ([[10, 10], [100, 10], [100, 30], [10, 30]], ("Header1", 0.99)),
            ([[120, 12], [210, 12], [210, 32], [120, 32]], ("Header2", 0.99)),
            ([[12, 40], [102, 40], [102, 60], [12, 60]], ("Value1", 0.98)),
            ([[125, 42], [215, 42], [215, 62], [125, 62]], ("Value2", 0.98)),
        ]

        # Mock data representing two lines of text
        cls.text_ocr_result: OcrResult = [
            ([[10, 10], [50, 10], [50, 30], [10, 30]], ("This", 0.99)),
            ([[60, 10], [80, 10], [80, 30], [60, 30]], ("is", 0.99)),
            ([[90, 10], [100, 10], [100, 30], [90, 30]], ("a", 0.99)),
            ([[110, 10], [150, 10], [150, 30], [110, 30]], ("line.", 0.99)),
            ([[10, 40], [80, 40], [80, 60], [10, 60]], ("Another", 0.98)),
            ([[90, 40], [130, 40], [130, 60], [90, 60]], ("line.", 0.98)),
        ]

        # Mock data representing a table where a cell value is split
        cls.split_cell_ocr_result: OcrResult = [
            ([[10, 10], [100, 10], [100, 30], [10, 30]], ("Header1", 0.99)),
            ([[120, 12], [210, 12], [210, 32], [120, 32]], ("Header2", 0.99)),
            ([[12, 40], [60, 40], [60, 60], [12, 60]], ("Value1A", 0.98)), # First part of a split cell
            ([[65, 40], [110, 40], [110, 60], [65, 60]], ("Value1B", 0.98)), # Second part, very close
            ([[125, 42], [215, 42], [215, 62], [125, 62]], ("Value2", 0.98)),
        ]

    def test_normalize_bbox(self):
        """Test normalization for both polygon and rectangle bboxes."""
        poly_bbox = [[10, 20], [100, 20], [100, 50], [10, 50]]
        rect_bbox = [10, 20, 100, 50]

        expected = {
            'cx': 55.0, 'cy': 35.0, 'w': 90.0, 'h': 30.0,
            'x1': 10, 'y1': 20, 'x2': 100, 'y2': 50
        }

        self.assertEqual(normalize_bbox(poly_bbox), expected)
        self.assertEqual(normalize_bbox(rect_bbox), expected)

    def test_detect_mode(self):
        """Test layout detection for table and text."""
        self.assertEqual(detect_mode(self.table_ocr_result), "table")
        self.assertEqual(detect_mode(self.text_ocr_result), "text")
        self.assertEqual(detect_mode([]), "text")

    def test_reconstruct_table(self):
        """Test TSV reconstruction for a table."""
        expected_tsv = "Header1\tHeader2\nValue1\tValue2"
        # Note: The simple clustering algorithm might have slight variations.
        # This test assumes a reasonably accurate clustering.
        result_tsv = reconstruct_table(self.table_ocr_result)
        self.assertEqual(result_tsv, expected_tsv)

    def test_reconstruct_text(self):
        """Test layout-preserved text reconstruction."""
        # The number of spaces can be heuristic. We test for content and structure.
        result_text = reconstruct_text(self.text_ocr_result)
        lines = result_text.split('\n')
        self.assertEqual(len(lines), 2)
        # Check if all words are present in the correct order
        self.assertIn("This is a line.", lines[0].replace("  ", " "))
        self.assertIn("Another line.", lines[1].replace("  ", " "))

    def test_reconstruct_table_col_gap_threshold(self):
        """Test TSV reconstruction with varying col_gap_threshold_ratio and horizontal_merge_threshold_ratio."""
        # With default horizontal_merge_threshold_ratio=0.5, "Value1A" and "Value1B" should merge
        # into one cell, separated by a space.
        result_merged = reconstruct_table(self.split_cell_ocr_result, col_gap_threshold_ratio=1.0, horizontal_merge_threshold_ratio=0.5)
        self.assertEqual(result_merged, "Header1\tHeader2\nValue1A Value1B\tValue2")

        # Test with a very low horizontal_merge_threshold_ratio to ensure they are NOT merged
        # and thus appear in separate columns (separated by a tab).
        result_not_merged = reconstruct_table(self.split_cell_ocr_result, col_gap_threshold_ratio=1.0, horizontal_merge_threshold_ratio=0.01)
        self.assertIn("Value1A\tValue1B", result_not_merged)
        self.assertNotIn("Value1A Value1B", result_not_merged)



if __name__ == '__main__':
    unittest.main(verbosity=2)
