from django.contrib import admin
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile


@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'profession', 'can_give_consultations')
    list_filter = ('profession', 'can_give_consultations')
    search_fields = ('user_id', 'profession')


@admin.register(BusinessmanProfile)
class BusinessmanProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'business_name', 'offers_local_products')
    list_filter = ('offers_local_products',)
    search_fields = ('user_id', 'business_name')


@admin.register(ConsumerProfile)
class ConsumerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id')
    search_fields = ('user_id',)

