from drf_spectacular.utils import  OpenApiExample, OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema, extend_schema_view
from apps.products.serializers import CategorySerializer, ProductSerializer

# Products

product_schema_view = extend_schema_view(
    list=extend_schema(
        summary="List products",
        description="Return all products. You can filter them by category.",
        parameters=[
            OpenApiParameter(
                name="category_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter products by category ID.",
            ),
        ],
        responses={
            200: ProductSerializer(many=True),
        },
    ),
    create=extend_schema(
        summary="Create product",
        description="Create a new product.",
        request=ProductSerializer,
        responses={
            201: ProductSerializer,
            400: OpenApiResponse(description="Invalid product data."),
            401: OpenApiResponse(description="Authentication required."),
        },
        examples=[
            OpenApiExample(
                "Product example",
                value={
                    "category": 1,
                    "name": "Radar",
                    "description": "Energy drink 500ml",
                    "price": "1500.00",
                    "stock": 10,
                    "is_active": True,
                },
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Get product",
        description="Return a single product by its UUID.",
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(description="Product not found"),
        },
    ),
    update=extend_schema(
        summary="Update product",
        description="Update all fields of an existing product.",
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Invalid product data."),
            404: OpenApiResponse(description="Product not found."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    partial_update=extend_schema(
        summary="Partially update product",
        description="Update one or more fields of an existing product.",
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Invalid product data."),
            404: OpenApiResponse(description="Product not found."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    destroy=extend_schema(
        summary="Delete product",
        description="Delete an existing product.",
        responses={
            204: OpenApiResponse(description="Product deleted successfully."),
            404: OpenApiResponse(description="Product not found."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
)

# Categories

category_schema_view = extend_schema_view(
    list=extend_schema(
        summary="List categories",
        description="Return the main categories and their subcategories.",
        responses={
            200: CategorySerializer(many=True),
        },
    ),
    create=extend_schema(
        summary="Create category",
        description="Create a new category. You can optionally set a parent category.",
        request=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(description="Invalid category data."),
            401: OpenApiResponse(description="Authentication required."),
        },
        examples=[
            OpenApiExample(
                "Category example",
                value={
                    "name": "Beverages",
                    "description": "Different types of beverages.",
                    "parent": None,
                },
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Get category",
        description="Return a single category by its ID.",
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description="Category not found."),
        },
    ),
    update=extend_schema(
        summary="Update category",
        description="Update all fields of an existing category.",
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(description="Invalid category data."),
            404: OpenApiResponse(description="Category not found."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    partial_update=extend_schema(
        summary="Partially update category",
        description="Update one or more fields of an existing category.",
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(description="Invalid category data."),
            404: OpenApiResponse(description="Category not found."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    destroy=extend_schema(
        summary="Delete category",
        description="Delete an existing category.",
        responses={
            204: OpenApiResponse(description="Category deleted successfully."),
            404: OpenApiResponse(description="Category not found."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
)