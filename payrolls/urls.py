from django.urls import path
from payrolls.views import (
    CalculateSalary,
    ManagePayPeriodView,
    ListEmployeesWithNightHours,
    CalculateAllSalaries,
    ListSalaryRecordsByPeriod,
    SalaryRecordEmployeeDetail,
    EmployeeAttendanceDetailView,
    LiveAttendanceSummaryView,
)
from payrolls.views_admin import ResetAttendancePaidStatusView

urlpatterns = [
    path("calculate/", CalculateSalary.as_view(), name="calculate-salary"),
    path("period/", ManagePayPeriodView.as_view(), name="manage-pay-period"),
    path(
        "night-hours/", ListEmployeesWithNightHours.as_view(), name="list-night-hours"
    ),
    path(
        "calculate-all/", CalculateAllSalaries.as_view(), name="calculate-all-salaries"
    ),
    path("records/", ListSalaryRecordsByPeriod.as_view(), name="list-salary-records"),
    path(
        "records/<int:pk>/",
        SalaryRecordEmployeeDetail.as_view(),
        name="salary-record-detail",
    ),
    path(
        "attendance-details/",
        EmployeeAttendanceDetailView.as_view(),
        name="employee-attendance-details",
    ),
    # Resumen en tiempo real de horas acumuladas (sin calcular salario)
    path(
        "live-summary/",
        LiveAttendanceSummaryView.as_view(),
        name="live-attendance-summary",
    ),
    # Endpoints administrativos (solo para staff/superuser)
    path(
        "admin/reset-attendance/",
        ResetAttendancePaidStatusView.as_view(),
        name="reset-attendance-paid-status",
    ),
]
