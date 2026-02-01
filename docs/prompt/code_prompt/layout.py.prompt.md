# layout.py Prompt

你是 OCR 版面重建算法工程师。请基于 `prompt/needs.txt` 生成 **`layout.py`** 的实现代码。只输出该文件的代码，不要输出其他文件，不要输出解释性文字。

## 目标与职责
- 将 OCR 检测结果重建为：
  - 表格模式：TSV（\t 列分隔，\n 行分隔）。
  - 文本模式：保留换行/缩进的纯文本。
- 提供自动检测启发式（表格 vs 文本）。

## 约束
- Python 3.11。
- 代码注释必须为英文。

## 核心算法（MVP）
### 表格模式
- 行聚类：按 bbox 中心 y 聚类，阈值与平均字符高度相关（可配置）。
- 列聚类：按 bbox 中心 x 聚类，使用“相邻 x 间距阈值”或 1D 聚类。
- 输出：按列索引填入，缺失列补空字符串。

### 文本模式
- 按 y 聚类成行；行内按 x 排序拼接。
- 用空格估计间隔（基于相邻 bbox 的 x gap 映射到空格数）。

## 接口要求（请在代码中清晰定义）
- `detect_mode(ocr_items) -> str`：返回 `"table"` 或 `"text"`。
- `reconstruct_table(ocr_items) -> str`：返回 TSV。
- `reconstruct_text(ocr_items) -> str`：返回保留布局的文本。
- `normalize_bbox(bbox)`：统一 bbox 表示，便于聚类。

## 输入/输出约定
- `ocr_items` 格式兼容 `ocr_engine.py` 输出：`(bbox, text, score)`。
- bbox 可为四点或矩形；需在本模块统一成中心点与宽高。

## 输出要求
- 仅输出 `layout.py` 代码。