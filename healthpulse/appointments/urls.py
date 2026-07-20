from django.urls import path
from appointments import views

app_name = "appointments"

urlpatterns = [
    path("api/check-slot/", views.check_slot, name="check_slot"),
    path("api/book/", views.book_appointment, name="book"),
    path("api/list/", views.list_appointments, name="list"),
    path("api/<str:appointment_id>/cancel/", views.cancel_appointment, name="cancel"),
    path("api/<str:appointment_id>/reschedule/", views.reschedule_appointment, name="reschedule"),
]
