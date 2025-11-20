from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class Media(models.Model):
    """
    Modelo para almacenar información de archivos multimedia.
    Los archivos físicos se almacenan en Supabase Storage.
    """
    name = models.CharField(max_length=200, null=True, blank=True, default='0')
    description = models.CharField(max_length=200, null=True, blank=True, default='0')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.00)
    url = models.URLField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Generic relation para permitir asociar media con diferentes modelos
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Media'
        verbose_name_plural = 'Media'

    def __str__(self):
        return self.name or f"Media {self.pk}"

