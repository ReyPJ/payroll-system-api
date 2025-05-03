from django.urls import path
from payrolls.views import CalculateSalary, ManagePayPeriodView

urlpatterns = [
    path("<int:employee_id>/", CalculateSalary.as_view(), name="calculate-salary"),
    path("period/", ManagePayPeriodView.as_view(), name="manage-pay-period"),
]
