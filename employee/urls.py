from django.urls import path
from employee.views import (
    EmployeeListCreateView,
    EmployeeDetailView,
    EmployeeQRCodeView,
    CurrentlyWorkingEmployeesView,
)

urlpatterns = [
    path("", EmployeeListCreateView.as_view(), name="Crear y listar empleados"),
    path(
        "<int:pk>/", EmployeeDetailView.as_view(), name="Get, Update, Destroy empleados"
    ),
    path(
        "<int:pk>/make-qr-code/",
        EmployeeQRCodeView.as_view(),
        name="Generar QR para empleado",
    ),
    path(
        "active/",
        CurrentlyWorkingEmployeesView.as_view(),
        name="Empleados trabajando actualmente",
    ),
]
