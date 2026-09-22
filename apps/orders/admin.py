from django.contrib import admin
from apps.orders.models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["product", "quantity", "price", "cost_display"]
    readonly_fields = ["cost_display", "created_on", "updated_on"]
    @admin.display(description="Total")
    def cost_display(self, obj):
        return f"${obj.cost:.2f}"
    
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "total_display", "status", "created_on", "expires_at"]
    list_display_links = ["id", "user"]
    list_filter = ["status", "created_on", "expires_at"]
    search_fields = ["user__email", "id"]
    readonly_fields = ["total_display", "created_on"]
    inlines = [OrderItemInline]
    ordering = ["-created_on"]
    list_per_page = 20
    
    @admin.display(description="Total")
    def total_display(self, obj):
        return f"${obj.total_cost:.2f}"
    
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "product", "quantity", "price", "cost_display", "created_on"]
    search_fields = ["order__user__email", "product__name"]
    list_filter = ["created_on"]
    readonly_fields = ["cost_display", "created_on", "updated_on"]
    list_per_page = 20
    
    @admin.display(description="Total")
    def cost_display(self, obj):
        return f"${obj.cost:.2f}"
    
    
