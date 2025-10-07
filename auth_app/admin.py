from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from auth_app.models import User
from profiles.models import SpecialistProfile, BusinessmanProfile

class SpecialistProfileInline(admin.StackedInline):
    model = SpecialistProfile
    can_delete = False
    verbose_name_plural = "Perfil Profesional"

class BusinessmanProfileInline(admin.StackedInline):
    model = BusinessmanProfile
    can_delete = False
    verbose_name_plural = "Perfil de Negocio"

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("phone_number", "full_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    ordering = ("phone_number",)
    search_fields = ("phone_number", "full_name")

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Información personal", {"fields": ("full_name", "last_name", "role", "latitude", "longitude", "profile_picture", "bio")}),
        ("Permisos", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Fechas importantes", {"fields": ("date_joined",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "full_name", "role", "password1", "password2", "is_staff", "is_active")
        }),
    )

    def get_inline_instances(self, request, obj=None):
        inlines = []
        if obj:
            if obj.role == "Specialist":
                inlines.append(SpecialistProfileInline(self.model, self.admin_site))
            elif obj.role == "businessman":
                inlines.append(BusinessmanProfileInline(self.model, self.admin_site))
        return inlines
