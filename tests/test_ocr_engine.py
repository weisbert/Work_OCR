import logging
import os
import unittest
from pathlib import Path

os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")

from ocr_engine import OCREngine


class TestOCREngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.image_path = Path("test_pic") / "test_pic1_data_table.png"
        cls.logger = logging.getLogger("ocr_engine_test")
        cls.logger.setLevel(logging.INFO)

    def test_initialize(self) -> None:
        engine = OCREngine(lang="ch", logger=self.logger)
        elapsed = engine.initialize()
        self.assertIsInstance(elapsed, float)
        self.assertGreaterEqual(elapsed, 0.0)

    def test_recognize_output_format(self) -> None:
        if not self.image_path.exists():
            self.skipTest("test image not found")

        engine = OCREngine(lang="ch", logger=self.logger)
        engine.initialize()
        results = engine.recognize(str(self.image_path))

        self.assertIsInstance(results, list)
        if not results:
            self.fail("OCR returned empty result; check model download or image quality")

        for item in results:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            bbox, text_score = item
            text, score = text_score

            self.assertIsInstance(bbox, list)
            self.assertEqual(len(bbox), 4)
            for point in bbox:
                self.assertIsInstance(point, list)
                self.assertEqual(len(point), 2)

            self.assertIsInstance(text, str)
            self.assertIsInstance(score, float)


if __name__ == "__main__":
    unittest.main(verbosity=2)
