from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from employee.models import Employee
from authentication.models import NFCToken


class CustomTokenObtainPairSerializer(serializers.Serializer):
    unique_pin = serializers.CharField(required=True)

    def validate(self, attrs):
        unique_pin = attrs.get("unique_pin")

        try:
            user = Employee.objects.get(unique_pin=unique_pin)
        except Employee.DoesNotExist:
            raise serializers.ValidationError("PIN incorrecto o usuario no encontrado")

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


class NFCTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = NFCToken
        fields = ["id", "employee", "tag_id", "token", "revoked", "created_at"]
        read_only_fields = ["token", "revoked", "created_at"]

    def create(self, validated_data):
        nfc_token = NFCToken.objects.create(**validated_data)
        nfc_token.generate_token()
        nfc_token.save()
        return nfc_token


class NFCTokenValidateSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

    def validate(self, attrs):
        token = attrs.get("token")
        payload = NFCToken.validate_token(token)

        if not payload:
            raise serializers.ValidationError("Token inválido o revocado")

        return payload
