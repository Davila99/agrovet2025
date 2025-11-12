from django.contrib import admin
from .models import Category, Add, Follow
from django.utils.html import format_html


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Add)
class AddAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'publisher_display', 'price', 'category', 'status', 'created_at')
    list_filter = ('status', 'condition', 'category')
    search_fields = ('title', 'description', 'publisher__full_name', 'location_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('publisher', 'main_image')
    filter_horizontal = ('secondary_images',)
    list_select_related = ('publisher', 'category', 'main_image')

    fieldsets = (
        (None, {'fields': ('publisher', 'title', 'description', 'price', 'category', 'condition', 'status')}),
        ('Media', {'fields': ('main_image', 'secondary_images', 'main_image_preview')}),
        ('Ubicación', {'fields': ('location_name', 'latitude', 'longitude')}),
        ('Tiempos', {'fields': ('created_at', 'updated_at')}),
    )

    def publisher_display(self, obj):
        try:
            return obj.publisher.full_name or str(obj.publisher)
        except Exception:
            return str(obj.publisher)
    publisher_display.short_description = 'Publisher'

    @admin.display(description='Main image')
    def main_image_preview(self, obj):
        if obj.main_image:
            url = getattr(obj.main_image, 'file_url', None) or getattr(obj.main_image, 'url', None) or None
            if url:
                return format_html('<img src="{}" style="max-height:120px; max-width:240px; object-fit:cover;" />', url)
            return str(obj.main_image)
        return '—'


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following', 'created_at')
    search_fields = ('follower__full_name', 'following__full_name', 'follower__phone_number', 'following__phone_number')
    raw_id_fields = ('follower', 'following')
