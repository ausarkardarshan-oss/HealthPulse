from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from doctors.models import Doctor
from patients.models import Patient
from appointments.models import Appointment
from common.decorators import json_endpoint


@login_required
@json_endpoint
def list_doctors(request):
    try:
        doctors = [
            {
                "django_user_id": d.django_user_id,
                "full_name": d.full_name,
                "specialization": d.specialization,
                "working_hours": d.working_hours,
            }
            for d in Doctor.objects.order_by("full_name")
        ]
        return JsonResponse({"ok": True, "doctors": doctors})
    except Exception:
        return JsonResponse({"ok": True, "doctors": []})



@login_required
@json_endpoint
def doctor_appointments(request):
    """Doctor-only: appointments filtered by status (upcoming/completed/cancelled)."""
    if not request.user.profile.is_doctor:
        return JsonResponse({"ok": False, "error": "Doctors only."}, status=403)

    status = request.GET.get("status", "upcoming")
    qs = Appointment.objects(doctor_id=request.user.id)
    if status != "all":
        qs = qs.filter(status=status)

    results = []
    for a in qs.order_by("date", "time_slot"):
        patient = Patient.objects(django_user_id=a.patient_id).first()
        results.append({
            "id": str(a.id),
            "patient_name": patient.full_name if patient else "Unknown",
            "patient_id": a.patient_id,
            "date": a.date,
            "time_slot": a.time_slot,
            "reason": a.reason,
            "status": a.status,
        })
    return JsonResponse({"ok": True, "appointments": results})
