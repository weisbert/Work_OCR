# -*- coding: utf-8 -*-
"""
This module provides functionalities for layout reconstruction from OCR results.
It can reconstruct text into a structured table (TSV) or plain text with layout preservation.
"""

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


def reconstruct_table(ocr_result: OcrResult, row_height_ratio: float = 0.5) -> str:
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

    # 2. Column Identification
    all_x_centers = sorted([it['norm_bbox']['cx'] for it in items])
    
    col_boundaries = []
    if all_x_centers:
        col_boundaries.append(all_x_centers[0])
        for i in range(1, len(all_x_centers)):
            # A significant gap suggests a new column
            # Use a threshold based on average item width
            avg_w = sum(it['norm_bbox']['w'] for it in items) / len(items)
            if (all_x_centers[i] - all_x_centers[i-1]) > avg_w:
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
