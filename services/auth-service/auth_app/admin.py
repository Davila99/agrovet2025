from django.contrib import admin
from auth_app.models import User, PhoneResetCode


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone_number', 'full_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined')
    search_fields = ('phone_number', 'full_name', 'last_name')
    readonly_fields = ('date_joined',)


@admin.register(PhoneResetCode)
class PhoneResetCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'code', 'created_at', 'is_valid')
    list_filter = ('created_at',)
    search_fields = ('user__phone_number', 'code')
    readonly_fields = ('created_at',)

