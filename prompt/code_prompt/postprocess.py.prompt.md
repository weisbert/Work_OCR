# postprocess.py Prompt

你是数据处理与配置持久化工程师。请基于 `prompt/needs.txt` 生成 **`postprocess.py`** 的实现代码。只输出该文件的代码，不要输出其他文件，不要输出解释性文字。

## 目标与职责
- 实现“表格预处理 Tab”所需的处理管线。
- 包含阈值替换、单位统一、数值/单位分离、工程/科学计数法转换。
- 负责配置持久化（`config.json`）的读写与默认值。

## 约束
- Python 3.11。
- 代码注释必须为英文。
- 不引入重型依赖（标准库优先）。

## 管线顺序（必须固定）
1. 解析单元格（识别数值 + 工程前缀 / 科学计数法）。
2. 阈值替换（不取绝对值）。
3. 单位统一（目标前缀 f~G）。
4. 数值/单位分离（可选）。
5. 计数法转换（可选）。
6. 复制策略输出（全量/只数值/只单位）。

## 关键规则摘要
- 支持工程前缀：f p n u m (空) k M G（大小写输入不敏感，输出规范化）。
- 阈值替换：先换算到阈值单位，再比较数值本身。
- 特殊值 `-`：保持 `-`；不可解析需 log “parse failed”。
- 科学计数法 ↔ 工程单位 需按需求文档示例实现。

## 接口要求（请在代码中清晰定义）
- `parse_cell(cell_str) -> ParsedValue | None`。
- `apply_threshold(value, threshold, replace_with)`。
- `convert_unit(value, target_prefix)`。
- `split_value_unit(value) -> (value_str, unit_str)`。
- `to_scientific(value)` / `to_engineering(value)` / `sci_to_prefix(value)`。
- `process_tsv(tsv_text, settings) -> ProcessedResult`。
- `load_config(path)` / `save_config(path, settings)`。

## 输出要求
- 仅输出 `postprocess.py` 代码。