from django.db import models
from django.urls import reverse

class Video(models.Model):
    id = models.CharField(max_length=20, null=False, unique=True, primary_key=True)
    title = models.CharField(max_length=200, null=False)
    date_added = models.DateTimeField(auto_now_add=True)
    thumbnail = models.TextField(null=False)
    duration = models.CharField(null=False, max_length=10)

    def get_absolute_url(self):
        return reverse("download", args=[str(self.id)])
   
    def __str__(self):
        return self.title
    