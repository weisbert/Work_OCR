# -*- coding: utf-8 -*-
"""
This module provides functionalities for layout reconstruction from OCR results.
It can reconstruct text into a structured table (TSV) or plain text with layout preservation.
"""

import re
from typing import List, Tuple, Dict, Any, Union

# Define a type for a single OCR item, which includes the bounding box, text, and score.
# Bbox can be List[List[int]] (four points) or List[int] (x1, y1, x2, y2).
OcrItem = Tuple[Union[List[List[int]], List[int]], Tuple[str, float]]
OcrResult = List[OcrItem]

def normalize_bbox(bbox: Union[List[List[int]], List[int]]) -> Dict[str, float]:
    """
    Normalizes a bounding box into a dictionary with center coordinates, width, and height.
    This handles both 4-point polygons and 2-point rectangle formats.

    Args:
        bbox: The bounding box, either as [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] or [x1,y1,x2,y2].

    Returns:
        A dictionary with keys 'cx', 'cy', 'w', 'h'.
    """
    if isinstance(bbox[0], list): # Polygon format [[x1,y1],...]
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        x1, y1 = min(x_coords), min(y_coords)
        x2, y2 = max(x_coords), max(y_coords)
    else: # Rectangle format [x1,y1,x2,y2]
        x1, y1, x2, y2 = bbox

    width = x2 - x1
    height = y2 - y1
    return {
        'cx': x1 + width / 2,
        'cy': y1 + height / 2,
        'w': width,
        'h': height,
        'x1': x1,
        'y1': y1,
        'x2': x2,
        'y2': y2,
    }

def detect_mode(ocr_result: OcrResult, col_threshold_ratio: float = 0.7) -> str:
    """
    Detects if the layout is more likely a table or plain text.
    Heuristic: If a significant number of items are vertically aligned, it's a table.

    Args:
        ocr_result: The list of OCR items.
        col_threshold_ratio: Ratio of average character width to determine column alignment.

    Returns:
        "table" or "text".
    """
    if not ocr_result or len(ocr_result) < 3:
        return "text"

    items = [{'text': item[1][0], 'norm_bbox': normalize_bbox(item[0])} for item in ocr_result]
    
    avg_char_w = sum(it['norm_bbox']['w'] / len(it['text']) for it in items if it['text']) / len(items)
    col_threshold = avg_char_w * col_threshold_ratio

    # Count how many items are part of a vertical alignment
    aligned_indices = set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if abs(items[i]['norm_bbox']['cx'] - items[j]['norm_bbox']['cx']) < col_threshold:
                aligned_indices.add(i)
                aligned_indices.add(j)

    # If half or more of the items seem to be part of a column, assume table.
    # The threshold len(items) / 2 is a heuristic and might need tuning.
    if len(aligned_indices) >= len(items) / 2 and len(items) > 2:
        return "table"
    
    return "text"


