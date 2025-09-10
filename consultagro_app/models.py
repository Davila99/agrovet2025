from django.contrib import admin
from .models import (
    User, Specialty, UserSpecialty, Profile, WorkImage,
    Chat, Message, Call, Notification,
    Ad, AdImage
)

# --------------------------
# 1. User
# --------------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "phone_number", "role", "is_online", "is_active", "created_at")
    search_fields = ("full_name", "phone_number")
    list_filter = ("role", "is_active", "is_online", "created_at")
    ordering = ("-created_at",)


# --------------------------
# 2. Especialidades
# --------------------------
@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type")
    list_filter = ("type",)
    search_fields = ("name",)


@admin.register(UserSpecialty)
class UserSpecialtyAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "specialty")
    list_filter = ("specialty",)
    search_fields = ("user__full_name", "specialty__name")


# --------------------------
# 3. Perfil
# --------------------------
class WorkImageInline(admin.TabularInline):
    model = Profile.work_images.through
    extra = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "years_experience")
    search_fields = ("user__full_name",)
    inlines = [WorkImageInline]


@admin.register(WorkImage)
class WorkImageAdmin(admin.ModelAdmin):
    list_display = ("id", "image", "created_at")
    ordering = ("-created_at",)


# --------------------------
# 4. Chats y mensajes
# --------------------------
class MessageInline(admin.TabularInline):
    model = Message
    extra = 1


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "started_at", "ended_at", "rating")
    filter_horizontal = ("participants",)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "sender", "text", "created_at")
    search_fields = ("text", "sender__full_name")
    ordering = ("-created_at",)


# --------------------------
# 5. Llamadas
# --------------------------
@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ("id", "caller", "receiver", "type", "started_at", "ended_at")
    list_filter = ("type", "started_at")
    search_fields = ("caller__full_name", "receiver__full_name")


# --------------------------
# 6. Notificaciones
# --------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "seen", "created_at")
    list_filter = ("seen",)
    search_fields = ("title", "user__full_name")
    ordering = ("-created_at",)


# --------------------------
# 7. Anuncios
# --------------------------
class AdImageInline(admin.TabularInline):
    model = AdImage
    extra = 1


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "location", "created_at")
    search_fields = ("title", "description", "user__full_name")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
    inlines = [AdImageInline]


@admin.register(AdImage)
class AdImageAdmin(admin.ModelAdmin):
    list_display = ("id", "ad", "image")
