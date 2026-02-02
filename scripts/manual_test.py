import argparse
import os
from pathlib import Path
import sys
# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from work_ocr.ocr_engine import OCREngine
from work_ocr.layout import reconstruct_table

def run_manual_test():
    """
    A simple script to manually run the OCR engine on a test image
    and see the formatted output.
    """
    parser = argparse.ArgumentParser(description="Run manual OCR test.")
    parser.add_argument(
        "--image-path",
        type=str,
        required=True,
        help="Path to the input image.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Enable fast mode for OCR.",
    )
    args = parser.parse_args()
    
    # 1. Define the input image path
    image_path = Path(__file__).parent.parent / args.image_path
    if not image_path.exists():
        print(f"Error: Test image not found at '{image_path}'")
        return

    print(f"Input image: {image_path}\n")

    # 2. Initialize the OCR Engine
    print("Initializing the OCR engine (this may take a moment)...")
    if args.fast:
        print("Fast mode enabled.")
        engine = OCREngine(lang="ch", use_angle_cls=False, cpu_threads=os.cpu_count())
    else:
        engine = OCREngine(lang="ch")
        
    try:
        init_time = engine.initialize()
        print(f"Engine initialized in {init_time:.2f} seconds.\n")
    except Exception as e:
        print(f"Error initializing engine: {e}")
        return

    # 3. Run recognition
    print("Running recognition on the image...")
    try:
        results = engine.recognize(str(image_path))
        print("Recognition complete.\n")
    except Exception as e:
        print(f"Error during recognition: {e}")
        return

    # 4. Print the formatted output
    print("=" * 25)
    print("   OCR Parsed Output")
    print("=" * 25)
    
    tsv_output = reconstruct_table(results)
    print(tsv_output)

if __name__ == "__main__":
    run_manual_test()


