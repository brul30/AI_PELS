from django.db import models
from django.contrib.postgres.fields import ArrayField

# Create your models here.

class Word(models.Model):

    word = models.CharField(max_length=100)
    phonetic = ArrayField(models.CharField(max_length=100, blank=True), default=list, blank=True)
    laymans = ArrayField(models.CharField(max_length=100, blank=True), default=list, blank=True)

    def __str__(self):
        return self.word