from django.contrib import admin
from .models import SpecialistProfile, BusinessmanProfile, ConsumerProfile


# === CLASES INLINE ===
class SpecialistProfileInline(admin.StackedInline):
    model = SpecialistProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Especialista'
    fk_name = 'user'
    fieldsets = (
        ('Información Profesional', {
            'fields': ('profession', 'experience_years', 'about_us'),
        }),
        ('Puntuación', {
            'fields': ('puntuations', 'point'),
            'classes': ('collapse',),
        }),
        ('Permisos y Funcionalidades', {
            'fields': ('can_give_consultations', 'can_offer_online_services'),
        }),
    )
    readonly_fields = ('puntuations', 'point')


class BusinessmanProfileInline(admin.StackedInline):
    model = BusinessmanProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Empresario'
    fk_name = 'user'
    fieldsets = (
        ('Datos del Negocio', {
            'fields': ('business_name', 'descriptions'),
        }),
        ('Ubicación y Contacto', {
            'fields': ('contact',),
        }),
        ('Funciones', {
            'fields': ('offers_local_products',),
        }),
    )


class ConsumerProfileInline(admin.StackedInline):
    model = ConsumerProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Consumidor'
    fk_name = 'user'
    extra = 0


# === ADMIN DE SPECIALIST ===
from django.contrib import admin
from .models import SpecialistProfile

@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_display', 'profession', 'experience_years',
        'can_give_consultations', 'can_offer_online_services',
        'average_score'
    )
    list_display_links = ('user_display',)
    search_fields = ('user__full_name', 'user__phone_number', 'profession', 'about_us')
    list_filter = ('profession', 'can_give_consultations', 'can_offer_online_services')
    ordering = ('user__full_name',)
    readonly_fields = ('puntuations', 'point', 'user')
    list_select_related = ('user',)  # Optimiza consultas al mostrar user

    fieldsets = (
        ('Usuario Asociado', {
            'fields': ('user',),
        }),
        ('Información Profesional', {
            'fields': ('profession', 'experience_years', 'about_us'),
        }),
        ('Funciones y Puntuación', {
            'fields': ('can_give_consultations', 'can_offer_online_services', 'puntuations', 'point'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Usuario', ordering='user__full_name')
    def user_display(self, obj):
        return obj.user.full_name or obj.user.phone_number

    @admin.display(description='Puntuación Promedio')
    def average_score(self, obj):
        return f"{obj.point:.2f}" if obj.point else "—"



# === ADMIN DE BUSINESSMAN ===
@admin.register(BusinessmanProfile)
class BusinessmanProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user_display', 'contact', 'offers_local_products')
    list_display_links = ('business_name',)
    search_fields = ('business_name', 'user__full_name', 'user__phone_number', 'contact')
    list_filter = ('offers_local_products',)
    readonly_fields = ('user',)
    ordering = ('business_name',)

    fieldsets = (
        ('Usuario Asociado', {'fields': ('user',)}),
        ('Información del Negocio', {'fields': ('business_name', 'descriptions')}),
        ('Ubicación y Contacto', {'fields': ('contact',)}),
        ('Funciones', {'fields': ('offers_local_products',)}),
    )

    @admin.display(description='Usuario', ordering='user__full_name')
    def user_display(self, obj):
        return obj.user.full_name or obj.user.phone_number


# === ADMIN DE CONSUMER ===
@admin.register(ConsumerProfile)
class ConsumerProfileAdmin(admin.ModelAdmin):
    list_display = ('user_display',)
    search_fields = ('user__full_name', 'user__phone_number')
    readonly_fields = ('user',)
    ordering = ('user__full_name',)

    fieldsets = (('Usuario Asociado', {'fields': ('user',)}),)

    @admin.display(description='Usuario', ordering='user__full_name')
    def user_display(self, obj):
        return obj.user.full_name or obj.user.phone_number
