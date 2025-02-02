from rest_framework import generics, permissions, status
from rest_framework.response import Response
from attendance.serializers import AttendanceRegisterSerializer
from employee.models import Employee
from attendance.models import AttendanceRegister


class AttendanceMarkView(generics.CreateAPIView):
    serializer_class = AttendanceRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        method = data.get("method")
        hash = data.get("hash")

        if not method or not hash:
            return Response(
                {"error": "Metodo e identificador son requridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if method == "fingerprint":
            employee = Employee.objects.filter(fingerprint_hash=hash).first()
        elif method == "faceId":
            employee = Employee.objects.filter(face_template=hash).first()
        else:
            return Response({"error": "Metodo no valido"})

        if not employee:
            return Response({"error": "Empleado no encontrado"}, status=status.HTTP_400_BAD_REQUEST)

        AttendanceRegister.objects.create(employee=employee, method=method)
        return Response({"message": f"Marcado exitoso para {employee.username}"})
