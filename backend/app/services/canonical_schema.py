"""
Canonical Financial Schema Definition.

Defines semantic concepts for financial data, independent of column names.
This allows rules to be schema-agnostic and reusable across datasets.
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class CanonicalFinancialConcept(str, Enum):
    """Canonical concepts for financial/transaction data."""
    
    # Transaction Identifiers
    TRANSACTION_ID = "transaction_id"
    PAYMENT_ID = "payment_id"
    REFERENCE_NUMBER = "reference_number"
    ORDER_ID = "order_id"
    
    # Account Information
    ACCOUNT_NUMBER = "account_number"
    ACCOUNT_ID = "account_id"
    ACCOUNT_TYPE = "account_type"
    ACCOUNT_BALANCE = "account_balance"
    ACCOUNT_HOLDER = "account_holder"
    
    # Transaction Details
    TRANSACTION_DATE = "transaction_date"
    TRANSACTION_TIME = "transaction_time"
    TRANSACTION_TYPE = "transaction_type"
    TRANSACTION_STATUS = "transaction_status"
    TRANSACTION_AMOUNT = "transaction_amount"
    TRANSACTION_CURRENCY = "transaction_currency"
    DEBIT_CREDIT = "debit_credit"
    
    # Merchant/Vendor Information
    MERCHANT_NAME = "merchant_name"
    MERCHANT_ID = "merchant_id"
    MERCHANT_CATEGORY = "merchant_category"
    MERCHANT_DESCRIPTION = "merchant_description"
    
    # Payment Information
    PAYMENT_METHOD = "payment_method"
    PAYMENT_DESCRIPTION = "payment_description"
    PAYMENT_NARRATIVE = "payment_narrative"
    PAYMENT_STATUS = "payment_status"
    
    # Customer Information
    CUSTOMER_ID = "customer_id"
    CUSTOMER_NAME = "customer_name"
    CUSTOMER_EMAIL = "customer_email"
    CUSTOMER_PHONE = "customer_phone"
    CUSTOMER_ADDRESS = "customer_address"
    
    # Location Information
    COUNTRY = "country"
    STATE = "state"
    CITY = "city"
    ZIP_CODE = "zip_code"
    
    # Additional Metadata
    NOTES = "notes"
    TAGS = "tags"
    CATEGORY = "category"
    SUBCATEGORY = "subcategory"


# Canonical schema metadata
CANONICAL_SCHEMA: Dict[str, Dict[str, Any]] = {
    CanonicalFinancialConcept.TRANSACTION_ID.value: {
        "description": "Unique identifier for a transaction",
        "data_type": "string",
        "patterns": ["transaction", "txn", "tx_id", "payment_id", "reference"],
        "validation": "alphanumeric, 8-30 characters",
        "examples": ["TXN-2024-12345", "1234567890", "PAY-ABC-123"]
    },
    CanonicalFinancialConcept.ACCOUNT_NUMBER.value: {
        "description": "Bank account number",
        "data_type": "numeric_string",
        "patterns": ["account", "acct", "account_number", "account_no"],
        "validation": "8-16 digits",
        "examples": ["12345678", "9876543210123456"]
    },
    CanonicalFinancialConcept.TRANSACTION_AMOUNT.value: {
        "description": "Transaction amount (can be positive or negative)",
        "data_type": "numeric",
        "patterns": ["amount", "value", "balance", "total", "sum"],
        "validation": "numeric, typically -$100M to $100M",
        "examples": [100.50, -25.00, 1000.00]
    },
    CanonicalFinancialConcept.MERCHANT_NAME.value: {
        "description": "Name of merchant/vendor",
        "data_type": "string",
        "patterns": ["merchant", "vendor", "payee", "recipient"],
        "validation": "text, typically 1-200 characters",
        "examples": ["AMAZON", "Starbucks", "WALMART"]
    },
    CanonicalFinancialConcept.MERCHANT_DESCRIPTION.value: {
        "description": "Description of merchant transaction",
        "data_type": "string",
        "patterns": ["description", "merchant_description", "transaction_description"],
        "validation": "text, typically 1-500 characters",
        "examples": ["AMAZON.COM PURCHASE", "STARBUCKS STORE #123"]
    },
    CanonicalFinancialConcept.PAYMENT_NARRATIVE.value: {
        "description": "Payment narrative or notes",
        "data_type": "string",
        "patterns": ["narrative", "payment_narrative", "notes", "memo", "remarks"],
        "validation": "text, variable length",
        "examples": ["Payment for services", "Monthly subscription"]
    },
    CanonicalFinancialConcept.TRANSACTION_TYPE.value: {
        "description": "Type of transaction",
        "data_type": "categorical",
        "patterns": ["transaction_type", "type", "category", "transaction_category"],
        "validation": "categorical values",
        "examples": ["DEBIT", "CREDIT", "PURCHASE", "TRANSFER"]
    },
    CanonicalFinancialConcept.DEBIT_CREDIT.value: {
        "description": "Debit or credit indicator",
        "data_type": "categorical",
        "patterns": ["debit", "credit", "debit_credit", "direction"],
        "validation": "DEBIT/CREDIT/D/C/DR/CR",
        "examples": ["DEBIT", "CREDIT", "D", "C"]
    },
    CanonicalFinancialConcept.TRANSACTION_DATE.value: {
        "description": "Transaction date",
        "data_type": "date",
        "patterns": ["date", "transaction_date", "timestamp", "posted", "settled"],
        "validation": "valid date format",
        "examples": ["2024-01-15", "01/15/2024"]
    },
    CanonicalFinancialConcept.ACCOUNT_TYPE.value: {
        "description": "Type of account",
        "data_type": "categorical",
        "patterns": ["account_type", "account_category", "account_class"],
        "validation": "CHECKING/SAVINGS/CREDIT/etc",
        "examples": ["CHECKING", "SAVINGS", "CREDIT"]
    },
    CanonicalFinancialConcept.CUSTOMER_EMAIL.value: {
        "description": "Customer email address",
        "data_type": "string",
        "patterns": ["email", "customer_email", "user_email", "contact_email"],
        "validation": "valid email format",
        "examples": ["customer@example.com"]
    },
    CanonicalFinancialConcept.CUSTOMER_PHONE.value: {
        "description": "Customer phone number",
        "data_type": "string",
        "patterns": ["phone", "customer_phone", "contact_phone", "mobile"],
        "validation": "valid phone format",
        "examples": ["+1-555-123-4567", "5551234567"]
    },
}


def get_canonical_concepts() -> List[str]:
    """Get list of all canonical concept names."""
    return [concept.value for concept in CanonicalFinancialConcept]


def get_concept_metadata(concept: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a canonical concept."""
    return CANONICAL_SCHEMA.get(concept)


