from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        unique=True,
        validators=[RegexValidator(regex=r'^\+?\d{7,15}$', message="Ingrese un número válido")]
    )
    
    ROLE_CHOICES = (
        ("veter", "Veterinario"),
        ("agron", "Agrónomo"),
        ("duani", "Dueño de animales"),
        ("duene", "Dueño de negocio"),
    )
    role = models.CharField(_("rol"), max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    
    full_name = models.CharField(_("nombre completo"), max_length=150, blank=True)
    profile_picture = models.ImageField(_("foto de perfil"), upload_to="profiles/", blank=True, null=True)
    bio = models.TextField(_("Sobre mi"), blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.full_name or self.phone_number} ({self.get_role_display() if self.role else 'Sin rol'})"