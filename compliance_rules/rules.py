import json
import re
import sys 
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RULES_FILE = BASE_DIR / "legal_rules.json"
EXTRACTED_FILE = BASE_DIR.parent / "extracted_product.json"
REPORT_FILE = BASE_DIR.parent / "compliance_report.json"


# ============================================================
# LOAD RULE DATABASE
# ============================================================

def load_rules():
    """Load legal rules from legal_rules.json."""

    try:
        with open(RULES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except FileNotFoundError:
        print("ERROR: legal_rules.json not found.")
        return {
            "database_name": "Unknown",
            "version": "Unknown",
            "last_updated": "Unknown",
            "rules": []
        }

    except json.JSONDecodeError:
        print("ERROR: legal_rules.json contains invalid JSON.")
        return {
            "database_name": "Unknown",
            "version": "Unknown",
            "last_updated": "Unknown",
            "rules": []
        }


RULE_DATABASE = load_rules()


# ============================================================
# BASIC HELPERS
# ============================================================

def get_rule(rule_id):
    """Return a rule using its rule ID."""

    for rule in RULE_DATABASE.get("rules", []):
        if rule.get("rule_id") == rule_id:
            return rule

    return None


def get_field(data, field_name):
    """Safely get a field from extracted_product.json."""

    return data.get("fields", {}).get(field_name)


def is_empty(value):
    """Check whether a value is empty or missing."""

    if value is None:
        return True

    if isinstance(value, str) and not value.strip():
        return True

    return False


def get_confidence(field):
    """Get OCR/extraction confidence."""

    if not isinstance(field, dict):
        return 0.0

    try:
        return float(field.get("confidence", 0.0))
    except (ValueError, TypeError):
        return 0.0


def get_value(field):
    """Get extracted value from a field."""

    if isinstance(field, dict):
        return field.get("value")

    return field


def create_result(
    rule_id,
    status,
    value=None,
    confidence=0.0,
    reason="",
    box=None
):
    """Create a standard compliance result."""

    rule = get_rule(rule_id)

    if rule:
        rule_number = rule.get("rule_number", "N/A")
        field_name = rule.get("field", "N/A")
        name = rule.get("name", "N/A")
        source = rule.get(
            "source",
            "Legal Metrology (Packaged Commodities) Rules, 2011"
        )
    else:
        rule_number = "N/A"
        field_name = "N/A"
        name = "N/A"
        source = "N/A"

    return {
        "rule_id": rule_id,
        "rule_number": rule_number,
        "field": field_name,
        "name": name,
        "status": status,
        "value": value,
        "confidence": confidence,
        "reason": reason,
        "box": box,
        "source": source
    }


# ============================================================
# PRODUCT NAME CHECK
# ============================================================

def check_product_name(data):
    rule_id = "LM-PC-001"

    field = get_field(data, "product_name")

    if is_empty(field):
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=None,
            confidence=0.0,
            reason=(
                "Common or generic name was not detected by the "
                "extraction system. Manual verification is required."
            )
        )

    value = get_value(field)
    confidence = get_confidence(field)

    if confidence < 0.70:
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "A possible product name was detected, but the "
                "extraction confidence is low. Manual verification "
                "is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=value,
        confidence=confidence,
        reason="Common or generic name was detected.",
        box=field.get("box") if isinstance(field, dict) else None
    )


# ============================================================
# NET QUANTITY CHECK
# ============================================================

def parse_quantity(value):
    """
    Extract numeric quantity and unit.

    Examples:
        39 g
        500 g
        1 kg
        750 ml
        2 L
        10 pieces
    """

    if value is None:
        return None, None

    text = str(value).strip().lower()

    pattern = r"^\s*(\d+(?:\.\d+)?)\s*(kg|g|mg|l|ml|cl|m|cm|mm|pcs|pieces|piece|n|number)\s*$"

    match = re.fullmatch(pattern, text)

    if not match:
        return None, None

    quantity = float(match.group(1))
    unit = match.group(2)

    if quantity <= 0:
        return None, None

    return quantity, unit


