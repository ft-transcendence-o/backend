"""
Django settings for pong project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
from dotenv import load_dotenv
from os import getenv, path

load_dotenv(verbose=True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = getenv("SECRET_KEY")

INSTALLED_APPS = [
    # Make sure "daphne" is at the top
    "daphne",
    "authentication",
    "game",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

ROOT_URLCONF = "pong.urls"

WSGI_APPLICATION = "pong.wsgi.application"
ASGI_APPLICATION = "pong.asgi.application"

TIME_ZONE = "Asia/Seoul"
USE_TZ = False