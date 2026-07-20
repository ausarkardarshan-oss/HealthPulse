"""
Regex-based validators. Every function raises the matching custom
exception from common.exceptions on failure and returns the cleaned
value on success, so callers can do:

    phone = validate_phone(request.POST["phone"])
"""
import re
from datetime import datetime

from common.exceptions import (
    InvalidAadhaarException,
    InvalidPhoneException,
    InvalidEmailException,
    InvalidDateException,
    InvalidVitalsException,
)

AADHAAR_RE = re.compile(r"^\d{12}$")
# Indian mobile: optional +91 / 0 prefix, then a 10-digit number starting 6-9
PHONE_RE = re.compile(r"^(?:\+91|0)?[6-9]\d{9}$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_aadhaar(value: str) -> str:
    value = (value or "").strip()
    if not AADHAAR_RE.match(value):
        raise InvalidAadhaarException()
    return value


def validate_phone(value: str) -> str:
    value = (value or "").strip().replace(" ", "")
    if not PHONE_RE.match(value):
        raise InvalidPhoneException()
    return value[-10:]


def validate_email(value: str) -> str:
    value = (value or "").strip()
    if not EMAIL_RE.match(value):
        raise InvalidEmailException()
    return value


def validate_date(value: str) -> str:
    value = (value or "").strip()
    if not DATE_RE.match(value):
        raise InvalidDateException()
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise InvalidDateException("That date doesn't exist. Use YYYY-MM-DD.")
    return value


# Plausible physiological ranges used as a sanity check, not a diagnosis.
VITAL_RANGES = {
    "bp_systolic": (60, 260),
    "bp_diastolic": (30, 160),
    "sugar": (20, 600),        # mg/dL
    "weight": (1, 400),        # kg
    "heart_rate": (20, 250),   # bpm
    "temperature": (30, 45),   # Celsius
}


def validate_vitals(data: dict) -> dict:
    cleaned = {}
    for field, (low, high) in VITAL_RANGES.items():
        if field not in data or data[field] in (None, ""):
            continue
        try:
            num = float(data[field])
        except (TypeError, ValueError):
            raise InvalidVitalsException(f"{field.replace('_', ' ').title()} must be a number.")
        if not (low <= num <= high):
            raise InvalidVitalsException(
                f"{field.replace('_', ' ').title()} of {num} is outside the plausible range ({low}-{high})."
            )
        cleaned[field] = num
    return cleaned
