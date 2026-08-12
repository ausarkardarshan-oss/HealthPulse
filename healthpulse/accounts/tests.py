from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase


class RegistrationMongoFallbackTests(TestCase):
    def test_patient_registration_succeeds_when_mongo_is_unavailable(self):
        payload = {
            "role": "patient",
            "full_name": "Alice Example",
            "username": "alice",
            "email": "alice@example.com",
            "phone": "9876543210",
            "aadhaar": "123456789012",
            "gender": "F",
            "dob": "1997-05-15",
            "address": "Demo address",
            "password": "strongpass123",
            "confirm_password": "strongpass123",
        }

        with patch("accounts.views.Patient.save", side_effect=Exception("Mongo unavailable")):
            response = self.client.post("/accounts/register/", payload)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username="alice").exists())
