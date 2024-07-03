from django.urls import path

from . import user

urlpatterns = [
    path("user/", user.temp_access_token, name="user"),
    path("user/redirect/", user.redirect, name="redirect"),
    path("user/lock/", user.need_login, name="need_login"),
    path("user/info/", user.get_user_info, name="info"),
    path("user/token/", user.get_token_info, name="token"),
]