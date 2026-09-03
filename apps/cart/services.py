from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from apps.cart.models import Cart, CartItem
from apps.products.models import Product

class CartService:
    @staticmethod
    def get_or_create_cart(user) -> Cart:
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart
    
    @staticmethod
    def add_product_to_cart(user, product_id: int, quantity: int) -> CartItem:
        cart = CartService.get_or_create_cart(user)
        product = get_object_or_404(Product, id=product_id)
        
        if product.stock < quantity:
            raise ValidationError({"cantidad": "No hay suficiente stock disponible."})
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity}
        )
        
        # Validacion: stock sumando lo que ya tenia en el carrito
        if not created:
            if product.stock < (cart_item.quantity + quantity):
                raise ValidationError({"cantidad": "El total acumulado supera el stock disponible."})
            cart_item.quantity += quantity
            cart_item.save()
        
        return cart_item
    
    @staticmethod
    def remove_product_from_cart(user, product_id: int) -> bool:
        cart = CartService.get_or_create_cart(user)
        deleted_count, _ = cart.items.filter(product_id=product_id).delete()
        if deleted_count == 0:
            raise ValidationError({"error": "El producto no esta en el carrito. "})
        
        return True