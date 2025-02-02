from django.urls import path
from payrolls.views import CalculateSalary

urlpatterns = [
    path("<int:employee_id>/", CalculateSalary.as_view(), name="calculate-salary"),
]
