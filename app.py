import streamlit as st
import subprocess
import sys
import json
import shutil
from pathlib import Path
from PIL import Image


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Legal Metrology Compliance Checker",
    page_icon="⚖️",
    layout="wide"
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TEST_IMAGES_DIR = BASE_DIR / "test_images"
PROCESSED_DIR = BASE_DIR / "processed_images"

OCR_FILE = BASE_DIR / "ocr_output.json"
EXTRACTED_FILE = BASE_DIR / "extracted_product.json"
REPORT_FILE = BASE_DIR / "compliance_report.json"

PROCESSING_SCRIPT = BASE_DIR / "imageproccesing" / "proccesing.py"
OCR_SCRIPT = BASE_DIR / "ocr.py"
EXTRACTION_SCRIPT = BASE_DIR / "compliance_rules" / "extraction.py"
RULES_SCRIPT = BASE_DIR / "compliance_rules" / "rules.py"


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 38px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 17px;
        color: #666;
        margin-bottom: 25px;
    }

    .result-box {
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin: 15px 0;
        border: 1px solid #ddd;
    }

    .result-title {
        font-size: 30px;
        font-weight: 700;
    }

    .section-title {
        font-size: 23px;
        font-weight: 650;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    .small-text {
        font-size: 14px;
        color: #666;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">⚖️ Automated Legal Metrology Compliance Checker</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'AI-assisted inspection support for packaged commodity declarations'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🔎 Inspection Pipeline")

    st.write("1. 📤 Upload package image")
    st.write("2. 🖼️ Image preprocessing")
    st.write("3. 🔤 OCR text extraction")
    st.write("4. 📋 Declaration extraction")
    st.write("5. ⚖️ Rule-based compliance check")
    st.write("6. 📊 Compliance report")

    st.divider()

    st.caption(
        "This system provides inspection support based on "
        "configured Legal Metrology rules. It does not replace "
        "official inspection or legal determination."
    )


# ============================================================
# UPLOAD
# ============================================================

st.markdown(
    '<div class="section-title">📤 Upload Package Image</div>',
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader(
    "Upload the front/back/side image of a packaged commodity",
    type=["jpg", "jpeg", "png"],
    help="Use a clear image containing the package declarations."
)


# ============================================================
# DISPLAY UPLOADED IMAGE
# ============================================================

if uploaded_file is not None:

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("📷 Uploaded Image")

        st.image(
            uploaded_file,
            use_container_width=True
        )

    with col2:

        st.subheader("📄 File Information")

        st.write(
            "**File name:**",
            uploaded_file.name
        )

        st.write(
            "**File type:**",
            uploaded_file.type
        )

        st.write(
            "**File size:**",
            f"{uploaded_file.size / 1024:.1f} KB"
        )


# ============================================================
# CHECK BUTTON
# ============================================================

if uploaded_file is not None:

    st.divider()

    check_button = st.button(
        "🔍 Check Compliance",
        type="primary",
        use_container_width=True
    )

    if check_button:

        try:

            # ------------------------------------------------
            # CREATE REQUIRED FOLDERS
            # ------------------------------------------------

            TEST_IMAGES_DIR.mkdir(
                exist_ok=True
            )

            PROCESSED_DIR.mkdir(
                exist_ok=True
            )


            # ------------------------------------------------
            # REMOVE OLD TEST IMAGE
            # ------------------------------------------------

            for old_file in TEST_IMAGES_DIR.iterdir():

                if old_file.is_file():

                    try:
                        old_file.unlink()
                    except Exception:
                        pass


            # ------------------------------------------------
            # REMOVE OLD PROCESSED IMAGES
            # ------------------------------------------------

            for old_file in PROCESSED_DIR.iterdir():

                if old_file.is_file():

                    try:
                        old_file.unlink()
                    except Exception:
                        pass


            # ------------------------------------------------
            # SAVE UPLOADED IMAGE
            # ------------------------------------------------

            extension = Path(
                uploaded_file.name
            ).suffix.lower()

            if extension not in [
                ".jpg",
                ".jpeg",
                ".png"
            ]:

                extension = ".jpg"

            input_path = (
                TEST_IMAGES_DIR /
                f"uploaded_package{extension}"
            )

            with open(
                input_path,
                "wb"
            ) as file:

                file.write(
                    uploaded_file.getbuffer()
                )


            # =================================================
            # STEP 1 — IMAGE PROCESSING
            # =================================================

            st.divider()

            st.subheader(
                "🖼️ Step 1 — Image Preprocessing"
            )

            processing_progress = st.empty()

            processing_progress.info(
                "Processing package image..."
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(PROCESSING_SCRIPT)
                ],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:

                st.error(
                    "Image preprocessing failed."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(
                        result.stderr
                    )

                st.stop()

            processing_progress.success(
                "✓ Image preprocessing completed"
            )


            # ------------------------------------------------
            # FIND PROCESSED IMAGE
            # ------------------------------------------------

            processed_image_path = (
                PROCESSED_DIR /
                "processed_uploaded_package.jpg"
            )

            if not processed_image_path.exists():

                st.error(
                    "Processed image was not generated."
                )

                st.stop()


            # =================================================
            # STEP 2 — OCR
            # =================================================

            st.subheader(
                "🔤 Step 2 — OCR Text Extraction"
            )

            with st.spinner(
                "Running PaddleOCR..."
            ):

                result = subprocess.run(
                    [
                        sys.executable,
                        str(OCR_SCRIPT)
                    ],
                    cwd=str(BASE_DIR),
                    capture_output=True,
                    text=True
                )

            if result.returncode != 0:

                st.error(
                    "OCR processing failed."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(
                        result.stderr
                    )

                st.stop()

            st.success(
                "✓ OCR completed successfully"
            )


            # =================================================
            # STEP 3 — FIELD EXTRACTION
            # =================================================

            st.subheader(
                "📋 Step 3 — Declaration Extraction"
            )

            with st.spinner(
                "Extracting package declarations..."
            ):

                result = subprocess.run(
                    [
                        sys.executable,
                        str(EXTRACTION_SCRIPT)
                    ],
                    cwd=str(BASE_DIR),
                    capture_output=True,
                    text=True
                )

            if result.returncode != 0:

                st.error(
                    "Declaration extraction failed."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(
                        result.stderr
                    )

                st.stop()

            st.success(
                "✓ Declaration extraction completed"
            )


            # =================================================
            # STEP 4 — COMPLIANCE CHECK
            # =================================================

            st.subheader(
                "⚖️ Step 4 — Legal Metrology Compliance Check"
            )

            with st.spinner(
                "Applying configured legal rules..."
            ):

                result = subprocess.run(
                    [
                        sys.executable,
                        str(RULES_SCRIPT)
                    ],
                    cwd=str(BASE_DIR),
                    capture_output=True,
                    text=True
                )

            if result.returncode != 0:

                st.error(
                    "Compliance checking failed."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(
                        result.stderr
                    )

                st.stop()

            st.success(
                "✓ Compliance check completed"
            )


            # =================================================
            # LOAD RESULTS
            # =================================================

            if not EXTRACTED_FILE.exists():

                st.error(
                    "extracted_product.json was not generated."
                )

                st.stop()

            if not REPORT_FILE.exists():

                st.error(
                    "compliance_report.json was not generated."
                )

                st.stop()


            with open(
                EXTRACTED_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                extracted_data = json.load(file)


            with open(
                REPORT_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                report = json.load(file)


            # =================================================
            # OVERALL RESULT
            # =================================================

            st.divider()

            st.subheader(
                "🎯 Compliance Result"
            )

            overall_status = report.get(
                "overall_status",
                "UNKNOWN"
            )


            if overall_status == "COMPLIANT":

                st.success(
                    "✅ COMPLIANT"
                )

                st.markdown(
                    """
                    <div class="result-box">
                        <div class="result-title">
                            ✅ COMPLIANT
                        </div>
                        <p>
                            All configured checks passed based on
                            the information extracted from the image.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


            elif overall_status == "NON-COMPLIANT":

                st.error(
                    "❌ NON-COMPLIANT"
                )

                st.markdown(
                    """
                    <div class="result-box">
                        <div class="result-title">
                            ❌ NON-COMPLIANT
                        </div>
                        <p>
                            One or more configured compliance checks
                            failed.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


            else:

                st.warning(
                    "⚠️ NEEDS REVIEW"
                )

                st.markdown(
                    """
                    <div class="result-box">
                        <div class="result-title">
                            ⚠️ NEEDS REVIEW
                        </div>
                        <p>
                            Some declarations could not be confidently
                            detected. Manual verification is required.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


            # =================================================
            # SUMMARY
            # =================================================

            summary = report.get(
                "summary",
                {}
            )

            st.subheader(
                "📊 Inspection Summary"
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "Total Checks",
                    summary.get(
                        "total_checks",
                        0
                    )
                )

            with c2:
                st.metric(
                    "Passed",
                    summary.get(
                        "passed",
                        0
                    )
                )

            with c3:
                st.metric(
                    "Failed",
                    summary.get(
                        "failed",
                        0
                    )
                )

            with c4:
                st.metric(
                    "Needs Review",
                    summary.get(
                        "needs_review",
                        0
                    )
                )


            # =================================================
            # EXTRACTED DECLARATIONS
            # =================================================

            st.divider()

            st.subheader(
                "📋 Extracted Package Declarations"
            )

            fields = extracted_data.get(
                "fields",
                {}
            )


            field_display_names = {

                "product_name":
                    "Product Name",

                "net_quantity":
                    "Net Quantity",

                "mrp":
                    "MRP",

                "unit_sale_price":
                    "Unit Sale Price",

                "packed_date":
                    "Packed Date",

                "use_by_date":
                    "Use By / Best Before",

                "lot_number":
                    "Lot / Batch Number",

                "manufacturer":
                    "Manufacturer",

                "packer":
                    "Packer",

                "importer":
                    "Importer",

                "responsible_entity":
                    "Responsible Entity",

                "marketed_by":
                    "Marketed By",

                "country_of_origin":
                    "Country of Origin",

                "customer_care":
                    "Customer Care"
            }


            rows = []

            for field_name, display_name in field_display_names.items():

                field = fields.get(
                    field_name,
                    {}
                )

                if isinstance(field, dict):

                    value = field.get(
                        "value"
                    )

                    confidence = field.get(
                        "confidence",
                        0.0
                    )

                else:

                    value = field
                    confidence = 0.0


                if value is None:

                    value_text = "Not detected"

                else:

                    value_text = str(value)


                rows.append(
                    {
                        "Declaration":
                            display_name,

                        "Extracted Value":
                            value_text,

                        "Confidence":
                            f"{confidence * 100:.1f}%"
                    }
                )


            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True
            )


            # =================================================
            # COMPLIANCE DETAILS
            # =================================================

            st.divider()

            st.subheader(
                "⚖️ Rule-wise Compliance Analysis"
            )

            results = report.get(
                "results",
                []
            )


            for result_item in results:

                status = result_item.get(
                    "status",
                    "UNKNOWN"
                )

                field_name = result_item.get(
                    "field",
                    "Unknown"
                )

                rule_number = result_item.get(
                    "rule_number",
                    "N/A"
                )

                rule_name = result_item.get(
                    "name",
                    field_name
                )

                value = result_item.get(
                    "value"
                )

                confidence = result_item.get(
                    "confidence",
                    0
                )

                reason = result_item.get(
                    "reason",
                    ""
                )


                if status == "PASS":

                    icon = "✅"

                elif status == "FAIL":

                    icon = "❌"

                elif status == "NEEDS REVIEW":

                    icon = "⚠️"

                else:

                    icon = "ℹ️"


                with st.expander(
                    f"{icon} {rule_name} — {status}"
                ):

                    col_a, col_b = st.columns(2)

                    with col_a:

                        st.write(
                            "**Rule:**",
                            f"Rule {rule_number}"
                        )

                        st.write(
                            "**Field:**",
                            field_name
                        )

                        st.write(
                            "**Detected value:**",
                            value if value is not None
                            else "Not detected"
                        )

                    with col_b:

                        st.write(
                            "**Confidence:**",
                            f"{confidence * 100:.1f}%"
                        )

                        st.write(
                            "**Status:**",
                            status
                        )

                    st.write(
                        "**Explanation:**",
                        reason
                    )


            # =================================================
            # PROCESSED IMAGE
            # =================================================

            st.divider()

            st.subheader(
                "🖼️ OCR Processing Evidence"
            )

            st.image(
                str(processed_image_path),
                caption="Processed image used for OCR",
                use_container_width=True
            )


            # =================================================
            # OCR TEXT
            # =================================================

            if OCR_FILE.exists():

                with st.expander(
                    "🔤 View Raw OCR Output"
                ):

                    with open(
                        OCR_FILE,
                        "r",
                        encoding="utf-8"
                    ) as file:

                        ocr_data = json.load(file)


                    ocr_items = ocr_data.get(
                        "ocr",
                        []
                    )


                    if ocr_items:

                        for item in ocr_items:

                            st.write(
                                f"**{item.get('text', '')}** "
                                f"— confidence: "
                                f"{item.get('confidence', 0) * 100:.1f}%"
                            )

                    else:

                        st.write(
                            "No OCR text detected."
                        )


            # =================================================
            # LEGAL DISCLAIMER
            # =================================================

            st.divider()

            st.info(
                "ℹ️ This prototype is an AI-assisted inspection "
                "support system. A NEEDS REVIEW result indicates "
                "that the declaration could not be confidently "
                "verified from the image and requires manual "
                "inspection. Physical quantity measurement and "
                "official legal determination are outside the "
                "scope of image-based verification."
            )


        except Exception as error:

            st.error(
                "An unexpected error occurred."
            )

            with st.expander(
                "Technical details"
            ):

                st.exception(
                    error
                )


# ============================================================
# INITIAL STATE
# ============================================================

else:

    st.info(
        "👆 Upload a package image above to begin the inspection."
    )

    st.markdown(
        """
        ### What this prototype does

        **1. Image Processing**  
        Enhances the package image for OCR.

        **2. OCR**  
        Detects text using PaddleOCR.

        **3. Declaration Extraction**  
        Identifies fields such as MRP, net quantity,
        dates and responsible entities.

        **4. Rule Engine**  
        Compares extracted information against the
        configured Legal Metrology rules.

        **5. Explainable Result**  
        Shows PASS, NON-COMPLIANT or NEEDS REVIEW
        with reasons and confidence scores.
        """
    )