from rest_framework import generics, permissions, status
from rest_framework.response import Response
from attendance.serializers import AttendanceRegisterSerializer
from employee.models import Employee
from attendance.models import AttendanceRegister
from django.utils.timezone import localtime


class AttendanceMarkView(generics.CreateAPIView):
    serializer_class = AttendanceRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        method = data.get("method")
        hash_value = data.get("hash")

        if not method or not hash_value:
            return Response(
                {"error": "Método e identificador son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar empleado según método de autenticación
        if method == "fingerprint":
            employee = Employee.objects.filter(fingerprint_hash=hash).first()
        elif method == "faceId":
            employee = Employee.objects.filter(face_template=hash).first()
        else:
            return Response(
                {"error": "Método no válido"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not employee:
            return Response(
                {"error": "Empleado no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        # Registrar entrada con timestamp real
        AttendanceRegister.objects.create(
            employee=employee,
            method=method,
            timestamp_in=localtime(employee.get_current_timestamp()),
        )

        return Response(
            {"message": f"Entrada registrada exitosamente para {employee.username}"},
            status=status.HTTP_201_CREATED,
        )


class AttendanceMarkOutView(generics.UpdateAPIView):
    queryset = AttendanceRegister.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = AttendanceRegisterSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        method = data.get("method")
        hash = data.get("hash")

        if not method or not hash:
            return Response(
                {"error": "Método e identificador son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar empleado
        if method == "fingerprint":
            employee = Employee.objects.filter(fingerprint_hash=hash).first()
        elif method == "faceId":
            employee = Employee.objects.filter(face_template=hash).first()
        else:
            return Response(
                {"error": "Método no válido"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not employee:
            return Response(
                {"error": "Empleado no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        # Buscar registro de entrada pendiente
        attendance = AttendanceRegister.objects.filter(
            employee=employee, timestamp_out__isnull=True
        ).first()

        if not attendance:
            return Response(
                {"error": "No hay registro de entrada pendiente"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Registrar salida con timestamp real
        attendance.timestamp_out = localtime(employee.get_current_timestamp())
        attendance.save()

        return Response(
            {"message": f"Salida registrada exitosamente para {employee.username}"}
        )
