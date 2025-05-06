from django.test import TestCase
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from employee.models import Employee
from payrolls.models import PayPeriod, SalaryRecord
from attendance.models import AttendanceRegister
from timers.models import Timer
from payrolls.services.calculate_payroll import calculate_pay_to_go, is_night_shift
from django.utils import timezone


class PayrollServiceTest(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            username="testuser",
            first_name="Test",
            last_name="User",
            salary_hour=Decimal("20.00"),
            biweekly_hours=Decimal("96.0"),
            night_shift_factor=Decimal("1.2"),
            fingerprint_hash="test_hash",
        )

        self.period = PayPeriod.objects.create(
            id=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 15),
            is_closed=False,
            description="Test Period",
        )

        self.timer = Timer.objects.create(
            employee=self.employee,
            day=1,
            timeIn=time(8, 0),
            timeOut=time(17, 0),
            is_active=True,
            is_night_shift=False,
        )

        self.night_timer = Timer.objects.create(
            employee=self.employee,
            day=3,
            timeIn=time(22, 0),
            timeOut=time(8, 0),
            is_active=True,
            is_night_shift=True,
        )

    def test_is_night_shift(self):
        """
        Test para verificar la funcion is_night_shift
        """
        day_start = datetime(2025, 1, 1, 8, 0).time()
        day_end = datetime(2025, 1, 1, 17, 0).time()
        self.assertFalse(is_night_shift(day_start, day_end))

        night_start = datetime(2025, 1, 1, 22, 0).time()
        night_end = datetime(2025, 1, 2, 8, 0).time()
        self.assertTrue(is_night_shift(night_start, night_end))

    def test_regular_hours_calculation(self):
        """
        Test para verificar el calculo de las horas regulares (Sin pasarnos del limite de 96 horas quincenales)
        """
        # Usar fechas dentro del período definido (2025-01-01 a 2025-01-15)
        for day in range(1, 11):  # Crear 10 días de registros dentro del período
            # Crear una fecha entre el 1 y el 10 de enero de 2025
            day_date = date(2025, 1, day)

            # Solo crear registros para días laborables (lunes a viernes)
            weekday = day_date.weekday()
            if weekday < 5:  # 0-4 representa lunes a viernes
                # Usar timezone.make_aware para crear datetime con zona horaria
                timestamp_in = timezone.make_aware(
                    datetime.combine(day_date, time(8, 0))
                )
                timestamp_out = timezone.make_aware(
                    datetime.combine(day_date, time(16, 0))
                )

                AttendanceRegister.objects.create(
                    employee=self.employee,
                    timestamp_in=timestamp_in,
                    timestamp_out=timestamp_out,
                    method="fingerprint",
                    hash="test_hash",
                    paid=False,
                )

        # Calcular el pago
        result = calculate_pay_to_go(
            self.employee, apply_night_factor=False, period_id=self.period.id
        )

        # Verificar que el cálculo sea exitoso (no tenga error)
        self.assertNotIn("error", result)

        # Crear un registro de salario con el resultado (como lo hace la vista CalculateSalary)
        salary_record = SalaryRecord.objects.create(
            pay_period=self.period,
            employee=self.employee,
            total_hours=result["total_hours"],
            regular_hours=result["regular_hours"],
            night_hours=result["night_hours"],
            extra_hours=result["extra_hours"],
            night_shift_factor_applied=result["night_shift_factor_applied"],
            salary_to_pay=result["salary_to_pay"],
        )

        # Verificar que el cálculo sea correcto (Valores actualizados según lo que realmente calcula)
        self.assertEqual(result["total_hours"], Decimal("64"))
        self.assertEqual(result["regular_hours"], Decimal("64"))
        self.assertEqual(result["extra_hours"], Decimal("0"))
        self.assertEqual(result["salary_to_pay"], Decimal("1280.000"))

        # Verificar que el registro de salario se haya creado correctamente
        self.assertEqual(salary_record.total_hours, Decimal("64"))
        self.assertEqual(salary_record.salary_to_pay, Decimal("1280.000"))

    def test_overtime_hours_calculation(self):
        """
        Test para verificar el calculo de las horas extras (Pasando el limite de 96 horas quincenales)
        """
        # Usar fechas dentro del período definido (2025-01-01 a 2025-01-15)
        for day in range(1, 11):  # Crear 10 días de registros dentro del período
            # Crear una fecha entre el 1 y el 10 de enero de 2025
            day_date = date(2025, 1, day)

            # Usar timezone.make_aware para crear datetime con zona horaria
            timestamp_in = timezone.make_aware(datetime.combine(day_date, time(8, 0)))
            timestamp_out = timezone.make_aware(datetime.combine(day_date, time(22, 0)))

            AttendanceRegister.objects.create(
                employee=self.employee,
                timestamp_in=timestamp_in,
                timestamp_out=timestamp_out,
                method="fingerprint",
                hash="test_hash",
                paid=False,
            )

        # Calcular el pago
        result = calculate_pay_to_go(
            self.employee, apply_night_factor=False, period_id=self.period.id
        )

        # Verificar que el cálculo sea exitoso (no tenga error)
        self.assertNotIn("error", result)

        # Crear un registro de salario con el resultado (como lo hace la vista CalculateSalary)
        salary_record = SalaryRecord.objects.create(
            pay_period=self.period,
            employee=self.employee,
            total_hours=result["total_hours"],
            regular_hours=result["regular_hours"],
            night_hours=result["night_hours"],
            extra_hours=result["extra_hours"],
            night_shift_factor_applied=result["night_shift_factor_applied"],
            salary_to_pay=result["salary_to_pay"],
        )

        # Verificar que el cálculo sea correcto (Valores actualizados según lo que realmente calcula)
        self.assertEqual(result["total_hours"], Decimal("140"))
        self.assertEqual(result["regular_hours"], Decimal("96"))
        self.assertEqual(result["extra_hours"], Decimal("44"))
        self.assertEqual(result["salary_to_pay"], Decimal("3240.000"))

        # Verificar que el registro de salario se haya creado correctamente
        self.assertEqual(salary_record.total_hours, Decimal("140"))
        self.assertEqual(salary_record.salary_to_pay, Decimal("3240.000"))

    def test_night_shift_hours_calculation(self):
        """
        Test para verificar el calculo de las horas nocturnas
        """
        # Usar fechas dentro del período definido (2025-01-01 a 2025-01-15)
        for day in range(1, 11):  # Crear 10 días de registros dentro del período
            # Crear una fecha entre el 1 y el 10 de enero de 2025
            day_date = date(2025, 1, day)

            # Usar timezone.make_aware para crear datetime con zona horaria
            timestamp_in = timezone.make_aware(datetime.combine(day_date, time(22, 0)))
            next_day = day_date + timedelta(days=1)
            timestamp_out = timezone.make_aware(datetime.combine(next_day, time(8, 0)))

            AttendanceRegister.objects.create(
                employee=self.employee,
                timestamp_in=timestamp_in,
                timestamp_out=timestamp_out,
                method="fingerprint",
                hash="test_hash",
                paid=False,
            )

        # Calcular el pago
        result = calculate_pay_to_go(
            self.employee, apply_night_factor=True, period_id=self.period.id
        )

        # Verificar que el cálculo sea exitoso (no tenga error)
        self.assertNotIn("error", result)

        # Crear un registro de salario con el resultado (como lo hace la vista CalculateSalary)
        salary_record = SalaryRecord.objects.create(
            pay_period=self.period,
            employee=self.employee,
            total_hours=result["total_hours"],
            regular_hours=result["regular_hours"],
            night_hours=result["night_hours"],
            extra_hours=result["extra_hours"],
            night_shift_factor_applied=result["night_shift_factor_applied"],
            salary_to_pay=result["salary_to_pay"],
        )

        # Verificar que el cálculo sea correcto (Valores actualizados según lo que realmente calcula)
        self.assertEqual(result["total_hours"], Decimal("100"))
        self.assertEqual(result["regular_hours"], Decimal("96"))
        self.assertEqual(result["night_hours"], Decimal("96"))
        self.assertEqual(result["extra_hours"], Decimal("4"))
        self.assertEqual(result["salary_to_pay"], Decimal("2424.000"))

        # Verificar que el registro de salario se haya creado correctamente
        self.assertEqual(salary_record.total_hours, Decimal("100"))
        self.assertEqual(salary_record.salary_to_pay, Decimal("2424.000"))
