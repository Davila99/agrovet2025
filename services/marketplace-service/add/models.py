from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Add(models.Model):
    CONDITION_CHOICES = [
        ("new", _("Nuevo")),
        ("used", _("Usado")),
        ("semi_new", _("Seminuevo")),
    ]

    STATUS_CHOICES = [
        ("active", _("Activo")),
        ("paused", _("Pausado")),
        ("sold", _("Vendido")),
        ("archived", _("Archivado")),
    ]

    # Store user_id from Auth Service instead of ForeignKey
    publisher_id = models.IntegerField(db_index=True, help_text="ID del usuario en Auth Service")
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="adds")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    location_name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    
    # Store media IDs from Media Service instead of ForeignKey
    main_image_id = models.IntegerField(null=True, blank=True, help_text="ID de media en Media Service")
    secondary_image_ids = models.JSONField(default=list, blank=True, help_text="Lista de IDs de media en Media Service (máx 4)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = 'Anuncio'
        verbose_name_plural = 'Anuncios'

    def clean(self):
        """Validar que no haya más de 4 imágenes secundarias."""
        if len(self.secondary_image_ids) > 4:
            raise ValidationError("Solo se permiten hasta 4 imágenes secundarias.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - Publisher ID {self.publisher_id}"


class Follow(models.Model):
    """Relación de seguimiento entre usuarios."""
    follower_id = models.IntegerField(db_index=True, help_text="ID del seguidor en Auth Service")
    following_id = models.IntegerField(db_index=True, help_text="ID del seguido en Auth Service")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower_id", "following_id")
        verbose_name = 'Seguimiento'
        verbose_name_plural = 'Seguimientos'

    def __str__(self):
        return f"User {self.follower_id} sigue a {self.following_id}"

