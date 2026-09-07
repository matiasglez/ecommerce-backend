from django.db import transaction
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
        
        order = Order.objects.create(user=user) # Creamos orden
        
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