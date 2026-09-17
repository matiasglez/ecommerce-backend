from rest_framework import serializers
from apps.payments.models import Payment, PaymentTransaction


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ("id", "transaction_id", "amount", "status", "created_on")
        read_only_fields = ("id", "transaction_id", "amount", "status", "created_on")
        

class PaymentSerializer(serializers.ModelSerializer):
    transactions = PaymentTransactionSerializer(many=True, read_only=True)
    init_point = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Payment
        fields = ("id", "order", "amount", "status", "payment_method",
                "transactions", "init_point", "created_on", "updated_on")
        read_only_fields = ("id", "order", "amount", "status", "payment_method",
                "transactions", "init_point", "created_on", "updated_on")

    

class PaymentCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(help_text="ID de la orden que quieres pagar")
    payment_method = serializers.ChoiceField(choices=Payment.PaymentMethod.choices, default=Payment.PaymentMethod.MOCK)