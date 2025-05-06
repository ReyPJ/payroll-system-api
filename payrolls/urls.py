from django.urls import path
from payrolls.views import (
    CalculateSalary,
    ManagePayPeriodView,
    ListEmployeesWithNightHours,
)

urlpatterns = [
    path("calculate/", CalculateSalary.as_view(), name="calculate-salary"),
    path("period/", ManagePayPeriodView.as_view(), name="manage-pay-period"),
    path(
        "night-hours/", ListEmployeesWithNightHours.as_view(), name="list-night-hours"
    ),
]
