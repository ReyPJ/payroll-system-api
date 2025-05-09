from attendance.views import (
    AttendanceMarkView,
    AttendanceMarkOutView,
    AttendanceStatsView,
)
from django.urls import path


urlpatterns = [
    path("in/", AttendanceMarkView.as_view(), name="Marcaje de asistencia"),
    path("out/", AttendanceMarkOutView.as_view(), name="Marcaje de asistencia"),
    path("stats/", AttendanceStatsView.as_view(), name="Estadísticas de asistencia"),
]
