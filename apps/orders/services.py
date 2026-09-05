from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.orders.models import Order, OrderItem
from apps.products.models import Product


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(user, order_items):
        order = Order.objects.create(user=user)
        
        for item_data in order_items:
            product_id = item_data["product"].id
            quantity = item_data["quantity"]
            
            # Bloqueamos producto durante la transaccion
            product = Product.objects.select_for_update().get(id=product_id)
            
            if quantity > product.stock:
                raise ValidationError({
                    "quantity": (
                        f"No hay suficiente stock para {product.name}"
                        f"Stock disponible: {product.stock}"
                    )
                })
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product.price,
            )
            
            product.stock -= quantity
            product.save(update_fields=["stock"])
            
        return order