def normalize_quantity_unit(unit):
    """Normalize quantity units."""

    mapping = {
        "kg": "kg",
        "g": "g",
        "mg": "mg",

        "l": "l",
        "ml": "ml",
        "cl": "cl",

        "m": "m",
        "cm": "cm",
        "mm": "mm",

        "pcs": "number",
        "piece": "number",
        "pieces": "number",
        "n": "number",
        "number": "number"
    }

    return mapping.get(unit)


def check_net_quantity(data):
    rule_id = "LM-PC-002"

    field = get_field(data, "net_quantity")

    if is_empty(field):
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=None,
            confidence=0.0,
            reason=(
                "Net quantity was not detected. Manual verification "
                "of the package is required."
            )
        )

    value = get_value(field)
    confidence = get_confidence(field)

    quantity, unit = parse_quantity(value)

    if quantity is None or unit is None:
        return create_result(
            rule_id=rule_id,
            status="FAIL",
            value=value,
            confidence=confidence,
            reason=(
                "The detected net quantity does not match the "
                "supported quantity/unit format."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    normalized_unit = normalize_quantity_unit(unit)

    if normalized_unit is None:
        return create_result(
            rule_id=rule_id,
            status="FAIL",
            value=value,
            confidence=confidence,
            reason="The detected quantity uses an unsupported unit.",
            box=field.get("box") if isinstance(field, dict) else None
        )

    if confidence < 0.70:
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "Net quantity was detected, but OCR confidence is "
                "low. Manual verification is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=value,
        confidence=confidence,
        reason=(
            f"Net quantity {value} was detected. The declared "
            f"quantity has a valid quantity/unit format."
        ),
        box=field.get("box") if isinstance(field, dict) else None
    )


# ============================================================
# MRP CHECK
# ============================================================

def check_mrp(data):
    rule_id = "LM-PC-003"

    field = get_field(data, "mrp")

    if is_empty(field):
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=None,
            confidence=0.0,
            reason=(
                "MRP was not detected. Manual verification of the "
                "retail sale price is required."
            )
        )

    value = get_value(field)
    confidence = get_confidence(field)

    try:
        mrp_value = float(value)
    except (ValueError, TypeError):
        return create_result(
            rule_id=rule_id,
            status="FAIL",
            value=value,
            confidence=confidence,
            reason="The detected MRP is not a valid numeric value.",
            box=field.get("box") if isinstance(field, dict) else None
        )

    if mrp_value <= 0:
        return create_result(
            rule_id=rule_id,
            status="FAIL",
            value=value,
            confidence=confidence,
            reason="MRP must be greater than zero.",
            box=field.get("box") if isinstance(field, dict) else None
        )

    if confidence < 0.70:
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "MRP was detected, but OCR confidence is low. "
                "Manual verification is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=mrp_value,
        confidence=confidence,
        reason=(
            f"MRP of ₹{mrp_value:.2f} was detected and passed "
            f"the configured MRP validation."
        ),
        box=field.get("box") if isinstance(field, dict) else None
    )


# ============================================================
# RESPONSIBLE ENTITY CHECK
# ============================================================

def check_responsible_entity(data):
    rule_id = "LM-PC-004"

    manufacturer = get_field(data, "manufacturer")
    packer = get_field(data, "packer")
    importer = get_field(data, "importer")

    candidates = [
        ("manufacturer", manufacturer),
        ("packer", packer),
        ("importer", importer)
    ]

    for entity_type, field in candidates:

        if not is_empty(field):

            value = get_value(field)
            confidence = get_confidence(field)

            if confidence >= 0.70:

                return create_result(
                    rule_id=rule_id,
                    status="PASS",
                    value=value,
                    confidence=confidence,
                    reason=(
                        f"{entity_type.capitalize()} information "
                        f"was detected."
                    ),
                    box=(
                        field.get("box")
                        if isinstance(field, dict)
                        else None
                    )
                )

            return create_result(
                rule_id=rule_id,
                status="NEEDS REVIEW",
                value=value,
                confidence=confidence,
                reason=(
                    f"{entity_type.capitalize()} information was "
                    f"detected, but confidence is low. Manual "
                    f"verification is required."
                ),
                box=(
                    field.get("box")
                    if isinstance(field, dict)
                    else None
                )
            )

    return create_result(
        rule_id=rule_id,
        status="NEEDS REVIEW",
        value=None,
        confidence=0.0,
        reason=(
            "Manufacturer, packer, or importer information was "
            "not detected. Manual verification is required."
        )
    )


