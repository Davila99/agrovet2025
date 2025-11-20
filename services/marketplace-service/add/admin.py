from django.contrib import admin
from add.models import Add, Category, Follow


@admin.register(Add)
class AddAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'publisher_id', 'price', 'status', 'created_at')
    list_filter = ('status', 'condition', 'category', 'created_at')
    search_fields = ('title', 'description', 'publisher_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower_id', 'following_id', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('follower_id', 'following_id')

