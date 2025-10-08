from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from auth_app.models import User  


class SpecialistProfile(models.Model):
    """ Detalles del rol Especialista. """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='specialist_profile')
    
    profession = models.CharField(max_length=100, help_text="Veterinario, Agronomo, Sistemas, Etc...")
    experience_years = models.IntegerField(default=0)
    about_us = models.TextField(blank=True, verbose_name="Detalles/Acerca de")
    
    # Puntuaciones
    puntuations = models.FloatField(default=0.0)
    point = models.IntegerField(default=0)

    # Funcionalidades
    can_give_consultations = models.BooleanField(default=False)
    can_offer_online_services = models.BooleanField(default=False)
    
    # FK a las imágenes de perfil/portafolio
    # Nota: Las imágenes se definen en la app 'marketplace'

    def __str__(self):
        return f"Especialista: {self.user.username}"

class BusinessmanProfile(models.Model):
    """ Detalles del rol Businessman (Dueño de negocio). """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='businessman_profile')
    
    business_name = models.CharField(max_length=255)
    descriptions = models.TextField()
    contact = models.CharField(max_length=255) # Email o teléfono de contacto del negocio
    
    # Ubicación del negocio
    location_description = models.CharField(max_length=255, blank=True)
    
    # Funcionalidades
    offers_local_products = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Negocio: {self.business_name}"

class ConsumerProfile(models.Model):
    """ Detalles del rol Consumer (Usuario final). """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='consumer_profile')
    # Por ahora, solo contiene la FK a User, pero se mantiene para futuras expansiones.

    def __str__(self):
        return f"Consumer: {self.user.username}"