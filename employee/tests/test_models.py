from django.test import TestCase
from employee.models import Employee
from decimal import Decimal


class EmployeeModelTest(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            username="testuser",
            first_name="Test",
            last_name="User",
            salary_hour=Decimal("15.00"),
            biweekly_hours=Decimal("96.0"),
            night_shift_factor=Decimal("1.2"),
            is_admin=False,
        )

    def test_employee_creation(self):
        """
        Testea que el empleado se crea correctamente
        """
        self.assertEqual(self.employee.username, "testuser")
        self.assertEqual(self.employee.first_name, "Test")
        self.assertEqual(self.employee.last_name, "User")
        self.assertEqual(self.employee.salary_hour, Decimal("15.00"))
        self.assertEqual(self.employee.biweekly_hours, Decimal("96.0"))
        self.assertEqual(self.employee.night_shift_factor, Decimal("1.2"))
        self.assertFalse(self.employee.is_admin)

    def test_employee_full_name(self):
        """
        Testea que el nombre completo del empleado se genera correctamente
        """
        self.assertEqual(self.employee.get_full_name(), "Test User")
