# -*- coding: utf-8 -*-
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, getcontext

# Set precision for Decimal calculations
getcontext().prec = 50

# Engineering prefixes and their corresponding power of 10
PREFIX_TO_POWER = {
    'f': -15, 'p': -12, 'n': -9, 'u': -6, 'm': -3,
    '': 0,
    'k': 3, 'M': 6, 'G': 9,
}
POWER_TO_PREFIX = {v: k for k, v in PREFIX_TO_POWER.items()}

@dataclass
class ParsedValue:
    """Represents a parsed value from a cell, with numeric and unit components."""
    original_str: str
    numeric_value: Decimal | None = None
    prefix: str | None = None
    unit: str = ""
    is_special: bool = False # Indicates special values like '-'

    def get_base_value(self) -> Decimal | None:
        """Returns the value in its base unit (power of 0)."""
        if self.numeric_value is None:
            return None
        power = PREFIX_TO_POWER.get(self.prefix, 0)
        return self.numeric_value * (Decimal(10) ** power)

    def format(self) -> str:
        """Formats the parsed value back into a string."""
        if self.is_special or self.numeric_value is None:
            return self.original_str
        return f"{self.numeric_value.to_eng_string()}{self.prefix or ''}{self.unit}"

@dataclass
class PostprocessSettings:
    """Holds all settings for the post-processing pipeline."""
    apply_threshold: bool = False
    threshold_value: str = "0"
    threshold_replace_with: str = "0"
    
    apply_unit_conversion: bool = False
    target_unit_prefix: str = "" # Empty means base unit
    
    apply_notation_conversion: bool = False
    notation_style: str = "engineering" # "scientific", "engineering", "prefix"
    
    split_value_unit: bool = False
    copy_strategy: str = "all" # "all", "value_only", "unit_only"


DEFAULT_CONFIG_PATH = "config.json"

def parse_cell(cell_str: str) -> ParsedValue:
    """
    Parses a string from a cell to identify its numeric value, prefix, and unit.
    Handles engineering prefixes and scientific notation.
    """
    cell_str = cell_str.strip()
    if cell_str == '-':
        return ParsedValue(original_str=cell_str, is_special=True)

    # Regex to capture value, optional prefix, and optional unit
    # Supports: 123, 12.3k, 1.2e-3, 5n, -4uV
    pattern = re.compile(
        r"^\s*(-?[\d\.]+)"              # 1: Numeric value (e.g., -12.3)
        r"\s*(e[+-]?\d+)?\s*"           # 2: Optional scientific notation (e.g., e-3)
        r"([f|p|n|u|m|k|M|G])?"         # 3: Optional engineering prefix
        r"([a-zA-Z]*)\s*$"              # 4: Optional unit (e.g., V, Hz)
    )
    match = pattern.match(cell_str)

    if not match:
        return ParsedValue(original_str=cell_str) # Parse failed

    num_part, sci_part, prefix, unit = match.groups()
    
    try:
        numeric_value = Decimal(f"{num_part}{sci_part or ''}")
        return ParsedValue(
            original_str=cell_str,
            numeric_value=numeric_value,
            prefix=prefix or '',
            unit=unit or ''
        )
    except Exception:
        return ParsedValue(original_str=cell_str) # Conversion to Decimal failed


def apply_threshold(value: ParsedValue, threshold_str: str, replace_with_str: str) -> ParsedValue:
    """
    If the value is below the threshold, replace it.
    Comparison is done on base values.
    """
    if value.is_special or value.numeric_value is None:
        return value

    threshold = parse_cell(threshold_str)
    if threshold.numeric_value is None:
        return value # Invalid threshold

    val_base = value.get_base_value()
    thr_base = threshold.get_base_value()

    if val_base is not None and thr_base is not None and val_base < thr_base:
        return parse_cell(replace_with_str)
    
    return value


def convert_unit(value: ParsedValue, target_prefix: str) -> ParsedValue:
    """
    Converts the value to a target engineering prefix.
    """
    if value.is_special or value.numeric_value is None or target_prefix not in PREFIX_TO_POWER:
        return value

    base_value = value.get_base_value()
    if base_value is None:
        return value

    target_power = PREFIX_TO_POWER[target_prefix]
    new_numeric_value = base_value / (Decimal(10) ** target_power)
    
    value.numeric_value = new_numeric_value
    value.prefix = target_prefix
    return value

