from django.urls import path
from authentication.views import CustomTokenObtainPairView

urlpatterns = [
    path("", CustomTokenObtainPairView.as_view(), name="Obtener Token")
]
