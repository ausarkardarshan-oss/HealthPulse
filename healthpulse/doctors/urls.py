from django.urls import path
from doctors import views

app_name = "doctors"

urlpatterns = [
    path("api/list/", views.list_doctors, name="list"),
    path("api/appointments/", views.doctor_appointments, name="appointments"),
]
