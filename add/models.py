from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL


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

    publisher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="adds"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="adds")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    location_name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    main_image = models.ForeignKey(
        "media.Media", on_delete=models.SET_NULL, null=True, related_name="main_image_for"
    )
    secondary_images = models.ManyToManyField(
        "media.Media", blank=True, related_name="secondary_images_for"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        # Limit secondary images to max 4
        if self.pk:
            count = self.secondary_images.count()
        else:
            # if not saved yet, no related m2m count available — frontend should validate,
            # but we defensively allow checking in save()
            count = 0
        if count > 4:
            raise ValidationError("Solo se permiten hasta 4 imágenes secundarias.")

    def save(self, *args, **kwargs):
        # call full_clean to enforce model validation
        try:
            self.full_clean()
        except ValidationError:
            # re-raise so API/serializers can catch proper messages
            raise
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.publisher}"


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower} sigue a {self.following}"
