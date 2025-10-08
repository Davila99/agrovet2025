from django.contrib import admin
from .models import SpecialistProfile, BusinessmanProfile, ConsumerProfile

# --- Inlines (Recomendado para integrar en el User Admin) ---

# Clase Inline para el perfil de Especialista (para usar en UserAdmin)
class SpecialistProfileInline(admin.StackedInline):
    model = SpecialistProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Especialista'
    fieldsets = (
        (None, {
            'fields': ('profession', 'experience_years', 'about_us')
        }),
        ('Puntuación', {
            'fields': ('puntuations', 'point'),
            'classes': ('collapse',),
        }),
        ('Funcionalidades', {
            'fields': ('can_give_consultations', 'can_offer_online_services'),
        }),
    )
    readonly_fields = ('puntuations', 'point')
    
# Clase Inline para el perfil de Negocio (para usar en UserAdmin)
class BusinessmanProfileInline(admin.StackedInline):
    model = BusinessmanProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Negocio'
    fields = ('business_name', 'descriptions', 'contact', 'location_description', 'offers_local_products')

# Clase Inline para el perfil de Consumidor (para usar en UserAdmin)
class ConsumerProfileInline(admin.StackedInline):
    model = ConsumerProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Consumidor'
    # Como ConsumerProfile no tiene campos propios, lo dejamos simple.


# --- ModelAdmins (Para registro individual si se prefiere) ---

@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = ('user_username', 'profession', 'experience_years', 'can_give_consultations')
    search_fields = ('user__username', 'profession')
    list_filter = ('can_give_consultations', 'can_offer_online_services', 'profession')
    readonly_fields = ('puntuations', 'point', 'user') # 'user' es readonly porque es la clave primaria
    
    fieldsets = (
        (None, {
            'fields': ('user', 'profession', 'experience_years', 'about_us')
        }),
        ('Funcionalidades y Puntuación', {
            'fields': ('can_give_consultations', 'can_offer_online_services', 'puntuations', 'point'),
        }),
    )

    @admin.display(description='Usuario')
    def user_username(self, obj):
        # Muestra el nombre de usuario de la instancia de User
        return obj.user.username


@admin.register(BusinessmanProfile)
class BusinessmanProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user_username', 'contact', 'offers_local_products')
    search_fields = ('business_name', 'user__username', 'contact')
    list_filter = ('offers_local_products',)
    readonly_fields = ('user',)

    fieldsets = (
        (None, {
            'fields': ('user', 'business_name', 'contact', 'location_description', 'descriptions')
        }),
        ('Funcionalidades', {
            'fields': ('offers_local_products',),
        }),
    )
    
    @admin.display(description='Usuario')
    def user_username(self, obj):
        return obj.user.username


@admin.register(ConsumerProfile)
class ConsumerProfileAdmin(admin.ModelAdmin):
    list_display = ('user_username',)
    search_fields = ('user__username',)
    readonly_fields = ('user',)

    @admin.display(description='Usuario')
    def user_username(self, obj):
        return obj.user.username