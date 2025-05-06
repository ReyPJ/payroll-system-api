from django.urls import path
from employee.views import EmployeeListCreateView, EmployeeDetailView

urlpatterns = [
    path("", EmployeeListCreateView.as_view(), name="Crear y listar empleados"),
    path(
        "<int:pk>/", EmployeeDetailView.as_view(), name="Get, Update, Destroy empleados"
    ),
]
