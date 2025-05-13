from django.db import models
from employee.models import Employee
import jwt
from django.conf import settings
from datetime import datetime, timedelta, timezone


class NFCToken(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    tag_id = models.CharField(max_length=100)
    token = models.TextField()
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_token(self):
        """
        Genera un token JWT firmado para NFC que no supere los 504 bytes
        """
        payload = {
            "employee_id": self.employee.id,
            "tag_id": self.tag_id,
            "exp": datetime.now(timezone.utc) + timedelta(days=365),  # Expira en 1 año
            "iat": datetime.now(timezone.utc),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        # Verificar que el token no exceda 504 bytes
        if len(token.encode("utf-8")) > 504:
            raise ValueError("El token generado excede el límite de 504 bytes")

        self.token = token
        return token

    @staticmethod
    def validate_token(token):
        """
        Valida un token JWT y devuelve la información si es válido
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            nfc_token = NFCToken.objects.filter(token=token, revoked=False).first()

            if not nfc_token:
                return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
