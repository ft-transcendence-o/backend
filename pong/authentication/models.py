from django.db import models

# Create your models here.
class User(models.Model):
    id = models.IntegerField(primary_key=True)
    email = models.EmailField(unique=True)
    login = models.CharField(max_length=50, unique=True)
    usual_full_name = models.CharField(max_length=50)
    image_link = models.URLField(max_length=255)
    need_otp = models.BooleanField(default=True)
    print_secret = models.BooleanField(default=True)


class OTPSecret(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    secret = models.CharField(max_length=50)
    attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(null=True)
    is_locked = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)