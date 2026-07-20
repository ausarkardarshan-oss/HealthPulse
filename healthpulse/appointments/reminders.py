"""
Very lightweight in-process reminder scheduler using Python's threading
module, per the project spec.

Caveats (documented here on purpose, not hidden):
- Reminders only fire while this Django process stays alive. If you run
  `manage.py runserver` and restart it, any pending reminder threads are
  lost. For real production use you'd swap this for Celery + a persistent
  broker (Redis/RabbitMQ) - this module is intentionally simple.
- Only works with a single worker process (fine for `runserver` / a single
  gunicorn worker; not for multi-worker deployments).
"""
import threading
from datetime import datetime, timedelta

from notifications.models import Notification

REMINDER_OFFSETS = [
    ("1 day before", timedelta(days=1)),
    ("2 hours before", timedelta(hours=2)),
    ("30 minutes before", timedelta(minutes=30)),
]

# 12-hour "hh:mm AM/PM" -> datetime.time parsing
_TIME_FORMAT = "%I:%M %p"


def _appointment_datetime(date_str: str, time_slot: str) -> datetime:
    return datetime.strptime(f"{date_str} {time_slot}", f"%Y-%m-%d {_TIME_FORMAT}")


def _fire_reminder(user_id, patient_name, doctor_name, appt_dt, label):
    Notification(
        user_id=user_id,
        title="Appointment reminder",
        message=f"Reminder ({label}): appointment with {doctor_name} on "
                 f"{appt_dt.strftime('%b %d, %Y at %I:%M %p')}.",
        category="reminder",
    ).save()


def schedule_reminders(appointment, patient_name, doctor_name):
    """Spawn one daemon thread per reminder offset that hasn't already passed."""
    try:
        appt_dt = _appointment_datetime(appointment.date, appointment.time_slot)
    except ValueError:
        return  # malformed date/time - silently skip scheduling, booking still succeeds

    now = datetime.now()
    for label, offset in REMINDER_OFFSETS:
        fire_at = appt_dt - offset
        delay = (fire_at - now).total_seconds()
        if delay <= 0:
            continue  # that reminder window has already passed

        timer = threading.Timer(
            delay,
            _fire_reminder,
            args=(appointment.patient_id, patient_name, doctor_name, appt_dt, label),
        )
        timer.daemon = True
        timer.start()
