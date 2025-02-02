# from core.permissions import IsAdmin
from rest_framework import generics, permissions
from timers.models import Timer
from timers.serializers import TimerSeriealizer


class TimerListCreateView(generics.ListCreateAPIView):
    serializer_class = TimerSeriealizer
    queryset = Timer.objects.all()
    permission_classes = [permissions.AllowAny]


class TimerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TimerSeriealizer
    queryset = Timer.objects.all()
    permission_classes = [permissions.AllowAny]
