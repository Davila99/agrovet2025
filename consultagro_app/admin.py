from django.contrib import admin
from .models import (
    User, VetProfile, AgronomoProfile, PropietarioProfile,
    Specialty, UserSpecialty, WorkImage, Chat, Message,
    Block, Call, Notification, Ad, AdImage
)

# --------------------------
# 1. Usuarios
# --------------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "phone_number", "role", "is_online", "created_at")
    search_fields = ("full_name", "phone_number")
    list_filter = ("role", "is_online", "created_at")
    ordering = ("-created_at",)


# --------------------------
# 2. Perfiles
# --------------------------
@admin.register(VetProfile)
class VetProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "years_experience")
    search_fields = ("user__full_name",)

@admin.register(AgronomoProfile)
class AgronomoProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "years_experience")
    search_fields = ("user__full_name",)

@admin.register(PropietarioProfile)
class PropietarioProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__full_name",)


# --------------------------
# 3. Especialidades
# --------------------------
@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type")
    list_filter = ("type",)
    search_fields = ("name",)

@admin.register(UserSpecialty)
class UserSpecialtyAdmin(admin.ModelAdmin):
    list_display = ("user", "specialty")
    search_fields = ("user__full_name", "specialty__name")
    list_filter = ("specialty__type",)


# --------------------------
# 4. Imágenes de trabajos
# --------------------------
@admin.register(WorkImage)
class WorkImageAdmin(admin.ModelAdmin):
    list_display = ("user", "image_url", "created_at")
    search_fields = ("user__full_name",)


# --------------------------
# 5. Chats y mensajes
# --------------------------
@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "user1", "user2", "started_at", "ended_at", "rating")
    search_fields = ("user1__full_name", "user2__full_name")
    list_filter = ("started_at",)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "sender", "message", "created_at")
    search_fields = ("message", "sender__full_name")
    list_filter = ("created_at",)


# --------------------------
# 6. Bloqueos
# --------------------------
@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ("blocker", "blocked")
    search_fields = ("blocker__full_name", "blocked__full_name")


# --------------------------
# 7. Llamadas
# --------------------------
@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ("id", "caller", "receiver", "type", "started_at", "ended_at")
    list_filter = ("type", "started_at")
    search_fields = ("caller__full_name", "receiver__full_name")


# --------------------------
# 8. Notificaciones
# --------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message", "seen", "created_at")
    list_filter = ("seen", "created_at")
    search_fields = ("user__full_name", "message")


# --------------------------
# 9. Anuncios
# --------------------------
@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "location", "created_at")
    search_fields = ("title", "description", "user__full_name")
    list_filter = ("created_at",)


@admin.register(AdImage)
class AdImageAdmin(admin.ModelAdmin):
    list_display = ("ad", "image_url")
    search_fields = ("ad__title",)