def reconstruct_table(ocr_result: OcrResult, row_height_ratio: float = 0.5, col_gap_threshold_ratio: float = 1.0, horizontal_merge_threshold_ratio: float = 0.5) -> str:
    """
    Reconstructs OCR results into a TSV (Tab-Separated Values) string.
    
    Args:
        ocr_result: The list of OCR items from the OCR engine.
        row_height_ratio: Multiplier for average height to determine row clustering tolerance.

    Returns:
        A string formatted as TSV.
    """
    if not ocr_result:
        return ""

    items = [{'text': item[1][0], 'norm_bbox': normalize_bbox(item[0])} for item in ocr_result]
    
    if not items:
        return ""

    # Calculate average character width for general use
    total_text_len = sum(len(it['text']) for it in items)
    total_width = sum(it['norm_bbox']['w'] for it in items)
    avg_char_w = total_width / total_text_len if total_text_len > 0 else 10 # Default if no text

    # 1. Row Clustering
    avg_h = sum(it['norm_bbox']['h'] for it in items) / len(items)
    row_y_tolerance = avg_h * row_height_ratio
    
    items.sort(key=lambda x: x['norm_bbox']['cy'])
    
    rows = []
    if items:
        current_row = [items[0]]
        for item in items[1:]:
            # If item's vertical center is close to the current row's average, add it
            avg_row_y = sum(i['norm_bbox']['cy'] for i in current_row) / len(current_row)
            if abs(item['norm_bbox']['cy'] - avg_row_y) < row_y_tolerance:
                current_row.append(item)
            else:
                rows.append(sorted(current_row, key=lambda x: x['norm_bbox']['cx']))
                current_row = [item]
        rows.append(sorted(current_row, key=lambda x: x['norm_bbox']['cx']))

    # 1.5 Horizontal Merging within Rows
    merged_rows = []
    for row in rows:
        if not row:
            merged_rows.append([])
            continue

        current_merged_row = [row[0]]
        for i in range(1, len(row)):
            prev_item = current_merged_row[-1]
            current_item = row[i]

            gap = current_item['norm_bbox']['x1'] - prev_item['norm_bbox']['x2']

            if gap < (avg_char_w * horizontal_merge_threshold_ratio) and gap > - (avg_char_w * horizontal_merge_threshold_ratio): # Allow for slight overlaps or very small gaps
                # Merge current_item into prev_item
                prev_item['text'] += " " + current_item['text']
                # Update bbox to encompass both
                prev_item['norm_bbox']['x2'] = max(prev_item['norm_bbox']['x2'], current_item['norm_bbox']['x2'])
                prev_item['norm_bbox']['w'] = prev_item['norm_bbox']['x2'] - prev_item['norm_bbox']['x1']
                # Recalculate center
                prev_item['norm_bbox']['cx'] = prev_item['norm_bbox']['x1'] + prev_item['norm_bbox']['w'] / 2
            else:
                current_merged_row.append(current_item)
        merged_rows.append(current_merged_row)
    rows = merged_rows

    # 2. Column Identification
    all_x_centers = sorted([it['norm_bbox']['cx'] for row in rows for it in row])
    
    col_boundaries = []
    if all_x_centers:
        col_boundaries.append(all_x_centers[0])
        for i in range(1, len(all_x_centers)):
            # A significant gap suggests a new column
            # Use a threshold based on average character width and col_gap_threshold_ratio
            if (all_x_centers[i] - all_x_centers[i-1]) > (avg_char_w * col_gap_threshold_ratio):
                 col_boundaries.append(all_x_centers[i])

    # Deduplicate column boundaries
    unique_cols = []
    if col_boundaries:
        unique_cols.append(col_boundaries[0])
        for x in col_boundaries[1:]:
            # Check if this new boundary is too close to the last one
            is_new_col = True
            for uc in unique_cols:
                if abs(x - uc) < avg_h: # Use avg_h as it's a stable measure
                   is_new_col = False
                   break
            if is_new_col:
                unique_cols.append(x)
    
    col_boundaries = sorted(unique_cols)

    # 3. Grid Construction & Cell Placement
    grid = [["" for _ in col_boundaries] for _ in rows]
    
    for i, row in enumerate(rows):
        for item in row:
            # Find which column this item belongs to
            col_idx = -1
            min_dist = float('inf')
            for j, col_x in enumerate(col_boundaries):
                dist = abs(item['norm_bbox']['cx'] - col_x)
                if dist < min_dist:
                    min_dist = dist
                    col_idx = j
            
            if col_idx != -1:
                # Append text to the cell, separated by space if multiple items fall in one cell
                if grid[i][col_idx]:
                    grid[i][col_idx] += " " + item['text']
                else:
                    grid[i][col_idx] = item['text']

    # 4. TSV Generation
    return "\n".join("\t".join(row) for row in grid)


