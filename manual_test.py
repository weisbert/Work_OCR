# manual_test.py
from pathlib import Path
from pprint import pprint
from ocr_engine import OCREngine

def run_manual_test():
    """
    A simple script to manually run the OCR engine on a test image
    and see the formatted output.
    """
    # 1. Define the input image path
    image_path = Path("test_pic") / "test_pic1_data_table.png"
    if not image_path.exists():
        print(f"Error: Test image not found at '{image_path}'")
        return

    print(f"Input image: {image_path}\n")

    # 2. Initialize the OCR Engine
    print("Initializing the OCR engine (this may take a moment)...")
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
    print(f"Found {len(results)} items.\n")

    # Using pprint for better readability of the list of tuples
    pprint(results)


if __name__ == "__main__":
    run_manual_test()
