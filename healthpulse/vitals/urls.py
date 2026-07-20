from django.urls import path
from vitals import views

app_name = "vitals"

urlpatterns = [
    path("api/add/", views.add_vitals, name="add"),
    path("api/chart/", views.chart_data, name="chart"),
    path("api/summary/", views.summary, name="summary"),
]
