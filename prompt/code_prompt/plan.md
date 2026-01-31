# 项目推进计划（Plan）

## 1. 需求对齐与输入准备
- 确认最终 UI 技术栈（Tkinter / PySide6 / Qt）。
- 明确截图库/全局热键依赖（是否接受第三方库）。
- 确认日志输出与进度展示样式（文本 + 进度条）。
  - 决策：UI 技术栈为 PySide6（Qt for Python）。
  - 决策：截图库使用 mss；全局热键使用 pywin32（RegisterHotKey），Windows-only 优先。
  - 决策：日志为可滚动 QPlainTextEdit 追加；进度为阶段式（例如 8 阶段）。
  - 可选：Auto-scroll 开关 + 最大行数限制。

## 2. 模块实现顺序（≤5 个 .py）
1. `ocr_engine.py`：先封装 PaddleOCR，确认识别输出格式稳定。
2. `layout.py`：实现表格/文本布局重建与自动模式检测。
3. `postprocess.py`：实现表格预处理管线与配置持久化。
4. `capture.py`：实现截图框选与热键注册。
5. `app.py`：组装 UI、打通完整流程。

## 3. 关键里程碑与验收点
- M1：OCR 能输出 bbox+text，表格模式 TSV 可粘贴到 Excel。
- M2：文本模式保留换行/缩进；自动模式检测可用。
- M3：预处理 Tab 全功能（阈值替换、单位统一、分离、计数法转换）。
- M4：截图、Copy、Clear、日志与进度全流程可用。

## 4. 测试与验证
- 使用 `test_pic/test_pic1_data.png` 进行表格识别。
- 输出与 `test_pic/test_pic1_data_table_anwser.txt` 进行逐格对比。
- 验证阈值替换（`5n` + `-4u`）、工程计数法转换（`12345` → `12.3E+03`）。

## 5. 风险与缓解
- CPU-only 性能：记录耗时并考虑图像缩放策略。
- 表格结构恢复偏差：允许用户在结果区手动修正。
- 字符混淆（u/n/m）：在后处理阶段加入纠错（可选）。

## 6. 交付物清单
- 5 个 `.py` 文件（代码拆分按需求）。
- `README.md`：安装、运行、快捷键与常见问题。
- 测试样例说明与验收对比记录。
