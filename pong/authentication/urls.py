from django.urls import path

from . import auth

urlpatterns = [
    path('token/exchange/', auth.exchange_access_token, name='exchange_token'),
    path('user/info/', auth.get_user_info, name='user_info'),
    path('otp/qrcode/', auth.otp_test, name='otp_qrcode'),
    path('otp/verify/', auth.verify_otp, name='otp_verify'),

    # path("user/", auth.temp_access_token, name="user"),
    # path("user/real", auth.exchange_access_token, name="user_real"),
    # path("user/redirect/", auth.redirect, name="redirect"),
    # path("user/lock/", auth.need_login, name="need_login"),
    # path("user/info/", auth.get_user_info, name="info"),
    # path("user/token/", auth.get_token_info, name="token"),
    # path("user/otp/", auth.otp_test, name="otp"),
]