from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from employee.models import Employee
from decimal import Decimal


class EmployeeViewTest(TestCase):
    def setUp(self):
        """
        Primero creamos un admin para los tests
        """
        self.client = APIClient()
        self.admin = Employee.objects.create(
            username="admin",
            first_name="Admin",
            last_name="User",
            is_admin=True,
            salary_hour=Decimal("20.00"),
            use_finger_print=True,
            fingerprint_hash="admin_fingerprint_hash",
        )
        self.client.force_authenticate(user=self.admin)

    def test_create_employee(self):
        url = reverse("Crear y listar empleados")
        data = {
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "salary_hour": "15.00",
            "biweekly_hours": "96.0",
            "night_shift_factor": "1.2",
            "is_admin": False,
            "use_finger_print": True,
            "fingerprint_hash": "test_fingerprint_hash",
            "phone": "+50688888888",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Employee.objects.count(), 2)

        new_employee = Employee.objects.get(username="testuser")
        self.assertEqual(new_employee.first_name, "Test")
        self.assertEqual(new_employee.salary_hour, Decimal("15.00"))
