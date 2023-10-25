from django.db import models

# Create your models here.
class AudioData(models.Model):
    audio = models.TextField()