from django.db import models
from employee.models import Employee


class AttendanceRegister(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    timestamp_in = models.DateTimeField(auto_now_add=True)
    timestamp_out = models.DateTimeField(null=True, blank=True)
    method = models.CharField(
        choices=[("fingerprint", "Huella"), ("faceId", "Reconocimiento Facial")],
        max_length=80,
    )
    paid = models.BooleanField(default=False)
    pay_period = models.DateField(null=True)
    hash = models.TextField()
    sync = models.BooleanField(default=False)
