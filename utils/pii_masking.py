"""PII masking and sensitive data protection."""

from __future__ import annotations

import re
from typing import Any

PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("ssn_no_dash", re.compile(r"\b\d{9}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("phone", re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
    ("account_number", re.compile(r"\bACCT[-\s]?\d{8,16}\b", re.IGNORECASE)),
    ("member_id", re.compile(r"\bMEMB[-\s]?\d{6,12}\b", re.IGNORECASE)),
    ("policy_number", re.compile(r"\bPOL[-\s]?\d{6,12}\b", re.IGNORECASE)),
]

SENSITIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("password", re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+")),
    ("api_key", re.compile(r"(?i)(api[_-]?key|secret|token)\s*[=:]\s*\S+")),
    ("racf_password", re.compile(r"(?i)PASSCHK\s+\S+")),
]


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Mask PII in text and return masked text with detected field types."""
    masked_fields: list[str] = []
    result = text
    for field_type, pattern in PII_PATTERNS + SENSITIVE_PATTERNS:
        if pattern.search(result):
            masked_fields.append(field_type)
            result = pattern.sub(f"[MASKED_{field_type.upper()}]", result)
    return result, masked_fields


def mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask PII in dictionary values."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            masked, _ = mask_pii(value)
            result[key] = masked
        elif isinstance(value, dict):
            result[key] = mask_dict(value)
        elif isinstance(value, list):
            result[key] = [
                mask_pii(v)[0] if isinstance(v, str) else v for v in value
            ]
        else:
            result[key] = value
    return result
