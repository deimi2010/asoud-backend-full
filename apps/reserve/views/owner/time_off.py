from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.market.access import market_access_filter
from apps.reserve.models import Specialist, SpecialistTimeOff
from apps.reserve.serializers.owner import SpecialistTimeOffSerializer
from utils.response import ApiResponse


def _owned_specialists(user, *, write=False):
    return Specialist.objects.filter(
        market_access_filter('market__', user, write=write)
    ).distinct()


class SpecialistTimeOffListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SpecialistTimeOffSerializer

    def get(self, request):
        items = SpecialistTimeOff.objects.filter(
            specialist__in=_owned_specialists(request.user),
        ).select_related('specialist')
        if specialist_id := request.query_params.get('specialist'):
            items = items.filter(specialist_id=specialist_id)
        return Response(ApiResponse(
            success=True,
            code=200,
            data=SpecialistTimeOffSerializer(items, many=True).data,
        ))

    @transaction.atomic
    def post(self, request):
        serializer = SpecialistTimeOffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        specialist = get_object_or_404(
            _owned_specialists(request.user, write=True),
            id=serializer.validated_data['specialist'].id,
        )
        item, created = SpecialistTimeOff.objects.get_or_create(
            specialist=specialist,
            date=serializer.validated_data['date'],
            start=serializer.validated_data.get('start'),
            end=serializer.validated_data.get('end'),
            defaults={'reason': serializer.validated_data.get('reason', '')},
        )
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(ApiResponse(
            success=True, code=code, data=SpecialistTimeOffSerializer(item).data,
        ), status=code)


class SpecialistTimeOffDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SpecialistTimeOffSerializer

    @transaction.atomic
    def delete(self, request, pk):
        item = get_object_or_404(
            SpecialistTimeOff.objects.select_for_update(),
            id=pk,
            specialist__in=_owned_specialists(request.user, write=True),
        )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
