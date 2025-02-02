from django.urls import path
from timers.views import TimerListCreateView, TimerDetailView, TimerByEmployeeView


urlpatterns = [
    path("", TimerListCreateView.as_view(), name="Crear y listar horarios"),
    path("<int:pk>/", TimerDetailView.as_view(), name="Get, Update, Delete horario"),
    path(
        "<int:employee_id>/timers/",
        TimerByEmployeeView.as_view(),
        name="timers-by-employee",
    ),
]
