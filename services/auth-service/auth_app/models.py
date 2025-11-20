from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .managers import CustomUserManager
from django.dispatch import receiver
from django.db.models.signals import post_delete
from django.conf import settings
from datetime import timedelta
import sys
import os

# Add common to path for utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from auth_app.utils.supabase_utils import delete_image_from_supabase


class User(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de usuario personalizado con phone_number como identificador único.
    """
    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        unique=True,
        validators=[RegexValidator(regex=r'^\+?\d{7,15}$', message="Ingrese un número válido")]
    )
    
    ROLE_CHOICES = (
        ("Specialist", "Especialista"),
        ("businessman", "Empresario"),
        ("consumer", "Consumidor"),
    )
    role = models.CharField(_("rol"), max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    full_name = models.CharField(_("nombre"), max_length=150, blank=True)
    last_name = models.CharField(_("apellido"), max_length=150, blank=True)
    profile_picture = models.CharField(
        _("foto de perfil"),
        max_length=500,
        blank=True,
        null=True,
        help_text="URL de la imagen en Supabase"
    )
    bio = models.TextField(_("Sobre mi"), blank=True, null=True)
    
    # Campos de ubicación global
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ['full_name']

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.full_name or self.phone_number} ({self.get_role_display() if self.role else 'Sin rol'})"


@receiver(post_delete, sender=User)
def delete_user_profile_picture(sender, instance, **kwargs):
    """
    Elimina la imagen del bucket de Supabase cuando se elimina el usuario.
    """
    if instance.profile_picture:
        delete_image_from_supabase(instance.profile_picture)


class PhoneResetCode(models.Model):
    """
    Códigos temporales enviados por SMS para recuperar/actualizar contraseña vía número de teléfono.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='phone_reset_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['code', 'created_at'])]
        verbose_name = 'Código de Reset'
        verbose_name_plural = 'Códigos de Reset'

    def is_valid(self):
        """Verifica si el código aún es válido (10 minutos)."""
        return timezone.now() < self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"PhoneResetCode(user={self.user}, code={self.code})"

