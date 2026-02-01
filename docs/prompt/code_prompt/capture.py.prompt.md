# capture.py Prompt

你是资深 Windows 桌面工具开发者。请基于 `prompt/needs.txt` 生成 **`capture.py`** 的实现代码。只输出该文件的代码，不要输出其他文件，不要输出解释性文字。

## 目标与职责
- 提供截图框选能力（Snipaste-like 简化版）。
- 支持全局快捷键注册、冲突提示与禁用。
- 提供截图确认/取消的浮层按钮与 Enter/Esc 快捷键。
- 输出截图图像数据，并触发回调供上层处理。

## 约束
- Windows 11 + Python 3.11。
- CPU-only；不依赖 GPU。
- 代码注释必须为英文。
- 不做复杂图像编辑（马赛克/画笔/标注）。

## 关键交互
1. 进入截图模式 → 鼠标拖拽框选。
2. 框选完成后显示：√ 确认、× 取消。
3. Enter 确认；Esc 取消。
4. 确认后返回截图图像并触发回调。

## 接口要求（请在代码中清晰定义）
- `start_capture()`：进入截图模式。
- `register_hotkey(hotkey: str) -> bool`：注册全局快捷键，失败返回 False。
- 回调接口：例如 `on_capture(image, bbox)`。
- 允许外部传入 logger 记录关键阶段。

## 输出要求
- 仅输出 `capture.py` 代码。
- 不要硬编码上层 UI 细节，但需提供可集成的回调接口。