from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from auth_app.models import CustomUser 

class Specialitys(models.Model):
        name = models.CharField(
        max_length=100
        )
        type_choices=[
            ('vet' , 'Veterinario'),
            ('agron' , 'Agronomo'),
            ('both' , 'Ambos'),
        ]
        type=models.CharField(
            max_length=20,
            choices=type_choices,
            default='both'
        )
        
        def __str__(self):
            return f"{self.name} ({self.get_type_display()})"


class BusinessOwner(models.Model):
    user=models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="business_profile"
    )
    def __str__(self):
        return f"{self.user.full_name}"


class ProfesionalPerfil(models.Model):
    year_experience= models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="professional_profile"
    )
    specialitys=models.ManyToManyField(Specialitys,blank=True)
    def __str__(self):
        return f"{self.user.full_name}"
    
