import json
import re
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OCR_FILE = BASE_DIR.parent / "ocr_output.json"
OUTPUT_FILE = BASE_DIR.parent / "extracted_product.json"


# ============================================================
# CONFIGURATION
# ============================================================

MIN_CONFIDENCE = 0.70


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(text):
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_for_matching(text):
    text = clean_text(text).upper()

    text = text.replace(":", " ")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_confidence(item):
    try:
        return float(item.get("confidence", 0.0))
    except (ValueError, TypeError):
        return 0.0


def get_box(item):

    box = item.get("box")

    if box is None:
        return None

    try:
        return box.tolist()
    except AttributeError:
        return box


def make_field(value, confidence, box):

    return {
        "value": value,
        "confidence": round(float(confidence), 4),
        "box": box
    }


# ============================================================
# LOAD OCR
# ============================================================

def load_ocr_data():

    if not OCR_FILE.exists():

        print("ERROR: ocr_output.json not found.")

        return []

    try:

        with open(
            OCR_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except json.JSONDecodeError:

        print("ERROR: ocr_output.json contains invalid JSON.")

        return []

    ocr_items = data.get("ocr", [])

    if not isinstance(ocr_items, list):

        print("ERROR: OCR data is not a list.")

        return []

    return ocr_items


# ============================================================
# PREPARE OCR ITEMS
# ============================================================

def prepare_items(ocr_items):

    prepared = []

    for index, item in enumerate(ocr_items):

        if not isinstance(item, dict):
            continue

        text = clean_text(item.get("text"))

        if not text:
            continue

        prepared.append({

            "index": index,

            "text": text,

            "normalized":
                normalize_for_matching(text),

            "confidence":
                get_confidence(item),

            "box":
                get_box(item)
        })

    return prepared


# ============================================================
# KEYWORD CHECK
# ============================================================

def contains_keyword(text, keywords):

    normalized = normalize_for_matching(text)

    for keyword in keywords:

        keyword_normalized = normalize_for_matching(keyword)

        if keyword_normalized in normalized:

            return True

    return False


# ============================================================
# TEXT AFTER LABEL
# ============================================================

def text_after_label(text, labels):

    original = clean_text(text)

    upper = original.upper()

    for label in labels:

        label_upper = label.upper()

        position = upper.find(label_upper)

        if position != -1:

            value = original[
                position + len(label):
            ].strip()

            value = value.lstrip(":- ")

            if value:

                return value

    return None


# ============================================================
# FIND NEXT USEFUL OCR ITEM
# ============================================================

def find_next_item(items, index, max_distance=5):

    for offset in range(1, max_distance + 1):

        next_index = index + offset

        if next_index >= len(items):
            break

        item = items[next_index]

        if item["text"].strip():

            return item

    return None


# ============================================================
# GENERIC LABELLED FIELD
# ============================================================

def extract_labelled_field(
    items,
    labels,
    max_distance=5
):

    for i, item in enumerate(items):

        text = item["text"]

        # Same line
        value = text_after_label(
            text,
            labels
        )

        if value:

            return make_field(
                value,
                item["confidence"],
                item["box"]
            )

        # Label on one line, value later
        if contains_keyword(
            text,
            labels
        ):

            next_item = find_next_item(
                items,
                i,
                max_distance
            )

            if next_item:

                return make_field(
                    next_item["text"],
                    min(
                        item["confidence"],
                        next_item["confidence"]
                    ),
                    next_item["box"]
                )

    return None


# ============================================================
# PRODUCT NAME
# ============================================================

def is_bad_product_name_candidate(text):

    normalized = normalize_for_matching(text)

    if not normalized:
        return True

    bad_keywords = [

    # -----------------------------
    # Quantity / price declarations
    # -----------------------------

    "NET WEIGHT",
    "NET QUANTITY",
    "NET WT",

    "MRP",
    "MAXIMUM RETAIL PRICE",
    "RETAIL SALE PRICE",

    # -----------------------------
    # Manufacturer / packer / marketer
    # -----------------------------

    "MARKETED BY",
    "ZARKETED BY",

    "MANUFACTURED BY",
    "MANUFACTURED",

    "MANUFACTURER",
    "MANUFACTURING",

    "PACKED BY",
    "PACKER",

    "IMPORTED BY",
    "IMPORTER",

    "MARKETED",
    "MARKETER",

    # -----------------------------
    # Country
    # -----------------------------

    "COUNTRY OF ORIGIN",
    "MADE IN",

    # -----------------------------
    # Customer care
    # -----------------------------

    "CUSTOMER CARE",
    "CONSUMER CARE",
    "CARE NUMBER",
    "TOLL FREE",

    # -----------------------------
    # Lot / batch
    # -----------------------------

    "LOT NO",
    "LOT NUMBER",
    "BATCH NO",
    "BATCH NUMBER",

    # -----------------------------
    # Dates
    # -----------------------------

    "PACKED ON",
    "PACKING DATE",
    "PKD",
    "MFG",
    "MFD",
    "MANUFACTURED ON",

    "USE BY",
    "BEST BEFORE",
    "EXPIRY",

    # -----------------------------
    # Food information
    # -----------------------------

    "INGREDIENTS",
    "NUTRITION",
    "NUTRITIONAL INFORMATION",

    "TRANS FAT",
    "SATURATED FAT",
    "TOTAL FAT",
    "PROTEIN",
    "CARBOHYDRATE",
    "ENERGY",

    # -----------------------------
    # Storage / warnings
    # -----------------------------

    "KEEP IN A",
    "STORE IN",
    "STORAGE",

    "WARNING",
    "CAUTION",

    # -----------------------------
    # Common OCR fragments
    # -----------------------------

    "ZARKETED",
    "MARKETED BY:",
    "ZARKETED BY:",
    "MANUFACTURED BY:",
    "PACKED BY:",
    "IMPORTED BY:"
]

    for keyword in bad_keywords:

        if keyword in normalized:
            return True

    # Avoid obvious OCR paragraph fragments
    paragraph_words = [
        "TRANSFER",
        "INSFER",
        "CONTAINER",
        "CONTENTS",
        "CONSUMPTION",
        "TEMPERATURE",
        "HUMIDITY",
        "CONTAINER",
        "ILLUSTRATION",
        "VISUALIZATION"
    ]

    for keyword in paragraph_words:

        if keyword in normalized:

            return True

    # Pure numbers
    if re.fullmatch(
        r"[\d\s.,:/-]+",
        normalized
    ):

        return True

    # Quantity
    if re.fullmatch(
        r"\d+(?:\.\d+)?\s*"
        r"(G|KG|MG|ML|L|CM|MM|M)",
        normalized
    ):

        return True

    # Price
    if re.search(
        r"(₹|RS\.?|MRP|PER\s+(G|KG|ML|L|M|CM))",
        normalized
    ):

        return True

    # Very short
    words = normalized.split()

    if len(words) == 1 and len(words[0]) <= 2:

        return True

    return False


def extract_product_name(items):

    candidates = []

    for item in items:

        text = clean_text(item["text"])

        if is_bad_product_name_candidate(text):

            continue

        words = text.split()

        alphabetic_count = sum(
            1
            for char in text
            if char.isalpha()
        )

        if alphabetic_count < 3:

            continue

        if len(text) > 80:

            continue

        score = 0

        if len(words) >= 2:
            score += 2

        if len(words) >= 3:
            score += 1

        if item["confidence"] >= 0.90:
            score += 2

        candidates.append(
            (
                score,
                item
            )
        )

    if not candidates:

        return None

    candidates.sort(
        key=lambda x: (
            x[0],
            x[1]["confidence"]
        ),
        reverse=True
    )

    best = candidates[0][1]

    return make_field(
        best["text"],
        best["confidence"],
        best["box"]
    )


# ============================================================
# NET QUANTITY
# ============================================================

def extract_net_quantity(items):

    quantity_pattern = re.compile(
        r"(?<!\d)"
        r"(\d+(?:\.\d+)?)"
        r"\s*"
        r"(kg|g|mg|l|ml|cl|m|cm|mm|pcs|pieces|piece)"
        r"\b",
        re.IGNORECASE
    )

    for i, item in enumerate(items):

        if contains_keyword(
            item["text"],
            [
                "NET WEIGHT",
                "NET WT",
                "NET QUANTITY",
                "NET QTY"
            ]
        ):

            match = quantity_pattern.search(
                item["text"]
            )

            if match:

                return make_field(
                    match.group(0),
                    item["confidence"],
                    item["box"]
                )

            next_item = find_next_item(
                items,
                i
            )

            if next_item:

                match = quantity_pattern.search(
                    next_item["text"]
                )

                if match:

                    return make_field(
                        match.group(0),
                        min(
                            item["confidence"],
                            next_item["confidence"]
                        ),
                        next_item["box"]
                    )

    # Fallback
    for item in items:

        match = quantity_pattern.fullmatch(
            item["text"].strip()
        )

        if match:

            return make_field(
                match.group(0),
                item["confidence"],
                item["box"]
            )

    return None


# ============================================================
# MRP
# ============================================================

def extract_mrp(items):
    """
    Extract MRP from OCR text.

    Strategy:
    1. Look for MRP keyword.
    2. Prefer a nearby price containing Rs./₹.
    3. Prefer a decimal price such as 10.00.
    4. Avoid large numbers such as lot codes, IDs, etc.
    """

    for i, item in enumerate(items):

        text = item["text"].strip()
        upper = text.upper()

        if "MRP" not in upper:
            continue

        # Check nearby OCR items
        for j in range(i, min(i + 8, len(items))):

            candidate = items[j]["text"].strip()

            # Ignore the MRP label itself
            if j == i:
                candidate = re.sub(r"\bMRP\b", "", candidate,
                                   flags=re.IGNORECASE).strip()

            if not candidate:
                continue

            # ------------------------------------------------
            # ₹ / RS price
            # ------------------------------------------------
            match = re.search(
                r"(?:₹|RS\.?|INR)\s*[:.]?\s*(\d+(?:\.\d{1,2})?)",
                candidate,
                re.IGNORECASE
            )

            if match:
                value = float(match.group(1))

                # Reject obviously unreasonable OCR numbers
                if 0 < value < 100000:
                    return {
                        "value": value,
                        "confidence": items[j]["confidence"],
                        "box": items[j]["box"]
                    }

            # ------------------------------------------------
            # Plain decimal price
            # Example: 10.00
            # ------------------------------------------------
            match = re.fullmatch(
                r"\s*(\d{1,6}\.\d{1,2})\s*",
                candidate
            )

            if match:
                value = float(match.group(1))

                if 0 < value < 100000:
                    return {
                        "value": value,
                        "confidence": items[j]["confidence"],
                        "box": items[j]["box"]
                    }

    return {
        "value": None,
        "confidence": 0.0,
        "box": None
    }


# ============================================================
# UNIT SALE PRICE
# ============================================================

def extract_unit_sale_price(items):

    pattern = re.compile(
        r"(?:₹|Rs\.?|INR)?\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*"
        r"(?:per|/)"
        r"\s*"
        r"(kg|g|mg|l|ml|cl|m|cm|mm|number|unit|piece|pieces|pcs)",
        re.IGNORECASE
    )

    for item in items:

        match = pattern.search(
            item["text"]
        )

        if match:

            return make_field(
                item["text"],
                item["confidence"],
                item["box"]
            )

    return None


# ============================================================
# PACKED / MANUFACTURING DATE
# ============================================================

def extract_packed_date(items):

    date_pattern = re.compile(
        r"\b"
        r"(?:"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|"
        r"\d{1,2}[/-]\d{2,4}"
        r"|"
        r"\d{2,4}[/-]\d{1,2}[/-]\d{1,2}"
        r")"
        r"\b"
    )

    labels = [
        "PKD",
        "PACKED ON",
        "PACKING DATE",
        "DATE OF PACKING",
        "MFD",
        "MFG",
        "MANUFACTURED ON",
        "DATE OF MANUFACTURE",
        "MANUFACTURING DATE"
    ]

    for i, item in enumerate(items):

        text = item["text"]

        if not contains_keyword(
            text,
            labels
        ):

            continue

        # Same line
        match = date_pattern.search(text)

        if match:

            return make_field(
                match.group(0),
                item["confidence"],
                item["box"]
            )

        # Search next several OCR lines
        for distance in range(1, 8):

            next_index = i + distance

            if next_index >= len(items):
                break

            next_item = items[next_index]

            match = date_pattern.search(
                next_item["text"]
            )

            if match:

                return make_field(
                    match.group(0),
                    min(
                        item["confidence"],
                        next_item["confidence"]
                    ),
                    next_item["box"]
                )

    return None


# ============================================================
# USE BY / BEST BEFORE
# ============================================================

def extract_use_by_date(items):

    date_pattern = re.compile(
        r"\b"
        r"(?:"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|"
        r"\d{1,2}[/-]\d{2,4}"
        r"|"
        r"\d{2,4}[/-]\d{1,2}[/-]\d{1,2}"
        r")"
        r"\b"
    )

    labels = [
        "USE BY",
        "BEST BEFORE",
        "EXPIRY",
        "EXPIRATION"
    ]

    for i, item in enumerate(items):

        if not contains_keyword(
            item["text"],
            labels
        ):

            continue

        match = date_pattern.search(
            item["text"]
        )

        if match:

            return make_field(
                match.group(0),
                item["confidence"],
                item["box"]
            )

        for distance in range(1, 5):

            next_index = i + distance

            if next_index >= len(items):
                break

            next_item = items[next_index]

            match = date_pattern.search(
                next_item["text"]
            )

            if match:

                return make_field(
                    match.group(0),
                    min(
                        item["confidence"],
                        next_item["confidence"]
                    ),
                    next_item["box"]
                )

    return None


# ============================================================
# LOT / BATCH NUMBER
# ============================================================

def extract_lot_number(items):

    labels = [
        "LOT NO",
        "LOT NUMBER",
        "BATCH NO",
        "BATCH NUMBER"
    ]

    # --------------------------------------------------------
    # First: explicit "LOT No." line
    # --------------------------------------------------------

    for i, item in enumerate(items):

        text = item["text"]

        # Ignore a line that is only the label
        value = text_after_label(
            text,
            labels
        )

        if value and value.strip(". "):

            return make_field(
                value,
                item["confidence"],
                item["box"]
            )

        if contains_keyword(
            text,
            labels
        ):

            # Search next few OCR items
            for distance in range(1, 5):

                next_index = i + distance

                if next_index >= len(items):
                    break

                next_item = items[next_index]

                candidate = next_item["text"].strip()

                # Ignore punctuation-only values
                if re.fullmatch(
                    r"[\s.:,-]+",
                    candidate
                ):

                    continue

                # Avoid unrelated long paragraphs
                if len(candidate) > 50:

                    continue

                return make_field(
                    candidate,
                    min(
                        item["confidence"],
                        next_item["confidence"]
                    ),
                    next_item["box"]
                )

    # --------------------------------------------------------
    # Fallback for common batch formats
    # --------------------------------------------------------

    batch_pattern = re.compile(
        r"(?i)"
        r"(?:LOT|BATCH)"
        r"\s*(?:NO\.?|NUMBER)?"
        r"\s*[:\-]?\s*"
        r"([A-Z0-9][A-Z0-9\/\-: ]{2,30})"
    )

    for item in items:

        match = batch_pattern.search(
            item["text"]
        )

        if match:

            value = match.group(1).strip()

            return make_field(
                value,
                item["confidence"],
                item["box"]
            )

    return None


# ============================================================
# MANUFACTURER
# ============================================================

def extract_manufacturer(items):

    return extract_labelled_field(
        items,
        [
            "MANUFACTURED BY",
            "MANUFACTURER",
            "MANUFACTURED AND MARKETED BY"
        ]
    )


# ============================================================
# PACKER
# ============================================================

def extract_packer(items):

    return extract_labelled_field(
        items,
        [
            "PACKED BY",
            "PACKER"
        ]
    )


# ============================================================
# IMPORTER
# ============================================================

def extract_importer(items):

    return extract_labelled_field(
        items,
        [
            "IMPORTED BY",
            "IMPORTER"
        ]
    )


# ============================================================
# MARKETED BY
# ============================================================

def extract_marketed_by(items):

    # Normal case
    field = extract_labelled_field(
        items,
        [
            "MARKETED BY"
        ]
    )

    if field:
        return field

    # OCR typo variations
    typo_labels = [
        "ZARKETED BY",
        "MARKETEO BY",
        "MARKETED 8Y",
        "MARKETEO 8Y",
        "ZARKETEO BY"
    ]

    for i, item in enumerate(items):

        if not contains_keyword(
            item["text"],
            typo_labels
        ):

            continue

        value = text_after_label(
            item["text"],
            typo_labels
        )

        if value:

            return make_field(
                value,
                item["confidence"],
                item["box"]
            )

        next_item = find_next_item(
            items,
            i
        )

        if next_item:

            return make_field(
                next_item["text"],
                min(
                    item["confidence"],
                    next_item["confidence"]
                ),
                next_item["box"]
            )

    return None


# ============================================================
# COUNTRY OF ORIGIN
# ============================================================

def extract_country_of_origin(items):

    labels = [
        "COUNTRY OF ORIGIN",
        "MADE IN",
        "PRODUCT OF"
    ]

    field = extract_labelled_field(
        items,
        labels
    )

    if field:

        return field

    for item in items:

        normalized = item["normalized"]

        match = re.search(
            r"\bMADE\s+IN\s+([A-Z][A-Z\s]{2,40})",
            normalized
        )

        if match:

            country = match.group(1).strip()

            return make_field(
                country,
                item["confidence"],
                item["box"]
            )

    return None


# ============================================================
# CUSTOMER CARE
# ============================================================

def extract_customer_care(items):

    labels = [
        "CUSTOMER CARE",
        "CONSUMER CARE",
        "CUSTOMER SERVICE",
        "CONSUMER SERVICES",
        "CARE NUMBER",
        "TOLL FREE",
        "HELPLINE"
    ]

    field = extract_labelled_field(
        items,
        labels
    )

    if field:
        return field

    phone_pattern = re.compile(
        r"(?:\+91[\s-]?)?"
        r"\b[6-9]\d{9}\b"
    )

    for i, item in enumerate(items):

        if contains_keyword(
            item["text"],
            labels
        ):

            match = phone_pattern.search(
                item["text"]
            )

            if match:

                return make_field(
                    match.group(0),
                    item["confidence"],
                    item["box"]
                )

            next_item = find_next_item(
                items,
                i
            )

            if next_item:

                match = phone_pattern.search(
                    next_item["text"]
                )

                if match:

                    return make_field(
                        match.group(0),
                        min(
                            item["confidence"],
                            next_item["confidence"]
                        ),
                        next_item["box"]
                    )

    return None


# ============================================================
# RESPONSIBLE ENTITY
# ============================================================

def determine_responsible_entity(
    manufacturer,
    packer,
    importer
):

    if manufacturer:
        return manufacturer

    if packer:
        return packer

    if importer:
        return importer

    return None


# ============================================================
# IMPORTED STATUS
# ============================================================

def determine_imported(
    importer,
    country_of_origin
):

    if importer:

        return True

    if country_of_origin:

        country = str(
            country_of_origin.get(
                "value",
                ""
            )
        ).upper()

        if country and country not in [
            "INDIA",
            "INDIAN"
        ]:

            return True

    return False


# ============================================================
# MAIN EXTRACTION
# ============================================================

def extract_product_data(ocr_items):

    items = prepare_items(
        ocr_items
    )

    print()
    print("=" * 40)
    print("FIELD EXTRACTION")
    print("=" * 40)

    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    product_name = extract_product_name(items)

    net_quantity = extract_net_quantity(items)

    mrp = extract_mrp(items)

    unit_sale_price = extract_unit_sale_price(items)

    packed_date = extract_packed_date(items)

    use_by_date = extract_use_by_date(items)

    lot_number = extract_lot_number(items)

    manufacturer = extract_manufacturer(items)

    packer = extract_packer(items)

    importer = extract_importer(items)

    marketed_by = extract_marketed_by(items)

    country_of_origin = extract_country_of_origin(items)

    customer_care = extract_customer_care(items)

    responsible_entity = determine_responsible_entity(
        manufacturer,
        packer,
        importer
    )

    imported = determine_imported(
        importer,
        country_of_origin
    )

    # --------------------------------------------------------
    # Fields
    # --------------------------------------------------------

    fields = {

        "product_name":
            product_name,

        "mrp":
            mrp,

        "net_quantity":
            net_quantity,

        "unit_sale_price":
            unit_sale_price,

        "packed_date":
            packed_date,

        "use_by_date":
            use_by_date,

        "lot_number":
            lot_number,

        "manufacturer":
            manufacturer,

        "packer":
            packer,

        "importer":
            importer,

        "responsible_entity":
            responsible_entity,

        "marketed_by":
            marketed_by,

        "country_of_origin":
            country_of_origin,

        "customer_care":
            customer_care,

        "imported": {

            "value":
                imported,

            "confidence":
                1.0,

            "box":
                None
        }
    }

    # --------------------------------------------------------
    # Warnings
    # --------------------------------------------------------

    warnings = []

    for field_name, field in fields.items():

        if field is None:

            warnings.append(
                f"{field_name} was not detected."
            )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    detected_count = sum(
        1
        for field in fields.values()
        if field is not None
    )

    if detected_count == 0:

        status = "EXTRACTION_FAILED"

    elif warnings:

        status = "EXTRACTED_WITH_WARNINGS"

    else:

        status = "EXTRACTED"

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    result = {

        "status":
            status,

        "fields":
            fields,

        "warnings":
            warnings,

        "ocr_item_count":
            len(items)
    }

    return result


# ============================================================
# PRINT RESULT
# ============================================================

def print_extraction_result(result):

    print()

    fields = result.get(
        "fields",
        {}
    )

    for field_name, field in fields.items():

        print()
        print(field_name)

        if field is None:

            print("  Value       : None")
            print("  Confidence  : 0.0")
            print("  Status      : NOT DETECTED")

        else:

            print(
                "  Value       :",
                field.get("value")
            )

            print(
                "  Confidence  :",
                field.get("confidence")
            )

            print(
                "  Box         :",
                field.get("box")
            )

    print()

    print(
        "Extraction status:",
        result.get("status")
    )

    warnings = result.get(
        "warnings",
        []
    )

    if warnings:

        print()
        print("Warnings:")

        for warning in warnings:

            print(
                " -",
                warning
            )


# ============================================================
# SAVE RESULT
# ============================================================

def save_extraction_result(result):

    try:

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                result,
                file,
                indent=4,
                ensure_ascii=False
            )

        print()

        print(
            "Output file:",
            OUTPUT_FILE
        )

        return True

    except Exception as error:

        print(
            "ERROR: Could not save extracted data:",
            error
        )

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 40)
    print("PRODUCT FIELD EXTRACTION")
    print("=" * 40)

    ocr_items = load_ocr_data()

    if not ocr_items:

        print()
        print(
            "No OCR data found."
        )

        print(
            "Run ocr.py first."
        )

        return

    print()

    print(
        "OCR items loaded:",
        len(ocr_items)
    )

    result = extract_product_data(
        ocr_items
    )

    print_extraction_result(
        result
    )

    save_extraction_result(
        result
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()