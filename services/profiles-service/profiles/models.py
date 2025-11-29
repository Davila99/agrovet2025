from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.fields import GenericRelation
import sys
import os

# Note: User model is in Auth Service, we store user_id as IntegerField
# Media model is in Media Service, we store media_id references


class SpecialistProfile(models.Model):
    """Detalles del rol Especialista."""
    user_id = models.IntegerField(unique=True, db_index=True, help_text="ID del usuario en Auth Service")
    
    PROFESSION_CHOICES = [
        ('Veterinario', 'Veterinario'),
        ('Agrónomo', 'Agrónomo'),
        ('Zootecnista', 'Zootecnista'),
    ]
    profession = models.CharField(
        max_length=100, 
        choices=PROFESSION_CHOICES,
        help_text="Solo se permiten: Veterinario, Agrónomo o Zootecnista"
    )
    experience_years = models.IntegerField(default=0)
    about_us = models.TextField(blank=True, verbose_name="Detalles/Acerca de")
    
    # Puntuación y reseñas
    puntuations = models.FloatField(default=0.0)
    point = models.IntegerField(default=0)

    # Funcionalidades
    can_give_consultations = models.BooleanField(default=False)
    can_offer_online_services = models.BooleanField(default=False)
    
    # Work images stored as JSON array of media_ids (from Media Service)
    work_images_ids = models.JSONField(default=list, blank=True, help_text="Lista de IDs de media en Media Service")
    
    # Documentos de verificación (media_ids desde Media Service)
    verification_title_id = models.IntegerField(null=True, blank=True, help_text="ID del media del título profesional")
    verification_student_card_id = models.IntegerField(null=True, blank=True, help_text="ID del media del carnet de estudiante")
    verification_graduation_letter_id = models.IntegerField(null=True, blank=True, help_text="ID del media de la carta de egresado")

    class Meta:
        verbose_name = 'Perfil Especialista'
        verbose_name_plural = 'Perfiles Especialistas'

    def __str__(self):
        return f"Especialista: user_id={self.user_id}"


class BusinessmanProfile(models.Model):
    """Detalles del rol Businessman (Dueño de negocio)."""
    user_id = models.IntegerField(unique=True, db_index=True, help_text="ID del usuario en Auth Service")
    
    BUSINESS_TYPE_CHOICES = [
        ('Agroveterinaria', 'Agroveterinaria'),
        ('Empresa Agropecuaria', 'Empresa Agropecuaria'),
    ]
    business_type = models.CharField(
        max_length=100,
        choices=BUSINESS_TYPE_CHOICES,
        default='Agroveterinaria',
        help_text="Tipo de negocio: Agroveterinaria o Empresa Agropecuaria"
    )
    
    business_name = models.CharField(max_length=255)
    descriptions = models.TextField()
    contact = models.CharField(max_length=255)  # Email o teléfono de contacto del negocio
    
    # Funcionalidades
    offers_local_products = models.BooleanField(default=True)

    # Products and services stored as JSON array of media_ids
    products_and_services_ids = models.JSONField(default=list, blank=True, help_text="Lista de IDs de media en Media Service")
    
    class Meta:
        verbose_name = 'Perfil Empresario'
        verbose_name_plural = 'Perfiles Empresarios'

    def __str__(self):
        return f"Negocio: {self.business_name} (user_id={self.user_id})"


class ConsumerProfile(models.Model):
    """Detalles del rol Consumer (Usuario final)."""
    user_id = models.IntegerField(unique=True, db_index=True, help_text="ID del usuario en Auth Service")
    # Por ahora, solo contiene la FK a User, pero se mantiene para futuras expansiones.

    class Meta:
        verbose_name = 'Perfil Consumidor'
        verbose_name_plural = 'Perfiles Consumidores'

    def __str__(self):
        return f"Consumer: user_id={self.user_id}"

