from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from employee.models import Employee
from payrolls.models import PayPeriod
from decimal import Decimal
from datetime import date


class PayPeriodViewTest(TestCase):
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

    def test_create_pay_period(self):
        """Test para crear un nuevo periodo de pago"""
        url = reverse("manage-pay-period")
        data = {
            "action": "create_new",
            "start_date": "2025-01-01",
            "end_date": "2025-01-15",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PayPeriod.objects.count(), 1)

        period = PayPeriod.objects.first()
        self.assertEqual(period.start_date, date(2025, 1, 1))
        self.assertEqual(period.end_date, date(2025, 1, 15))
        self.assertFalse(period.is_closed)

    def test_close_pay_period(self):
        """Test para cerrar un periodo de pago"""
        period = PayPeriod.objects.create(
            start_date=date(2023, 6, 1), end_date=date(2023, 6, 15), is_closed=False
        )
        url = reverse("manage-pay-period")
        data = {
            "action": "close_current",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PayPeriod.objects.count(), 1)

        period.refresh_from_db()
        self.assertTrue(period.is_closed)
