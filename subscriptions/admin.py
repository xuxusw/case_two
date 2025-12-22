from django.contrib import admin

# Register your models here.

from .models import SubscriptionPlan, UserSubscription, Transaction, PromoCode, RefundPolicy

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'auto_renew')
    list_filter = ('status', 'auto_renew', 'plan')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('start_date',) # чтобы нельзя было случайно подделать дату начала

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'transaction_type', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('user__username', 'external_id')
    readonly_fields = ('created_at',)

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'max_uses', 'used_count', 'is_active', 'valid_to')
    list_filter = ('is_active', 'valid_to')
    search_fields = ('code',)

@admin.register(RefundPolicy)
class RefundPolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'full_refund_days', 'partial_refund_enabled')