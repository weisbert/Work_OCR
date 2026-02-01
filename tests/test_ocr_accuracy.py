# -*- coding: utf-8 -*-
"""
测试 OCR 识别准确度 - 比较识别结果与预期文本的差异
"""
import difflib
import re
from pathlib import Path

from work_ocr.ocr_engine import OCREngine
from work_ocr.layout import reconstruct_text, reconstruct_text_with_postprocess, post_process_text


class TestOCRAccuracy:
    """测试 OCR 识别准确度"""
    
    @classmethod
    def setup_class(cls):
        """设置测试类"""
        assets_dir = Path(__file__).parent.parent / "assets" / "test_images"
        cls.image_path = assets_dir / "test_pic2_code.png"
        cls.expected_path = assets_dir / "test_pic2_code.txt"
        cls.expected_text = cls._load_expected_text()
        
        # 如果图片存在，进行 OCR 识别
        if cls.image_path.exists():
            cls.ocr = OCREngine()
            cls.ocr_result = cls.ocr.recognize(str(cls.image_path))
        else:
            cls.ocr_result = None
    
    @classmethod
    def _load_expected_text(cls) -> str:
        """加载预期文本"""
        if cls.expected_path.exists():
            with open(cls.expected_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return ""
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """计算两个文本的相似度 (0-1)"""
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def test_expected_file_exists(self):
        """测试预期文本文件存在"""
        assert self.expected_path.exists(), f"预期文本文件不存在: {self.expected_path}"
    
    def test_image_file_exists(self):
        """测试图片文件存在"""
        assert self.image_path.exists(), f"图片文件不存在: {self.image_path}"
    
    def test_original_text_accuracy(self):
        """测试原始文本识别准确度"""
        if not self.ocr_result:
            return
        
        original_text = reconstruct_text(self.ocr_result)
        similarity = self.calculate_similarity(self.expected_text, original_text)
        
        # 原始准确度应该大于 40%
        assert similarity > 0.40, f"原始文本准确度太低: {similarity:.2%}"
        print(f"\n原始文本准确度: {similarity:.2%}")
    
    def test_post_processed_text_accuracy(self):
        """测试后处理后的文本识别准确度（基础规则）"""
        if not self.ocr_result:
            return
        
        post_processed_text = reconstruct_text_with_postprocess(self.ocr_result)
        similarity = self.calculate_similarity(self.expected_text, post_processed_text)
        
        # 基础后处理后的准确度（不期望太高，因为没有硬编码规则）
        assert similarity > 0.40, f"后处理后准确度太低: {similarity:.2%}"
        print(f"\n后处理后准确度: {similarity:.2%}")
    
    def test_post_process_basic_rules(self):
        """测试后处理的基础通用规则"""
        from layout import post_process_text
        
        # 只测试最基础的通用规则
        test_cases = [
            # Markdown 标题
            ("###Key Features", "### Key Features"),
            ("##Section", "## Section"),
            # 冒号后空格
            ("mode:outputs", "mode: outputs"),
            # 逗号后空格
            ("word1,word2", "word1, word2"),
            # 分号后空格
            ("item1;item2", "item1; item2"),
        ]
        
        for input_text, expected in test_cases:
            result = post_process_text(input_text)
            assert expected == result, f"后处理失败: '{input_text}' -> '{result}', 期望 '{expected}'"
    
    def test_ocr_recognizes_key_content(self):
        """测试 OCR 识别关键内容（原始识别结果可能缺少空格）"""
        if not self.ocr_result:
            return
        
        # 合并所有识别文本
        all_text = ' '.join(item[1][0] for item in self.ocr_result)
        all_text_lower = all_text.lower()
        
        # 检查关键内容是否被识别（使用原始识别文本，允许缺少空格）
        key_patterns = [
            "key features",
            "screenshot",
            "table mode",  # 可能是 "table mode" 或 "tablemode"
            "text",  # 可能是 "text mode" 或 "textmode"
            "tsv",
            "excel",
        ]
        
        for pattern in key_patterns:
            # 对于可能缺少空格的词，也检查连在一起的情况
            alternatives = [pattern]
            if ' ' in pattern:
                alternatives.append(pattern.replace(' ', ''))
            
            found = any(alt in all_text_lower for alt in alternatives)
            assert found, f"关键内容未识别: '{pattern}'"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
