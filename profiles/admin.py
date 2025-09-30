from django.contrib import admin
from auth_app.models import CustomUser 
from .models import ProfesionalPerfil,BusinessOwner,Specialitys

@admin.register(Specialitys)
class SpecialitysAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')

@admin.register(ProfesionalPerfil)
class ProfesionalPerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'year_experience')

@admin.register(BusinessOwner)
class BusinessOwnerAdmin(admin.ModelAdmin):
    list_display = ('user',)