# ============================================================
# MARKETED BY CHECK
# ============================================================

def check_marketed_by(data):

    field = get_field(data, "marketed_by")

    if is_empty(field):
        return {
            "rule_id": "N/A",
            "rule_number": "N/A",
            "field": "marketed_by",
            "name": "Marketed by",
            "status": "NEEDS REVIEW",
            "value": None,
            "confidence": 0.0,
            "reason": "Marketed-by information was not detected.",
            "box": None,
            "source": "Extraction result"
        }

    value = get_value(field)
    confidence = get_confidence(field)

    if confidence < 0.70:
        status = "NEEDS REVIEW"
        reason = (
            "Marketed-by information was detected, but OCR "
            "confidence is low."
        )
    else:
        status = "PASS"
        reason = "Marketed-by information was detected."

    return {
        "rule_id": "N/A",
        "rule_number": "N/A",
        "field": "marketed_by",
        "name": "Marketed by",
        "status": status,
        "value": value,
        "confidence": confidence,
        "reason": reason,
        "box": field.get("box") if isinstance(field, dict) else None,
        "source": "Extraction result"
    }


# ============================================================
# PACKED DATE CHECK
# ============================================================

def check_packed_date(data):

    rule_id = "LM-PC-006"

    field = get_field(data, "packed_date")

    if is_empty(field):
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=None,
            confidence=0.0,
            reason=(
                "Manufacture or packing information was not detected. "
                "Manual verification is required."
            )
        )

    value = get_value(field)
    confidence = get_confidence(field)

    if confidence < 0.70:
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "Manufacture or packing information was detected "
                "with low confidence. Manual verification is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=value,
        confidence=confidence,
        reason=(
            "Manufacture or packing information was detected "
            "and has sufficient extraction confidence."
        ),
        box=field.get("box") if isinstance(field, dict) else None
    )


# ============================================================
# USE-BY / BEST-BEFORE CHECK
# ============================================================

def check_use_by_date(data):

    rule_id = "LM-PC-007"

    field = get_field(data, "use_by_date")

    if is_empty(field):
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=None,
            confidence=0.0,
            reason=(
                "Best-before/use-by information was not detected. "
                "Manual verification is required where applicable."
            )
        )

    value = get_value(field)
    confidence = get_confidence(field)

    if confidence < 0.70:
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "Best-before/use-by information was detected with "
                "low confidence. Manual verification is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=value,
        confidence=confidence,
        reason=(
            "Best before / Use by was detected and has sufficient "
            "extraction confidence."
        ),
        box=field.get("box") if isinstance(field, dict) else None
    )


# ============================================================
# COUNTRY OF ORIGIN CHECK
# ============================================================

def check_country_of_origin(data):

    rule_id = "LM-PC-005"

    imported_field = get_field(data, "imported")
    country_field = get_field(data, "country_of_origin")

    imported = get_value(imported_field)

    # If extraction explicitly says the product is not imported
    if imported is False:
        return create_result(
            rule_id=rule_id,
            status="NOT APPLICABLE",
            value=None,
            confidence=0.0,
            reason=(
                "Country-of-origin checking was not triggered because "
                "the product was not identified as imported."
            )
        )

    if is_empty(country_field):
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=None,
            confidence=0.0,
            reason=(
                "The product may be imported, but country-of-origin "
                "information was not detected. Manual verification "
                "is required."
            )
        )

    value = get_value(country_field)
    confidence = get_confidence(country_field)

    if confidence < 0.70:
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "Country-of-origin information was detected with "
                "low confidence."
            ),
            box=(
                country_field.get("box")
                if isinstance(country_field, dict)
                else None
            )
        )

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=value,
        confidence=confidence,
        reason="Country-of-origin information was detected.",
        box=(
            country_field.get("box")
            if isinstance(country_field, dict)
            else None
        )
    )


