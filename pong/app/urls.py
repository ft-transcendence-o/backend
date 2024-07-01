from django.urls import path

from . import user

urlpatterns = [
    path("user/", user.take_access_token, name="user"),
    path("user/redirect/", user.redirect, name="redirect"),
]