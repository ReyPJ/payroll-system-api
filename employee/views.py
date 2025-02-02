from rest_framework import generics, permissions, status
from rest_framework.response import Response
from employee.models import Employee
from employee.serializers import EmployeeSerializer


class EmployeeListCreateView(generics.ListCreateAPIView):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.all()
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        data = serializer.data
        data["full_name"] = instance.get_full_name()

        return Response(data, status=status.HTTP_200_OK)
