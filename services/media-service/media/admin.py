from django.contrib import admin
from media.models import Media


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'url', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

