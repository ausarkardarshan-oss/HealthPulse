"""
Usage:
    python manage.py seed_data

Creates a handful of demo users so you can log in immediately:
  Doctors:  dr.mehta / password123   dr.rao / password123
  Patients: asha.k / password123     rahul.s / password123
"""
import random
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Profile
from patients.models import Patient
from doctors.models import Doctor
from vitals.models import Vitals
from appointments.models import Appointment


class Command(BaseCommand):
    help = "Seed demo doctors, patients, vitals, and appointments."

    def handle(self, *args, **options):
        self.stdout.write("Seeding HealthPulse demo data...")

        doctors_data = [
            dict(username="dr.mehta", full_name="Anjali Mehta", specialization="Cardiologist", phone="9812345601"),
            dict(username="dr.rao", full_name="Kiran Rao", specialization="General Physician", phone="9812345602"),
        ]
        patients_data = [
            dict(username="asha.k", full_name="Asha Kulkarni", phone="9812345001", gender="F", dob="1990-04-12"),
            dict(username="rahul.s", full_name="Rahul Sharma", phone="9812345002", gender="M", dob="1985-11-02"),
        ]

        doctor_users = []
        for d in doctors_data:
            user, created = User.objects.get_or_create(
                username=d["username"],
                defaults={"email": f"{d['username']}@healthpulse.demo", "first_name": d["full_name"].split()[0]},
            )
            if created:
                user.set_password("password123")
                user.save()
            profile = user.profile
            profile.role = Profile.ROLE_DOCTOR
            profile.phone = d["phone"]
            profile.save()

            Doctor.objects(django_user_id=user.id).delete()
            Doctor(
                django_user_id=user.id, full_name=d["full_name"], email=user.email,
                phone=d["phone"], specialization=d["specialization"],
            ).save()
            doctor_users.append(user)
            self.stdout.write(f"  Doctor ready: {d['username']} / password123")

        patient_users = []
        for p in patients_data:
            user, created = User.objects.get_or_create(
                username=p["username"],
                defaults={"email": f"{p['username']}@healthpulse.demo", "first_name": p["full_name"].split()[0]},
            )
            if created:
                user.set_password("password123")
                user.save()
            profile = user.profile
            profile.role = Profile.ROLE_PATIENT
            profile.phone = p["phone"]
            profile.save()

            Patient.objects(django_user_id=user.id).delete()
            Patient(
                django_user_id=user.id, full_name=p["full_name"], aadhaar=f"{random.randint(10**11, 10**12 - 1)}",
                phone=p["phone"], email=user.email, gender=p["gender"], dob=p["dob"],
                assigned_doctor_id=doctor_users[0].id,
            ).save()
            patient_users.append(user)
            self.stdout.write(f"  Patient ready: {p['username']} / password123")

        # Seed some vitals history for the first patient
        Vitals.objects(patient_id=patient_users[0].id).delete()
        for i in range(10, 0, -1):
            Vitals(
                patient_id=patient_users[0].id,
                bp_systolic=random.randint(110, 135),
                bp_diastolic=random.randint(70, 88),
                sugar=random.randint(85, 130),
                weight=round(random.uniform(60, 64), 1),
                heart_rate=random.randint(64, 84),
                temperature=round(random.uniform(36.4, 37.1), 1),
                recorded_at=datetime.utcnow() - timedelta(days=i * 3),
            ).save()

        # Seed one upcoming appointment
        Appointment.objects(patient_id=patient_users[0].id).delete()
        tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
        Appointment(
            patient_id=patient_users[0].id,
            doctor_id=doctor_users[0].id,
            date=tomorrow,
            time_slot="10:00 AM",
            reason="Routine checkup",
            status="upcoming",
        ).save()

        self.stdout.write(self.style.SUCCESS("Done. Log in with any of the accounts above."))
