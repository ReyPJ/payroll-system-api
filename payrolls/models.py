from django.db import models
from employee.models import Employee


class PayPeriod(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    description = models.CharField(max_length=50, blank=True)

    def save(self, *args, **kwargs):
        self.description = f"Quincena {self.start_date} - {self.end_date}"
        super().save(*args, **kwargs)


class SalaryRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    total_hours = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hours = models.DecimalField(max_digits=10, decimal_places=2)
    salary_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    sync = models.BooleanField(default=False)  # Por si quieres marcar como sincronizado
    pay_period = models.ForeignKey(PayPeriod, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Pago a {self.employee.username} - {self.paid_at}"
