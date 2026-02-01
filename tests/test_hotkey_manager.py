# -*- coding: utf-8 -*-
"""Tests for the hotkey manager module."""

import unittest
import sys
import os

from work_ocr.hotkey_manager import HotkeyManager


class TestHotkeyManager(unittest.TestCase):
    """Test cases for HotkeyManager."""

    def test_validate_hotkey_valid(self):
        """Test validation of valid hotkey strings."""
        valid_hotkeys = [
            "ctrl+alt+s",
            "f1",
            "f12",
            "ctrl+shift+a",
            "alt+f4",
            "ctrl+alt+shift+s",
        ]
        for hotkey in valid_hotkeys:
            with self.subTest(hotkey=hotkey):
                self.assertTrue(HotkeyManager.validate_hotkey(hotkey))

    def test_validate_hotkey_invalid(self):
        """Test validation of invalid hotkey strings."""
        invalid_hotkeys = [
            "",
            "   ",
            None,
            "invalid+key+combination+that+does+not+exist",
        ]
        for hotkey in invalid_hotkeys:
            with self.subTest(hotkey=hotkey):
                self.assertFalse(HotkeyManager.validate_hotkey(hotkey))

    def test_format_hotkey_display(self):
        """Test formatting of hotkey strings for display."""
        test_cases = [
            ("ctrl+alt+s", "Ctrl+Alt+S"),
            ("f1", "F1"),
            ("ctrl+shift+a", "Ctrl+Shift+A"),
            ("alt+f4", "Alt+F4"),
            ("", ""),
        ]
        for input_hotkey, expected_output in test_cases:
            with self.subTest(input=input_hotkey):
                result = HotkeyManager.format_hotkey_display(input_hotkey)
                self.assertEqual(result, expected_output)

    def test_hotkey_manager_init(self):
        """Test HotkeyManager initialization."""
        mgr = HotkeyManager()
        self.assertIsNone(mgr.get_registered_hotkey())


if __name__ == "__main__":
    unittest.main(verbosity=2)
