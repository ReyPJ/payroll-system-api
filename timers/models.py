from django.db import models
from employee.models import Employee


class Timer(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    day = models.IntegerField(choices=[(i, i) for i in range(7)])
    timeIn = models.TimeField()
    expected_hours = models.DecimalField(max_digits=5, decimal_places=2, default=8.0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("employee", "day")

    def __str__(self):
        days = [
            "Domingo",
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
        ]
        return f"{self.employee.username} - {days[self.day]} ({self.timeIn}, {self.expected_hours} horas)"
