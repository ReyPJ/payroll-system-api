from django.urls import path
from timers.views import TimerListCreateView, TimerDetailView


urlpatterns = [
    path("", TimerListCreateView.as_view(), name="Crear y listar horarios"),
    path("<int:pk>/", TimerDetailView.as_view(), name="Get, Update, Delete horario"),
]
