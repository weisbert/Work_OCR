# ocr_engine.py Prompt

你是 OCR 模块开发工程师。请基于 `prompt/needs.txt` 生成 **`ocr_engine.py`** 的实现代码。只输出该文件的代码，不要输出其他文件，不要输出解释性文字。

## 目标与职责
- 封装 PaddleOCR（CPU）。
- 提供模型初始化与复用，避免重复加载。
- 提供统一识别接口：输入图像，输出检测框与识别文本。

## 约束
- Windows 11 + Python 3.11。
- 依赖：`paddlepaddle==3.2.0`（CPU），`paddleocr`。
- CPU-only；禁止依赖 GPU/CUDA。
- 代码注释必须为英文。

## 接口要求（请在代码中清晰定义）
- `class OCREngine` 或函数式 API 均可，但需：
  - `initialize()`：加载模型并记录耗时。
  - `recognize(image) -> list`：返回 `[(bbox, text, score), ...]`。
- 输出需兼容 `layout.py` 的行列聚类逻辑（bbox 为四点或矩形）。
- 支持最小日志输出（可注入 logger）。

## 性能与稳定性
- 初始化只做一次，后续复用。
- 对异常进行捕获并向上抛出明确错误。

## 输出要求
- 仅输出 `ocr_engine.py` 代码。