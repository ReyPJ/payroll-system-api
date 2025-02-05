from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

urlpatterns = [
    path("v1/employee/", include("employee.urls")),
    path("v1/timer/", include("timers.urls")),
    path("v1/docs/", SpectacularAPIView.as_view(), name="docs"),
    path(
        "v1/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="docs"),
        name="swagger-docs",
    ),
    path(
        "v1/docs/redoc/",
        SpectacularRedocView.as_view(url_name="docs"),
        name="redoc-docs",
    ),
    path("v1/attendance/", include("attendance.urls")),
    path("v1/auth/", include("authentication.urls")),
    path("v1/salary/", include("payrolls.urls")),
]
