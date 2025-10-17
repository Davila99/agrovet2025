from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings


class Media(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True, default='0')
    description = models.CharField(max_length=200, null=True, blank=True, default='0')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.00)
    url = models.URLField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.name or f"Media {self.pk}"

