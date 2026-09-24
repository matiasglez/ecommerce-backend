from rest_framework import serializers
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment


class OrderItemSerializer(serializers.ModelSerializer):
    cost = serializers.ReadOnlyField()
    product_name = serializers.CharField(
        source="product.name", read_only=True, allow_null=True
    )
    
    class Meta:
        model = OrderItem
        fields = (
            "id", "product", "product_name", "quantity", "price",
            "cost", "created_on", "updated_on"
        )
        read_only_fields = (
            "id", "price", "cost", "created_on", "updated_on"
        )


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)  
    total_cost = serializers.ReadOnlyField()
    payment = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = ("id", "user", "status", "order_items", "total_cost", "created_on", "expires_at", "payment")
        read_only_fields = ("id", "user", "status", "order_items", "total_cost", "created_on", "expires_at")

    def get_payment(self, obj):
        try:
            payment = obj.payment
        except Payment.DoesNotExist:
            return None
        return {
            "id": payment.id,
            "status": payment.status,
            "payment_method": payment.payment_method,
        }
        
        

        
            