# ============================================================
# CUSTOMER CARE CHECK
# ============================================================

def check_customer_care(data):

    rule_id = "LM-PC-008"

    field = get_field(data, "customer_care")

    if is_empty(field):
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=None,
            confidence=0.0,
            reason=(
                "Customer care information was not detected. "
                "Manual package verification is required."
            )
        )

    value = get_value(field)
    confidence = get_confidence(field)

    if confidence < 0.70:
        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "Customer care information was detected with "
                "low confidence."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=value,
        confidence=confidence,
        reason="Customer care information was detected.",
        box=field.get("box") if isinstance(field, dict) else None
    )


# ============================================================
# DIMENSIONS CHECK
# ============================================================

def check_dimensions(data):

    rule_id = "LM-PC-009"

    field = get_field(data, "dimensions")

    if is_empty(field):

        return create_result(
            rule_id=rule_id,
            status="NOT APPLICABLE",
            value=None,
            confidence=0.0,
            reason=(
                "Dimension checking is not enabled for this "
                "product."
            )
        )

    value = get_value(field)
    confidence = get_confidence(field)

    if confidence < 0.70:

        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "Dimensions were detected with low confidence. "
                "Manual verification is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=value,
        confidence=confidence,
        reason="Required dimensions were detected.",
        box=field.get("box") if isinstance(field, dict) else None
    )


# ============================================================
# STEP 5
# UNIT SALE PRICE CHECK
# ============================================================

def parse_unit_sale_price(value):
    """
    Extract unit sale price and unit.

    Examples:

        Rs. 0.26 per g
        ₹0.26 per g
        Rs 0.26/g
        0.26 per kg
        ₹2.50 per litre
    """

    if value is None:
        return None, None

    text = str(value).strip().lower()

    # Remove common currency symbols / prefixes
    text = text.replace("₹", "")
    text = text.replace("rs.", "rs")
    text = text.replace("rs", "")
    text = text.strip()

    patterns = [
        r"^\s*(\d+(?:\.\d+)?)\s*per\s*(kg|g|mg|l|ml|cl|m|cm|mm|number|unit|piece|pieces|pcs)\s*$",

        r"^\s*(\d+(?:\.\d+)?)\s*/\s*(kg|g|mg|l|ml|cl|m|cm|mm|number|unit|piece|pieces|pcs)\s*$"
    ]

    for pattern in patterns:

        match = re.fullmatch(pattern, text)

        if match:

            price = float(match.group(1))
            unit = match.group(2)

            if price < 0:
                return None, None

            return price, unit

    return None, None


def normalize_sale_price_unit(unit):
    """Normalize units used in unit sale price."""

    if unit is None:
        return None

    mapping = {
        "kg": "kg",
        "g": "g",
        "mg": "mg",

        "l": "l",
        "ml": "ml",
        "cl": "cl",

        "m": "m",
        "cm": "cm",
        "mm": "mm",

        "number": "number",
        "unit": "number",
        "piece": "number",
        "pieces": "number",
        "pcs": "number"
    }

    return mapping.get(unit)


