from django.db import models

# Create your models here.
class User(models.Model):
    id = models.IntegerField(primary_key=True)
    email = models.EmailField(unique=True)
    login = models.CharField(max_length=50, unique=True)
    usual_full_name = models.CharField(max_length=50)
    secret = models.CharField(max_length=255)
    image_link = models.URLField(max_length=255)