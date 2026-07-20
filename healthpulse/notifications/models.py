from datetime import datetime
from mongoengine import Document, IntField, StringField, BooleanField, DateTimeField


class Notification(Document):
    CATEGORY_CHOICES = [
        "appointment_booked", "appointment_cancelled", "appointment_rescheduled",
        "reminder", "vitals_updated", "doctor_message",
    ]

    user_id = IntField(required=True)  # Profile/User id of the recipient
    title = StringField(required=True, max_length=140)
    message = StringField(required=True)
    category = StringField(choices=CATEGORY_CHOICES, default="reminder")
    is_read = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "notifications",
        "indexes": ["user_id", "-created_at"],
        "ordering": ["-created_at"],
    }
