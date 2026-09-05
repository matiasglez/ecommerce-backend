from django.db import models
from django.utils.functional import cached_property
from django.conf import settings
from apps.products.models import Product


class Order(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("CANCELLED", "Cancelled"),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    created_on = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    
    class Meta:
        ordering = ["-created_on"] # Ordenes mas nuevas
    
    def __str__(self):
        return f"Orden {self.id} - Usuario: {self.user.email} - Estado: {self.status}"
    
    
    @cached_property
    def total_cost(self):
        """Monto total de todos los items en la orden"""
        return sum(item.cost for item in self.order_items.all())
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name="product_orders") # SI el producto se borra, no se borra el historial de compras
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    quantity = models.PositiveIntegerField(default=1)
    
    # Precio unitario exacto en el momento de la compra
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ("-created_on",)
        
        constraints = [models.UniqueConstraint(fields=["order", "product"], name="unique_product_per_order",)]
    
    def __str__(self):
        product_name = self.product.name if self.product else "Eliminado"
        return f"Item {self.id} - Producto: {product_name} - Cantidad: {self.quantity}"
    
    @cached_property
    def cost(self):
        """Costo total de este item"""
        return self.quantity * self.price