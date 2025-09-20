from authentication.serializers import (
    CustomTokenObtainPairSerializer,
    NFCTokenSerializer,
    NFCTokenValidateSerializer,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from authentication.models import NFCToken
from employee.models import Employee


class CustomTokenObtainPairView(APIView):
    serializer_class = CustomTokenObtainPairSerializer

    @staticmethod
    def post(self, request, *args, **kwargs):
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NFCTokenCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NFCTokenSerializer

    @staticmethod
    def post(self, request):
        employee_id = request.data.get("employee_id")
        tag_id = request.data.get("tag_id")

        if not employee_id or not tag_id:
            return Response(
                {"error": "Se requiere employee_id y tag_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response(
                {"error": "Empleado no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        data = {"employee": employee.id, "tag_id": tag_id}

        serializer = NFCTokenSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NFCTokenValidateView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = NFCTokenValidateSerializer

    @staticmethod
    def post(self, request):
        serializer = NFCTokenValidateSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NFCTokenRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NFCTokenSerializer

    @staticmethod
    def post(self, request, pk):
        try:
            nfc_token = NFCToken.objects.get(pk=pk)
        except NFCToken.DoesNotExist:
            return Response(
                {"error": "Token NFC no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        nfc_token.revoked = True
        nfc_token.save()

        return Response(
            {"message": "Token NFC revocado exitosamente"}, status=status.HTTP_200_OK
        )
