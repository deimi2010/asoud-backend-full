import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.price_inquiry.models import Inquiry, InquiryAnswer
from apps.price_inquiry.serializers import (
    InquiryAnswerSerializer,
    InquiryCreateSerializer,
    InquiryExpireSetSerializer,
    InquiryImageListSerializer,
    InquirySendSetSerializer,
    InquirySerializer,
    InquiryUpdateSerializer,
)
from utils.response import ApiResponse


logger = logging.getLogger(__name__)


def _notify_owners(inquiry_id, inquiry_name):
    try:
        async_to_sync(get_channel_layer().group_send)(
            'owners',
            {
                'type': 'send_notification',
                'data': {
                    'type': 'inquiry',
                    'message': 'New Inquiry Added',
                    'inquiry': {'id': str(inquiry_id), 'name': inquiry_name},
                },
            },
        )
    except Exception:
        logger.exception('Failed to publish inquiry %s', inquiry_id)


def _not_found():
    return Response(
        ApiResponse(success=False, code=404, error='Inquiry Not Found'),
        status=status.HTTP_404_NOT_FOUND,
    )


class AuthenticatedInquiryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]


class InquiryCreateView(AuthenticatedInquiryView):
    serializer_class = InquiryCreateSerializer
    def post(self, request):
        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save(user=request.user)
        return Response(
            ApiResponse(
                success=True,
                code=201,
                data=InquirySerializer(inquiry).data,
            ),
            status=status.HTTP_201_CREATED,
        )


class InquiryUpdateView(AuthenticatedInquiryView):
    serializer_class = InquiryUpdateSerializer
    @transaction.atomic
    def put(self, request, pk=None):
        try:
            inquiry = Inquiry.objects.select_for_update().get(
                id=pk,
                user=request.user,
            )
        except Inquiry.DoesNotExist:
            return _not_found()
        if inquiry.send is not None:
            return Response(
                ApiResponse(success=False, code=409, error='Sent inquiry is immutable'),
                status=status.HTTP_409_CONFLICT,
            )
        serializer = InquiryUpdateSerializer(inquiry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ApiResponse(success=True, code=200, data=InquirySerializer(inquiry).data)
        )


class InquiryDeleteView(AuthenticatedInquiryView):
    serializer_class = InquirySerializer
    @transaction.atomic
    def delete(self, request, pk=None):
        try:
            inquiry = Inquiry.objects.select_for_update().get(
                id=pk,
                user=request.user,
            )
        except Inquiry.DoesNotExist:
            return _not_found()
        if inquiry.send is not None:
            return Response(
                ApiResponse(success=False, code=409, error='Sent inquiry is immutable'),
                status=status.HTTP_409_CONFLICT,
            )
        inquiry.delete()
        return Response(
            ApiResponse(success=True, code=200, data={}),
            status=status.HTTP_200_OK,
        )

    post = delete


class InquirySendSetView(AuthenticatedInquiryView):
    serializer_class = InquirySendSetSerializer
    @transaction.atomic
    def post(self, request, pk):
        try:
            inquiry = Inquiry.objects.select_for_update().get(
                id=pk,
                user=request.user,
            )
        except Inquiry.DoesNotExist:
            return _not_found()
        if inquiry.expiry <= timezone.now():
            return Response(
                ApiResponse(success=False, code=400, error='Inquiry has expired'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = InquirySendSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if inquiry.send is None:
            inquiry.send = serializer.validated_data['send']
            inquiry.save(update_fields=['send', 'updated_at'])
            transaction.on_commit(lambda: _notify_owners(inquiry.id, inquiry.name))
        return Response(
            ApiResponse(success=True, code=200, data=InquirySerializer(inquiry).data)
        )


class InquiryImageUploadView(AuthenticatedInquiryView):
    serializer_class = InquiryImageListSerializer
    @transaction.atomic
    def post(self, request, pk):
        try:
            inquiry = Inquiry.objects.select_for_update().get(
                id=pk,
                user=request.user,
            )
        except Inquiry.DoesNotExist:
            return _not_found()
        if inquiry.send is not None:
            return Response(
                ApiResponse(success=False, code=409, error='Sent inquiry is immutable'),
                status=status.HTTP_409_CONFLICT,
            )
        serializer = InquiryImageListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(inquiry=inquiry)
        return Response(
            ApiResponse(success=True, code=200, data=InquirySerializer(inquiry).data)
        )


class InquiryExpiryRenewView(AuthenticatedInquiryView):
    serializer_class = InquiryExpireSetSerializer
    @transaction.atomic
    def post(self, request, pk):
        try:
            inquiry = Inquiry.objects.select_for_update().get(
                id=pk,
                user=request.user,
            )
        except Inquiry.DoesNotExist:
            return _not_found()
        serializer = InquiryExpireSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry.expiry = serializer.validated_data['expiry']
        inquiry.save(update_fields=['expiry', 'updated_at'])
        return Response(
            ApiResponse(success=True, code=200, data=InquirySerializer(inquiry).data)
        )


class InquiryListView(AuthenticatedInquiryView):
    serializer_class = InquirySerializer
    def get(self, request):
        inquiries = (
            Inquiry.objects.filter(user=request.user)
            .select_related('user')
            .prefetch_related('images')
        )
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=InquirySerializer(inquiries, many=True).data,
            )
        )


class InquiryDetailView(AuthenticatedInquiryView):
    serializer_class = InquirySerializer
    def get(self, request, pk):
        try:
            inquiry = Inquiry.objects.select_related('user').prefetch_related('images').get(
                id=pk,
                user=request.user,
            )
        except Inquiry.DoesNotExist:
            return _not_found()
        return Response(
            ApiResponse(success=True, code=200, data=InquirySerializer(inquiry).data)
        )


class InquiryAnswerListView(AuthenticatedInquiryView):
    serializer_class = InquiryAnswerSerializer
    def get(self, request, inquiry_pk):
        if not Inquiry.objects.filter(id=inquiry_pk, user=request.user).exists():
            return _not_found()
        answers = (
            InquiryAnswer.objects.filter(inquiry_id=inquiry_pk)
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


class InquiryAnswerDetailView(AuthenticatedInquiryView):
    serializer_class = InquiryAnswerSerializer
    def get(self, request, pk, inquiry_pk):
        try:
            answer = (
                InquiryAnswer.objects.select_related('inquiry', 'user')
                .prefetch_related('images', 'inquiry__images')
                .get(
                    id=pk,
                    inquiry_id=inquiry_pk,
                    inquiry__user=request.user,
                )
            )
        except InquiryAnswer.DoesNotExist:
            return Response(
                ApiResponse(success=False, code=404, error='Inquiry Answer Not Found'),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            ApiResponse(success=True, code=200, data=InquiryAnswerSerializer(answer).data)
        )
