from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from mongoengine.queryset.visitor import Q

from patients.models import Patient
from doctors.models import Doctor
from vitals.models import Vitals
from appointments.models import Appointment
from notifications.models import Notification
from common.decorators import json_endpoint


def _health_score(latest_vitals):
    """A simple, transparent 0-100 score from the latest reading. Not medical advice."""
    if not latest_vitals:
        return None
    score = 100
    if latest_vitals.bp_systolic:
        if latest_vitals.bp_systolic >= 140 or latest_vitals.bp_systolic < 90:
            score -= 20
    if latest_vitals.sugar:
        if latest_vitals.sugar >= 180 or latest_vitals.sugar < 70:
            score -= 20
    if latest_vitals.heart_rate:
        if latest_vitals.heart_rate > 100 or latest_vitals.heart_rate < 50:
            score -= 15
    if latest_vitals.temperature:
        if latest_vitals.temperature >= 38:
            score -= 15
    return max(score, 0)


@login_required
def dashboard(request):
    profile = request.user.profile
    context = {"profile": profile, "role": profile.role}

    # If MongoDB is down, keep the dashboard page from crashing.
    # The AJAX endpoints will also degrade gracefully.
    try:
        unread_count = Notification.objects(user_id=request.user.id, is_read=False).count()
    except Exception:
        unread_count = 0
    context["unread_count"] = unread_count


    if profile.is_patient:
        try:
            patient = Patient.objects(django_user_id=request.user.id).first()
            latest_vitals = Vitals.objects(patient_id=request.user.id).order_by("-recorded_at").first()
            upcoming = (
                Appointment.objects(patient_id=request.user.id, status="upcoming")
                .order_by("date", "time_slot")
                .first()
            )
            assigned_doctor = None
            if patient and patient.assigned_doctor_id:
                assigned_doctor = Doctor.objects(django_user_id=patient.assigned_doctor_id).first()
            elif upcoming:
                assigned_doctor = Doctor.objects(django_user_id=upcoming.doctor_id).first()

            context.update({
                "patient": patient,
                "latest_vitals": latest_vitals,
                "upcoming_appointment": upcoming,
                "assigned_doctor": assigned_doctor,
                "health_score": _health_score(latest_vitals),
                "doctors": Doctor.objects.order_by("full_name"),
            })
        except Exception:
            context.update({
                "patient": None,
                "latest_vitals": None,
                "upcoming_appointment": None,
                "assigned_doctor": None,
                "health_score": None,
                "doctors": [],
            })
    else:
        try:
            doctor = Doctor.objects(django_user_id=request.user.id).first()
            today = datetime.utcnow().strftime("%Y-%m-%d")
            context.update({
                "doctor": doctor,
                "total_patients": Patient.objects.count(),
                "todays_appointments": Appointment.objects(
                    doctor_id=request.user.id, date=today, status="upcoming"
                ).order_by("time_slot"),
                "pending_requests": Appointment.objects(
                    doctor_id=request.user.id, status="upcoming"
                ).count(),
            })
        except Exception:
            context.update({
                "doctor": None,
                "total_patients": 0,
                "todays_appointments": [],
                "pending_requests": 0,
            })


    return render(request, "dashboard.html", context)


@login_required
@json_endpoint
def global_search(request):
    """Search patients (name/phone), doctors (name/specialization) and
    appointments (date). Patients only see themselves in patient results;
    doctors see everyone."""
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"ok": True, "patients": [], "doctors": [], "appointments": []})

    patients_results = []
    if request.user.profile.is_doctor:
        matches = Patient.objects.filter(Q(full_name__icontains=query) | Q(phone__icontains=query))
        patients_results = [
            {"django_user_id": p.django_user_id, "full_name": p.full_name, "phone": p.phone}
            for p in matches[:10]
        ]

    doctors_results = [
        {"django_user_id": d.django_user_id, "full_name": d.full_name, "specialization": d.specialization}
        for d in Doctor.objects.filter(Q(full_name__icontains=query) | Q(specialization__icontains=query))[:10]
    ]

    appt_qs = Appointment.objects.filter(date__icontains=query)
    if request.user.profile.is_patient:
        appt_qs = appt_qs.filter(patient_id=request.user.id)
    else:
        appt_qs = appt_qs.filter(doctor_id=request.user.id)
    appointments_results = [
        {"id": str(a.id), "date": a.date, "time_slot": a.time_slot, "status": a.status}
        for a in appt_qs[:10]
    ]

    return JsonResponse({
        "ok": True,
        "patients": patients_results,
        "doctors": doctors_results,
        "appointments": appointments_results,
    })
