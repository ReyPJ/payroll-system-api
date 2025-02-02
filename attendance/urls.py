from attendance.views import AttendanceMarkView, AttendanceMarkOutView
from django.urls import path


urlpatterns = [
    path("in/", AttendanceMarkView.as_view(), name="Marcaje de asistencia"),
    path("out/", AttendanceMarkOutView.as_view(), name="Marcaje de asistencia"),
]
