from datetime import datetime
from mongoengine import Document, IntField, FloatField, DateTimeField


class Vitals(Document):
    patient_id = IntField(required=True)  # Patient.django_user_id
    bp_systolic = FloatField(null=True)
    bp_diastolic = FloatField(null=True)
    sugar = FloatField(null=True)          # mg/dL
    weight = FloatField(null=True)         # kg
    heart_rate = FloatField(null=True)     # bpm
    temperature = FloatField(null=True)    # Celsius
    recorded_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "vitals",
        "indexes": ["patient_id", "-recorded_at"],
        "ordering": ["-recorded_at"],
    }

    def health_status(self):
        """Very rough traffic-light status based on the latest BP + sugar."""
        if self.bp_systolic and self.bp_systolic >= 140:
            return "warning"
        if self.sugar and self.sugar >= 180:
            return "warning"
        if self.bp_systolic and self.bp_systolic < 90:
            return "warning"
        return "normal"
