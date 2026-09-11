from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from apps.orders.serializers import OrderSerializer

order_schema_view = extend_schema_view(
    list=extend_schema(
        summary="List user orders",
        description="Return all orders belonging to the authenticated user ordered by creation date.",
        responses={
            200: OrderSerializer(many=True),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    ),
    retrieve=extend_schema(
        summary="Get order details",
        description="Return details and items of a specific order by ID.",
        responses={
            200: OrderSerializer,
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            404: OpenApiResponse(description="Order not found."),
        },
    ),
    checkout=extend_schema(
        summary="Process checkout",
        description=(
            "Create a new order from the user's shopping cart."
            "The order starts with PENDING status and has an expiration time."
        ),
        request=None,
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(description="The shopping cart is empty or there is not enough stock."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
)
