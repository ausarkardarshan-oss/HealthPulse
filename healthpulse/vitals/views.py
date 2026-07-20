from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from vitals.models import Vitals
from common.decorators import json_endpoint
from common.validators import validate_vitals
from notifications.models import Notification

PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}


@login_required
@json_endpoint
def add_vitals(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)

    cleaned = validate_vitals(request.json)
    if not cleaned:
        return JsonResponse({"ok": False, "error": "Enter at least one vitals value."}, status=400)

    vitals = Vitals(patient_id=request.user.id, **cleaned)
    vitals.save()

    Notification(
        user_id=request.user.id,
        title="Vitals updated",
        message="Your latest vitals have been recorded.",
        category="vitals_updated",
    ).save()

    return JsonResponse({
        "ok": True,
        "vitals": {
            "id": str(vitals.id),
            "recorded_at": vitals.recorded_at.strftime("%Y-%m-%d %H:%M"),
            "status": vitals.health_status(),
            **cleaned,
        },
    })


@login_required
@json_endpoint
def chart_data(request):
    """Time series for Chart.js: bp/sugar/weight/heart_rate over a period."""
    patient_id = request.GET.get("patient_id")
    patient_id = int(patient_id) if patient_id else request.user.id

    if patient_id != request.user.id and not request.user.profile.is_doctor:
        return JsonResponse({"ok": False, "error": "Not authorized."}, status=403)

    period = request.GET.get("period", "30d")
    days = PERIOD_DAYS.get(period, 30)
    since = datetime.utcnow() - timedelta(days=days)

    try:
        records = Vitals.objects(patient_id=patient_id, recorded_at__gte=since).order_by("recorded_at")

        labels, bp_sys, bp_dia, sugar, weight, hr = [], [], [], [], [], []
        for r in records:
            labels.append(r.recorded_at.strftime("%b %d"))
            bp_sys.append(r.bp_systolic)
            bp_dia.append(r.bp_diastolic)
            sugar.append(r.sugar)
            weight.append(r.weight)
            hr.append(r.heart_rate)

        return JsonResponse({
            "ok": True,
            "labels": labels,
            "series": {
                "bp_systolic": bp_sys,
                "bp_diastolic": bp_dia,
                "sugar": sugar,
                "weight": weight,
                "heart_rate": hr,
            },
        })
    except Exception:
        return JsonResponse({
            "ok": True,
            "labels": [],
            "series": {
                "bp_systolic": [],
                "bp_diastolic": [],
                "sugar": [],
                "weight": [],
                "heart_rate": [],
            },
        })



@login_required
@json_endpoint
def summary(request):
    """Latest reading + simple averages, used by the vitals tab."""
    patient_id = request.GET.get("patient_id")
    patient_id = int(patient_id) if patient_id else request.user.id

    try:
        records = list(Vitals.objects(patient_id=patient_id).order_by("-recorded_at")[:30])
        if not records:
            return JsonResponse({"ok": True, "latest": None, "averages": None, "history": []})
    except Exception:
        return JsonResponse({"ok": True, "latest": None, "averages": None, "history": []})


    latest = records[0]

    def avg(field):
        vals = [getattr(r, field) for r in records if getattr(r, field) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    averages = {
        "bp_systolic": avg("bp_systolic"),
        "bp_diastolic": avg("bp_diastolic"),
        "sugar": avg("sugar"),
        "weight": avg("weight"),
        "heart_rate": avg("heart_rate"),
        "temperature": avg("temperature"),
    }

    history = [
        {
            "id": str(r.id),
            "recorded_at": r.recorded_at.strftime("%Y-%m-%d %H:%M"),
            "bp_systolic": r.bp_systolic,
            "bp_diastolic": r.bp_diastolic,
            "sugar": r.sugar,
            "weight": r.weight,
            "heart_rate": r.heart_rate,
            "temperature": r.temperature,
            "status": r.health_status(),
        }
        for r in records
    ]

    return JsonResponse({
        "ok": True,
        "latest": history[0],
        "averages": averages,
        "history": history,
    })
