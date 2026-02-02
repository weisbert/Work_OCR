# -*- coding: utf-8 -*-
"""OCR engine wrapper with cancellation support."""

from __future__ import annotations

import time
from pathlib import Path
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

try:
    import numpy as np
except Exception:
    np = None

try:
    import cv2
except Exception:
    cv2 = None

try:
    from PIL import Image
except Exception:
    Image = None

from paddleocr import PaddleOCR

BBox = List[List[float]]
OCRResult = List[Tuple[BBox, str, float]]


class OCREngineError(RuntimeError):
    """Raised when OCR initialization or recognition fails."""


class CancelledError(OCREngineError):
    """Raised when OCR operation is cancelled."""


class OCREngine:
    """Lightweight PaddleOCR wrapper with cancellation support."""

    def __init__(
        self,
        lang: str = "ch",
        logger: Optional[Any] = None,
        padding: int = 10,
        **kwargs: Any,
    ) -> None:
        self.lang = lang
        self._logger = logger
        self._padding = padding
        self.ocr_params = self._convert_params(kwargs)
        self._ocr: Optional[PaddleOCR] = None
        self._initialized = False
        self._cancelled = False

    def _convert_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parameters for PaddleOCR."""
        converted = dict(params)
        converted.pop("show_log", None)
        converted.pop("logger", None)
        
        if "use_angle_cls" in converted:
            use_angle_cls = converted.pop("use_angle_cls")
            converted["use_textline_orientation"] = use_angle_cls
        
        return converted

    def initialize(self) -> None:
        """Initialize the PaddleOCR model."""
        if self._cancelled:
            raise CancelledError("OCR initialization was cancelled")
        
        if self._initialized:
            return
        
        import paddle
        self._set_paddle_flags(paddle)
        paddle.set_device("cpu")
        
        init_params = {"lang": self.lang, **self.ocr_params}
        self._log_info(f"Initializing PaddleOCR...")
        self._ocr = PaddleOCR(**init_params)
        self._initialized = True
        self._log_info("OCR initialized")

    def cancel(self):
        """Mark this engine as cancelled."""
        self._cancelled = True
        self._log_info("OCR cancellation requested")

    def is_cancelled(self) -> bool:
        """Check if this engine has been cancelled."""
        return self._cancelled

    def recognize(self, image: Any) -> OCRResult:
        """Run OCR on an image.
        
        Note: This method blocks until recognition completes.
        To cancel, call cancel() from another thread before/during execution.
        """
        if self._cancelled:
            raise CancelledError("OCR was cancelled before start")

        if not self._initialized:
            self.initialize()
        
        if self._cancelled:
            raise CancelledError("OCR was cancelled after init")

        image_np = self._normalize_input(image)
        padded_image = self._add_padding(image_np)

        self._log_info("Starting OCR recognition...")
        start = time.time()
        
        try:
            raw = self._ocr.predict(padded_image)
        except Exception as e:
            if self._cancelled:
                raise CancelledError("OCR was cancelled") from e
            raise OCREngineError(f"OCR recognition failed: {e}") from e

        elapsed = time.time() - start
        self._log_info(f"OCR completed in {elapsed:.2f}s")

        if self._cancelled:
            raise CancelledError("OCR was cancelled after completion")

        return self._extract_results(raw)

    def _extract_results(self, raw: Any) -> OCRResult:
        """Extract OCR results from PaddleOCR output."""
        if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
            return []

        result_dict = raw[0]
        boxes = result_dict.get("rec_polys", [])
        texts = result_dict.get("rec_texts", [])
        scores = result_dict.get("rec_scores", [])

        results = []
        for box, text, score in zip(boxes, texts, scores):
            if hasattr(box, 'tolist'):
                bbox_list = [[pt[0] - self._padding, pt[1] - self._padding] for pt in box]
            else:
                bbox_list = box
            results.append((bbox_list, (str(text), float(score))))
        
        return results

    def _normalize_input(self, image: Any) -> np.ndarray:
        """Normalize input to numpy array."""
        if isinstance(image, np.ndarray):
            return image
        if isinstance(image, (str, Path)):
            if cv2 is None:
                raise OCREngineError("OpenCV required")
            img = cv2.imread(str(image))
            if img is None:
                raise OCREngineError(f"Cannot read image: {image}")
            return img
        if Image is not None and isinstance(image, Image.Image):
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        raise OCREngineError(f"Unsupported image type: {type(image)}")

    def _add_padding(self, image: np.ndarray) -> np.ndarray:
        """Add white border to image."""
        if self._padding <= 0 or cv2 is None:
            return image
        return cv2.copyMakeBorder(
            image, self._padding, self._padding, self._padding, self._padding,
            cv2.BORDER_CONSTANT, value=[255, 255, 255]
        )

    def _log_info(self, message: str) -> None:
        if self._logger:
            try:
                self._logger.info(message)
            except:
                pass

    def _log_warning(self, message: str) -> None:
        if self._logger:
            try:
                self._logger.warning(message)
            except:
                pass

    @staticmethod
    def _set_paddle_flags(paddle_module: Any) -> None:
        flags = {
            "FLAGS_use_mkldnn": False,
            "FLAGS_enable_onednn": False,
            "FLAGS_enable_new_ir": False,
            "FLAGS_enable_new_executor": False,
            "FLAGS_enable_pir_api": False,
            "FLAGS_enable_pir_in_executor": False,
        }
        for name, value in flags.items():
            try:
                paddle_module.set_flags({name: value})
            except:
                pass
