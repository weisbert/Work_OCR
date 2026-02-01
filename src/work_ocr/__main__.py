# -*- coding: utf-8 -*-
"""
Entry point for running Work OCR as a module.

Usage:
    python -m work_ocr
"""

import sys
from .app import main

if __name__ == "__main__":
    sys.exit(main())
