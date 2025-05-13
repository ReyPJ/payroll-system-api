from django.urls import path
from authentication.views import (
    CustomTokenObtainPairView,
    NFCTokenCreateView,
    NFCTokenValidateView,
    NFCTokenRevokeView,
)

urlpatterns = [
    path("", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("nfc/create/", NFCTokenCreateView.as_view(), name="nfc_token_create"),
    path("nfc/validate/", NFCTokenValidateView.as_view(), name="nfc_token_validate"),
    path("nfc/revoke/<int:pk>/", NFCTokenRevokeView.as_view(), name="nfc_token_revoke"),
]
