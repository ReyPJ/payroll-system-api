from rest_framework import generics, permissions, status
from rest_framework.response import Response
from employee.models import Employee
from employee.serializers import EmployeeSerializer
import qrcode
import random
from django.http import HttpResponse
from io import BytesIO


class EmployeeListCreateView(generics.ListCreateAPIView):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = self.request.user

        if not Employee.objects.filter(id=user.id, is_admin=True).exists():
            return Response(
                {"error": "No tienes permiso para realizar esta accion"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().create(request, *args, **kwargs)


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        data = serializer.data
        data["full_name"] = instance.get_full_name()

        return Response(data, status=status.HTTP_200_OK)


class EmployeeQRCodeView(generics.CreateAPIView):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Obtener el empleado por ID que viene en la URL
        employee = self.get_object()

        if employee.qr_code:
            qr = qrcode.make(employee.qr_code)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            buffer.seek(0)

            response = HttpResponse(buffer, content_type="image/png")
            response["Content-Disposition"] = (
                f'attachment; filename="{employee.first_name}_{employee.last_name}_qr.png"'
            )
            return response

        # Generar código random
        code = random.randint(100000, 999999)
        # Guardar el código en el campo qr_code
        employee.qr_code = code
        employee.save()

        # Generar el QR con el código
        qr = qrcode.make(str(code))
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)

        # Preparar la respuesta para descargar el QR
        response = HttpResponse(buffer, content_type="image/png")
        response["Content-Disposition"] = (
            f'attachment; filename="{employee.first_name}_{employee.last_name}_qr.png"'
        )
        return response