def get_expected_sale_price_unit(quantity, quantity_unit):
    """
    Determine the applicable unit-sale-price unit based on
    declared net quantity.

    Based on the configured Legal Metrology rule:

        < 1 kg  -> per gram
        > 1 kg  -> per kilogram

        < 1 litre -> per millilitre
        > 1 litre -> per litre

        < 1 metre -> per centimetre
        > 1 metre -> per metre

        Number-based commodities -> per number/unit
    """

    if quantity is None or quantity_unit is None:
        return None

    quantity_unit = normalize_quantity_unit(quantity_unit)

    # Weight
    if quantity_unit == "g":

        if quantity < 1000:
            return "g"

        elif quantity > 1000:
            return "kg"

        else:
            # Exactly 1 kg.
            # Treat as kg for practical rule-engine purposes.
            return "kg"

    if quantity_unit == "kg":
        return "g" if quantity < 1 else "kg"

    if quantity_unit == "mg":
        # Convert mg to grams
        grams = quantity / 1000

        if grams < 1000:
            return "g"

        return "kg"

    # Volume
    if quantity_unit == "ml":

        if quantity < 1000:
            return "ml"

        elif quantity > 1000:
            return "l"

        else:
            return "l"

    if quantity_unit == "l":
        return "ml" if quantity < 1 else "l"

    if quantity_unit == "cl":

        ml = quantity * 10

        if ml < 1000:
            return "ml"

        return "l"

    # Length
    if quantity_unit == "cm":

        if quantity < 100:
            return "cm"

        return "m"

    if quantity_unit == "m":

        if quantity < 1:
            return "cm"

        return "m"

    if quantity_unit == "mm":

        cm = quantity / 10

        if cm < 100:
            return "cm"

        return "m"

    # Number based
    if quantity_unit == "number":
        return "number"

    return None


