from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from auth_app.models import CustomUser 

class ProfesionalPerfil(models.Model):
    year_experience= models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    user = models.OnetoOneField(
        CustomUser,
        on_delete=models.CASCADE
    )
   
    def __str__(self):
        return (self)
    
    
