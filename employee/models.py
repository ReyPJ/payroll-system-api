from django.db import models
from django.contrib.auth.models import AbstractUser


class Employee(AbstractUser):
    salary_hour = models.DecimalField(max_digits=10, decimal_places=2)
    use_finger_print = models.BooleanField(default=False)
    use_face_id = models.BooleanField(default=False)
    fingerprint_hash = models.TextField(blank=True, null=True)
    face_tamplate = models.TextField(blank=True, null=True)
    is_admin = models.BooleanField(default=False)
