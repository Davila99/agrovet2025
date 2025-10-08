from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .managers import CustomUserManager # Importación necesaria
from django.dispatch import receiver
from auth_app.utils.supabase_utils import delete_image_from_supabase
from django.db.models.signals import post_delete



class User(AbstractBaseUser, PermissionsMixin):
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
    
    # Campos de ubicación global (según el esquema original)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)

    is_staff = models.BooleanField(default=False) # Cambié a False por defecto
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ['full_name'] # Puedes agregar campos que pides al registrar

    objects = CustomUserManager()

    def __str__(self):
        # Usamos full_name o phone_number ya que 'username' no existe en AbstractBaseUser
        return f"{self.full_name or self.phone_number} ({self.get_role_display() if self.role else 'Sin rol'})"
    
# ✅ MOVER ESTE BLOQUE FUERA DE LA CLASE
@receiver(post_delete, sender=User)
def delete_user_profile_picture(sender, instance, **kwargs):
    """
    Elimina la imagen del bucket de Supabase cuando se elimina el usuario.
    """
    if instance.profile_picture:
        delete_image_from_supabase(instance.profile_picture)