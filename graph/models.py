from django.db import models

# Create your models here.
class PacketList (models.Model):
    packet = models.JSONField()

    
