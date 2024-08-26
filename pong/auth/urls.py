from django.urls import path

from .views import (
    UserInfo,
    OAuthView,
    QRcodeView,
    OTPView,
    LoginView,
    StatusView,
)

urlpatterns = [
    path("info", UserInfo.as_view(), name="user_info"),
    path("token", OAuthView.as_view(), name="token"),
    path("otp/qrcode", QRcodeView.as_view(), name="otp_qrcode"),
    path("otp/verify", OTPView.as_view(), name="otp_verify"),
    path("login", LoginView.as_view(), name="login"),
    path("auth-status", StatusView.as_view(), name="auth_status"),
]
