from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import mixins, status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from apps.payments.models import Payment
from apps.payments.serializers import PaymentCreateSerializer, PaymentSerializer
from apps.payments.services import PaymentService
from apps.payments.integrations.mercadopago import MercadoPagoClient
from apps.payments.schemas import payment_schema_view



@payment_schema_view
class PaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
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
        responses=PaymentSerializer
    )
    def create_payment(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment, _ = PaymentService.process_payment(
            user=request.user,
            order_id=serializer.validated_data["order_id"],
            payment_method=serializer.validated_data["payment_method"],
        )
        
        response_serializer = PaymentSerializer(payment)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class MercadoPagoWebhookView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Mercado Pago Webhook",
        description="Recibe notificaciones IPN/Webhook de Mercado Pago",
        request=None,
        responses={200: OpenApiResponse(response=None, description="Notificación recibida")},
    )
    def post(self, request, *args, **kwargs):
        # Datos del body o query params
        data = request.data if request.data else request.query_params.dict()

        payment_id = None
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], dict):
                payment_id = data["data"].get("id")
            if not payment_id:
                payment_id = data.get("id")

        # Verificamos la firma de seguridad si esta configurado el webhook secret
        if not MercadoPagoClient.verify_webhook_signature(request, payment_id):
            return Response({"error": "Firma no valida"}, status=status.HTTP_401_UNAUTHORIZED)

        PaymentService.handle_webhook(data)
        return Response(status=status.HTTP_200_OK)

