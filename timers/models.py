from django.db import models
from employee.models import Employee


class Timer(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    day = models.IntegerField(choices=[(i, i) for i in range(7)])
    timeIn = models.TimeField()
    timeOut = models.TimeField()