def reconstruct_text(ocr_result: OcrResult, space_width_ratio: float = 0.5) -> str:
    """
    Reconstructs OCR results into a plain text string, preserving layout.
    
    Args:
        ocr_result: The list of OCR items.
        space_width_ratio: Ratio of average char width to determine number of spaces.

    Returns:
        A string with layout preserved.
    """
    if not ocr_result:
        return ""

    items = [{'text': item[1][0], 'norm_bbox': normalize_bbox(item[0])} for item in ocr_result]

    # Calculate average character width for space estimation
    total_text_len = sum(len(it['text']) for it in items)
    total_width = sum(it['norm_bbox']['w'] for it in items)
    avg_char_w = total_width / total_text_len if total_text_len > 0 else 10 # Default if no text

    # Group items by row
    items.sort(key=lambda x: x['norm_bbox']['y1'])
    
    rows = []
    if items:
        current_row = [items[0]]
        avg_h = sum(it['norm_bbox']['h'] for it in items) / len(items)
        row_y_tolerance = avg_h * 0.5

        for item in items[1:]:
            avg_row_y1 = sum(i['norm_bbox']['y1'] for i in current_row) / len(current_row)
            if abs(item['norm_bbox']['y1'] - avg_row_y1) < row_y_tolerance:
                current_row.append(item)
            else:
                rows.append(sorted(current_row, key=lambda x: x['norm_bbox']['x1']))
                current_row = [item]
        rows.append(sorted(current_row, key=lambda x: x['norm_bbox']['x1']))

    # Reconstruct lines with spacing
    output_lines = []
    for row in rows:
        line_str = ""
        if not row:
            continue
        
        # Add indentation for the first element
        # A simple heuristic based on the first element's x position
        # You may want a more robust indentation logic
        # leading_spaces = int(row[0]['norm_bbox']['x1'] / avg_char_w)
        # line_str += " " * leading_spaces
        line_str += row[0]['text']

        for i in range(1, len(row)):
            prev_item = row[i-1]
            current_item = row[i]
            
            gap = current_item['norm_bbox']['x1'] - prev_item['norm_bbox']['x2']
            if gap > 0:
                num_spaces = max(1, int(gap / (avg_char_w * space_width_ratio)))
                line_str += " " * num_spaces
            
            line_str += current_item['text']
        output_lines.append(line_str)

    return "\n".join(output_lines)


def post_process_text(text: str) -> str:
    """
    对识别结果进行基础后处理，修复通用的 OCR 识别问题。
    
    仅处理最通用的文本模式：
    1. Markdown 标题和内容之间缺少空格
    2. 标点后缺少空格（冒号、逗号、分号）
    
    Args:
        text: 原始识别文本
        
    Returns:
        后处理后的文本
    """
    # 1. Markdown 标题后加空格：###Key -> ### Key
    text = re.sub(r'(#{1,6})([^\s#])', r'\1 \2', text)
    
    # 2. 冒号后加空格（非 URL 场景）：mode:outputs -> mode: outputs
    text = re.sub(r'(:)([^\s/])', r'\1 \2', text)
    
    # 3. 逗号后加空格：word1,word2 -> word1, word2
    text = re.sub(r',([^\s])', r', \1', text)
    
    # 4. 分号后加空格
    text = re.sub(r';([^\s])', r'; \1', text)
    
    return text


def _add_list_markers_by_indent(ocr_result: OcrResult, text: str) -> str:
    """
    基于缩进级别自动添加列表标记
    
    简单规则：如果某行相对于最左行有明显缩进（超过 2 个字符宽度），
    且该行没有现有标记，则添加 "- "
    """
    if not ocr_result or len(ocr_result) < 2:
        return text
    
    items = [{'text': item[1][0], 'norm_bbox': normalize_bbox(item[0])} 
             for item in ocr_result]
    
    min_x1 = min(it['norm_bbox']['x1'] for it in items)
    items_with_text = [it for it in items if it['text']]
    avg_char_w = sum(it['norm_bbox']['w'] / len(it['text']) for it in items_with_text) / len(items_with_text) if items_with_text else 10
    indent_threshold = avg_char_w * 2
    
    lines = text.split('\n')
    processed_lines = []
    first_content_found = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            processed_lines.append(line)
            continue
        
        # 跳过标题和已有标记的行
        if stripped.startswith('#') or re.match(r'^[-*+\d]', stripped):
            processed_lines.append(line)
            first_content_found = True
            continue
        
        # 查找对应 OCR 项检查缩进
        matching_item = next((it for it in items if stripped in it['text']), None)
        
        if matching_item and first_content_found:
            if matching_item['norm_bbox']['x1'] > min_x1 + indent_threshold:
                processed_lines.append('- ' + line)
                continue
        
        processed_lines.append(line)
        first_content_found = True
    
    return '\n'.join(processed_lines)


def reconstruct_text_with_postprocess(ocr_result: OcrResult, space_width_ratio: float = 0.5) -> str:
    """
    重构文本并应用后处理，提高识别准确度。
    
    流程：
    1. 基础文本重构
    2. 通用空格修复
    3. 基于缩进添加列表标记
    
    Args:
        ocr_result: The list of OCR items.
        space_width_ratio: Ratio of average char width to determine number of spaces.
        
    Returns:
        A string with layout preserved and common OCR errors fixed.
    """
    raw_text = reconstruct_text(ocr_result, space_width_ratio)
    fixed_text = post_process_text(raw_text)
    return _add_list_markers_by_indent(ocr_result, fixed_text)
