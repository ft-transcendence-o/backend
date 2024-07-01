from django.urls import path

from . import user

urlpatterns = [
    path("user/", user.test, name="user"),
    path("user/redirect/", user.redirect, name="redirect"),
]