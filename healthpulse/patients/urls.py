from django.urls import path
from patients import views

app_name = "patients"

urlpatterns = [
    path("api/list/", views.list_patients, name="list"),
    path("api/<int:user_id>/", views.patient_detail, name="detail"),
    path("api/update/", views.update_patient, name="update"),
    path("api/<int:user_id>/note/", views.add_doctor_note, name="add_note"),
]
