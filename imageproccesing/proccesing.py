import cv2
import os
import numpy as np

# =========================
# CONFIGURATION
# =========================

INPUT_FOLDER = "test_images"
OUTPUT_FOLDER = "processed_images"

MAX_WIDTH = 1500


# =========================
# CREATE OUTPUT FOLDER
# =========================

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# =========================
# QUALITY CHECK
# =========================

def check_image_quality(image):
    """
    Checks blur and brightness of the image.
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Blur detection
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Brightness
    brightness = np.mean(gray)

    print(f"Blur score: {blur_score:.2f}")
    print(f"Brightness: {brightness:.2f}")

    if blur_score < 50:
        print("Warning: Image may be blurry.")

    if brightness < 40:
        print("Warning: Image may be too dark.")

    if brightness > 220:
        print("Warning: Image may be too bright.")


# =========================
# RESIZE IMAGE
# =========================

def resize_image(image):
    """
    Resize image if its width is greater than MAX_WIDTH.
    """

    height, width = image.shape[:2]

    if width > MAX_WIDTH:

        scale = MAX_WIDTH / width

        new_width = int(width * scale)
        new_height = int(height * scale)

        image = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA
        )

    return image


# =========================
# CROP WHITE BORDER
# =========================

def crop_white_border(image):
    """
    Removes unnecessary white border around the package.
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Threshold
    _, threshold = cv2.threshold(
        gray,
        245,
        255,
        cv2.THRESH_BINARY_INV
    )

    # Find contours
    contours, _ = cv2.findContours(
        threshold,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return image

    # Largest contour
    largest_contour = max(
        contours,
        key=cv2.contourArea
    )

    x, y, w, h = cv2.boundingRect(largest_contour)

    # Avoid extremely small crops
    if w < 100 or h < 100:
        return image

    cropped = image[y:y + h, x:x + w]

    return cropped


# =========================
# ROTATE IMAGE
# =========================

def rotate_image(image):
    """
    Currently no rotation is applied.
    """

    return image


# =========================
# GRAYSCALE
# =========================

def convert_to_grayscale(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return gray


# =========================
# DENOISING
# =========================

def denoise_image(gray):

    denoised = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    return denoised


# =========================
# CLAHE ENHANCEMENT
# =========================

def enhance_contrast(gray):

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(gray)

    return enhanced


# =========================
# ADAPTIVE THRESHOLD
# =========================

def create_threshold(enhanced):

    threshold = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    return threshold


# =========================
# PROCESS SINGLE IMAGE
# =========================

def process_image(image_path):

    print("\n====================================")
    print("Processing:", image_path)
    print("====================================")

    # -------------------------
    # Read image
    # -------------------------

    image = cv2.imread(image_path)

    if image is None:

        print("ERROR: Could not read image.")

        return None

    print("Original image loaded.")

    # -------------------------
    # Quality check
    # -------------------------

    check_image_quality(image)

    # -------------------------
    # Resize
    # -------------------------

    resized = resize_image(image)

    # -------------------------
    # Crop white border
    # -------------------------

    cropped = crop_white_border(resized)

    # -------------------------
    # Rotation
    # -------------------------

    rotated = rotate_image(cropped)

    # -------------------------
    # Grayscale
    # -------------------------

    grayscale = convert_to_grayscale(rotated)

    # -------------------------
    # Denoising
    # -------------------------

    denoised = denoise_image(grayscale)

    # -------------------------
    # Contrast enhancement
    # -------------------------

    enhanced = enhance_contrast(denoised)

    # -------------------------
    # Threshold
    # -------------------------

    threshold = create_threshold(enhanced)

    # -------------------------
    # Get filename
    # -------------------------

    filename = os.path.basename(image_path)

    name, extension = os.path.splitext(filename)

    # -------------------------
    # Save intermediate images
    # -------------------------

    cv2.imwrite(
        os.path.join(
            OUTPUT_FOLDER,
            f"{name}_original.jpg"
        ),
        rotated
    )

    cv2.imwrite(
        os.path.join(
            OUTPUT_FOLDER,
            f"{name}_grayscale.jpg"
        ),
        grayscale
    )

    cv2.imwrite(
        os.path.join(
            OUTPUT_FOLDER,
            f"{name}_enhanced.jpg"
        ),
        enhanced
    )

    cv2.imwrite(
        os.path.join(
            OUTPUT_FOLDER,
            f"{name}_threshold.jpg"
        ),
        threshold
    )

    # -------------------------
    # FINAL OCR IMAGE
    # -------------------------
    #
    # We use ENHANCED image for OCR.
    #
    # IMPORTANT:
    # Do NOT use cv2.imshow(), cv2.waitKey()
    # or cv2.destroyAllWindows() here.
    #
    # Streamlit runs in a web browser and
    # these OpenCV GUI commands can freeze
    # the application.
    # -------------------------

    final_output_path = os.path.join(
        OUTPUT_FOLDER,
        f"processed_{name}.jpg"
    )

    cv2.imwrite(
        final_output_path,
        enhanced
    )

    print("\nProcessing completed successfully.")
    print("Final OCR image:")
    print(final_output_path)

    return final_output_path


# =========================
# PROCESS ALL IMAGES
# =========================

def process_all_images():

    print("\n====================================")
    print("LEGAL METROLOGY IMAGE PROCESSING")
    print("====================================")

    if not os.path.exists(INPUT_FOLDER):

        print(
            f"ERROR: Input folder '{INPUT_FOLDER}' "
            "does not exist."
        )

        return

    # Get image files
    image_files = []

    for filename in os.listdir(INPUT_FOLDER):

        if filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):

            image_files.append(filename)

    if len(image_files) == 0:

        print(
            f"No images found in '{INPUT_FOLDER}'."
        )

        return

    print(
        f"\nFound {len(image_files)} image(s)."
    )

    # Process each image
    for filename in image_files:

        image_path = os.path.join(
            INPUT_FOLDER,
            filename
        )

        process_image(image_path)

    print("\n====================================")
    print("ALL IMAGES PROCESSED")
    print("====================================")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    process_all_images()