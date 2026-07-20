from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """
    Extends Django's built-in User with a role. Lives in SQLite alongside
    User/Session since it's part of the auth story, not clinical data.
    Clinical/domain data (Patient, Doctor, Vitals, ...) lives in MongoDB
    and links back here via `django_user_id`.
    """

    ROLE_PATIENT = "patient"
    ROLE_DOCTOR = "doctor"
    ROLE_CHOICES = [
        (ROLE_PATIENT, "Patient"),
        (ROLE_DOCTOR, "Doctor"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_PATIENT)
    phone = models.CharField(max_length=15, blank=True)
    dark_mode = models.BooleanField(default=False)
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_doctor(self):
        return self.role == self.ROLE_DOCTOR

    @property
    def is_patient(self):
        return self.role == self.ROLE_PATIENT
