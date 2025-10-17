from django.contrib import admin
from .models import Media


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "description", "url", "created_at")
	list_display_links = ("id", "name")
	search_fields = ("name", "description")
	readonly_fields = ("created_at",)

