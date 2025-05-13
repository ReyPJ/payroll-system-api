from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class Employee(AbstractUser):
    phone = PhoneNumberField(blank=True, region="CR")
    salary_hour = models.DecimalField(max_digits=10, decimal_places=2)
    biweekly_hours = models.DecimalField(max_digits=5, decimal_places=2, default=96.0)
    night_shift_factor = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.0
    )
    is_admin = models.BooleanField(default=False)
    unique_pin = models.CharField(max_length=10, blank=True, null=True, unique=True)

    def get_current_timestamp(self):
        # Retorna el timestamp actual ajustado a la zona horaria local
        return timezone.now()
