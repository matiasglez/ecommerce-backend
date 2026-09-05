from rest_framework import serializers
from apps.orders.models import Order, OrderItem
from apps.orders.services import OrderService

class OrderItemSerializer(serializers.ModelSerializer):
    cost = serializers.ReadOnlyField()
    
    class Meta:
        model = OrderItem
        fields = (
            "id", "product", "quantity", "price",
            "cost", "created_on", "updated_on"
        )
        read_only_fields = (
            "id", "price", "cost", "created_on", "updated_on"
        )
        
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor que 0")
        return value


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True)  
    total_cost = serializers.ReadOnlyField()
    
    class Meta:
        model = Order
        fields = ("id", "user", "status", "order_items", "total_cost", "created_on",)
        read_only_fields = ("id", "user", "status", "order_items", "total_cost", "created_on",)
        
    
    def create(self, validated_data):
        order_items = validated_data.pop("order_items", None)
        
        if not order_items:
            raise serializers.ValidationError({"order_items": "Debes agregar al menos un producto a la orden"})
        
        user = self.context["request"].user 
        
        return OrderService.create_order(
            user=user,
            order_items=order_items,
        )
        
            