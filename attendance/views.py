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
        unique_pin = data.get("unique_pin")
        qr_code = data.get("qr_code")

        if (
            not method
            or (method != "pin" and not hash_value)
            and (method == "pin" and not unique_pin)
            and (method == "qr_code" and not qr_code)
        ):
            return Response(
                {"error": "Método e identificador son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar empleado según método de autenticación
        if method == "fingerprint":
            employee = Employee.objects.filter(fingerprint_hash=hash_value).first()
        elif method == "faceId":
            employee = Employee.objects.filter(face_tamplate=hash_value).first()
        elif method == "pin":
            employee = Employee.objects.filter(
                is_admin=False, unique_pin=unique_pin
            ).first()
        elif method == "qr_code":
            employee = Employee.objects.filter(qr_code=qr_code).first()
        else:
            return Response(
                {"error": "Método no válido"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not employee:
            return Response(
                {"error": "Empleado no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        employee_full_name = employee.get_full_name()

        # Registrar entrada con timestamp real
        AttendanceRegister.objects.create(
            employee=employee,
            method=method,
            timestamp_in=localtime(employee.get_current_timestamp()),
            hash=hash_value if method != "pin" else "",
            unique_pin=unique_pin if method == "pin" else None,
            qr_code=qr_code if method == "qr_code" else None,
        )

        return Response(
            [
                {
                    "message": f"Entrada registrada exitosamente para {employee.username}"
                },
                {"employee_name": {employee_full_name}},
            ],
            status=status.HTTP_201_CREATED,
        )


class AttendanceMarkOutView(generics.UpdateAPIView):
    queryset = AttendanceRegister.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = AttendanceRegisterSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        method = data.get("method")
        hash_value = data.get("hash")
        unique_pin = data.get("unique_pin")

        if (
            not method
            or (method != "pin" and not hash_value)
            and (method == "pin" and not unique_pin)
        ):
            return Response(
                {"error": "Método e identificador son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar empleado
        if method == "fingerprint":
            employee = Employee.objects.filter(fingerprint_hash=hash_value).first()
        elif method == "faceId":
            employee = Employee.objects.filter(face_tamplate=hash_value).first()
        elif method == "pin":
            employee = Employee.objects.filter(
                is_admin=False, unique_pin=unique_pin
            ).first()
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

        employee_full_name = employee.get_full_name()

        # Registrar salida con timestamp real
        attendance.timestamp_out = localtime(employee.get_current_timestamp())
        attendance.save()

        return Response(
            [
                {"message": f"Salida registrada exitosamente para {employee.username}"},
                {"employee_name": {employee_full_name}},
            ],
            status=status.HTTP_201_CREATED,
        )
