from drf_spectacular.utils import OpenApiResponse, OpenApiParameter, OpenApiTypes, OpenApiExample, extend_schema, extend_schema_view
from apps.cart.serializers import AddItemSerializer, CartSerializer

cart_schema_view = extend_schema_view(
    list=extend_schema(
        summary="Get active cart",
        description="Returns the user's active shopping cart with all items and total price.",
        responses={
            200: CartSerializer,
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    add_item=extend_schema(
        summary="Add item to cart",
        description="Adds a product or increases its quantity in the cart.",
        request=AddItemSerializer,
        parameters=[
            OpenApiParameter(
                name="pk",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="UUID of the product to remove.",
            )
        ],
        responses={
            200: OpenApiResponse(description="Product added successfully."),
            400: OpenApiResponse(description="Invalid data or not enough stock."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Product not found."),
        },
        examples=[
            OpenApiExample(
                "Add item example",
                value={
                    "product_id": "a3bb189e-8bf9-3888-9912-ace4e6543002",
                    "quantity": 2,
                },
            )
        ],
    ),
    delete_item=extend_schema(
        summary="Remove item from cart",
        description="Deletes a product completely from the shopping cart using its product UUID.",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="UUID of the product to remove.",)           
            ],        
        responses={
            204: OpenApiResponse(description="Product removed successfully."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Product or item not found in cart."),
        },
    ),
)