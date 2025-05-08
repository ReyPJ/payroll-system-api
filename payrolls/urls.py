from django.urls import path
from payrolls.views import (
    CalculateSalary,
    ManagePayPeriodView,
    ListEmployeesWithNightHours,
    CalculateAllSalaries,
    ListSalaryRecordsByPeriod,
    SalaryRecordEmployeeDetail,
    EmployeeAttendanceDetailView,
)

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
]
