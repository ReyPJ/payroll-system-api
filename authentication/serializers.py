from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from employee.models import Employee


class CustomTokenObtainPairSerializer(serializers.Serializer):
    fingerprint = serializers.CharField(required=False)
    unique_pin = serializers.CharField(required=False)

    def validate(self, attrs):
        if "fingerprint" in attrs:
            fingerprint = attrs.get("fingerprint")

            try:
                user = Employee.objects.get(fingerprint_hash=fingerprint)
            except Employee.DoesNotExist:
                raise serializers.ValidationError(
                    "Huella incorrecta o usuario no encontrado"
                )

            if not user.is_admin:
                raise serializers.ValidationError(
                    "Solo los administradores pueden iniciar sesión"
                )

            if not user.use_finger_print:
                raise serializers.ValidationError(
                    "Este usuario no tiene habilitada la autenticación por huella"
                )

        if "unique_pin" in attrs:
            unique_pin = attrs.get("unique_pin")

            try:
                user = Employee.objects.get(unique_pin=unique_pin)
            except Employee.DoesNotExist:
                raise serializers.ValidationError(
                    "PIN incorrecto o usuario no encontrado"
                )

            if not user.is_admin:
                raise serializers.ValidationError(
                    "Solo los administradores pueden iniciar sesión"
                )

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "username": user.username,
            "is_admin": user.is_admin,
        }
