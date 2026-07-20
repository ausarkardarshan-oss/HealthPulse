from datetime import datetime
from mongoengine import Document, IntField, StringField, DateTimeField


class Appointment(Document):
    STATUS_CHOICES = ["upcoming", "completed", "cancelled"]

    patient_id = IntField(required=True)   # Patient.django_user_id
    doctor_id = IntField(required=True)    # Doctor.django_user_id
    date = StringField(required=True)      # YYYY-MM-DD
    time_slot = StringField(required=True)  # e.g. "10:00 AM"
    reason = StringField(default="")
    status = StringField(choices=STATUS_CHOICES, default="upcoming")
    doctor_notes = StringField(default="")
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "appointments",
        "indexes": [
            "patient_id",
            "doctor_id",
            {"fields": ["doctor_id", "date", "time_slot"]},
        ],
        "ordering": ["date", "time_slot"],
    }
