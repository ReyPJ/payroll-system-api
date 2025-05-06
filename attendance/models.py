from django.db import models
from employee.models import Employee
from payrolls.models import PayPeriod


class AttendanceRegister(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    timestamp_in = models.DateTimeField()
    timestamp_out = models.DateTimeField(null=True, blank=True)
    method = models.CharField(
        choices=[("fingerprint", "Huella"), ("faceId", "Reconocimiento Facial")],
        max_length=80,
    )
    paid = models.BooleanField(default=False)
    pay_period = models.ForeignKey(
        PayPeriod, on_delete=models.SET_NULL, null=True, blank=True
    )
    hash = models.TextField()
    sync = models.BooleanField(default=False)
