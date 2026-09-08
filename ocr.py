import json
from pathlib import Path
from paddleocr import PaddleOCR


# ============================================================
# FILE PATHS
# ============================================================

IMAGE_PATH = "processed_images/processed_product.jpg"
OUTPUT_FILE = "ocr_output.json"


# ============================================================
# OCR SETUP
# ============================================================

ocr = PaddleOCR(
    lang="en",

    # Important for Windows + PaddlePaddle 3.x
    enable_mkldnn=False,

    # Disable unnecessary document processing
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)


# ============================================================
# RUN OCR
# ============================================================

def run_ocr():

    print("\n========================================")
    print("OCR PROCESSING")
    print("========================================")

    if not Path(IMAGE_PATH).exists():

        print(
            f"ERROR: Image not found: {IMAGE_PATH}"
        )

        return

    print(
        f"Input image:\n{IMAGE_PATH}"
    )

    # --------------------------------------------------------
    # Run PaddleOCR
    # --------------------------------------------------------

    results = ocr.predict(
        IMAGE_PATH
    )

    ocr_results = []

    # --------------------------------------------------------
    # Extract OCR results
    # --------------------------------------------------------

    for result in results:

        # Text
        texts = result.get(
            "rec_texts",
            []
        )

        # Confidence
        scores = result.get(
            "rec_scores",
            []
        )

        # Bounding boxes
        boxes = result.get(
            "rec_boxes",
            []
        )

        for i, text in enumerate(texts):

            text = str(text).strip()

            if not text:
                continue

            # Confidence
            if i < len(scores):

                try:
                    confidence = float(
                        scores[i]
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    confidence = 0.0

            else:

                confidence = 0.0

            # Bounding box
            if i < len(boxes):

                box = boxes[i]

                # Paddle may return numpy array
                if hasattr(
                    box,
                    "tolist"
                ):

                    box = box.tolist()

                else:

                    box = list(box)

            else:

                box = [
                    0,
                    0,
                    0,
                    0
                ]

            # ------------------------------------------------
            # Store OCR item
            # ------------------------------------------------

            ocr_results.append({

                "text": text,

                "confidence": round(
                    confidence,
                    4
                ),

                "box": box
            })

    # ========================================================
    # CREATE OUTPUT
    # ========================================================

    output = {

        "image": IMAGE_PATH,

        "ocr": ocr_results
    }

    # ========================================================
    # SAVE JSON
    # ========================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print("\n========================================")
    print("OCR COMPLETED")
    print("========================================")

    print(
        f"Detected OCR items: "
        f"{len(ocr_results)}"
    )

    print("\nDetected text:\n")

    for item in ocr_results:

        print(
            f"{item['text']} "
            f"| confidence="
            f"{item['confidence']:.4f} "
            f"| box="
            f"{item['box']}"
        )

    print("\n========================================")
    print("DONE")
    print("========================================")

    print(
        f"\nSaved: {OUTPUT_FILE}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    run_ocr()