from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from apps.payments.serializers import PaymentCreateSerializer, PaymentSerializer

payment_schema_view = extend_schema_view(
    list=extend_schema(
        summary="List user payments",
        description="Return all payments belonging to the authenticated user.",
        responses={
            200: PaymentSerializer(many=True),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    ),
    retrieve=extend_schema(
        summary="Get payment details",
        description="Return details of a specific payment by ID.",
        responses={
            200: PaymentSerializer,
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            404: OpenApiResponse(description="Payment not found."),
        },
    ),
    create_payment=extend_schema(
        summary="Process payment",
        description="Create a payment for an order using the selected payment method.",
        request=PaymentCreateSerializer,
        responses={
            201: PaymentSerializer,
            400: OpenApiResponse(description="Invalid payment data or payment method."),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            404: OpenApiResponse(description="Order not found."),
        },
        examples=[
            OpenApiExample(
                "Mock payment example",
                value={
                    "order_id": 1,
                    "payment_method": "MOCK",
                },
            )
        ],
    ),
)