def check_unit_sale_price(data, required=True):
    """
    Validate unit sale price.

    For the current biscuit example:

        Net quantity = 39 g
        Expected unit = per g
        Detected = Rs. 0.26 per g

    Therefore the check should PASS.
    """

    rule_id = "LM-PC-010"

    field = get_field(data, "unit_sale_price")

    # --------------------------------------------------------
    # If this check is disabled / not applicable
    # --------------------------------------------------------

    if not required:

        return create_result(
            rule_id=rule_id,
            status="NOT APPLICABLE",
            value=get_value(field) if not is_empty(field) else None,
            confidence=get_confidence(field) if not is_empty(field) else 0.0,
            reason=(
                "Unit sale price checking is not enabled for the "
                "current product configuration."
            ),
            box=(
                field.get("box")
                if isinstance(field, dict)
                else None
            )
        )

    # --------------------------------------------------------
    # Missing unit sale price
    # --------------------------------------------------------

    if is_empty(field):

        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=None,
            confidence=0.0,
            reason=(
                "Unit sale price was not detected. Manual verification "
                "is required to determine whether the declaration is "
                "present and applicable."
            )
        )

    value = get_value(field)
    confidence = get_confidence(field)

    # --------------------------------------------------------
    # Parse declared unit sale price
    # --------------------------------------------------------

    sale_price, sale_unit = parse_unit_sale_price(value)

    if sale_price is None or sale_unit is None:

        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "A unit sale price was detected, but its value/unit "
                "could not be reliably parsed. Manual verification "
                "is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    normalized_sale_unit = normalize_sale_price_unit(sale_unit)

    if normalized_sale_unit is None:

        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "The declared unit sale price uses an unsupported "
                "unit. Manual verification is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    # --------------------------------------------------------
    # Get net quantity
    # --------------------------------------------------------

    quantity_field = get_field(data, "net_quantity")

    if is_empty(quantity_field):

        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "Unit sale price was detected, but net quantity "
                "was not available to determine the applicable "
                "unit. Manual verification is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    quantity_value = get_value(quantity_field)

    quantity, quantity_unit = parse_quantity(quantity_value)

    if quantity is None or quantity_unit is None:

        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "Unit sale price was detected, but the net quantity "
                "could not be reliably interpreted to determine "
                "the applicable sale-price unit."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    # --------------------------------------------------------
    # Determine expected unit
    # --------------------------------------------------------

    expected_unit = get_expected_sale_price_unit(
        quantity,
        quantity_unit
    )

    if expected_unit is None:

        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                "The applicable unit sale price unit could not be "
                "determined from the declared quantity. Manual "
                "verification is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    # --------------------------------------------------------
    # Compare declared unit with expected unit
    # --------------------------------------------------------

    if normalized_sale_unit != expected_unit:

        return create_result(
            rule_id=rule_id,
            status="FAIL",
            value=value,
            confidence=confidence,
            reason=(
                f"The declared unit sale price is expressed per "
                f"{normalized_sale_unit}, but the configured rule "
                f"indicates per {expected_unit} for the declared "
                f"net quantity of {quantity_value}."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    # --------------------------------------------------------
    # Confidence check
    # --------------------------------------------------------

    if confidence < 0.70:

        return create_result(
            rule_id=rule_id,
            status="NEEDS REVIEW",
            value=value,
            confidence=confidence,
            reason=(
                f"Unit sale price was detected as {value}, and the "
                f"unit is appropriate for the declared quantity, "
                f"but OCR confidence is low. Manual verification "
                f"is required."
            ),
            box=field.get("box") if isinstance(field, dict) else None
        )

    # --------------------------------------------------------
    # PASS
    # --------------------------------------------------------

    return create_result(
        rule_id=rule_id,
        status="PASS",
        value=value,
        confidence=confidence,
        reason=(
            f"Unit sale price {value} was detected. The declared "
            f"unit is appropriate for the declared net quantity "
            f"of {quantity_value}."
        ),
        box=field.get("box") if isinstance(field, dict) else None
    )


# ============================================================
# LOT / BATCH NUMBER
# ============================================================

def check_lot_number(data):

    field = get_field(data, "lot_number")

    if is_empty(field):

        return {
            "rule_id": "N/A",
            "rule_number": "N/A",
            "field": "lot_number",
            "name": "Lot / Batch number",
            "status": "NEEDS REVIEW",
            "value": None,
            "confidence": 0.0,
            "reason": "Lot/batch information was not detected.",
            "box": None,
            "source": "Extraction result"
        }

    value = get_value(field)
    confidence = get_confidence(field)

    if confidence < 0.70:

        status = "NEEDS REVIEW"
        reason = (
            "Lot/batch information was detected, but OCR "
            "confidence is low."
        )

    else:

        status = "PASS"
        reason = "Lot/batch information was detected."

    return {
        "rule_id": "N/A",
        "rule_number": "N/A",
        "field": "lot_number",
        "name": "Lot / Batch number",
        "status": status,
        "value": value,
        "confidence": confidence,
        "reason": reason,
        "box": field.get("box") if isinstance(field, dict) else None,
        "source": "Extraction result"
    }


# ============================================================
# OVERALL STATUS
# ============================================================

def calculate_overall_status(results):

    statuses = [
        result.get("status")
        for result in results
    ]

    if "FAIL" in statuses:
        return "NON-COMPLIANT"

    if "NEEDS REVIEW" in statuses:
        return "NEEDS REVIEW"

    return "COMPLIANT"


# ============================================================
# MAIN COMPLIANCE CHECK
# ============================================================

def run_compliance_check(
    extracted_data,
    unit_sale_price_required=True
):
    """
    Run all configured compliance checks.

    unit_sale_price_required=True is used for the current
    packaged-food test case.

    Applicability exceptions can be made more sophisticated
    later using product-category rules.
    """

    results = []

    # --------------------------------------------------------
    # Rule checks
    # --------------------------------------------------------

    results.append(
        check_product_name(extracted_data)
    )

    results.append(
        check_net_quantity(extracted_data)
    )

    results.append(
        check_mrp(extracted_data)
    )

    results.append(
        check_responsible_entity(extracted_data)
    )

    results.append(
        check_packed_date(extracted_data)
    )

    results.append(
        check_use_by_date(extracted_data)
    )

    results.append(
        check_country_of_origin(extracted_data)
    )

    results.append(
        check_customer_care(extracted_data)
    )

    results.append(
        check_dimensions(extracted_data)
    )

    # --------------------------------------------------------
    # STEP 5
    # Unit sale price
    # --------------------------------------------------------

    results.append(
        check_unit_sale_price(
            extracted_data,
            required=unit_sale_price_required
        )
    )

    # --------------------------------------------------------
    # Additional extracted information
    # --------------------------------------------------------

    results.append(
        check_marketed_by(extracted_data)
    )

    results.append(
        check_lot_number(extracted_data)
    )

    # --------------------------------------------------------
    # Overall status
    # --------------------------------------------------------

    overall_status = calculate_overall_status(results)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    passed = sum(
        1 for r in results
        if r.get("status") == "PASS"
    )

    failed = sum(
        1 for r in results
        if r.get("status") == "FAIL"
    )

    needs_review = sum(
        1 for r in results
        if r.get("status") == "NEEDS REVIEW"
    )

    not_applicable = sum(
        1 for r in results
        if r.get("status") == "NOT APPLICABLE"
    )

    report = {
        "generated_at": datetime.now().isoformat(),

        "rule_database": {
            "database_name": RULE_DATABASE.get(
                "database_name"
            ),
            "version": RULE_DATABASE.get(
                "version"
            ),
            "last_updated": RULE_DATABASE.get(
                "last_updated"
            )
        },

        "overall_status": overall_status,

        "summary": {
            "total_checks": len(results),
            "passed": passed,
            "failed": failed,
            "needs_review": needs_review,
            "not_applicable": not_applicable
        },

        "results": results
    }

    return report


# ============================================================
# PRINT REPORT
# ============================================================

def print_report(report):

    print()
    print("=" * 40)
    print("LEGAL METROLOGY COMPLIANCE CHECK")
    print("=" * 40)

    database = report.get("rule_database", {})

    print()
    print("Rule database:")
    print(database.get("database_name"))

    print("Version:", database.get("version"))
    print("Last updated:", database.get("last_updated"))

    print()
    print("=" * 40)
    print(
        "OVERALL STATUS:",
        report.get("overall_status")
    )
    print("=" * 40)

    for result in report.get("results", []):

        print()
        print(result.get("field"))

        print(
            "  Rule ID     :",
            result.get("rule_id")
        )

        print(
            "  Rule Number :",
            result.get("rule_number")
        )

        print(
            "  Status      :",
            result.get("status")
        )

        print(
            "  Value       :",
            result.get("value")
        )

        print(
            "  Confidence  :",
            result.get("confidence")
        )

        print(
            "  Reason      :",
            result.get("reason")
        )

    summary = report.get("summary", {})

    print()
    print("=" * 40)
    print("SUMMARY")
    print("=" * 40)

    print(
        "Total checks   :",
        summary.get("total_checks")
    )

    print(
        "Passed         :",
        summary.get("passed")
    )

    print(
        "Failed         :",
        summary.get("failed")
    )

    print(
        "Needs review   :",
        summary.get("needs_review")
    )

    print(
        "Not applicable :",
        summary.get("not_applicable")
    )

    print()
    print(
        "Output file:",
        REPORT_FILE
    )


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(report):

    try:

        with open(
            REPORT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as error:

        print(
            "ERROR: Could not save compliance report:",
            error
        )

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 40)
    print("LEGAL METROLOGY COMPLIANCE CHECK")
    print("=" * 40)

    # --------------------------------------------------------
    # Load extracted product data
    # --------------------------------------------------------

    try:

        with open(
            EXTRACTED_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            extracted_data = json.load(file)

    except FileNotFoundError:

        print()
        print(
            "ERROR: extracted_product.json was not found."
        )

        print(
            "Run the extraction program before running "
            "the compliance checker."
        )

        return

    except json.JSONDecodeError:

        print()
        print(
            "ERROR: extracted_product.json contains invalid JSON."
        )

        return

    # --------------------------------------------------------
    # Run compliance check
    # --------------------------------------------------------

    report = run_compliance_check(
        extracted_data,
        unit_sale_price_required=True
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_report(report)

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print_report(report)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()