from attendance.views import AttendanceMarkView
from django.urls import path


urlpatterns = [path("", AttendanceMarkView.as_view(), name="Marcaje de asistencia")]
