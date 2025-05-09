from django.db import models
from employee.models import Employee
from decimal import Decimal


class PayPeriod(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    description = models.CharField(max_length=50, blank=True)

    def save(self, *args, **kwargs):
        self.description = f"Quincena {self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.description


class SalaryRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    total_hours = models.DecimalField(max_digits=10, decimal_places=2)
    night_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    regular_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    extra_hours = models.DecimalField(max_digits=10, decimal_places=2)
    night_shift_factor_applied = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.0
    )
    salary_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    lunch_deduction_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions_description = models.CharField(
        max_length=255, blank=True, null=True
    )
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_at = models.DateTimeField(auto_now_add=True)
    sync = models.BooleanField(default=False)  # Por si quieres marcar como sincronizado
    pay_period = models.ForeignKey(PayPeriod, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Pago a {self.employee.username} - {self.paid_at}"

    def calculate_salary(self, apply_night_factor=False):
        """Calcula el salario basado en horas normales, nocturnas y extra"""
        regular_rate = self.employee.salary_hour

        # Aplicar el factor nocturno solo si se solicita
        night_factor = (
            self.employee.night_shift_factor if apply_night_factor else Decimal("1.0")
        )
        self.night_shift_factor_applied = night_factor

        # Calcular salario regular (hasta el límite de horas quincenales)
        regular_pay = self.regular_hours * regular_rate

        # Calcular salario por horas nocturnas (dentro de las regulares)
        night_pay = self.night_hours * regular_rate * (night_factor - Decimal("1.0"))

        # Calcular salario extra (siempre a 1.5x)
        extra_pay = self.extra_hours * regular_rate * Decimal("1.5")

        # Salario bruto antes de deducciones
        self.gross_salary = regular_pay + night_pay + extra_pay

        # Calcular deducciones por almuerzo
        lunch_deduction = self.lunch_deduction_hours * regular_rate

        # Salario final a pagar
        self.salary_to_pay = self.gross_salary - lunch_deduction - self.other_deductions

        return self.salary_to_pay
