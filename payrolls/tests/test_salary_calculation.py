from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from employee.models import Employee
from payrolls.models import PayPeriod, SalaryRecord
from attendance.models import AttendanceRegister
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.utils import timezone


class SalaryCalculationTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = Employee.objects.create(
            username="admin",
            is_admin=True,
            salary_hour=Decimal("40.00"),
            biweekly_hours=Decimal("96.0"),
            use_finger_print=True,
            fingerprint_hash="admin_test_hash",
        )
        self.client.force_authenticate(user=self.admin)

        self.employee = Employee.objects.create(
            username="employee",
            is_admin=False,
            salary_hour=Decimal("25.00"),
            biweekly_hours=Decimal("96.0"),
            use_finger_print=True,
            fingerprint_hash="employee_test_hash",
            night_shift_factor=Decimal("1.2"),
        )

        self.pay_period = PayPeriod.objects.create(
            start_date=date.today() - timedelta(days=15),
            end_date=date.today(),
            is_closed=False,
        )

        for day in range(10):
            day_date = date.today() - timedelta(days=10 - day)
            timestamp_in = timezone.make_aware(datetime.combine(day_date, time(8, 0)))
            timestamp_out = timezone.make_aware(datetime.combine(day_date, time(16, 0)))

            AttendanceRegister.objects.create(
                employee=self.employee,
                timestamp_in=timestamp_in,
                timestamp_out=timestamp_out,
                method="fingerprint",
                hash="test_hash",
                paid=False,
            )

    def test_calculate_salary(self):
        """Test para calcular el salario de un empleado"""
        url = reverse("calculate-salary")
        data = {
            "employee_id": self.employee.id,
            "apply_night_factor": False,
            "period_id": self.pay_period.id,
        }
        response = self.client.post(url, data, format="json")
        print(f"Response: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SalaryRecord.objects.count(), 1)
        salary_record = SalaryRecord.objects.first()
        self.assertEqual(salary_record.employee, self.employee)
        self.assertEqual(salary_record.pay_period, self.pay_period)
        self.assertEqual(salary_record.total_hours, Decimal("80"))
        self.assertEqual(salary_record.regular_hours, Decimal("80"))

        paid_records = AttendanceRegister.objects.filter(
            employee=self.employee, paid=True
        ).count()
        self.assertEqual(paid_records, 10)

    def test_calculate_salary_night_shift(self):
        """Test para calcular el salario de un empleado con horas nocturnas"""
        # Primero limpiamos los registros anteriores
        AttendanceRegister.objects.all().delete()

        # Creamos registros nocturnos
        for day in range(10):
            day_date = date.today() - timedelta(days=10 - day)
            # Horario nocturno de 10pm a 6am del día siguiente
            timestamp_in = timezone.make_aware(datetime.combine(day_date, time(22, 0)))
            next_day = day_date + timedelta(days=1)
            timestamp_out = timezone.make_aware(datetime.combine(next_day, time(6, 0)))

            AttendanceRegister.objects.create(
                employee=self.employee,
                timestamp_in=timestamp_in,
                timestamp_out=timestamp_out,
                method="fingerprint",
                hash="test_hash",
                paid=False,
            )

        url = reverse("calculate-salary")
        data = {
            "employee_id": self.employee.id,
            "apply_night_factor": True,
            "period_id": self.pay_period.id,
        }
        response = self.client.post(url, data, format="json")
        # Hacer la response un json
        print(f"Response: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SalaryRecord.objects.count(), 1)

        salary_record = SalaryRecord.objects.first()
        self.assertEqual(salary_record.employee, self.employee)
        self.assertEqual(salary_record.pay_period, self.pay_period)
        self.assertEqual(salary_record.total_hours, Decimal("80"))
        self.assertEqual(salary_record.regular_hours, Decimal("80"))
        self.assertEqual(salary_record.night_hours, Decimal("80"))
        self.assertEqual(salary_record.night_shift_factor_applied, Decimal("1.2"))

        paid_records = AttendanceRegister.objects.filter(
            employee=self.employee, paid=True
        ).count()
        self.assertEqual(paid_records, 10)