def find_matching_concepts(column_name: str, sample_values: List[Any] = None) -> List[Dict[str, Any]]:
    """
    Find canonical concepts that might match a column.
    Uses heuristics based on column name patterns.
    """
    column_lower = column_name.lower()
    matches = []
    
    for concept, metadata in CANONICAL_SCHEMA.items():
        # Check if column name matches any pattern
        for pattern in metadata.get("patterns", []):
            if pattern in column_lower:
                confidence = 0.7  # Base confidence from name match
                
                # Increase confidence if sample values validate
                if sample_values:
                    confidence = validate_concept_with_samples(concept, sample_values, confidence)
                
                matches.append({
                    "concept": concept,
                    "confidence": confidence,
                    "reason": f"Column name matches pattern '{pattern}'",
                    "metadata": metadata
                })
                break  # Only add once per concept
    
    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return matches


def validate_concept_with_samples(concept: str, sample_values: List[Any], base_confidence: float) -> float:
    """Validate concept match using sample values."""
    import re
    import pandas as pd
    
    metadata = CANONICAL_SCHEMA.get(concept)
    if not metadata:
        return base_confidence
    
    validation = metadata.get("validation", "")
    data_type = metadata.get("data_type", "")
    
    # Check data type matches
    if data_type == "numeric":
        try:
            numeric_count = sum(1 for v in sample_values[:10] if pd.api.types.is_number(v) or (isinstance(v, str) and v.replace('.', '').replace('-', '').isdigit()))
            if numeric_count / min(len(sample_values), 10) > 0.8:
                base_confidence += 0.1
        except:
            pass
    
    elif data_type == "date":
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # ISO
            r'\d{2}/\d{2}/\d{4}',  # US
            r'\d{2}\.\d{2}\.\d{4}',  # EU
        ]
        date_count = sum(1 for v in sample_values[:10] if any(re.match(p, str(v)) for p in date_patterns))
        if date_count / min(len(sample_values), 10) > 0.7:
            base_confidence += 0.1
    
    elif data_type == "categorical":
        unique_ratio = len(set(sample_values[:20])) / min(len(sample_values), 20)
        if unique_ratio < 0.5:  # Few unique values = likely categorical
            base_confidence += 0.1
    
    # Check validation patterns
    if "email" in validation.lower():
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        email_count = sum(1 for v in sample_values[:10] if re.match(email_pattern, str(v)))
        if email_count / min(len(sample_values), 10) > 0.7:
            base_confidence += 0.15
    
    if "phone" in validation.lower():
        phone_pattern = r'^\+?[\d\s\-\(\)]+$'
        phone_count = sum(1 for v in sample_values[:10] if re.match(phone_pattern, str(v)))
        if phone_count / min(len(sample_values), 10) > 0.7:
            base_confidence += 0.15
    
    return min(base_confidence, 0.95)  # Cap at 0.95








