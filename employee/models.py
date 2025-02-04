from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class Employee(AbstractUser):
    phone = PhoneNumberField(blank=True, region="CR")
    salary_hour = models.DecimalField(max_digits=10, decimal_places=2)
    use_finger_print = models.BooleanField(default=False)
    use_face_id = models.BooleanField(default=False)
    fingerprint_hash = models.TextField(blank=True, null=True)
    face_tamplate = models.TextField(blank=True, null=True)
    is_admin = models.BooleanField(default=False)

    def get_current_timestamp(self):
        # Retorna el timestamp actual ajustado a la zona horaria local
        return timezone.now()
