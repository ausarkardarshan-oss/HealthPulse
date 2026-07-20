"""
Custom exceptions for HealthPulse.

Views catch these and turn them into friendly JSON error messages
(see common.views_helpers.json_error) instead of letting a raw
traceback / 500 page reach the user.
"""


class HealthPulseException(Exception):
    """Base class for all domain-specific HealthPulse errors."""
    default_message = "Something went wrong. Please try again."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class InvalidAadhaarException(HealthPulseException):
    default_message = "Aadhaar number must be exactly 12 digits."


class InvalidPhoneException(HealthPulseException):
    default_message = "Enter a valid 10-digit Indian mobile number."


class InvalidEmailException(HealthPulseException):
    default_message = "Enter a valid email address."


class InvalidDateException(HealthPulseException):
    default_message = "Date must be in YYYY-MM-DD format."


class InvalidVitalsException(HealthPulseException):
    default_message = "One or more vitals values are out of a plausible range."


class DuplicateAppointmentException(HealthPulseException):
    default_message = "This slot is already booked."


class AppointmentTransactionError(HealthPulseException):
    default_message = "Could not complete the booking. The transaction was rolled back."
