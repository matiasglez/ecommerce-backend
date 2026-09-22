from django.contrib import admin
from apps.cart.models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ["product", "quantity", "subtotal_display"]
    readonly_fields = ["subtotal_display"]
    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        return f"${obj.subtotal:.2f}"
    
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "total_display", "created_on"]
    search_fields = ["user__email", "items__product__name"]
    list_filter = ["created_on"]
    readonly_fields = ["total_display"]
    inlines = [CartItemInline]
    list_per_page = 20
    
    @admin.display(description="Total")
    def total_display(self, obj):
        return f"${obj.total:.2f}"
    
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["cart", "product", "quantity", "subtotal_display"]
    search_fields = ["cart__user__email", "product__name"]
    list_filter = ["product"]
    readonly_fields = ["subtotal_display"]
    
    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        return f"${obj.subtotal:.2f}"
    
    list_per_page = 20