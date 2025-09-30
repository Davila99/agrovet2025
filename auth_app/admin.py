from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from profiles.models import ProfesionalPerfil, BusinessOwner

# Inlines
class ProfesionalPerfilInline(admin.StackedInline):
    model = ProfesionalPerfil
    can_delete = False
    verbose_name_plural = "Perfil Profesional"

class BusinessOwnerInline(admin.StackedInline):
    model = BusinessOwner
    can_delete = False
    verbose_name_plural = "Perfil de Negocio"

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):  # Hereda de UserAdmin para mantener todo
    list_display = ("phone_number", "full_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Información personal", {"fields": ("full_name", "profile_picture", "bio", "role")}),
        ("Permisos", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "full_name", "role", "password1", "password2", "is_staff", "is_active")}
        ),
    )
    search_fields = ("phone_number", "full_name")
    ordering = ("phone_number",)

    def get_inline_instances(self, request, obj=None):
        inlines = []
        if obj:
            if obj.role in ["veter", "agron"]:
                inlines.append(ProfesionalPerfilInline(self.model, self.admin_site))
            elif obj.role == "duene":
                inlines.append(BusinessOwnerInline(self.model, self.admin_site))
        return inlines
