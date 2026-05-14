"""
backend/app/services/llm/prompts.py
LLM prompt templates — now domain-aware.
Replace your existing prompts.py with this file.
"""

from typing import Dict, Any, List


# ─── Domain context injected into every extraction prompt ────────────────────

DOMAIN_CONTEXT = {
    "general": {
        "description": "a general-purpose dataset",
        "hints": [
            "Check for missing values and suggest appropriate fill strategies",
            "Flag obvious outliers in numeric columns",
            "Standardize inconsistent string formatting",
        ],
        "examples": "e.g. trim whitespace, fix casing, remove duplicates",
    },
    "healthcare": {
        "description": "a healthcare/medical dataset",
        "hints": [
            "Patient ages should be between 0 and 100",
            "Blood pressure systolic: 60–250, diastolic: 40–150",
            "BMI should be between 10 and 80",
            "Heart rate should be between 30 and 250 bpm",
            "ICD codes must follow valid format (e.g. A00.0–Z99.9)",
            "Dates of birth must be in the past, admission before discharge",
            "Flag negative lab values that cannot be negative (e.g. WBC count)",
            "Gender values should be standardized to Male/Female/Other/Unknown",
        ],
        "examples": "e.g. negative age, invalid ICD code, future birth date, impossible vitals",
    },
    "finance": {
        "description": "a financial/banking dataset",
        "hints": [
            "Account balances can be negative (overdraft) but flag extreme outliers",
            "Transaction amounts: flag unusually large single transactions",
            "Interest rates should typically be between 0% and 100%",
            "Credit scores typically range from 300 to 850",
            "Dates: transaction date must not be in the future",
            "Currency codes should be valid ISO 4217 (USD, EUR, GBP, etc.)",
            "Flag duplicate transaction IDs",
            "Loan amounts should be positive",
        ],
        "examples": "e.g. future transaction date, invalid currency code, duplicate transaction ID",
    },
    "hr": {
        "description": "a human resources/employee dataset",
        "hints": [
            "Employee age should be between 16 and 80",
            "Salary should be positive; flag extreme outliers per job level",
            "Hire date must be in the past and after employee birth date",
            "Department names should be standardized (e.g. 'IT' vs 'Information Technology')",
            "Performance ratings should be within defined scale (e.g. 1–5)",
            "Employee ID should be unique and non-null",
            "Years of experience cannot exceed (current year - hire year)",
            "Termination date must be after hire date",
        ],
        "examples": "e.g. salary of 0, hire date in future, duplicate employee ID",
    },
    "ecommerce": {
        "description": "an e-commerce/retail dataset",
        "hints": [
            "Product prices must be positive",
            "Quantity ordered should be a positive integer",
            "Discount percentage should be between 0% and 100%",
            "Order date must be before shipping date, which must be before delivery date",
            "Customer ratings should be between 1 and 5",
            "Stock quantity cannot be negative",
            "SKU/product codes should follow consistent format",
            "Email addresses should be valid format",
        ],
        "examples": "e.g. negative price, discount > 100%, shipping before order date",
    },
    "education": {
        "description": "an educational/academic dataset",
        "hints": [
            "Student grades should be within defined scale (e.g. 0–100 or A–F)",
            "Enrollment date must be before graduation date",
            "Student age for K-12: 5–19, university: 16–70",
            "GPA should be between 0.0 and 4.0 (or 0–5 depending on system)",
            "Attendance percentage should be between 0% and 100%",
            "Course codes should follow consistent format",
            "Standardize grade values (e.g. 'A' vs 'a' vs 'Excellent')",
        ],
        "examples": "e.g. GPA above 4.0, grade date before enrollment, attendance over 100%",
    },
    "logistics": {
        "description": "a logistics/supply chain dataset",
        "hints": [
            "Weight and volume must be positive",
            "Delivery date must be after pickup/shipment date",
            "Coordinates (lat/lon) must be within valid ranges: lat -90 to 90, lon -180 to 180",
            "Distance must be positive",
            "Vehicle capacity cannot be exceeded by load weight",
            "Tracking numbers should follow consistent format",
            "Zip/postal codes should be valid for the given country",
            "Flag shipments with unusually long delivery times",
        ],
        "examples": "e.g. negative weight, delivery before pickup, invalid coordinates",
    },
}


# ─── Main extraction prompt ───────────────────────────────────────────────────

def build_rule_extraction_prompt(
    profile_summary: Dict[str, Any],
    feedback_examples: List[Dict[str, Any]] | None = None,
    domain: str = "general",
) -> str:
    """Build a domain-aware prompt for LLM-based rule extraction."""

    ctx = DOMAIN_CONTEXT.get(domain, DOMAIN_CONTEXT["general"])

    hints_text = "\n".join(f"  - {h}" for h in ctx["hints"])

    prompt = f"""You are a data quality expert specializing in {ctx["description"]}.
Analyze the dataset profile below and extract specific, actionable data cleaning rules.

Dataset Profile:
{profile_summary}

Domain: {domain.upper()}
Domain-specific rules to consider:
{hints_text}

Focus on ({ctx["examples"]}).

Extract rules that:
1. Identify real data quality issues visible in the profile
2. Are specific to this domain's constraints
3. Suggest concrete cleaning actions
4. Have measurable confidence based on the data

Return a JSON array of rules. Each rule must have:
- predicate: machine-readable condition (e.g. "range(age, min=0, max=130)")
- action: cleaning action (e.g. "clip", "drop", "standardize", "flag", "fill_median")
- confidence: float 0.0–1.0
- explanation: clear human-readable description
- targets: {{"columns": ["column_name"]}}
- category: one of [range, categorical, regex, missing, uniqueness, standardization, anomaly]

"""

    if feedback_examples:
        prompt += f"\nPrevious user-approved rules for similar data (use as reference):\n{feedback_examples}\n"

    prompt += "\nReturn ONLY a valid JSON array. No explanation, no markdown, no extra text."
    return prompt


# ─── Column mapping prompt ────────────────────────────────────────────────────

def build_column_mapping_prompt(
    column_name: str,
    column_analysis: Dict[str, Any],
    canonical_concepts: List[str],
    domain: str = "general",
) -> str:
    """Build prompt for LLM-based column mapping."""
    ctx = DOMAIN_CONTEXT.get(domain, DOMAIN_CONTEXT["general"])
    return f"""Map this column from {ctx["description"]} to a canonical concept.

Column: {column_name}
Analysis: {column_analysis}
Domain: {domain}
Available Concepts: {canonical_concepts}

Return JSON with: concept, confidence (0.0-1.0), and explanation.
Return ONLY valid JSON, no other text."""


# ─── Feedback incorporation prompt ───────────────────────────────────────────

def build_feedback_incorporation_prompt(
    rule: Dict[str, Any],
    feedback_text: str,
    feedback_examples: List[Dict[str, Any]] | None = None,
) -> str:
    """Build prompt for incorporating user feedback into rules."""
    prompt = f"""A user provided feedback on this data cleaning rule:

Rule: {rule}
Feedback: {feedback_text}

Update the rule to incorporate this feedback. Return the improved rule as JSON
with the same fields (predicate, action, confidence, explanation, targets, category).
Return ONLY valid JSON."""

    if feedback_examples:
        prompt += f"\n\nSimilar feedback examples for reference:\n{feedback_examples}"

    return prompt
