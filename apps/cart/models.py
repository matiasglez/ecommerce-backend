from django.db import models
from django.conf import settings
from apps.products.models import Product
from django.core.validators import MinValueValidator

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_on = models.DateTimeField(auto_now_add=True)
    
    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())
    

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)]) # Explicito quantity >= 1
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_product_per_cart",
            )
        ]
        
    @property
    def subtotal(self):
        return self.product.price * self.quantity