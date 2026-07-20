from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from appointments.models import Appointment
from appointments.reminders import schedule_reminders
from doctors.models import Doctor
from patients.models import Patient
from notifications.models import Notification
from common.decorators import json_endpoint
from common.validators import validate_date
from common.exceptions import (
    DuplicateAppointmentException,
    AppointmentTransactionError,
    HealthPulseException,
)


def _appt_to_dict(a, patient_name=None, doctor_name=None):
    return {
        "id": str(a.id),
        "patient_id": a.patient_id,
        "doctor_id": a.doctor_id,
        "patient_name": patient_name,
        "doctor_name": doctor_name,
        "date": a.date,
        "time_slot": a.time_slot,
        "reason": a.reason,
        "status": a.status,
        "doctor_notes": a.doctor_notes,
    }


@login_required
@json_endpoint
def check_slot(request):
    doctor_id = int(request.GET.get("doctor_id", 0))
    date = request.GET.get("date", "")
    validate_date(date)

    doctor = Doctor.objects(django_user_id=doctor_id).first()
    if not doctor:
        return JsonResponse({"ok": False, "error": "Doctor not found."}, status=404)

    taken = set(
        a.time_slot for a in Appointment.objects(
            doctor_id=doctor_id, date=date, status="upcoming"
        )
    )
    slots = [
        {"time": t, "available": t not in taken}
        for t in doctor.working_hours
    ]
    return JsonResponse({"ok": True, "slots": slots})


@login_required
@json_endpoint
def book_appointment(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    if not request.user.profile.is_patient:
        return JsonResponse({"ok": False, "error": "Only patients can book appointments."}, status=403)

    data = request.json
    doctor_id = int(data.get("doctor_id", 0))
    date = validate_date(data.get("date", ""))
    time_slot = data.get("time_slot", "").strip()
    reason = data.get("reason", "").strip()

    doctor = Doctor.objects(django_user_id=doctor_id).first()
    if not doctor:
        return JsonResponse({"ok": False, "error": "Doctor not found."}, status=404)
    if time_slot not in doctor.working_hours:
        return JsonResponse({"ok": False, "error": "That time slot doesn't exist for this doctor."}, status=400)

    # --- duplicate / availability check ---
    already_booked = Appointment.objects(
        doctor_id=doctor_id, date=date, time_slot=time_slot, status="upcoming"
    ).first()
    if already_booked:
        raise DuplicateAppointmentException()

    patient = Patient.objects(django_user_id=request.user.id).first()

    # --- "transaction": create appointment, then dependent records.
    # If anything after the initial save fails, delete the appointment
    # again so we don't leave an orphaned booking behind. ---
    appointment = Appointment(
        patient_id=request.user.id,
        doctor_id=doctor_id,
        date=date,
        time_slot=time_slot,
        reason=reason,
        status="upcoming",
    )
    try:
        appointment.save()

        # Re-check for a race condition (two requests booking the same slot
        # at the same time) - if we're not the earliest "upcoming" record
        # for this doctor/date/slot, someone beat us to it.
        clash = Appointment.objects(
            doctor_id=doctor_id, date=date, time_slot=time_slot, status="upcoming"
        ).order_by("created_at").first()
        if clash and str(clash.id) != str(appointment.id):
            raise DuplicateAppointmentException()

        Notification(
            user_id=request.user.id,
            title="Appointment booked",
            message=f"Your appointment with Dr. {doctor.full_name} on {date} at {time_slot} is confirmed.",
            category="appointment_booked",
        ).save()

        schedule_reminders(appointment, patient.full_name if patient else "Patient", doctor.full_name)

    except HealthPulseException:
        appointment.delete()  # rollback
        raise
    except Exception as exc:
        appointment.delete()  # rollback
        raise AppointmentTransactionError(str(exc))

    return JsonResponse({"ok": True, "appointment": _appt_to_dict(appointment, doctor_name=doctor.full_name)})


@login_required
@json_endpoint
def list_appointments(request):
    try:
        if request.user.profile.is_doctor:
            qs = Appointment.objects(doctor_id=request.user.id)
        else:
            qs = Appointment.objects(patient_id=request.user.id)

        grouped = {"upcoming": [], "completed": [], "cancelled": []}
        for a in qs.order_by("-date", "-time_slot"):
            patient = Patient.objects(django_user_id=a.patient_id).first()
            doctor = Doctor.objects(django_user_id=a.doctor_id).first()
            grouped.setdefault(a.status, []).append(_appt_to_dict(
                a,
                patient_name=patient.full_name if patient else "Unknown",
                doctor_name=doctor.full_name if doctor else "Unknown",
            ))
        return JsonResponse({"ok": True, "appointments": grouped})
    except Exception:
        return JsonResponse({"ok": True, "appointments": {"upcoming": [], "completed": [], "cancelled": []}})



@login_required
@json_endpoint
def cancel_appointment(request, appointment_id):
    appointment = Appointment.objects(id=appointment_id).first()
    if not appointment:
        return JsonResponse({"ok": False, "error": "Appointment not found."}, status=404)
    if request.user.id not in (appointment.patient_id, appointment.doctor_id):
        return JsonResponse({"ok": False, "error": "Not authorized."}, status=403)

    appointment.status = "cancelled"
    appointment.save()

    Notification(
        user_id=appointment.patient_id,
        title="Appointment cancelled",
        message=f"Your appointment on {appointment.date} at {appointment.time_slot} was cancelled.",
        category="appointment_cancelled",
    ).save()

    return JsonResponse({"ok": True})


@login_required
@json_endpoint
def reschedule_appointment(request, appointment_id):
    appointment = Appointment.objects(id=appointment_id).first()
    if not appointment:
        return JsonResponse({"ok": False, "error": "Appointment not found."}, status=404)
    if request.user.id != appointment.patient_id:
        return JsonResponse({"ok": False, "error": "Not authorized."}, status=403)

    new_date = validate_date(request.json.get("date", ""))
    new_slot = request.json.get("time_slot", "").strip()

    clash = Appointment.objects(
        doctor_id=appointment.doctor_id, date=new_date, time_slot=new_slot, status="upcoming"
    ).first()
    if clash:
        raise DuplicateAppointmentException()

    appointment.date = new_date
    appointment.time_slot = new_slot
    appointment.save()

    doctor = Doctor.objects(django_user_id=appointment.doctor_id).first()
    patient = Patient.objects(django_user_id=appointment.patient_id).first()
    Notification(
        user_id=appointment.patient_id,
        title="Appointment rescheduled",
        message=f"Your appointment has been moved to {new_date} at {new_slot}.",
        category="appointment_rescheduled",
    ).save()
    if doctor and patient:
        schedule_reminders(appointment, patient.full_name, doctor.full_name)

    return JsonResponse({"ok": True, "appointment": _appt_to_dict(appointment)})
