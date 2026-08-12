import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.price_inquiry.models import Inquiry, InquiryAnswer
from apps.price_inquiry.serializers import (
    InquiryAnswerCreateSerializer,
    InquiryAnswerSerializer,
    InquirySerializer,
)
from utils.response import ApiResponse


logger = logging.getLogger(__name__)


class IsMarketOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.markets.exists()
        )


def _notify_inquiry_owner(user_id, answer_id, detail):
    try:
        async_to_sync(get_channel_layer().group_send)(
            f'user_{user_id}',
            {
                'type': 'send_notification',
                'data': {
                    'type': 'inquiry-answer',
                    'message': 'New Answer To Your Inquiry',
                    'inquiry-answer': {'id': str(answer_id), 'detail': detail},
                },
            },
        )
    except Exception:
        logger.exception('Failed to publish inquiry answer %s', answer_id)


class OwnerInquiryView(views.APIView):
    permission_classes = [IsMarketOwner]


class InquiryListView(OwnerInquiryView):
    def get(self, request):
        inquiries = Inquiry.objects.filter(
            send__isnull=False,
            expiry__gt=timezone.now(),
        ).select_related('user').prefetch_related('images')
        if name := request.GET.get('name'):
            inquiries = inquiries.filter(name__icontains=name)
        if inquiry_type := request.GET.get('type'):
            inquiries = inquiries.filter(type=inquiry_type)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=InquirySerializer(inquiries, many=True).data,
            )
        )


class InquiryDetailView(OwnerInquiryView):
    def get(self, request, pk):
        try:
            inquiry = Inquiry.objects.select_related('user').prefetch_related('images').get(
                id=pk,
                send__isnull=False,
                expiry__gt=timezone.now(),
            )
        except Inquiry.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={'code': 'inquiry_not_found', 'detail': 'Inquiry not found'},
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            ApiResponse(success=True, code=200, data=InquirySerializer(inquiry).data)
        )


class InquiryAnswerCreateView(OwnerInquiryView):
    @transaction.atomic
    def post(self, request):
        serializer = InquiryAnswerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            inquiry = Inquiry.objects.select_for_update().get(
                id=serializer.validated_data['inquiry'],
                send__isnull=False,
                expiry__gt=timezone.now(),
            )
        except Inquiry.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={'code': 'inquiry_not_found', 'detail': 'Active inquiry not found'},
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        if InquiryAnswer.objects.filter(inquiry=inquiry, user=request.user).exists():
            return Response(
                ApiResponse(
                    success=False,
                    code=409,
                    error={'code': 'duplicate_answer', 'detail': 'Inquiry already answered'},
                ),
                status=status.HTTP_409_CONFLICT,
            )
        answer = serializer.save(inquiry=inquiry, user=request.user)
        transaction.on_commit(
            lambda: _notify_inquiry_owner(
                inquiry.user_id,
                answer.id,
                answer.detail,
            )
        )
        return Response(
            ApiResponse(
                success=True,
                code=201,
                data=InquiryAnswerSerializer(answer).data,
            ),
            status=status.HTTP_201_CREATED,
        )


class InquiryAnswerListView(OwnerInquiryView):
    def get(self, request):
        answers = (
            InquiryAnswer.objects.filter(user=request.user)
            .select_related('inquiry', 'user')
            .prefetch_related('images', 'inquiry__images')
        )
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=InquiryAnswerSerializer(answers, many=True).data,
            )
        )


class InquiryAnswerDetailView(OwnerInquiryView):
    def get(self, request, pk):
        try:
            answer = (
                InquiryAnswer.objects.select_related('inquiry', 'user')
                .prefetch_related('images', 'inquiry__images')
                .get(id=pk, user=request.user)
            )
        except InquiryAnswer.DoesNotExist:
            return Response(
                ApiResponse(success=False, code=404, error='Inquiry Answer Not Found'),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            ApiResponse(success=True, code=200, data=InquiryAnswerSerializer(answer).data)
        )
