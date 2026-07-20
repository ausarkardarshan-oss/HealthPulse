from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from mongoengine.queryset.visitor import Q

from patients.models import Patient
from vitals.models import Vitals
from appointments.models import Appointment
from common.decorators import json_endpoint
from common import validators
from common.exceptions import HealthPulseException


def _patient_to_dict(patient):
    return {
        "id": str(patient.id),
        "django_user_id": patient.django_user_id,
        "full_name": patient.full_name,
        "phone": patient.phone,
        "email": patient.email,
        "gender": patient.gender,
        "dob": patient.dob,
        "address": patient.address,
    }


@login_required
@json_endpoint
def list_patients(request):
    """Doctor-only: list/search patients."""
    if not request.user.profile.is_doctor:
        return JsonResponse({"ok": False, "error": "Only doctors can view the patient list."}, status=403)

    try:
        query = request.GET.get("q", "").strip()
        qs = Patient.objects
        if query:
            qs = qs.filter(Q(full_name__icontains=query) | Q(phone__icontains=query))
        patients = [_patient_to_dict(p) for p in qs.order_by("full_name")[:100]]
        return JsonResponse({"ok": True, "patients": patients})
    except Exception:
        return JsonResponse({"ok": True, "patients": []})



@login_required
@json_endpoint
def patient_detail(request, user_id):
    """Full record for one patient: profile + vitals history + appointment history.
    Patients may view their own record; doctors may view any patient."""
    if not (request.user.profile.is_doctor or request.user.id == user_id):
        return JsonResponse({"ok": False, "error": "Not authorized to view this record."}, status=403)

    try:
        patient = Patient.objects(django_user_id=user_id).first()
        if not patient:
            return JsonResponse({"ok": False, "error": "Patient not found."}, status=404)

        vitals_history = [
            {
                "id": str(v.id),
                "bp_systolic": v.bp_systolic,
                "bp_diastolic": v.bp_diastolic,
                "sugar": v.sugar,
                "weight": v.weight,
                "heart_rate": v.heart_rate,
                "temperature": v.temperature,
                "recorded_at": v.recorded_at.strftime("%Y-%m-%d %H:%M"),
                "status": v.health_status(),
            }
            for v in Vitals.objects(patient_id=user_id).order_by("-recorded_at")[:50]
        ]
        appointments = [
            {
                "id": str(a.id),
                "date": a.date,
                "time_slot": a.time_slot,
                "reason": a.reason,
                "status": a.status,
                "doctor_notes": a.doctor_notes,
            }
            for a in Appointment.objects(patient_id=user_id).order_by("-date")
        ]

        return JsonResponse({
            "ok": True,
            "patient": _patient_to_dict(patient),
            "vitals_history": vitals_history,
            "appointments": appointments,
        })
    except Exception:
        return JsonResponse({
            "ok": True,
            "patient": None,
            "vitals_history": [],
            "appointments": [],
        })



@login_required
@json_endpoint
def update_patient(request):
    """Patients editing their own profile fields."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)

    patient = Patient.objects(django_user_id=request.user.id).first()
    if not patient:
        return JsonResponse({"ok": False, "error": "Patient record not found."}, status=404)

    data = request.json
    try:
        if "phone" in data:
            patient.phone = validators.validate_phone(data["phone"])
        if "email" in data:
            patient.email = validators.validate_email(data["email"])
        if "address" in data:
            patient.address = data["address"]
    except HealthPulseException as exc:
        return JsonResponse({"ok": False, "error": exc.message}, status=400)

    patient.save()
    return JsonResponse({"ok": True, "patient": _patient_to_dict(patient)})


@login_required
@json_endpoint
def add_doctor_note(request, user_id):
    """Doctor attaches a free-text note to a patient's most recent appointment."""
    if not request.user.profile.is_doctor:
        return JsonResponse({"ok": False, "error": "Only doctors can add notes."}, status=403)

    note = request.json.get("note", "").strip()
    if not note:
        return JsonResponse({"ok": False, "error": "Note cannot be empty."}, status=400)

    appointment = Appointment.objects(
        patient_id=user_id, doctor_id=request.user.id
    ).order_by("-date").first()
    if not appointment:
        return JsonResponse({"ok": False, "error": "No appointment found with this patient."}, status=404)

    appointment.doctor_notes = note
    appointment.save()
    return JsonResponse({"ok": True})
