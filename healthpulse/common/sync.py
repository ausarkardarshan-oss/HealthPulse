import logging
from accounts.models import Profile
from patients.models import Patient
from doctors.models import Doctor

logger = logging.getLogger(__name__)


def sync_profile_to_mongo(profile):
    """
    Syncs a single SQLite Profile instance to its corresponding MongoEngine
    Patient or Doctor document. Creates or updates the Mongo record.
    """
    if not profile or not profile.user:
        return None

    try:
        user = profile.user
        full_name = profile.full_name or user.get_full_name() or user.username
        email = profile.email or user.email or f"{user.username}@healthpulse.local"
        phone = profile.phone or "0000000000"

        if profile.is_doctor:
            doc = Doctor.objects(django_user_id=user.id).first()
            if not doc:
                doc = Doctor(
                    django_user_id=user.id,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    specialization=profile.specialization or "General Physician",
                )
            else:
                doc.full_name = full_name
                doc.email = email
                doc.phone = phone
                if profile.specialization:
                    doc.specialization = profile.specialization
            doc.save()
            return doc
        else:
            pat = Patient.objects(django_user_id=user.id).first()
            aadhaar = profile.aadhaar or "000000000000"
            gender = profile.gender or "M"
            dob = profile.dob or "1990-01-01"
            address = profile.address or ""
            assigned_doc_id = profile.assigned_doctor_id

            if not pat:
                pat = Patient(
                    django_user_id=user.id,
                    full_name=full_name,
                    aadhaar=aadhaar,
                    phone=phone,
                    email=email,
                    gender=gender,
                    dob=dob,
                    address=address,
                    assigned_doctor_id=assigned_doc_id,
                )
            else:
                pat.full_name = full_name
                pat.phone = phone
                pat.email = email
                if profile.aadhaar:
                    pat.aadhaar = profile.aadhaar
                if profile.gender:
                    pat.gender = profile.gender
                if profile.dob:
                    pat.dob = profile.dob
                if profile.address:
                    pat.address = profile.address
                if profile.assigned_doctor_id:
                    pat.assigned_doctor_id = profile.assigned_doctor_id
            pat.save()
            return pat
    except Exception as exc:
        logger.warning("Failed to sync profile %s to MongoEngine: %s", profile, exc)
        return None


def sync_all_profiles_to_mongo():
    """
    Called on app startup to ensure all existing SQLite profiles have
    corresponding MongoEngine documents even after process restart.
    """
    try:
        profiles = Profile.objects.select_related("user").all()
        for p in profiles:
            sync_profile_to_mongo(p)
        logger.info("Successfully synced %d profiles to MongoEngine.", len(profiles))
    except Exception as exc:
        logger.warning("Could not auto-sync profiles to MongoEngine: %s", exc)


def get_or_sync_patient(django_user_id):
    """
    Retrieves Patient MongoEngine document by django_user_id.
    If missing (e.g. server restart under mongomock), recreates it from SQLite Profile.
    """
    try:
        pat = Patient.objects(django_user_id=django_user_id).first()
        if not pat:
            prof = Profile.objects.filter(user_id=django_user_id).first()
            if prof and prof.is_patient:
                pat = sync_profile_to_mongo(prof)
        return pat
    except Exception:
        prof = Profile.objects.filter(user_id=django_user_id).first()
        if prof and prof.is_patient:
            return sync_profile_to_mongo(prof)
        return None


def get_or_sync_doctor(django_user_id):
    """
    Retrieves Doctor MongoEngine document by django_user_id.
    If missing (e.g. server restart under mongomock), recreates it from SQLite Profile.
    """
    try:
        doc = Doctor.objects(django_user_id=django_user_id).first()
        if not doc:
            prof = Profile.objects.filter(user_id=django_user_id).first()
            if prof and prof.is_doctor:
                doc = sync_profile_to_mongo(prof)
        return doc
    except Exception:
        prof = Profile.objects.filter(user_id=django_user_id).first()
        if prof and prof.is_doctor:
            return sync_profile_to_mongo(prof)
        return None
