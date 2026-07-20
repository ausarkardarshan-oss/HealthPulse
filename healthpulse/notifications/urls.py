from django.urls import path
from notifications import views

app_name = "notifications"

urlpatterns = [
    path("api/list/", views.list_notifications, name="list"),
    path("api/<str:notification_id>/read/", views.mark_read, name="mark_read"),
    path("api/mark-all-read/", views.mark_all_read, name="mark_all_read"),
]
