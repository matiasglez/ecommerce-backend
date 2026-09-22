from django.contrib import admin
from apps.payments.models import Payment, PaymentTransaction

class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    fields = ["transaction_id", "amount", "status", "created_on"]
    readonly_fields = ["transaction_id", "amount", "created_on"]
    
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "amount", "status", "payment_method", "created_on", "updated_on"]
    list_display_links = ["id", "order"]
    list_filter = ["status", "payment_method", "created_on"]
    search_fields = ["order__user__email", "order__id"]
    readonly_fields = ["created_on", "updated_on"]
    inlines = [PaymentTransactionInline]
    ordering = ["-created_on"]
    list_per_page = 20
    
@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "payment", "transaction_id", "amount", "status", "created_on"]
    list_display_links = ["id", "transaction_id"]
    list_filter = ["status", "created_on"]
    search_fields = ["payment__order__user__email", "payment__order__user__email"]
    readonly_fields = ["transaction_id", "amount", "created_on"]
    ordering = ["-created_on"]
    list_per_page = 20
