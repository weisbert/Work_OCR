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

    def format(self, precision: int | None = None) -> str:
        """Formats the parsed value back into a string.
        Avoids scientific notation for regular numbers.
        """
        if self.is_special or self.numeric_value is None:
            return self.original_str
        
        # Format numeric value without scientific notation
        num_str = format_decimal(self.numeric_value, precision)
        return f"{num_str}{self.prefix or ''}{self.unit}"

@dataclass
class PostprocessSettings:
    """Holds all settings for the post-processing pipeline."""
    apply_threshold: bool = False
    threshold_value: str = "0"
    threshold_replace_with: str = "0"
    
    apply_unit_conversion: bool = False
    target_unit_prefix: str = "" # Empty means base unit
    
    apply_notation_conversion: bool = False
    notation_style: str = "engineering" # "scientific", "engineering"
    
    split_value_unit: bool = False
    copy_strategy: str = "all" # "all", "value_only", "unit_only"
    
    precision: int = 6  # Number of significant digits for display


def format_decimal(value: Decimal, precision: int | None = None) -> str:
    """Format a Decimal value without scientific notation.
    
    Args:
        value: The Decimal value to format
        precision: Number of significant digits (None means keep original precision)
    
    Returns:
        String representation without scientific notation
    """
    if value is None:
        return ""
    
    # Use 'f' format to avoid scientific notation
    # First, get the string representation in fixed-point format
    str_val = format(value, 'f')
    
    # If precision is specified, we need to round to significant digits
    if precision is not None and precision > 0:
        # Convert to float to easily handle significant digits
        float_val = float(value)
        if float_val != 0:
            # Calculate the order of magnitude
            import math
            order = math.floor(math.log10(abs(float_val)))
            # Calculate decimal places needed
            decimal_places = max(0, precision - order - 1)
            # Format with the calculated decimal places
            format_str = f"{{:.{decimal_places}f}}"
            result = format_str.format(float_val)
            # Remove trailing zeros and possible trailing decimal point
            if '.' in result:
                result = result.rstrip('0').rstrip('.')
            return result if result else "0"
    
    # Remove trailing zeros after decimal point, but keep significant digits
    if '.' in str_val:
        # Split into integer and fractional parts
        int_part, frac_part = str_val.split('.')
        # Remove trailing zeros from fractional part
        frac_part = frac_part.rstrip('0')
        if frac_part:
            return f"{int_part}.{frac_part}"
        else:
            return int_part
    return str_val


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

def to_scientific(value: ParsedValue, precision: int = 6) -> str:
    """Converts a ParsedValue to a string in scientific notation.
    Format: mantissa with specified significant digits + E + signed 2-digit exponent
    Example: 10u with precision=3 -> 1.00E-05
    """
    if value.is_special or value.numeric_value is None:
        return value.original_str
    
    base_value = value.get_base_value()
    if base_value is None:
        return value.original_str
    
    if base_value == 0:
        return f"0.{('0' * (precision-1))}E+00"
    
    # Format with specified significant digits
    float_val = float(base_value)
    import math
    order = math.floor(math.log10(abs(float_val)))
    decimal_places = max(0, precision - 1)
    format_str = f"{{:.{decimal_places}E}}"
    return format_str.format(float_val)

def to_engineering(value: ParsedValue, precision: int = 6) -> str:
    """Converts a ParsedValue to a string in engineering notation (power is multiple of 3).
    Format: mantissa with specified significant digits + E + signed 3-digit exponent
    Example: 10u with precision=4 -> 10.00E-06
    """
    if value.is_special or value.numeric_value is None:
        return value.original_str

    base_value = value.get_base_value()
    if base_value is None:
        return value.original_str
        
    if base_value == 0:
        decimal_places = max(0, precision - 1)
        return f"0.{('0' * decimal_places)}E+00"

    # Calculate engineering exponent (multiple of 3)
    import math
    float_val = float(base_value)
    log_val = math.log10(abs(float_val))
    power = int(3 * math.floor(log_val / 3))
    mantissa = float_val / (10 ** power)
    
    # Format mantissa with specified significant digits
    # Engineering mantissa range: [1, 1000), so integer part can be 1-3 digits
    # Calculate decimal places: precision - number_of_integer_digits
    if mantissa != 0:
        integer_digits = int(math.log10(abs(mantissa))) + 1
        decimal_places = max(0, precision - integer_digits)
    else:
        decimal_places = max(0, precision - 1)
    format_str = f"{{:.{decimal_places}f}}"
    return f"{format_str.format(mantissa)}E{power:+03}"

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
    When split_value_unit is True, all values are converted to the target unit
    and a unit column is appended at the end.
    """
    lines = tsv_text.strip().split('\n')
    processed_lines = []

    for line in lines:
        cells = line.split('\t')
        processed_cells = []
        parsed_cells = []  # Store parsed cells for split value/unit logic
        
        for cell in cells:
            # 1. Parse
            parsed = parse_cell(cell)

            # 2. Apply Threshold
            if settings.apply_threshold:
                parsed = apply_threshold(parsed, settings.threshold_value, settings.threshold_replace_with)

            # 3. Unit Conversion (always applied if target unit is set, for split mode)
            if settings.apply_unit_conversion and not parsed.is_special:
                 parsed = convert_unit(parsed, settings.target_unit_prefix)

            parsed_cells.append(parsed)

        # Determine the unit for this row (for split mode)
        row_unit = settings.target_unit_prefix if settings.apply_unit_conversion else ''
        
        # Format each cell
        for parsed in parsed_cells:
            final_str = parsed.format(settings.precision)

            if not parsed.is_special and parsed.numeric_value is not None:
                # 4. Notation Conversion (applied after other transforms)
                if settings.apply_notation_conversion:
                    if settings.notation_style == "scientific":
                        final_str = to_scientific(parsed, settings.precision)
                    elif settings.notation_style == "engineering":
                        final_str = to_engineering(parsed, settings.precision)
                
                # 5. Splitting Value and Unit - format as number only (no unit)
                if settings.split_value_unit:
                    if settings.apply_notation_conversion:
                        # Already formatted with notation, keep as is
                        pass
                    else:
                        # Regular number format - use plain string without scientific notation
                        final_str = format_decimal(parsed.numeric_value, settings.precision)

            processed_cells.append(final_str)
        
        # 6. Append unit column if split_value_unit is enabled
        if settings.split_value_unit:
            processed_cells.append(row_unit)
        
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

