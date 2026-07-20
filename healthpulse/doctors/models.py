from datetime import datetime
from mongoengine import Document, StringField, IntField, DateTimeField, EmailField, ListField


class Doctor(Document):
    django_user_id = IntField(required=True, unique=True)
    full_name = StringField(required=True, max_length=120)
    email = EmailField(required=True)
    phone = StringField(required=True, max_length=10)
    specialization = StringField(default="General Physician", max_length=120)
    # Simple weekly availability, e.g. ["09:00 AM", "09:30 AM", ...]
    working_hours = ListField(StringField(), default=lambda: [
        "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
        "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM",
    ])
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "doctors",
        "indexes": ["django_user_id", "full_name", "specialization"],
    }

    def __str__(self):
        return f"Dr. {self.full_name} ({self.specialization})"
