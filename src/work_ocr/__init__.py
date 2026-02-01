# -*- coding: utf-8 -*-
"""
Work OCR - A desktop OCR application for Windows 11.

This package provides OCR functionality with focus on table data extraction
and text recognition using PaddleOCR (CPU-only).
"""

__version__ = "1.0.0"
__author__ = "Work OCR Team"

from .ocr_engine import OCREngine, OCREngineError
from .layout import detect_mode, reconstruct_table, reconstruct_text
from .postprocess import (
    ParsedValue,
    PostprocessSettings,
    parse_cell,
    apply_threshold,
    convert_unit,
    process_tsv,
)

__all__ = [
    "OCREngine",
    "OCREngineError",
    "detect_mode",
    "reconstruct_table",
    "reconstruct_text",
    "ParsedValue",
    "PostprocessSettings",
    "parse_cell",
    "apply_threshold",
    "convert_unit",
    "process_tsv",
]
