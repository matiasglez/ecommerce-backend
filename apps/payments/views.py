from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.payments.models import Payment
from apps.payments.schemas import payment_schema_view
from apps.payments.serializers import PaymentCreateSerializer, PaymentSerializer
from apps.payments.services import PaymentService
from apps.payments.integrations.mercadopago import verify_webhook_signature


@payment_schema_view
class PaymentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(order__user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create_payment":
            return PaymentCreateSerializer
        return PaymentSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path="create",
    )
    @extend_schema(
        request=PaymentCreateSerializer,
        responses=PaymentSerializer,
    )
    def create_payment(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment, init_point = PaymentService.process_payment(
            user=request.user,
            order_id=serializer.validated_data["order_id"],
            payment_method=serializer.validated_data["payment_method"],
        )

        response_serializer = PaymentSerializer(payment)
        data = response_serializer.data
        data["init_point"] = init_point

        return Response(data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path="webhook",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    @extend_schema(
        summary="Webhook Mercado Pago",
        request=None,
        responses={
            200: OpenApiResponse(description="Notification received"),
            401: OpenApiResponse(description="Invalid webhook signature"),
        },
    )
    def webhook(self, request):
        topic = (
            request.GET.get("type")
            or request.GET.get("topic")
            or request.data.get("type")
        )
        payment_id = (
            request.GET.get("data.id")
            or request.GET.get("id")
            or (request.data.get("data") or {}).get("id")
        )

        if not verify_webhook_signature(
            x_signature=request.headers.get("x-signature"),
            x_request_id=request.headers.get("x-request-id"),
            data_id=request.GET.get("data.id") or payment_id,
        ):
            return Response(
                {"detail": "Invalid signature"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if topic == "payment" and payment_id:
            PaymentService.handle_mercado_pago_webhook(payment_id)

        return Response(status=status.HTTP_200_OK)


def payment_success(request):
    return HttpResponse(
        "<h1>Pago exitoso</h1><p>Tu orden ha sido procesada correctamente.</p>"
    )


def payment_failure(request):
    return HttpResponse(
        "<h1>Pago fallido</h1><p>Ocurrio un error en la transacción.</p>"
    )


def payment_pending(request):
    return HttpResponse(
        "<h1>Pago pendiente</h1><p>Tu pago está en proceso de revisión.</p>"
    )
