from django.urls import path

from . import user

urlpatterns = [
    path("user/", user.temp_access_token, name="user"),
    path("user/real", user.exchange_access_token, name="user_real"),
    path("user/redirect/", user.redirect, name="redirect"),
    path("user/lock/", user.need_login, name="need_login"),
    path("user/info/", user.get_user_info, name="info"),
    path("user/token/", user.get_token_info, name="token"),
    path("user/otp/", user.otp_test, name="otp"),
]