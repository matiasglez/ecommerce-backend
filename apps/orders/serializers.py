from rest_framework import serializers
from apps.orders.models import Order, OrderItem


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


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)  
    total_cost = serializers.ReadOnlyField()
    
    class Meta:
        model = Order
        fields = ("id", "user", "status", "order_items", "total_cost", "created_on",)
        read_only_fields = ("id", "user", "status", "order_items", "total_cost", "created_on",)
        

        
            