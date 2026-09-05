from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.orders.models import Order, OrderItem


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(user, order_items):
        order = Order.objects.create(user=user)
        
        for item_data in order_items:
            product = item_data["product"]
            quantity = item_data["quantity"]
            
            if quantity > product.stock:
                raise ValidationError({"quantity": f"No hay suficiente stock para {product.name}"})
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product.price,
            )
            
            product.stock -= quantity
            product.save(update_fields=["stock"])
            
        return order