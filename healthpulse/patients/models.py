from datetime import datetime
from mongoengine import (
    Document, StringField, IntField, DateTimeField, EmailField,
)


class Patient(Document):
    """Clinical/profile record for a patient, stored in MongoDB."""

    django_user_id = IntField(required=True, unique=True)
    full_name = StringField(required=True, max_length=120)
    aadhaar = StringField(required=True, max_length=12)
    phone = StringField(required=True, max_length=10)
    email = EmailField(required=True)
    gender = StringField(choices=["M", "F", "O"], required=True)
    dob = StringField(required=True)  # YYYY-MM-DD
    address = StringField(default="")
    assigned_doctor_id = IntField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "patients",
        "indexes": ["django_user_id", "full_name", "phone"],
    }

    def __str__(self):
        return self.full_name
