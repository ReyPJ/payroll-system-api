from django.db import models
from employee.models import Employee
from payrolls.models import PayPeriod


class AttendanceRegister(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    timestamp_in = models.DateTimeField()
    timestamp_out = models.DateTimeField(null=True, blank=True)
    method = models.CharField(
        choices=[
            ("fingerprint", "Huella"),
            ("faceId", "Reconocimiento Facial"),
            ("pin", "PIN"),
            ("qr_code", "QR Code"),
        ],
        max_length=80,
    )
    paid = models.BooleanField(default=False)
    pay_period = models.ForeignKey(
        PayPeriod, on_delete=models.SET_NULL, null=True, blank=True
    )
    hash = models.TextField()
    sync = models.BooleanField(default=False)
    unique_pin = models.CharField(max_length=10, null=True, blank=True)
    qr_code = models.TextField(null=True, blank=True)


class AttendanceDetail(models.Model):
    """
    Modelo para almacenar los detalles diarios de asistencia de un empleado
    Esto se utilizará para reportes detallados de horas trabajadas por día
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    pay_period = models.ForeignKey(PayPeriod, on_delete=models.CASCADE)
    work_date = models.DateField()
    time_in = models.TimeField()
    time_out = models.TimeField()
    regular_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    night_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    extra_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    lunch_deduction = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ("employee", "work_date")

    def __str__(self):
        return f"{self.employee.username} - {self.work_date}"
