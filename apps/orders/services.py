from django.db import transaction
from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.cart.models import Cart
from apps.orders.models import Order, OrderItem
from apps.products.models import Product


class OrderService:
    @staticmethod
    @transaction.atomic
    
    def checkout(user):
        # Obtengo carrito del user
        try:
            cart = Cart.objects.prefetch_related("items__product").get(user=user)
        except Cart.DoesNotExist:
            raise ValidationError({"cart": "No tienes un carrito"})  

        cart_items = list(cart.items.all())
        
        if not cart_items:
            raise ValidationError({"cart": "El carrito esta vacio"})
        
        order = Order.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=15)) # Creamos orden y tiempo de expiracion
        
        for cart_item in cart_items:
            # Bloqueamos producto durante la transaccion
            product = Product.objects.select_for_update().get(id=cart_item.product.id)
            quantity = cart_item.quantity
            
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
        # Vaciamos carrito    
        cart.items.all().delete()
            
        return order
    
    @staticmethod
    @transaction.atomic
    def expire_order(order):
        if order.status != "PENDING":
            return order 
        
        for item in order.order_items.select_related("product"):
            if item.product:
                product = Product.objects.select_for_update().get(id=item.product.id)
                
                product.stock += item.quantity
                product.save(update_fields=["stock"])
                
        order.status = "CANCELLED"
        order.save(update_fields=["status"])
                
        return order
    
    @staticmethod
    def check_expiration(order):
        if order.status == "PENDING" and order.expires_at and timezone.now() >= order.expires_at:
            return OrderService.expire_order(order)
        
        return order