from __future__ import annotations

import time
from pathlib import Path
import os
from typing import Any, Iterable, List, Optional, Sequence, Tuple

os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    np = None

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None

from paddleocr import PaddleOCR

BBox = List[List[float]]
OCRResult = List[Tuple[BBox, str, float]]


class OCREngineError(RuntimeError):
    """Raised when OCR initialization or recognition fails."""


class OCREngine:
    """Lightweight PaddleOCR wrapper for CPU-only usage."""

    def __init__(
        self,
        lang: str = "ch",
        use_angle_cls: bool = True,
        logger: Optional[Any] = None,
        padding: int = 20,
    ) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._logger = logger
        self._padding = padding
        self._ocr: Optional[PaddleOCR] = None
        self._initialized = False
        self._init_seconds: Optional[float] = None

    def initialize(self) -> float:
        """Initialize the PaddleOCR model once and return elapsed seconds."""
        if self._initialized and self._init_seconds is not None:
            return self._init_seconds

        start = time.perf_counter()
        try:
            import paddle

            self._set_paddle_flags(paddle)
            paddle.set_device("cpu")
            self._ocr = PaddleOCR(
                use_textline_orientation=self.use_angle_cls,
                lang=self.lang,
            )
        except Exception as exc:
            raise OCREngineError(f"Failed to initialize PaddleOCR: {exc}") from exc

        self._initialized = True
        self._init_seconds = time.perf_counter() - start
        self._log_info(f"OCR initialized in {self._init_seconds:.3f}s")
        return self._init_seconds

    def recognize(self, image: Any) -> OCRResult:
        """Run OCR on an image and return [(bbox, text, score), ...]."""
        if not self._initialized:
            self.initialize()
        assert self._ocr is not None

        image_np = self._normalize_input(image)
        padded_image = self._add_padding(image_np)

        start = time.perf_counter()
        try:
            raw = self._ocr.predict(padded_image)
        except Exception as exc:
            raise OCREngineError(f"OCR recognition failed: {exc}") from exc
        elapsed = time.perf_counter() - start

        items = self._extract_items(raw)
        results: OCRResult = []
        for item in items:
            bbox, text_score = item
            text, score = text_score
            results.append((bbox, (str(text), float(score))))

        self._log_info(f"OCR recognize finished in {elapsed:.3f}s, {len(results)} items")
        if not results:
            self._log_warning("OCR result is empty")
        return results

    def _normalize_input(self, image: Any) -> np.ndarray:
        """Ensure the input image is a NumPy array in BGR format."""
        if isinstance(image, np.ndarray):
            return image
        if isinstance(image, (str, Path)):
            if cv2 is None:
                raise OCREngineError("OpenCV (cv2) is required to read image files.")
            image_bgr = cv2.imread(str(image))
            if image_bgr is None:
                raise OCREngineError(f"Could not read image from path: {image}")
            return image_bgr
        if Image is not None and isinstance(image, Image.Image):
            if np is None:
                raise OCREngineError("NumPy is required to handle PIL images")
            # Convert PIL (RGB) to OpenCV (BGR)
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        raise OCREngineError(f"Unsupported image type: {type(image)}")

    def _add_padding(self, image: np.ndarray) -> np.ndarray:
        """Add a white border to the image to help detect text near edges."""
        if self._padding <= 0:
            return image
        if cv2 is None:
            self._log_warning("OpenCV (cv2) not available, cannot add padding.")
            return image
        return cv2.copyMakeBorder(
            image,
            self._padding,
            self._padding,
            self._padding,
            self._padding,
            cv2.BORDER_CONSTANT,
            value=[255, 255, 255],  # White border
        )

    def _extract_items(self, raw: Any) -> Sequence[Sequence[Any]]:
        """Extracts items from the new dictionary-based PaddleOCR result format."""
        if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
            return []

        result_dict = raw[0]
        boxes = result_dict.get("rec_polys")
        texts = result_dict.get("rec_texts")
        scores = result_dict.get("rec_scores")

        if not all([boxes, texts, scores]) or len(texts) != len(scores) or len(texts) != len(boxes):
            return []

        reformatted_items = []
        for box, text, score in zip(boxes, texts, scores):
            # Convert numpy array to list of lists and adjust for padding
            if hasattr(box, 'tolist'):
                bbox_list = [[pt[0] - self._padding, pt[1] - self._padding] for pt in box]
            else:
                bbox_list = box
            reformatted_items.append([bbox_list, [text, score]])
        return reformatted_items

    @staticmethod
    def _is_item(obj: Any) -> bool:
        if not isinstance(obj, (list, tuple)) or len(obj) != 2:
            return False
        bbox = obj[0]
        if not isinstance(bbox, list) or len(bbox) != 4:
            return False
        if not all(isinstance(pt, (list, tuple)) and len(pt) == 2 for pt in bbox):
            return False
        return True

    def _log_info(self, message: str) -> None:
        if self._logger is not None:
            try:
                self._logger.info(message)
            except Exception:
                pass

    def _log_warning(self, message: str) -> None:
        if self._logger is not None:
            try:
                self._logger.warning(message)
            except Exception:
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
            except Exception:
                pass
