# Work OCR

一款基于 PaddleOCR (CPU-only) 的桌面 OCR 工具，专为 Windows 11 设计，专注于表格数据提取和文本识别。

![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%2011-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 功能特性

### 核心功能
- **截图 OCR** - 类似 Snipaste 的截图体验，支持框选区域
- **表格模式** - 自动识别表格结构，输出可直接粘贴到 Excel 的 TSV 格式
- **文本模式** - 保留原文换行和缩进
- **全局快捷键** - 支持自定义快捷键快速唤起截图（默认 `Ctrl+Alt+S`）

### 表格后处理功能
- **单位统一** - 支持工程单位前缀（f, p, n, u, m, k, M, G）自动换算
- **阈值替换** - 将小于阈值的数值替换为 `-` 或 `0`
- **数值/单位分离** - 将数值和单位分成两列输出
- **计数法转换** - 支持科学计数法和工程计数法
- **精度控制** - 可设置有效数字位数（1-15位）

## 系统要求

- **操作系统**: Windows 11
- **Python**: 3.11+
- **硬件**: CPU-only（无需 GPU）

## 安装步骤

### 1. 克隆仓库

```bash
git clone <repository-url>
cd Work_OCR
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

> **注意**: 首次运行 PaddleOCR 会自动下载模型文件，可能需要一些时间。

## 使用方法

### 启动应用

```bash
python app.py
```

### 基本操作

1. **截图识别**
   - 点击 "Screenshot" 按钮或按下全局快捷键（默认 `Ctrl+Alt+S`）
   - 拖拽鼠标框选需要识别的区域
   - 松开鼠标完成截图，自动开始 OCR 识别
   - 按 `ESC` 取消截图

2. **查看结果**
   - **OCR Result** 标签页 - 显示原始识别结果
   - **Post-processed** 标签页 - 显示表格后处理结果

3. **复制结果**
   - 点击 "Copy" 按钮复制当前标签页内容到剪贴板
   - 支持三种复制策略：全部 / 仅数值 / 仅单位

### 表格后处理设置

在 **Post-processed** 标签页中：

| 设置项 | 说明 |
|--------|------|
| **Enable Threshold Replacement** | 开启阈值替换功能 |
| Threshold | 阈值数值（如 `5n`） |
| Replace with | 替换为 `-` 或 `0` |
| **Enable Unit Unification** | 开启单位统一功能 |
| Target Unit | 目标单位前缀（f, p, n, u, m, k, M, G） |
| **Split Value and Unit** | 将数值和单位分成两列 |
| Notation | 计数法：None / Scientific / Engineering |
| Precision | 有效数字位数（1-15） |
| Copy Strategy | 复制策略：All / Values Only / Units Only |

### 全局快捷键设置

1. 在顶部工具栏的 "Hotkey" 输入框中输入快捷键组合
2. 点击 "Set Hotkey" 按钮注册
3. 成功后会显示 `(Global: Ctrl+Alt+S)`

**支持的快捷键格式**:
- `ctrl+alt+s`
- `f1`
- `ctrl+shift+a`
- `alt+f4`

留空并点击 "Set Hotkey" 可取消注册。

## 项目结构

```
Work_OCR/
├── app.py                  # 主应用程序入口
├── capture.py              # 截图功能模块
├── ocr_engine.py           # PaddleOCR 封装
├── layout.py               # 布局分析（表格/文本重建）
├── postprocess.py          # 表格后处理
├── hotkey_manager.py       # 全局热键管理
├── requirements.txt        # Python 依赖
├── config.json             # 用户配置文件（自动生成）
│
├── tests/                  # 单元测试
│   ├── test_app.py
│   ├── test_capture.py
│   ├── test_hotkey_manager.py
│   ├── test_layout.py
│   ├── test_ocr_engine.py
│   ├── test_ocr_accuracy.py
│   └── test_postprocess.py
│
├── test_pic/               # 测试图片
│   ├── test_pic1_data_table.png
│   ├── test_pic1_data_table_anwser.txt
│   ├── test_pic2_code.png
│   └── current_data.xlsx
│
└── prompt/                 # 需求文档
    ├── needs.txt           # 产品需求文档
    └── code_prompt/        # 代码提示文档
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_postprocess.py

# 运行带详细输出
pytest -v
```

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI 框架 | PySide6 |
| OCR 引擎 | PaddleOCR 3.4.0 + PaddlePaddle 3.2.0 (CPU) |
| 图像处理 | OpenCV, Pillow |
| 全局热键 | keyboard |
| 测试框架 | pytest, pytest-qt |

## 配置文件

应用会自动生成 `config.json` 保存用户设置：

```json
{
    "screenshot_hotkey": "ctrl+alt+s",
    "apply_threshold": false,
    "threshold_value": "5n",
    "threshold_replace_with": "-",
    "apply_unit_conversion": true,
    "target_unit_prefix": "u",
    "split_value_unit": true,
    "notation_style": "none",
    "precision": 6,
    "copy_strategy": "all"
}
```

## 注意事项

1. **首次运行**: PaddleOCR 需要下载模型文件，请保持网络连接
2. **CPU 性能**: 大尺寸图片 OCR 可能需要较长时间，建议在 log 面板查看进度
3. **全局热键冲突**: 如果注册失败，请尝试其他快捷键组合
4. **截图权限**: 确保应用有屏幕捕获权限

## 常见问题

**Q: OCR 识别速度慢怎么办？**  
A: 这是正常现象，CPU-only 模式下 PaddleOCR 处理大图需要时间。可以尝试缩小截图区域。

**Q: 表格识别不准确怎么办？**  
A: 表格结构恢复是启发式算法，复杂布局可能不准确。识别结果可手动编辑。

**Q: 全局快捷键无法注册？**  
A: 可能是快捷键已被其他软件占用，尝试更换其他组合如 `ctrl+f12` 或 `f1`。

## 许可证

MIT License

## 贡献指南

欢迎提交 Issue 和 Pull Request。

---

**Work OCR** - 让截图 OCR 更简单高效！
