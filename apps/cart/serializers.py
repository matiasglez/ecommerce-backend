from rest_framework import serializers
from apps.cart.models import Cart, CartItem
from apps.products.models import Product

class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price"]
        

class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)
    subtotal = serializers.ReadOnlyField()
    
    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "subtotal"]
        

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.ReadOnlyField()
    
    class Meta:
        model = Cart
        fields = ["id", "items", "total"]
        

class AddItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField(help_text="ID unico del producto a añadir.")
    quantity = serializers.IntegerField(default=1, min_value=1, help_text="Cantidad de unidades (Mínimo 1).")