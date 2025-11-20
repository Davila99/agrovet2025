from django.contrib import admin
from chat.models import ChatRoom, ChatMessage, ChatMessageReceipt


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_private', 'last_activity', 'created_at')
    list_filter = ('is_private', 'created_at')
    search_fields = ('name',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender_id', 'content', 'timestamp', 'delivered', 'read')
    list_filter = ('timestamp', 'delivered', 'read')
    search_fields = ('content', 'sender_id')


@admin.register(ChatMessageReceipt)
class ChatMessageReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user_id', 'delivered', 'read', 'delivered_at', 'read_at')
    list_filter = ('delivered', 'read', 'delivered_at', 'read_at')
    search_fields = ('user_id',)

