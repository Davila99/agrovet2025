from django.contrib import admin
from .models import SpecialistProfile, BusinessmanProfile, ConsumerProfile
from django.contrib.contenttypes.admin import GenericTabularInline
from media.models import Media
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.contenttypes.models import ContentType


class SpecialistProfileForm(forms.ModelForm):
    work_images_select = forms.ModelMultipleChoiceField(
        queryset=Media.objects.all(),
        required=False,
        widget=FilteredSelectMultiple('Media', is_stacked=False)
    )

    class Meta:
        model = SpecialistProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            ct = ContentType.objects.get_for_model(SpecialistProfile)
            self.fields['work_images_select'].initial = Media.objects.filter(content_type=ct, object_id=self.instance.pk)

    def save(self, commit=True):
        instance = super().save(commit)
        media_qs = self.cleaned_data.get('work_images_select')
        if media_qs:
            ct = ContentType.objects.get_for_model(SpecialistProfile)
            for m in media_qs:
                m.content_type = ct
                m.object_id = instance.pk
                m.save()
        return instance


class BusinessmanProfileForm(forms.ModelForm):
    products_select = forms.ModelMultipleChoiceField(
        queryset=Media.objects.all(),
        required=False,
        widget=FilteredSelectMultiple('Media', is_stacked=False)
    )

    class Meta:
        model = BusinessmanProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            ct = ContentType.objects.get_for_model(BusinessmanProfile)
            self.fields['products_select'].initial = Media.objects.filter(content_type=ct, object_id=self.instance.pk)

    def save(self, commit=True):
        instance = super().save(commit)
        media_qs = self.cleaned_data.get('products_select')
        if media_qs:
            ct = ContentType.objects.get_for_model(BusinessmanProfile)
            for m in media_qs:
                m.content_type = ct
                m.object_id = instance.pk
                m.save()
        return instance


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
            'fields': ('contact', 'location_description'),
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


# Inline genérico para manejar Media desde los perfiles (work_images / products_and_services)
class MediaInline(GenericTabularInline):
    model = Media
    ct_field = 'content_type'
    ct_fk_field = 'object_id'
    readonly_fields = ('created_at', 'url')
    extra = 1


# === ADMIN DE SPECIALIST ===
from django.contrib import admin
from .models import SpecialistProfile

@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    form = SpecialistProfileForm
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
    inlines = (MediaInline,)

    @admin.display(description='Work images')
    def work_images_list(self, obj):
        ct = ContentType.objects.get_for_model(SpecialistProfile)
        medias = Media.objects.filter(content_type=ct, object_id=obj.pk)
        return ', '.join([m.url or str(m.id) for m in medias])

    readonly_fields = ('work_images_list',) + readonly_fields

    @admin.display(description='Usuario', ordering='user__full_name')
    def user_display(self, obj):
        return obj.user.full_name or obj.user.phone_number

    @admin.display(description='Puntuación Promedio')
    def average_score(self, obj):
        return f"{obj.point:.2f}" if obj.point else "—"



# === ADMIN DE BUSINESSMAN ===
@admin.register(BusinessmanProfile)
class BusinessmanProfileAdmin(admin.ModelAdmin):
    form = BusinessmanProfileForm
    list_display = ('business_name', 'user_display', 'contact', 'offers_local_products')
    list_display_links = ('business_name',)
    search_fields = ('business_name', 'user__full_name', 'user__phone_number', 'contact')
    list_filter = ('offers_local_products',)
    readonly_fields = ('user',)
    ordering = ('business_name',)

    fieldsets = (
        ('Usuario Asociado', {'fields': ('user',)}),
        ('Información del Negocio', {'fields': ('business_name', 'descriptions')}),
        ('Ubicación y Contacto', {'fields': ('contact', 'location_description')}),
        ('Funciones', {'fields': ('offers_local_products',)}),
    )
    inlines = (MediaInline,)

    @admin.display(description='Products/Services')
    def products_list(self, obj):
        ct = ContentType.objects.get_for_model(BusinessmanProfile)
        medias = Media.objects.filter(content_type=ct, object_id=obj.pk)
        return ', '.join([m.url or str(m.id) for m in medias])
    readonly_fields = ('products_list',) + readonly_fields

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
