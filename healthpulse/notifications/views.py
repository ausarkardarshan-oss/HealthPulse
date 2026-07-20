from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from notifications.models import Notification
from common.decorators import json_endpoint


@login_required
@json_endpoint
def list_notifications(request):
    try:
        notes = Notification.objects(user_id=request.user.id).order_by("-created_at")[:30]
        data = [
            {
                "id": str(n.id),
                "title": n.title,
                "message": n.message,
                "category": n.category,
                "is_read": n.is_read,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for n in notes
        ]
        unread_count = Notification.objects(user_id=request.user.id, is_read=False).count()
        return JsonResponse({"ok": True, "notifications": data, "unread_count": unread_count})
    except Exception:
        return JsonResponse({"ok": True, "notifications": [], "unread_count": 0})



@login_required
@json_endpoint
def mark_read(request, notification_id):
    note = Notification.objects(id=notification_id, user_id=request.user.id).first()
    if not note:
        return JsonResponse({"ok": False, "error": "Notification not found."}, status=404)
    note.is_read = True
    note.save()
    return JsonResponse({"ok": True})


@login_required
@json_endpoint
def mark_all_read(request):
    Notification.objects(user_id=request.user.id, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})