def to_scientific(value: ParsedValue) -> str:
    """Converts a ParsedValue to a string in scientific notation."""
    if value.is_special or value.numeric_value is None:
        return value.original_str
    
    base_value = value.get_base_value()
    if base_value is None:
        return value.original_str
    
    return f"{base_value:e}{value.unit}"

def to_engineering(value: ParsedValue) -> str:
    """Converts a ParsedValue to a string in engineering notation (power is multiple of 3)."""
    if value.is_special or value.numeric_value is None:
        return value.original_str

    base_value = value.get_base_value()
    if base_value is None:
        return value.original_str
        
    if base_value == 0:
        return f"0{value.unit}"

    power = int(3 * (int(base_value.log10().quantize(1)) // 3))
    mantissa = base_value / (Decimal(10) ** power)
    return f"{mantissa.to_eng_string()}E{power:+03}{value.unit}"

def sci_to_prefix(value: ParsedValue) -> ParsedValue:
    """Converts a value (potentially from scientific notation) to use the best engineering prefix."""
    if value.is_special or value.numeric_value is None:
        return value
    
    base_value = value.get_base_value()
    if base_value is None:
        return value
    
    if base_value == 0:
        value.numeric_value = Decimal(0)
        value.prefix = ''
        return value

    power = int(base_value.log10())
    prefix_power = max(min(int(3 * round(power / 3)), 9), -15) # Clamp to G and f
    
    best_prefix = POWER_TO_PREFIX.get(prefix_power)
    if best_prefix is not None:
        return convert_unit(value, best_prefix)
    
    return value

def process_tsv(tsv_text: str, settings: PostprocessSettings) -> str:
    """
    Processes a whole TSV text block based on the provided settings.
    """
    lines = tsv_text.strip().split('\n')
    processed_lines = []

    for line in lines:
        cells = line.split('\t')
        processed_cells = []
        for cell in cells:
            # 1. Parse
            parsed = parse_cell(cell)

            # 2. Apply Threshold
            if settings.apply_threshold:
                parsed = apply_threshold(parsed, settings.threshold_value, settings.threshold_replace_with)

            # 3. Unit Conversion
            if settings.apply_unit_conversion and not parsed.is_special:
                 parsed = convert_unit(parsed, settings.target_unit_prefix)

            # --- Final Formatting ---
            final_str = parsed.format()

            if not parsed.is_special and parsed.numeric_value is not None:
                # 4. Notation Conversion (applied after other transforms)
                if settings.apply_notation_conversion:
                    if settings.notation_style == "scientific":
                        final_str = to_scientific(parsed)
                    elif settings.notation_style == "engineering":
                        final_str = to_engineering(parsed)
                    elif settings.notation_style == "prefix":
                        final_str = sci_to_prefix(parsed).format()
                
                # 5. Splitting Value and Unit
                if settings.split_value_unit:
                    value_str = f"{parsed.numeric_value.to_eng_string()}"
                    unit_str = f"{parsed.prefix or ''}{parsed.unit}"
                    final_str = f"{value_str}\t{unit_str}"
                
                # 6. Copy Strategy
                if settings.copy_strategy == "value_only":
                     final_str = f"{parsed.numeric_value.to_eng_string()}"
                elif settings.copy_strategy == "unit_only":
                     final_str = f"{parsed.prefix or ''}{parsed.unit}"

            processed_cells.append(final_str)
        processed_lines.append('\t'.join(processed_cells))

    return '\n'.join(processed_lines)

def load_config(path: str = DEFAULT_CONFIG_PATH) -> PostprocessSettings:
    """Loads settings from a JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return PostprocessSettings(**data)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        # Return default settings if file is missing, corrupt, or has wrong keys
        return PostprocessSettings()

def save_config(settings: PostprocessSettings, path: str = DEFAULT_CONFIG_PATH):
    """Saves settings to a JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(settings.__dict__, f, indent=4)

