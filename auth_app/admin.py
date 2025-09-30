from django.contrib import admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
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


admin.site.register(CustomUser, CustomUserAdmin)